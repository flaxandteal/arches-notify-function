# arches-notifications

Config-driven web and email notifications for Arches projects. Attach the
function to a graph in the function manager, define rules through the Vue
config panel, and notifications fire on matching tile saves. Power users
can subclass to add custom send logic.

---

## Installation

```bash
pip install arches-notifications
# or editable, from source:
pip install -e path/to/arches-notifications
```

Add to your project's `settings.py`:

```python
INSTALLED_APPS = [
    ...,
    "arches_notifications",
]
```

Mount the URLs in your project's `urls.py`:

```python
urlpatterns = [
    ...,
    path("", include("arches_notifications.urls")),
]
```

Run migrations:

```bash
python manage.py migrate arches_notifications
```

This creates two rows:
- A fallback `NotificationType` ("Arches notification") used by legacy rules
  without their own `notiftype_id`. Modern rules each get their own type
  auto-managed at function-save time — see [Per-rule notification types](#per-rule-notification-types).
- The `Function` registration for "Notify on tile save".

Rebuild the frontend so the Vue config panel and KO shim are bundled:

```bash
yarn build_development   # or yarn start during development
```

---

## Getting started (for configurators)

Once installed, the function is available in the function library of every
resource graph.

1. Open the graph designer for a resource model, switch to the **Functions**
   tab.
2. Click **"Notify on tile save"** in the function library to attach it.
3. The notification rules panel appears. Click **Add rule**.
4. Fill in the rule:
   - **Nodegroup** — required. The rule fires when a tile in this nodegroup
     is saved.
   - **Specific node** — optional. If set, the rule only fires when the
     **value of this node changed** during the save. Leave blank to fire
     on every tile save in the nodegroup.
   - **Notification name** — what users see in their email-preferences UI
     for this rule (e.g. "Monuments — Status changed"). Leave blank to
     auto-derive from the graph and nodegroup names.
   - **Groups to notify** — Django auth groups whose members will receive
     the notification. The user who saved the tile is always excluded.
   - **Message** — body of the notification. Supports two tokens:
     - `{name}` — interpolates the resource's display name.
     - `{value:<node_alias>}` — interpolates the value of any node in the
       saved tile (e.g. `"Status of {name} changed to {value:status}"`).
       Unknown aliases stay literal so typos are visible.
   - **Send email** — when checked, an HTML email is also sent. Shows
     extra fields:
     - **Email template** — the Django template that renders the email.
       Projects can extend the dropdown by setting
       `ARCHES_NOTIFICATIONS_EMAIL_TEMPLATES` (see [Adding email templates](#adding-email-templates)).
     - **Button text** — label on the call-to-action button in the email
       (default `"View resource"`).
     - **Link path** — the path the button links to. Leave blank to link to
       the resource's report page (`/report/<resource_instance_id>`).
   - **Resource name** (advanced, collapsed) — optional prefix/suffix
     handling for cases where one nodegroup is shared across resource
     types distinguished by a name prefix.
5. Save the graph. Notifications now fire on matching tile saves.

You can add multiple rules to one function — e.g. notify reviewers when a
"submission" nodegroup is saved AND notify curators when a "decision" nodegroup
is saved, all from the same function attachment.

Removing a rule (trash icon) deletes its `NotificationType` row immediately
via `DELETE /api/notifications/type/<uuid>` so it disappears from users'
email-preferences UI. The shared package default type is protected.

### Web notification "Open resource" button

The bell-dropdown notification card renders an **Open resource** button that
takes the recipient straight to `/report/<resource_instance_id>`. This works
with no JS override — the strategy puts the resource URL into the saved
notification's `context["link"]`, and the app ships a template override at
`templates/views/components/notification.htm` that:

- Renders an `<a>` "Open resource" button when `link` looks like a URL
  (starts with `/` or `http`).
- Falls back to core's "Download Zip" button when `link` is an export id
  string — so Arches' existing export/download notifications keep working.

The bell link is stored as a **relative path** (`/report/<id>`) so the
browser resolves it against the current origin — no environment-specific
config needed for in-app links.

### `PUBLIC_SERVER_ADDRESS` (required for email)

Email links must be absolute because they're rendered outside the app. The
strategy builds them via `request.build_absolute_uri` when an HTTP request
is available, and falls back to `settings.PUBLIC_SERVER_ADDRESS` for
request-less contexts (Celery tasks, lifecycle hooks, management commands).

Set `PUBLIC_SERVER_ADDRESS` to the **public** URL of the site in every
environment that sends email:

```bash
# .env / docker-compose
PUBLIC_SERVER_ADDRESS=https://dev.example.com/
```

The Quartz docker settings default this to `http://arches:8000/` (the
internal container hostname) if unset — fine for local dev where nothing
leaves the container, broken for any environment that actually delivers
mail. If recipients see links pointing at `arches:8000`, this is why.

If you're behind a reverse proxy and want `request.build_absolute_uri` to
produce the public URL on its own, also ensure the proxy forwards the
original `Host` header and Django has `USE_X_FORWARDED_HOST = True`.

### Testing notifications

**Web notifications** show up immediately for any logged-in member of the
target groups (bell icon, top right).

**Email notifications** require Django's email backend to be configured. For
development, use the console backend so emails print to the container logs:

```python
# settings_local.py
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "noreply@example.com"
```

Save a tile that matches a rule with **Send email** ticked, then watch the
Django container output — you'll see the rendered email there.

For more realistic testing with a UI, run a [Mailpit](https://github.com/axllent/mailpit)
container alongside your stack:

```yaml
# docker-compose
mailpit:
  image: axllent/mailpit
  ports: ["8025:8025", "1025:1025"]
```

```python
# settings_local.py
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "mailpit"
EMAIL_PORT = 1025
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
EMAIL_USE_TLS = False
DEFAULT_FROM_EMAIL = "noreply@example.com"
```

Open `http://localhost:8025` to inspect emails as they arrive.

Each recipient User needs a non-empty `email` field, and a row in
`UserXNotificationType` opting **out** of email for that type suppresses
the send. By default users are opted in.

---

## Architecture

Five moving parts. Knowing how they fit together makes it easier to extend.

```
┌─────────────────────────────────────────────────────────────────────┐
│  Function manager UI (Knockout)                                     │
│  └─ notify.js (KO shim)                                             │
│      ├─ snapshots FunctionXGraph.config → plain JS                  │
│      └─ mounts NotificationConfigPanel.vue                          │
│                                                                     │
│  Vue owns its own reactive state and exposes a `getSnapshot()` fn.  │
│  The shim hooks the Save Edits button in capture phase, flushes     │
│  once via koMapping.fromJS, then KO's save handler reads the up-to- │
│  date config. (A one-shot `markDirty()` on the first edit makes the │
│  Save Edits button appear; KO gates it on the dirty computed.)      │
│                                                                     │
│  After save: function manager calls                                 │
│  NotifyFunction.after_function_save(function_x_graph, request),     │
│  which upserts one NotificationType per rule (using rule's          │
│  auto-generated notiftype_id as the primary key).                   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼ (FunctionXGraph.config JSON)
┌─────────────────────────────────────────────────────────────────────┐
│  Tile.save() runs                                                   │
│    ↓                                                                │
│  NotifyFunction.save(tile, request, context)       ← pre-save hook  │
│    └─ stashes prior tile data if any rule needs change detection    │
│    ↓                                                                │
│  NotifyFunction.post_save(tile, request, context)  ← after DB write │
│    └─ for each matching rule:                                       │
│        ├─ if rule has node_alias: check it changed, else skip rule  │
│        └─ instantiate strategy (default or override), send          │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  NotificationStrategy.send_notification()                           │
│    ├─ resolve resource display name (with prefix/suffix processing) │
│    ├─ skip if duplicate of last notification on this resource       │
│    ├─ create Notification row                                       │
│    └─ create UserXNotification rows for each recipient              │
│                                                                     │
│  Arches' core `send_email_on_save` signal handler                   │
│  picks up new UserXNotification rows and sends emails               │
│  for any whose NotificationType has emailtemplate set.              │
└─────────────────────────────────────────────────────────────────────┘
```

### The five parts

| File | Role |
|---|---|
| `notification_config.py` | Plain dataclasses (`NotificationConfig`, `ResourceNameConfig`) describing a single rule. Read from the FunctionXGraph JSON via `from_dict`. |
| `notification_base_strategy.py` | `NotificationStrategy` — does the actual sending. Subclass to inject custom logic per nodegroup. |
| `functions/notify_function.py` | `NotifyFunction` — the Arches function class. Dispatches matching rules to strategies in `post_save`. |
| `media/js/.../notify.js` | KO shim. Bridges the Knockout function manager and the Vue config panel. |
| `src/.../NotificationConfigPanel/` | Vue 3 + PrimeVue config panel rendered inside the function manager. |

### Why `triggering_nodegroups: []`?

The Function row's `defaultconfig` sets `triggering_nodegroups: []` deliberately.
Arches' tile dispatcher fires `post_save` for every nodegroup on the graph when
this list is empty. Per-nodegroup routing then happens *inside*
`_configs_for_tile` against the panel's rule list. This keeps the rule list as
the single source of truth and avoids drift between the function attachment
and the configured rules.

### How change detection works

When a rule has **Specific node** set, the function needs the **previous**
value of that node to compare against. `Tile.save()` does load the prior row
internally but doesn't expose it to function hooks, so:

1. `NotifyFunction.save()` (pre-save) queries `TileModel.objects.filter(pk=...)`
   **only if** at least one matching rule has `node_alias` set. The result is
   stashed on `tile._notify_pre_save_data` as a dynamic attribute.
2. `NotifyFunction.post_save()` reads that attribute and diffs against
   `tile.data` for the relevant node. Equality is `!=` on the raw value — fine
   for primitives; comparison of complex datatypes (geojson, file-list) may
   produce false positives.

Rules without `node_alias` skip both steps — no DB query overhead.

### Per-rule notification types

Each rule owns its own `NotificationType` row. When a configurator clicks
Add Rule, the panel generates a fresh UUID (`crypto.randomUUID()`) and stores
it as the rule's `notiftype_id`. On save, `after_function_save` hook calls
`NotificationType.objects.update_or_create(typeid=..., defaults={...})`
for each rule — idempotent, fine to run on every save.

Why per-rule:

- Users see one opt-out entry **per rule** in their notification
  preferences (e.g. "Monuments — Status changed" vs "Monuments —
  Decision recorded"), and can disable web/email independently for each.
- Each rule can use a different `emailtemplate`.
- Rule renames (changing **Notification name**) propagate on the next save
  without orphaning rows — `update_or_create` keys on `typeid`, not name.

Removed rules: deleted immediately when the configurator clicks the trash
icon, via a `DELETE /api/notifications/type/<uuid>` call from the panel. The
package-shipped default type (`DEFAULT_NOTIFICATION_TYPE_ID`) is protected
from deletion since it's shared across graphs/projects.

### Adding email templates

The **Email template** dropdown is populated from `arches.urls.notification_email_templates`,
which returns `settings.ARCHES_NOTIFICATIONS_EMAIL_TEMPLATES` if set, or a
single-entry default referencing the bundled template.

To add project-specific templates:

```python
# settings.py
ARCHES_NOTIFICATIONS_EMAIL_TEMPLATES = [
    {"path": "email/general_notification.htm", "label": "General notification"},
    {"path": "email/curator_review.htm",      "label": "Curator review"},
    {"path": "email/digest.htm",              "label": "Daily digest"},
]
```

Each `path` must resolve through Django's template loaders. Drop the `.htm`
file under any installed app's `templates/email/` directory.

The context passed to email templates includes:

| Variable | Source |
|---|---|
| `greeting` | The rendered message body (after `{name}` / `{value:...}` interpolation). |
| `salutation` | Static `"Hi"`. |
| `username`, `email` | Recipient's User fields. |
| `email_link` | The button href. Configured per-rule via `link_path`; falls back to the resource report URL if empty. |
| `button_text` | Per-rule label. |
| `resource_link` | Relative path to the resource's report page (`/report/<id>`). Always set. |
| `resource_instance_id` | UUID string. |
| `resource_id` | The processed display name (after prefix/suffix handling). |

Plus anything returned by your `extra_context()` strategy hook.

---

## Customising via subclassing

When config alone isn't enough — you need to read tile data to alter the
message, conditionally skip a notification, or route to different groups —
subclass `NotifyFunction` and provide your own strategy class per nodegroup
alias.

### The `strategy_overrides` map

```python
from arches_notifications import NotifyFunction, NotificationStrategy

class MyCustomNotifyFunction(NotifyFunction):
    strategy_overrides = {
        "decision":   DecisionStrategy,
        "submission": SubmissionStrategy,
    }
```

Rules whose `nodegroup_alias` matches a key use that strategy class. Unmapped
nodegroups fall back to the default `NotificationStrategy`. The **config still
comes from the UI** — only the send logic is swapped.

Register your subclass as a separate Arches Function (own `details = {...}`
block, own `functionid`, own `classname`) so it appears in the function
library alongside the base one.

### Strategy hooks

There are three places to plug in, smallest to largest:

#### 1. `extra_context()` — inject context fields

Used when you only need to add fields to the notification context, e.g. a
workflow slug consumed by the inbox UI:

```python
class DecisionStrategy(NotificationStrategy):
    def extra_context(self) -> dict:
        return {"workflow_slug": "review-workflow"}
```

#### 2. `send_notification()` — full control before/after send

Most common override. Read tile data, alter the message, change recipients,
or skip entirely:

```python
class DecisionStrategy(NotificationStrategy):
    def send_notification(self) -> None:
        decision_id = self.tile.data.get(NODE_DECISION_ID)
        if decision_id is None:
            return  # don't fire — node was cleared

        label = self.get_domain_value_string(decision_id, NODE_DECISION_ID)
        self.config.message = f"Decision for {{name}}: {label}"

        # Re-route based on tile data
        if label == "Escalate":
            self.config.groups_to_notify = ["senior-curators", "admins"]

        super().send_notification()
```

#### 3. Override more methods if needed

The class is short and readable — most overrides are one of the above plus a
private helper. See `notification_base_strategy.py` for the available
methods (`_get_resource_name`, `_get_recipients`, `_create_notification`,
`notify_user`, `_clone_notification_for_user`, `get_domain_value_string`).

### Strategy attributes

| Attribute | Description |
|---|---|
| `self.tile` | The Arches tile that was saved. `self.tile.data` is `{node_uuid: value}`. |
| `self.request` | The Django HTTP request. |
| `self.user` | The Django user who saved the tile (`None` if unauthenticated). |
| `self.config` | The `NotificationConfig` for this rule. Mutable inside `send_notification`. |
| `self.name` | The resource display name after prefix/suffix processing. |
| `self.notification` | The saved `Notification` model instance once `send_notification` creates it; `None` before then. |
| `self.resource_instance_id` | UUID string of the resource instance. |

### Resolving node aliases to UUIDs

`tile.data` is keyed by node UUID. To compare or read by alias, get the UUID
from the node table. Cache it — don't query per-call:

```python
from arches.app.models.models import Node

NODE_DECISION_ID = str(
    Node.objects.get(alias="decision", graph__slug="my-graph").nodeid
)
```

(For a packaged helper, see `NotifyFunction._resolve_node_alias`, which caches
per `(alias, graph_slug)` pair.)

---

## `NotificationConfig` reference

Each row in the rules array deserializes into one of these. UI fields map
one-to-one.

| Field | Type | Default | Notes |
|---|---|---|---|
| `nodegroup_alias` | `str` | — | Required. Alias of the nodegroup whose tile saves trigger this rule. |
| `node_alias` | `str \| None` | `None` | When set, only fire when this node's value changed. |
| `message` | `str` | — | Body. `{name}` is replaced with the resource display name. |
| `notiftype_id` | `UUID` | auto-generated per rule by the UI | Primary key of the rule's own `NotificationType`. Upserted by `after_function_save`. Legacy rules without one fall back to `DEFAULT_NOTIFICATION_TYPE_ID` from migration 0001. |
| `notification_name` | `str \| None` | derived from `"{graph} — {nodegroup_alias}"` | Becomes `NotificationType.name`. Shown to users in their email-preferences UI. |
| `emailtemplate` | `str` | `"email/general_notification.htm"` | Django template path used to render the email body. Becomes `NotificationType.emailtemplate`. |
| `groups_to_notify` | `list[str]` | `[]` | Django auth group names. Tile-save user is excluded. |
| `email` | `bool` | `False` | Also send an email rendered from `NotificationType.emailtemplate`. |
| `button_text` | `str` | `"View resource"` | Email CTA label. |
| `link_path` | `str` | `""` | Email CTA href. Empty means "link to the resource report page" — the strategy substitutes `/report/<resource_instance_id>` at send time. Set to e.g. `/index.htm` for a fixed destination. |
| `resource_name` | `ResourceNameConfig` | empty | Optional `require_prefix` / `strip_prefix` / `strip_suffix`. |

### `ResourceNameConfig`

| Field | Effect |
|---|---|
| `require_prefix` | If set, the notification is skipped unless the resource name starts with this string. |
| `strip_prefix` | Removed from the start of the resource name before message interpolation. |
| `strip_suffix` | Removed from the end of the resource name before message interpolation. |

---

## Persistence across DB resets

Two migrations ship with the app:

- **`0001_notification_type`** — the default `NotificationType` row.
- **`0002_notify_function`** — the `Function` registration for "Notify on
  tile save".

Both use `update_or_create` so they're idempotent.

**Not** migrated automatically:

- **`FunctionXGraph` rows** (the per-graph attachment + the rules JSON).
  These are configuration data, not app data. To persist them across DB
  resets, either:
  - Use `manage.py packages -o create_package` / `load_package` to
    round-trip them with the graph definition, or
  - Write a project-level data migration that inserts the row with a
    specific `graph_id` and `config` payload.
