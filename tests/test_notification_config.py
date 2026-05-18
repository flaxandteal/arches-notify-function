"""Pure-dataclass tests — notification_config has no Arches imports, so
these need no stubs."""
from uuid import UUID

import pytest

from arches_notifications.notification_config import (
    DEFAULT_EMAIL_TEMPLATE,
    DEFAULT_NOTIFICATION_TYPE_ID,
    NotificationConfig,
    ResourceNameConfig,
)


# --- ResourceNameConfig.apply -------------------------------------------------

def test_apply_passthrough_when_unconfigured():
    assert ResourceNameConfig().apply("Site 42") == "Site 42"


def test_apply_require_prefix_rejects_non_match_with_none():
    cfg = ResourceNameConfig(require_prefix="LIC-")
    assert cfg.apply("Site 42") is None


def test_apply_require_prefix_keeps_match():
    cfg = ResourceNameConfig(require_prefix="LIC-")
    assert cfg.apply("LIC-Site 42") == "LIC-Site 42"


def test_apply_strips_prefix_and_suffix_and_trims():
    cfg = ResourceNameConfig(strip_prefix="LIC-", strip_suffix="(draft)")
    assert cfg.apply("LIC- Site 42 (draft)") == "Site 42"


def test_apply_require_prefix_checked_before_stripping():
    # strip_prefix would have removed the text require_prefix looks for;
    # the require check must run against the raw name first.
    cfg = ResourceNameConfig(require_prefix="LIC-", strip_prefix="LIC-")
    assert cfg.apply("LIC-Site 42") == "Site 42"
    assert cfg.apply("Site 42") is None


def test_apply_empty_string_survives():
    assert ResourceNameConfig().apply("") == ""


# --- NotificationConfig.from_dict --------------------------------------------

def test_from_dict_minimal_uses_defaults():
    cfg = NotificationConfig.from_dict(
        {"nodegroup_alias": "ng", "message": "hi"}
    )
    assert cfg.nodegroup_alias == "ng"
    assert cfg.message == "hi"
    assert cfg.notiftype_id == DEFAULT_NOTIFICATION_TYPE_ID
    assert cfg.groups_to_notify == []
    assert cfg.email is False
    assert cfg.button_text == "View resource"
    assert cfg.link_path == ""
    assert cfg.node_alias is None
    assert cfg.notification_name is None
    assert cfg.emailtemplate == DEFAULT_EMAIL_TEMPLATE
    assert isinstance(cfg.resource_name, ResourceNameConfig)


def test_from_dict_parses_explicit_type_id():
    tid = "11111111-2222-3333-4444-555555555555"
    cfg = NotificationConfig.from_dict(
        {"nodegroup_alias": "ng", "message": "m", "notiftype_id": tid}
    )
    assert cfg.notiftype_id == UUID(tid)


@pytest.mark.parametrize("falsy", [None, "", 0])
def test_from_dict_blank_type_id_falls_back_to_default(falsy):
    cfg = NotificationConfig.from_dict(
        {"nodegroup_alias": "ng", "message": "m", "notiftype_id": falsy}
    )
    assert cfg.notiftype_id == DEFAULT_NOTIFICATION_TYPE_ID


@pytest.mark.parametrize(
    "field,blank,expected",
    [
        ("button_text", "", "View resource"),
        ("button_text", None, "View resource"),
        ("link_path", None, ""),
        ("emailtemplate", "", DEFAULT_EMAIL_TEMPLATE),
        ("node_alias", "", None),
        ("notification_name", "", None),
    ],
)
def test_from_dict_blank_fields_coerce_to_defaults(field, blank, expected):
    cfg = NotificationConfig.from_dict(
        {"nodegroup_alias": "ng", "message": "m", field: blank}
    )
    assert getattr(cfg, field) == expected


def test_from_dict_builds_nested_resource_name():
    cfg = NotificationConfig.from_dict(
        {
            "nodegroup_alias": "ng",
            "message": "m",
            "resource_name": {
                "require_prefix": "LIC-",
                "strip_prefix": "LIC-",
                "strip_suffix": "(draft)",
            },
        }
    )
    # from_dict must build a real ResourceNameConfig with every field
    # carried across from the nested dict...
    assert isinstance(cfg.resource_name, ResourceNameConfig)
    assert cfg.resource_name.require_prefix == "LIC-"
    assert cfg.resource_name.strip_prefix == "LIC-"
    assert cfg.resource_name.strip_suffix == "(draft)"
    # ...and the constructed config must actually process a name end to end.
    assert cfg.resource_name.apply("LIC-Site 42 (draft)") == "Site 42"
    assert cfg.resource_name.apply("Site 42") is None


def test_from_dict_omitted_resource_name_is_noop_config():
    cfg = NotificationConfig.from_dict({"nodegroup_alias": "ng", "message": "m"})
    assert isinstance(cfg.resource_name, ResourceNameConfig)
    assert cfg.resource_name.require_prefix is None
    assert cfg.resource_name.strip_prefix is None
    assert cfg.resource_name.strip_suffix is None
    # A default config must pass any name through untouched.
    assert cfg.resource_name.apply("Site 42") == "Site 42"


def test_from_dict_missing_required_keys_raises():
    with pytest.raises(KeyError):
        NotificationConfig.from_dict({"message": "m"})
    with pytest.raises(KeyError):
        NotificationConfig.from_dict({"nodegroup_alias": "ng"})
