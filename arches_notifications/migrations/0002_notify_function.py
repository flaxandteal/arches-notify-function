from django.db import migrations


FUNCTION_ID = "f5a0e2b0-1c3e-4a8f-9d2c-1a2b3c4d5e6f"


def register_notify_function(apps, _schema_editor):
    Function = apps.get_model("models", "Function")
    Function.objects.update_or_create(
        functionid=FUNCTION_ID,
        defaults={
            "name": "Notify on tile save",
            "functiontype": "node",
            "description": (
                "Sends notifications to configured groups when matching tiles "
                "are saved."
            ),
            "defaultconfig": {"triggering_nodegroups": [], "nodegroups": []},
            "modulename": "notify_function.py",
            "classname": "NotifyFunction",
            "component": "views/components/functions/notify",
        },
    )


def unregister_notify_function(apps, _schema_editor):
    Function = apps.get_model("models", "Function")
    Function.objects.filter(functionid=FUNCTION_ID).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("arches_notifications", "0001_notification_type"),
    ]

    operations = [
        migrations.RunPython(register_notify_function, unregister_notify_function),
    ]
