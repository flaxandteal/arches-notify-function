import uuid

from django.db import models


class NotificationFailure(models.Model):
    """An email that could not be sent after every retry."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    notification_type = models.TextField(blank=True)
    resource_instance_id = models.TextField(blank=True)
    recipient = models.TextField()
    reason = models.TextField()
    attempts = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["-created"]
