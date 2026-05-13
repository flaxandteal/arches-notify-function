from __future__ import annotations

from typing import TYPE_CHECKING

from arches.app.functions.base import BaseFunction

from arches_notifications.notification_config import NotificationConfig
from arches_notifications.notification_base_strategy import NotificationStrategy

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.http import HttpRequest


# Read by `python manage.py fn register --source <path>/notify_function.py`.
# triggering_nodegroups stays [] so Arches fires post_save for every nodegroup;
# per-nodegroup routing happens in _configs_for_tile.
details = {
    "functionid": "f5a0e2b0-1c3e-4a8f-9d2c-1a2b3c4d5e6f",
    "name": "Notify on tile save",
    "type": "node",
    "description": "Sends notifications to configured groups when matching tiles are saved.",
    "defaultconfig": {"triggering_nodegroups": [], "nodegroups": []},
    "classname": "NotifyFunction",
    "component": "views/components/functions/notify",
}


class NotifyFunction(BaseFunction):
    """Concrete, installable Arches function that sends notifications on tile save.

    Tier 1 — config-driven (no subclass needed):
        Attach this function to a graph in the Arches graph designer and
        configure nodegroup triggers via the UI. Config is stored as JSON on
        the FunctionXGraph record and deserialized into NotificationConfig
        instances at runtime.

    Config storage:
        On the FunctionXGraph row, set ``config.triggering_nodegroups = []`` so
        Arches' Tile dispatcher (arches.app.models.tile._getFunctionClassInstances)
        fires post_save for every nodegroup on the graph. Per-nodegroup routing
        is then done internally against ``config.nodegroups`` — the rule list
        edited via NotificationConfigPanel. Keeping triggering_nodegroups empty
        means the panel's rule list is the single source of truth and the two
        don't drift out of sync.

    Tier 2 — strategy overrides (subclass for custom logic):
        Subclass NotifyFunction and declare strategy_overrides to plug in
        custom NotificationStrategy subclasses for specific nodegroups. Config
        (which nodegroups to watch, groups, message, etc.) still comes from
        the UI / DB — only the send logic is overridden.

        Example:
            class NotifyExcavation(NotifyFunction):
                strategy_overrides = {
                    "cur-e-decision": CurEDecisionStrategy,
                    "report":         ReportStrategy,
                }

        In the strategy, add extra context fields via extra_context():
            class ReportStrategy(NotificationStrategy):
                def extra_context(self) -> dict:
                    return {"response_slug": "licensing-workflow"}

        Or override send_notification() for full control:
            class ReportStrategy(NotificationStrategy):
                def send_notification(self) -> None:
                    stage = self._get_stage()
                    self.config.groups_to_notify = ["assessors" if stage == "Draft" else "reviewers"]
                    super().send_notification()
    """

    # Tier 2: map nodegroup alias → NotificationStrategy subclass.
    # Config is still read from self.config (the DB); only the strategy class
    # is swapped in. Falls back to NotificationStrategy for unmapped aliases.
    strategy_overrides: dict[str, type[NotificationStrategy]] = {}

    # Per-class cache of (alias, graph_slug) → UUID string, populated lazily.
    _alias_uuid_cache: dict[tuple[str, str], str] = {}

    def post_save(self, tile, request: HttpRequest, context: dict | None = None) -> None:
        nodegroup_id = str(tile.nodegroup_id)
        graph_slug = tile.resourceinstance.graph.slug
        user = self._get_user(request)

        for config in self._configs_for_tile(nodegroup_id, graph_slug):
            strategy_class = type(self).strategy_overrides.get(
                config.nodegroup_alias, NotificationStrategy
            )
            strategy_class(tile, request, user, config).send_notification()

    def _configs_for_tile(self, nodegroup_id: str, graph_slug: str) -> list[NotificationConfig]:
        entries = (self.config or {}).get("nodegroups", [])
        matched = []
        for entry in entries:
            alias = entry.get("nodegroup_alias", "")
            resolved = self._resolve_alias(alias, graph_slug)
            if resolved == nodegroup_id:
                matched.append(NotificationConfig.from_dict(entry))
        return matched

    def _resolve_alias(self, alias: str, graph_slug: str) -> str:
        """Return the nodegroup UUID string for a nodegroup alias, cached per class."""
        cls = type(self)
        cache_key = (alias, graph_slug)
        if cache_key not in cls._alias_uuid_cache:
            from arches.app.models.models import Node
            node = Node.objects.filter(alias=alias, graph__slug=graph_slug).first()
            cls._alias_uuid_cache[cache_key] = str(node.nodegroup_id) if node else alias
        return cls._alias_uuid_cache[cache_key]

    @staticmethod
    def _get_user(request: HttpRequest) -> User | None:
        if request and getattr(request.user, "is_authenticated", False):
            return request.user
        return None
