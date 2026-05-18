from dataclasses import dataclass, field
from uuid import UUID

# Created by migration 0001_notification_type. Used as the default when a
# rule does not specify its own type. Override by editing the rule's JSON
# config directly if you want a different NotificationType per rule.
DEFAULT_NOTIFICATION_TYPE_ID = UUID("a85b3f1c-7d4e-4d5a-9b5e-2a3b4c5d6e7f")
DEFAULT_EMAIL_TEMPLATE = "email/general_notification.htm"


@dataclass
class ResourceNameConfig:
    require_prefix: str | None = None
    strip_prefix: str | None = None
    strip_suffix: str | None = None

    def apply(self, name: str) -> str | None:
        """Return cleaned name, or None if the require_prefix filter fails."""
        if self.require_prefix and not name.startswith(self.require_prefix):
            return None
        if self.strip_prefix:
            name = name.removeprefix(self.strip_prefix).strip()
        if self.strip_suffix:
            name = name.removesuffix(self.strip_suffix).strip()
        return name

    @classmethod
    def from_dict(cls, data: dict[str, str | None]) -> "ResourceNameConfig":
        return cls(
            require_prefix=data.get("require_prefix"),
            strip_prefix=data.get("strip_prefix"),
            strip_suffix=data.get("strip_suffix"),
        )


@dataclass
class NotificationConfig:
    nodegroup_alias: str
    message: str
    notiftype_id: UUID = DEFAULT_NOTIFICATION_TYPE_ID
    groups_to_notify: list[str] = field(default_factory=list)
    email: bool = False
    button_text: str = "View resource"
    # Empty means "link to the resource report page" — the strategy fills it
    # in from resource_instance_id at send time. Override with a fixed path
    # like "/index.htm" if you want every email to land on the same page.
    link_path: str = ""
    resource_name: ResourceNameConfig = field(default_factory=ResourceNameConfig)
    # Optional: only fire when this node within the nodegroup has changed.
    # Empty / None means "fire on any tile save in the nodegroup".
    node_alias: str | None = None
    # Used as NotificationType.name (the label users see in their email
    # preferences). When empty, after_function_save derives one from the
    # nodegroup alias.
    notification_name: str | None = None
    # Used as NotificationType.emailtemplate (Django template path).
    emailtemplate: str = DEFAULT_EMAIL_TEMPLATE

    @classmethod
    def from_dict(cls, data: dict) -> "NotificationConfig":
        raw_type_id = data.get("notiftype_id")
        return cls(
            nodegroup_alias=data["nodegroup_alias"],
            message=data["message"],
            notiftype_id=UUID(raw_type_id) if raw_type_id else DEFAULT_NOTIFICATION_TYPE_ID,
            groups_to_notify=data.get("groups_to_notify", []),
            email=data.get("email", False),
            button_text=data.get("button_text") or "View resource",
            link_path=data.get("link_path") or "",
            resource_name=ResourceNameConfig.from_dict(data.get("resource_name") or {}),
            node_alias=data.get("node_alias") or None,
            notification_name=data.get("notification_name") or None,
            emailtemplate=data.get("emailtemplate") or DEFAULT_EMAIL_TEMPLATE,
        )
