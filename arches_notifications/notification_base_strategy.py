from __future__ import annotations

import re
from typing import TYPE_CHECKING

from arches.app.models import models
from arches.app.models.resource import Resource

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.http import HttpRequest

    from .notification_config import NotificationConfig


# Matches {name} and {value:<node_alias>} tokens in a rule's message.
# Alias chars match what Arches allows: lowercase, digits, underscore, hyphen.
_MESSAGE_TOKEN_RE = re.compile(
    r"\{(name|value:([a-z0-9_\-]+))\}", re.IGNORECASE
)


class NotificationStrategy:
    def __init__(
        self,
        tile: models.Tile,
        request: HttpRequest,
        user: User | None,
        config: NotificationConfig,
    ) -> None:
        self.request = request
        self.tile = tile
        self.resource_instance_id = str(tile.resourceinstance.resourceinstanceid)
        self.user = user
        self.config = config
        self.name = self._get_resource_name()
        self.notification: models.Notification | None = None

    def send_notification(self) -> None:
        if self.name is None:
            # require_prefix filter explicitly rejected this resource.
            return

        message = self._render_message(self.config.message)

        recipients = self._get_recipients()
        if not recipients:
            return

        self.notification = self._create_notification(message)
        for user in recipients:
            self.notify_user(user)

    def extra_context(self) -> dict:
        """Override in a subclass to inject extra notification context fields.

        Called just before the Notification record is saved, so the returned
        dict is merged into the context. Use this to add fields like
        ``response_slug`` without needing to mutate a saved object.

        Example::

            def extra_context(self) -> dict:
                return {"response_slug": "licensing-workflow"}
        """
        return {}

    def _get_resource_name(self) -> str | None:
        """Resolve the resource display name, applying the rule's optional
        prefix/suffix processing.

        Returns:
            - the processed name string (possibly empty) → fire as normal.
            - ``None`` only when ``require_prefix`` is set and the raw name
              doesn't match → send_notification treats this as an explicit
              skip signal.
        """
        raw = Resource.objects.get(pk=self.resource_instance_id).displayname()
        if not raw:
            return ""  # no display name yet — fire anyway with empty {name}
        return self.config.resource_name.apply(raw)

    def _create_notification(self, message: str) -> models.Notification:
        resource_link = self.request.build_absolute_uri(
            f"/report/{self.resource_instance_id}"
        )
        context: dict = {
            "resource_instance_id": self.resource_instance_id,
            "resource_id": self.name,
            # Always present so the bell-dropdown "Open resource" button can
            # render. Email branch overrides email_link from config when set.
            "resource_link": resource_link,
            # Stored under `link` so core's notification viewmodel forwards
            # it to the bell template (no JS override needed). Our template
            # override at views/components/notification.htm differentiates
            # URL-style links (this) from core's exportid strings.
            "link": resource_link,
        }
        if self.config.email:
            email_link = (
                self.request.build_absolute_uri(self.config.link_path)
                if self.config.link_path
                else resource_link
            )
            context.update({
                "greeting": message,
                "salutation": "Hi",
                "username": "",
                "email": "",
                "email_link": email_link,
                "button_text": self.config.button_text,
            })
        context.update(self.extra_context())
        notification = models.Notification(
            message=message,
            context=context,
            notiftype_id=self.config.notiftype_id,
        )
        notification.save()
        return notification

    def _get_recipients(self) -> list[User]:
        from django.contrib.auth.models import User
        return list(
            User.objects.filter(groups__name__in=self.config.groups_to_notify)
            .exclude(pk=self.user.pk if self.user else None)
            .distinct()
        )

    def notify_user(self, user: User) -> None:
        if self.config.email:
            notif = self._clone_notification_for_user(user)
        else:
            notif = self.notification
        models.UserXNotification(notif=notif, recipient=user).save()

    def _clone_notification_for_user(self, user: User) -> models.Notification:
        context = {**self.notification.context, "username": user.username, "email": user.email}
        notif = models.Notification(
            message=self.notification.message,
            context=context,
            notiftype_id=self.notification.notiftype_id,
        )
        notif.save()
        return notif

    def get_domain_value_string(
        self, value_id: str, node_id: str, language: str | None = None
    ) -> str | None:
        from django.conf import settings
        lang = language or getattr(settings, "LANGUAGE_CODE", "en")
        node = models.Node.objects.filter(pk=node_id).first()
        options = node.config.get("options", [])
        return next(
            (opt.get("text", {}).get(lang) for opt in options if opt.get("id") == value_id),
            None,
        )

    def _render_message(self, raw: str) -> str:
        """Substitute ``{name}`` and ``{value:<node_alias>}`` tokens in a
        rule message. Unknown aliases are left literal so the configurator
        can see the typo rather than getting an empty string."""
        def replace(match: re.Match) -> str:
            token = match.group(1)
            if token.lower() == "name":
                return self.name or ""
            alias = match.group(2)
            value = self._resolve_node_value_by_alias(alias)
            return value if value is not None else match.group(0)
        return _MESSAGE_TOKEN_RE.sub(replace, raw)

    def _resolve_node_value_by_alias(self, alias: str) -> str | None:
        """Look up the saved tile value for a node by its alias and coerce
        to a display string. Returns None if the alias doesn't resolve to
        a node on this tile's graph."""
        graph_id = self.tile.resourceinstance.graph_id
        node = (
            models.Node.objects.filter(alias=alias, graph_id=graph_id)
            .only("nodeid", "datatype")
            .first()
        )
        if not node:
            return None
        raw_value = (self.tile.data or {}).get(str(node.nodeid))
        return self._coerce_value_to_string(raw_value, node)

    def _coerce_value_to_string(self, value, node) -> str:
        """Best-effort stringify of a tile value for use in a notification
        message. Handles the common datatypes; falls back to str() for
        anything unexpected."""
        from django.conf import settings
        if value is None:
            return ""
        if isinstance(value, bool):
            return "Yes" if value else "No"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str):
            # Could be a concept/domain-value UUID for some datatypes.
            if node.datatype == "domain-value":
                resolved = self.get_domain_value_string(value, str(node.nodeid))
                return resolved or value
            return value
        if isinstance(value, list):
            return ", ".join(
                self._coerce_value_to_string(v, node) for v in value
            )
        if isinstance(value, dict):
            # i18n string: {"en": {"value": "..."}, ...} or {"en": "...", ...}
            lang = getattr(settings, "LANGUAGE_CODE", "en")
            primary = value.get(lang) or value.get(lang.split("-")[0])
            if isinstance(primary, dict):
                return str(primary.get("value", ""))
            if primary is not None:
                return str(primary)
            return ""
        return str(value)
