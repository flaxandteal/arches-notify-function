from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID


@dataclass
class ResourceNameConfig:
    require_prefix: Optional[str] = None
    strip_prefix: Optional[str] = None
    strip_suffix: Optional[str] = None

    def apply(self, name: str) -> Optional[str]:
        """Return cleaned name, or None if the require_prefix filter fails."""
        if self.require_prefix and not name.startswith(self.require_prefix):
            return None
        if self.strip_prefix:
            name = name.removeprefix(self.strip_prefix).strip()
        if self.strip_suffix:
            name = name.removesuffix(self.strip_suffix).strip()
        return name

    @classmethod
    def from_dict(cls, data: dict) -> "ResourceNameConfig":
        return cls(
            require_prefix=data.get("require_prefix"),
            strip_prefix=data.get("strip_prefix"),
            strip_suffix=data.get("strip_suffix"),
        )


@dataclass
class NotificationConfig:
    nodegroup_alias: str
    message: str
    notiftype_id: UUID
    groups_to_notify: list[str] = field(default_factory=list)
    email: bool = False
    button_text: str = "Open Arches"
    link_path: str = "/index.htm"
    resource_name: ResourceNameConfig = field(default_factory=ResourceNameConfig)

    @classmethod
    def from_dict(cls, data: dict) -> "NotificationConfig":
        return cls(
            nodegroup_alias=data["nodegroup_alias"],
            message=data["message"],
            notiftype_id=UUID(data["notiftype_id"]),
            groups_to_notify=data.get("groups_to_notify", []),
            email=data.get("email", False),
            button_text=data.get("button_text", "Open Arches"),
            link_path=data.get("link_path", "/index.htm"),
            resource_name=ResourceNameConfig.from_dict(data.get("resource_name") or {}),
        )
