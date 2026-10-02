"""Email delivery for notification rules: retried in the background when a
Celery worker is available, recorded and reported to admins when it fails."""
import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string

from arches.app.models import models
from arches.app.utils.task_management import check_if_celery_available

from arches_notifications.models import NotificationFailure

logger = logging.getLogger(__name__)

FAILURE_NOTIFICATION_TYPE_ID = "5d0f3c2e-8b1a-4c6e-9f7d-3e2a1b4c5d60"  # migration 0003
MAX_RETRIES = 3


def queue_email(notification_id, address: str, username: str = "") -> None:
    if check_if_celery_available():
        send_notification_email.delay(str(notification_id), address, username)
        return
    # ponytail: no worker means one attempt and no retry; failures are still
    # recorded and reported.
    try:
        deliver(notification_id, address, username)
    except Exception as exc:
        report_failure(notification_id, address, exc, attempts=1)


@shared_task(bind=True, max_retries=MAX_RETRIES)
def send_notification_email(self, notification_id: str, address: str, username: str = "") -> None:
    try:
        deliver(notification_id, address, username)
    except Exception as exc:
        if self.request.retries < MAX_RETRIES:
            logger.warning("Notification email to %s failed, retrying: %s", address, exc)
            raise self.retry(exc=exc, countdown=60 * 2**self.request.retries)
        report_failure(notification_id, address, exc, attempts=self.request.retries + 1)


def deliver(notification_id, address: str, username: str) -> None:
    notification = models.Notification.objects.select_related("notiftype").get(pk=notification_id)
    context = {
        **notification.context,
        "email": address,
        "username": username,
        "notification_title": notification.notiftype.name,
    }
    body = render_to_string(notification.notiftype.emailtemplate, context)
    message = EmailMultiAlternatives(
        notification.notiftype.name, body, settings.DEFAULT_FROM_EMAIL, [address]
    )
    message.attach_alternative(body, "text/html")
    message.send()


def report_failure(notification_id, address: str, exc: Exception, attempts: int) -> None:
    notification = (
        models.Notification.objects.select_related("notiftype").filter(pk=notification_id).first()
    )
    context = notification.context if notification else {}
    failure = NotificationFailure.objects.create(
        notification_type=notification.notiftype.name if notification and notification.notiftype else "",
        resource_instance_id=context.get("resource_instance_id", ""),
        recipient=address,
        reason=str(exc),
        attempts=attempts,
    )
    logger.error("Notification email failed after %s attempt(s); failure %s", attempts, failure.pk)
    alert_admins(failure)


def alert_admins(failure: NotificationFailure) -> None:
    # The alert leaves out the recipient and the error text (which can quote
    # the address): no personal data. Both are on the failure record.
    message = (
        f"A notification email could not be sent after {failure.attempts} attempt(s). "
        f"Type: {failure.notification_type or 'unknown'}. "
        f"Resource: {failure.resource_instance_id or 'unknown'}. "
        f"Failure record: {failure.pk}."
    )
    alert = models.Notification.objects.create(
        message=message,
        context={"resource_instance_id": failure.resource_instance_id},
        notiftype_id=FAILURE_NOTIFICATION_TYPE_ID,
    )
    superusers = list(User.objects.filter(is_superuser=True, is_active=True))
    # bulk_create: core's post_save handler would email each row itself and
    # swallow any failure; the email is sent below instead.
    models.UserXNotification.objects.bulk_create(
        models.UserXNotification(notif=alert, recipient=user) for user in superusers
    )
    addresses = [user.email for user in superusers if user.email]
    if not addresses:
        return
    try:
        send_mail("Notification email failed", message, settings.DEFAULT_FROM_EMAIL, addresses)
    except Exception:
        logger.exception("Could not email superusers about notification failure %s", failure.pk)
