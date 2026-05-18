from django.db import migrations


NOTIFICATION_TYPE_ID = "a85b3f1c-7d4e-4d5a-9b5e-2a3b4c5d6e7f"
NOTIFICATION_TYPE_NAME = "Arches notification"
EMAIL_TEMPLATE = "email/general_notification.htm"


def create_notification_type(apps, _schema_editor):
    NotificationType = apps.get_model("models", "NotificationType")
    NotificationType.objects.update_or_create(
        typeid=NOTIFICATION_TYPE_ID,
        defaults={
            "name": NOTIFICATION_TYPE_NAME,
            "emailtemplate": EMAIL_TEMPLATE,
            "emailnotify": True,
            "webnotify": True,
        },
    )


def remove_notification_type(apps, _schema_editor):
    NotificationType = apps.get_model("models", "NotificationType")
    NotificationType.objects.filter(typeid=NOTIFICATION_TYPE_ID).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("models", "9979_update_stage_for_bulk_edit"),
    ]

    operations = [
        migrations.RunPython(create_notification_type, remove_notification_type),
    ]
