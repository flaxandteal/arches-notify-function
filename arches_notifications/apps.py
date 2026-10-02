from django.apps import AppConfig


class ArchesNotificationsConfig(AppConfig):
    name = "arches_notifications"
    is_arches_application = True

    def ready(self):
        from django.db.models.signals import post_save

        from arches_notifications.transaction_events import record_created_resource

        # No sender filter: Arches saves resources through the Resource proxy,
        # whose saves are not sent with sender=ResourceInstance.
        post_save.connect(record_created_resource, dispatch_uid="arches_notifications_created")
