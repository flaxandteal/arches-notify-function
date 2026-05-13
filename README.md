# arches-notifications

Config-driven notification functions for Arches projects. Allows you to send web and email notifications to Django auth groups when specific nodegroup tiles are saved, with optional custom logic per nodegroup.

---

## Installation

Install the package into your Arches project:

```bash
pip install arches-notifications
```

Or, if working from source within a monorepo:

```bash
pip install -e path/to/arches-notifications
```

Add `"arches_notifications"` to `INSTALLED_APPS` in your project's `settings.py`:

```python
INSTALLED_APPS = [
    ...
    "arches_notifications",
]
```

---

## Overview

The notification system works through three concepts:

1. **`NotificationConfig`** — a dataclass describing what to send and to whom for a given nodegroup
2. **`NotifyFunction`** — a base Arches function class you subclass once per resource graph; it maps nodegroup aliases to configs
3. **`NotificationStrategy`** — the class that does the sending; subclass it when you need conditional logic beyond the config

When a tile is saved on a triggering nodegroup, Arches calls `post_save` on the attached function. `NotifyFunction` resolves the nodegroup to its config, instantiates the appropriate strategy, and sends the notification.

---

## Setting Up a Notification Function

### 1. Define the function

Create a file in your project's `functions/` directory. Subclass `NotifyFunction`, set `graph_slug` to the slug of the resource graph you want to watch, and define `strategy_registry` with one entry per nodegroup you want to trigger on.

```python
from uuid import UUID
from arches_notifications import NotifyFunction, NotificationConfig

details = {
    "functionid": "your-unique-uuid-here",
    "name": "Notify My Team",
    "type": "node",
    "description": "Sends notifications when key tiles are saved on My Resource.",
    "defaultconfig": {
        "triggering_nodegroups": [
            "sign-off",       # nodegroup aliases listed here for reference —
            "submission",     # Arches requires UUIDs in triggering_nodegroups,
        ],                    # see note below
    },
    "classname": "NotifyMyTeam",
    "component": "",
}

class NotifyMyTeam(NotifyFunction):
    strategy_registry = {
        "sign-off": {
            "config": NotificationConfig(
                message="A sign-off has been submitted for {name}.",
                notiftype_id=UUID("f49995b9-59ea-4f85-adbb-0e3a60587bd6"),
                groups_to_notify=["reviewers", "admins"],
                email=True,
                response_slug="my-workflow",
                button_text="Review Sign-Off",
            )
        },
        "submission": {
            "config": NotificationConfig(
                message="A new submission {name} requires attention.",
                notiftype_id=UUID("f49995b9-59ea-4f85-adbb-0e3a60587bd6"),
                groups_to_notify=["admins"],
                email=False,
                response_slug="my-workflow",
            )
        },
    }
```

> **Note on `triggering_nodegroups`:** Arches requires nodegroup UUIDs in `defaultconfig`. The `strategy_registry` keys are resolved from aliases automatically at runtime, but `triggering_nodegroups` is read by Arches before your code runs. You can either list the UUIDs there, or look them up from your graph and keep them as constants at the top of the file.

### 2. Register the function

Add your functions directory to `FUNCTION_LOCATIONS` in `settings.py`:

```python
FUNCTION_LOCATIONS.append("myproject.functions")
```

### 3. Attach the function to the graph

In the Arches graph designer, open the resource graph and attach the function. Set the triggering nodegroups to match the nodegroups your `strategy_registry` covers.

---

## NotificationConfig Reference

```python
NotificationConfig(
    message="A new record {name} has been created.",  # required; {name} is replaced with the resource display name
    notiftype_id=UUID("..."),                          # required; UUID of the Arches NotificationType
    groups_to_notify=["group-name"],                   # Django auth group names; defaults to []
    email=False,                                       # send email as well as web notification; defaults to False
    response_slug=None,                                # workflow slug used by the frontend to open the right view
    check_prefix=None,                                 # only notify if the resource name starts with this string
    remove_prefix=None,                                # strip this prefix from the resource name before use in message
    remove_suffix=None,                                # strip this suffix from the resource name before use in message
    button_text="Open Arches",                         # label on the email button; defaults to "Open Arches"
    link_path="/index.htm",                            # path used to build the email button URL; defaults to /index.htm
)
```

### `message`

The notification message shown to recipients. Use `{name}` as a placeholder for the resource display name:

```python
message="The application {name} has been submitted for review."
```

### `groups_to_notify`

A list of Django auth group names. All users who are members of any listed group will receive the notification, except the user who triggered the save.

```python
groups_to_notify=["curators", "administrators"]
```

### `check_prefix`

If set, the notification is only sent if the resource display name (after any prefix/suffix removal) starts with this string. Useful when one nodegroup is shared across resource types distinguished by a name prefix.

```python
check_prefix="SMC"
```

### `remove_prefix` / `remove_suffix`

Arches resource display names sometimes include a type label (e.g. `"Excavation Licence EXC/2024/001"`). These strip that label before the name is used in the message or prefix check:

```python
remove_prefix="Excavation Licence"
# "Excavation Licence EXC/2024/001" → "EXC/2024/001"
```

### `email`

When `True`, an email notification is sent in addition to the web notification. Each recipient gets their own email with their username and address filled in. The email template is controlled by the `NotificationType` configured in Arches.

### `response_slug`

The slug of the workflow or view the frontend should open when the user clicks the notification. Stored in the notification context and read by the notification component.

---

## Resolving Node and Nodegroup IDs

### `node_id(alias, graph_slug)`

When writing custom strategy logic that reads from `tile.data`, you need the node's UUID as the dict key. Use `node_id` to resolve an alias rather than hardcoding UUIDs:

```python
from arches_notifications import node_id

grade = self.tile.data[node_id("grade_decision", "my-resource-graph")]
```

Results are cached per `alias`/`graph_slug` pair for the lifetime of the process, so the DB is only hit once.

---

## Custom Strategies

When the base config is not enough — for example, you need to read tile data to change the message, conditionally skip the notification, or route to different groups based on what was saved — subclass `NotificationStrategy` and override `send_notification`.

### Basic example: customising the message from tile data

```python
from arches_notifications import NotificationStrategy, node_id

DECISION_NODE = "grade-decision"
GRAPH = "my-resource-graph"

class GradeDecisionStrategy(NotificationStrategy):
    def send_notification(self):
        decision_id = self.tile.data.get(node_id(DECISION_NODE, GRAPH))
        if decision_id:
            decision_label = self.get_domain_value_string(decision_id, node_id(DECISION_NODE, GRAPH))
            self.notification.message = (
                f"The grade decision for {self.name} has been set to '{decision_label}'."
            )
            self.notification.save()
        super().send_notification()
```

Register it in the `strategy_registry`:

```python
strategy_registry = {
    "grade-decision": {
        "strategy": GradeDecisionStrategy,
        "config": NotificationConfig(
            message="The grade decision for {name} has been updated.",
            notiftype_id=UUID("..."),
            groups_to_notify=["curators"],
        ),
    }
}
```

### Skipping the notification conditionally

Return before calling `super()` to suppress the notification entirely. The base `send_notification` deletes the unsent notification record automatically if you let it run, but if you return early you should delete it yourself:

```python
class ConditionalStrategy(NotificationStrategy):
    def send_notification(self):
        stage = self.tile.data.get(node_id("stage", GRAPH))
        if stage != FINAL_STAGE_ID:
            self.notification.delete()
            return
        super().send_notification()
```

### Changing the recipient groups dynamically

```python
class RoutedStrategy(NotificationStrategy):
    def send_notification(self):
        value = self.tile.data.get(node_id("classification", GRAPH))
        if value == HIGH_PRIORITY_ID:
            self.config.groups_to_notify = ["senior-curators", "admins"]
        else:
            self.config.groups_to_notify = ["curators"]
        super().send_notification()
```

### Available attributes in a strategy

| Attribute | Description |
|---|---|
| `self.tile` | The Arches tile that was saved |
| `self.request` | The Django HTTP request |
| `self.user` | The Django user who saved the tile (`None` if unauthenticated) |
| `self.config` | The `NotificationConfig` for this nodegroup |
| `self.name` | The resource display name (after prefix/suffix processing) |
| `self.notification` | The unsaved-or-saved `Notification` model instance |
| `self.resource_instance_id` | UUID string of the resource instance |

### `get_domain_value_string(value_id, node_id, language=None)`

Resolves a domain value UUID to its display label. Uses `settings.LANGUAGE_CODE` by default; pass `language` to override:

```python
label = self.get_domain_value_string(value_id, node_id("status", GRAPH), language="en")
```

---

## Creating a NotificationType

Each `NotificationConfig` requires a `notiftype_id` pointing to an Arches `NotificationType`. Create one via a migration in your project:

```python
from django.db import migrations

def add_notification_type(apps, schema_editor):
    NotificationType = apps.get_model("models", "NotificationType")
    NotificationType.objects.get_or_create(
        typeid="f49995b9-59ea-4f85-adbb-0e3a60587bd6",
        defaults={
            "name": "My Project Notifications",
            "emailtemplate": "email/general_notification.htm",
            "emailnotify": True,
            "webnotify": True,
        },
    )

class Migration(migrations.Migration):
    dependencies = [...]
    operations = [migrations.RunPython(add_notification_type)]
```
