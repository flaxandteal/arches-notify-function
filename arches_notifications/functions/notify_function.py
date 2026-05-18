from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from arches.app.functions.base import BaseFunction

from arches_notifications.notification_config import NotificationConfig
from arches_notifications.notification_base_strategy import NotificationStrategy

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.http import HttpRequest

logger = logging.getLogger(__name__)


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

    # Per-class caches of (alias, graph_slug) → UUID, populated lazily.
    # Staleness handled via _graph_publication (invalidate on re-publish);
    # _CACHE_MAX_ENTRIES is a backstop against pathological growth only.
    _CACHE_MAX_ENTRIES = 500
    _alias_uuid_cache: dict[tuple[str, str], str] = {}
    _node_uuid_cache: dict[tuple[str, str], str] = {}
    # graph_slug → last-seen GraphModel.publication_id (as str), per class.
    _graph_publication: dict[str, str] = {}

    @classmethod
    def _check_publication(cls, graph_slug: str) -> None:
        """Drop a graph's cached entries if its publication id changed
        (i.e. it was re-published). One indexed lookup per call, far
        lighter than the Node join it guards."""
        from arches.app.models.models import GraphModel
        pub = (
            GraphModel.objects.filter(slug=graph_slug, source_identifier__isnull=True)
            .values_list("publication_id", flat=True)
            .first()
        )
        pub = str(pub) if pub else ""
        if cls._graph_publication.get(graph_slug) != pub:
            cls._invalidate_graph_cache(graph_slug)
            cls._graph_publication[graph_slug] = pub

    @classmethod
    def _cache_put(cls, cache: dict[tuple[str, str], str], key: tuple[str, str], value: str) -> str:
        """Insert into a per-class cache, clearing it first if it is at
        _CACHE_MAX_ENTRIES. Full clear over LRU: entries are cheap to
        recompute and this only fires under pathological growth."""
        if len(cache) >= cls._CACHE_MAX_ENTRIES:
            cache.clear()
        cache[key] = value
        return value

    @classmethod
    def _invalidate_graph_cache(cls, graph_slug: str) -> None:
        """Drop all cached alias→UUID entries for one graph."""
        for cache in (cls._alias_uuid_cache, cls._node_uuid_cache):
            for key in [k for k in cache if k[1] == graph_slug]:
                del cache[key]

    def after_function_save(self, function_x_graph, request) -> None:
        """Fired by the function manager after the FunctionXGraph row is saved.
        Upserts a NotificationType per rule so each rule shows up as its own
        opt-out entry in Arches' user-notification preferences UI, and the
        per-rule emailtemplate is honoured at send time. Deletion of types
        for removed rules is handled by the Vue panel calling the
        delete-notification-type endpoint when the trash icon is clicked."""
        from arches.app.models.models import NotificationType
        config = function_x_graph.config or {}
        graph_name = getattr(function_x_graph.graph, "name", "") or ""
        for rule in config.get("nodegroups", []):
            type_id = rule.get("notiftype_id")
            if not type_id:
                continue
            nodegroup_alias = rule.get("nodegroup_alias") or "rule"
            default_name = f"{graph_name} — {nodegroup_alias}".strip(" —")
            NotificationType.objects.update_or_create(
                typeid=type_id,
                defaults={
                    "name": rule.get("notification_name") or default_name,
                    "emailtemplate": rule.get("emailtemplate") or "email/general_notification.htm",
                    "emailnotify": bool(rule.get("email")),
                    "webnotify": True,
                },
            )

    def save(self, tile, request: HttpRequest, context: dict | None = None) -> None:
        """Pre-save hook. Stash the prior tile data on the tile instance only
        if at least one matching rule wants change detection (i.e. has
        node_alias set). Otherwise we skip the DB lookup entirely."""
        nodegroup_id = str(tile.nodegroup_id)
        graph_slug = tile.resourceinstance.graph.slug
        configs = self._configs_for_tile(nodegroup_id, graph_slug)
        if not any(c.node_alias for c in configs):
            return
        from arches.app.models.models import TileModel
        existing = TileModel.objects.filter(pk=tile.pk).first()
        tile._notify_pre_save_data = existing.data if existing else {}

    def post_save(self, tile, request: HttpRequest, context: dict | None = None) -> None:
        nodegroup_id = str(tile.nodegroup_id)
        graph_slug = tile.resourceinstance.graph.slug
        user = self._get_user(request)

        for config in self._configs_for_tile(nodegroup_id, graph_slug):
            if config.node_alias and not self._node_changed(tile, config.node_alias, graph_slug):
                continue
            strategy_class = type(self).strategy_overrides.get(
                config.nodegroup_alias, NotificationStrategy
            )
            try:
                strategy_class(tile, request, user, config).send_notification()
            except Exception:
                logger.exception(
                    "Notification rule failed for nodegroup_alias=%s on tile %s",
                    config.nodegroup_alias,
                    getattr(tile, "pk", None),
                )

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
        cls._check_publication(graph_slug)
        cache_key = (alias, graph_slug)
        if cache_key not in cls._alias_uuid_cache:
            from arches.app.models.models import Node
            node = Node.objects.filter(alias=alias, graph__slug=graph_slug).first()
            return cls._cache_put(
                cls._alias_uuid_cache, cache_key, str(node.nodegroup_id) if node else alias
            )
        return cls._alias_uuid_cache[cache_key]

    def _resolve_node_alias(self, alias: str, graph_slug: str) -> str:
        """Return the node UUID string for a node alias, cached per class."""
        cls = type(self)
        cls._check_publication(graph_slug)
        cache_key = (alias, graph_slug)
        if cache_key not in cls._node_uuid_cache:
            from arches.app.models.models import Node
            node = Node.objects.filter(alias=alias, graph__slug=graph_slug).first()
            return cls._cache_put(
                cls._node_uuid_cache, cache_key, str(node.nodeid) if node else alias
            )
        return cls._node_uuid_cache[cache_key]

    def _node_changed(self, tile, node_alias: str, graph_slug: str) -> bool:
        """True if the named node's value differs from the pre-save data."""
        node_id = self._resolve_node_alias(node_alias, graph_slug)
        before = (getattr(tile, "_notify_pre_save_data", {}) or {}).get(node_id)
        after = (tile.data or {}).get(node_id)
        return before != after

    @staticmethod
    def _get_user(request: HttpRequest) -> User | None:
        if request and getattr(request.user, "is_authenticated", False):
            return request.user
        return None
