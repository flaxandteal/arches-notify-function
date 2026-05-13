from arches.app.functions.base import BaseFunction
from .notification_config import NotificationConfig
from .notification_base_strategy import NotificationStrategy


class NotifyFunction(BaseFunction):
    """Concrete, installable Arches function that sends notifications on tile save.

    Tier 1 — config-driven (no subclass needed):
        Attach this function to a graph in the Arches graph designer and
        configure nodegroup triggers via the UI. Config is stored as JSON on
        the FunctionXGraph record and deserialized into NotificationConfig
        instances at runtime.

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

        In the strategy, set extra context fields before calling super():
            class ReportStrategy(NotificationStrategy):
                def send_notification(self):
                    self.notification.context["response_slug"] = "licensing-workflow"
                    self.notification.save()
                    super().send_notification()

    Legacy (strategy_registry still supported):
        Existing subclasses that define strategy_registry continue to work
        unchanged. New code should use strategy_overrides instead.
    """

    # Tier 2: map nodegroup alias → NotificationStrategy subclass.
    # Config is still read from self.config (the DB); only the strategy class
    # is swapped in. Falls back to NotificationStrategy for unmapped aliases.
    strategy_overrides: dict = {}

    # --- Legacy support ---------------------------------------------------
    # Pre-redesign subclasses used strategy_registry to hardcode both config
    # and strategy in one place. Still works; prefer strategy_overrides for
    # new code.
    strategy_registry: dict = {}
    _resolved_registry_cache = None
    # ----------------------------------------------------------------------

    # Per-class cache of nodegroup alias → UUID string, populated lazily.
    _alias_uuid_cache: dict = {}

    def post_save(self, tile, request, context):
        if type(self).strategy_registry:
            self._legacy_post_save(tile, request)
            return

        nodegroup_id = str(tile.nodegroup_id)
        graph_slug = tile.resourceinstance.graph.slug
        user = self._get_user(request)

        for config in self._configs_for_tile(nodegroup_id, graph_slug):
            strategy_class = type(self).strategy_overrides.get(
                config.nodegroup_alias, NotificationStrategy
            )
            strategy_class(tile, request, user, config).send_notification()

    # ------------------------------------------------------------------
    # Config-driven helpers
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Legacy path (strategy_registry)
    # ------------------------------------------------------------------

    def _legacy_post_save(self, tile, request):
        registry = self._get_resolved_registry(tile)
        node_group_id = str(tile.nodegroup_id)
        if node_group_id not in registry:
            return
        entry = registry[node_group_id]
        strategy_class = entry.get("strategy", NotificationStrategy)
        user = self._get_user(request)
        strategy_class(tile, request, user, entry["config"]).send_notification()

    def _get_resolved_registry(self, tile):
        cls = type(self)
        if cls._resolved_registry_cache is None:
            graph_slug = tile.resourceinstance.graph.slug
            cls._resolved_registry_cache = self._resolve_legacy_aliases(
                cls.strategy_registry, graph_slug
            )
        return cls._resolved_registry_cache

    def _resolve_legacy_aliases(self, registry, graph_slug):
        from arches.app.models.models import Node
        resolved = {}
        for alias, entry in registry.items():
            node = Node.objects.filter(alias=alias, graph__slug=graph_slug).first()
            resolved[str(node.nodegroup_id) if node else alias] = entry
        return resolved

    # ------------------------------------------------------------------
    # Shared util
    # ------------------------------------------------------------------

    @staticmethod
    def _get_user(request):
        if request and getattr(request.user, "is_authenticated", False):
            return request.user
        return None
