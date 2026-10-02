import uuid

from django.db import migrations, models

FAILURE_NOTIFICATION_TYPE_ID = "5d0f3c2e-8b1a-4c6e-9f7d-3e2a1b4c5d60"


def create_failure_notification_type(apps, _schema_editor):
    NotificationType = apps.get_model("models", "NotificationType")
    NotificationType.objects.update_or_create(
        typeid=FAILURE_NOTIFICATION_TYPE_ID,
        defaults={
            "name": "Notification email failed",
            "emailtemplate": "email/general_notification.htm",
            "emailnotify": False,
            "webnotify": True,
        },
    )


def remove_failure_notification_type(apps, _schema_editor):
    NotificationType = apps.get_model("models", "NotificationType")
    NotificationType.objects.filter(typeid=FAILURE_NOTIFICATION_TYPE_ID).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("arches_notifications", "0002_notify_function"),
    ]

    operations = [
        migrations.CreateModel(
            name="NotificationFailure",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("notification_type", models.TextField(blank=True)),
                ("resource_instance_id", models.TextField(blank=True)),
                ("recipient", models.TextField()),
                ("reason", models.TextField()),
                ("attempts", models.PositiveSmallIntegerField()),
            ],
            options={"ordering": ["-created"]},
        ),
        migrations.RunPython(create_failure_notification_type, remove_failure_notification_type),
    ]
