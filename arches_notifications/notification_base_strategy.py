import logging

from arches.app.models import models
from arches.app.models.resource import Resource


class NotificationStrategy:
    def __init__(self, tile, request, user, config):
        self.request = request
        self.tile = tile
        self.resource_instance_id = str(tile.resourceinstance.resourceinstanceid)
        self.user = user
        self.config = config
        self.name = self._get_resource_name()
        self.notification: models.Notification | None = None

    def send_notification(self):
        if self.name is None:
            # resource_name.require_prefix filter failed
            return

        message = self.config.message.format(name=self.name)

        if self._is_duplicate(message):
            logging.debug(
                "Skipping duplicate notification for resource %s", self.resource_instance_id
            )
            return

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
        raw = Resource.objects.get(pk=self.resource_instance_id).displayname()
        return self.config.resource_name.apply(raw) if raw else raw

    def _is_duplicate(self, message: str) -> bool:
        """Return True if the most recent notification for this resource and
        type has an identical message — i.e. nothing has changed."""
        latest = (
            models.Notification.objects.filter(
                context__resource_instance_id=self.resource_instance_id,
                notiftype_id=self.config.notiftype_id,
            )
            .order_by("-created")
            .first()
        )
        return latest is not None and latest.message == message

    def _create_notification(self, message: str) -> models.Notification:
        context = {
            "resource_instance_id": self.resource_instance_id,
            "resource_id": self.name,
        }
        if self.config.email:
            context.update({
                "greeting": message,
                "salutation": "Hi",
                "username": "",
                "email": "",
                "link": self.request.build_absolute_uri(self.config.link_path),
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

    def _get_recipients(self) -> list:
        from django.contrib.auth.models import User
        return list(
            User.objects.filter(groups__name__in=self.config.groups_to_notify)
            .exclude(pk=self.user.pk if self.user else None)
            .distinct()
        )

    def notify_user(self, user) -> None:
        if self.config.email:
            notif = self._clone_notification_for_user(user)
        else:
            notif = self.notification
        models.UserXNotification(notif=notif, recipient=user).save()

    def _clone_notification_for_user(self, user) -> models.Notification:
        context = {**self.notification.context, "username": user.username, "email": user.email}
        notif = models.Notification(
            message=self.notification.message,
            context=context,
            notiftype_id=self.notification.notiftype_id,
        )
        notif.save()
        return notif

    def get_domain_value_string(self, value_id: str, node_id: str, language: str | None = None) -> str | None:
        from django.conf import settings
        lang = language or getattr(settings, "LANGUAGE_CODE", "en")
        node = models.Node.objects.filter(pk=node_id).first()
        options = node.config.get("options", [])
        return next(
            (opt.get("text", {}).get(lang) for opt in options if opt.get("id") == value_id),
            None,
        )
