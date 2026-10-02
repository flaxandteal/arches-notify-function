"""NotificationStrategy._render_message token substitution.

__init__ does DB work, so we build a bare instance via object.__new__ and
inject only what _render_message touches: `name` and the per-alias value
resolver (itself unit-tested elsewhere / against the real ORM)."""
import pytest

pytest.importorskip("django")

from arches_notifications.notification_base_strategy import NotificationStrategy


def _strategy(name, values):
    s = object.__new__(NotificationStrategy)
    s.name = name
    s._resolve_node_value_by_alias = lambda alias: values.get(alias)
    return s


def test_render_substitutes_name():
    s = _strategy("Site 42", {})
    assert s._render_message("Resource {name} changed") == "Resource Site 42 changed"


def test_render_name_token_is_case_insensitive():
    s = _strategy("Site 42", {})
    assert s._render_message("{NAME}") == "Site 42"


def test_render_name_none_becomes_empty():
    s = _strategy(None, {})
    assert s._render_message("[{name}]") == "[]"


def test_render_substitutes_value_token_by_alias():
    s = _strategy("X", {"status": "Approved"})
    assert s._render_message("Status is {value:status}") == "Status is Approved"


def test_render_unknown_alias_left_literal():
    # None from the resolver means "alias didn't resolve" — keep the raw
    # token so a configurator sees the typo instead of a silent blank.
    s = _strategy("X", {})
    assert s._render_message("{value:bogus}") == "{value:bogus}"


def test_render_empty_string_value_is_substituted_not_literal():
    s = _strategy("X", {"note": ""})
    assert s._render_message("<{value:note}>") == "<>"


def test_render_multiple_mixed_tokens():
    s = _strategy("Tomb", {"grade": "A", "status": "Open"})
    out = s._render_message("{name}: grade {value:grade}, {value:status}")
    assert out == "Tomb: grade A, Open"


def test_render_alias_with_hyphen_and_digits():
    s = _strategy("X", {"grade-2": "ok"})
    assert s._render_message("{value:grade-2}") == "ok"


def test_render_no_tokens_passes_through():
    s = _strategy("X", {})
    assert s._render_message("nothing to do here") == "nothing to do here"


# --- _email_recipients: who gets an email ------------------------------------

def _routing_strategy(monkeypatch, recipients_mode, addresses, opted_out=(), email=True):
    from types import SimpleNamespace
    from unittest.mock import MagicMock
    from arches_notifications import notification_base_strategy as nbs
    from arches_notifications.notification_config import NotificationConfig
    s = object.__new__(NotificationStrategy)
    s.config = NotificationConfig(
        nodegroup_alias="a", message="m", email=email,
        email_recipients=recipients_mode, email_addresses=addresses,
    )
    opt_out_model = MagicMock()
    opt_out_model.objects.filter.return_value.values_list.return_value = list(opted_out)
    monkeypatch.setattr(nbs.models, "UserXNotificationType", opt_out_model, raising=False)
    return s


def _member(pk, email, username="u"):
    from types import SimpleNamespace
    return SimpleNamespace(pk=pk, email=email, username=username)


def test_members_mode_emails_members_only(monkeypatch):
    s = _routing_strategy(monkeypatch, "members", ["inbox@example.org"])
    assert s._email_recipients([_member(1, "m@example.org", "m")]) == [("m@example.org", "m")]


def test_members_mode_skips_opted_out_and_blank_emails(monkeypatch):
    s = _routing_strategy(monkeypatch, "members", [], opted_out=[1])
    members = [_member(1, "out@example.org"), _member(2, ""), _member(3, "in@example.org", "in")]
    assert s._email_recipients(members) == [("in@example.org", "in")]


def test_members_and_extra_skips_address_a_member_already_gets(monkeypatch):
    s = _routing_strategy(monkeypatch, "members_and_extra", ["M@example.org", "inbox@example.org"])
    emails = s._email_recipients([_member(1, "m@example.org", "m")])
    assert emails == [("m@example.org", "m"), ("inbox@example.org", "")]


def test_extra_only_emails_every_address_and_no_members(monkeypatch):
    s = _routing_strategy(monkeypatch, "extra_only", ["m@example.org"])
    assert s._email_recipients([_member(1, "m@example.org")]) == [("m@example.org", "")]


def test_no_emails_when_email_unticked(monkeypatch):
    s = _routing_strategy(monkeypatch, "members_and_extra", ["inbox@example.org"], email=False)
    assert s._email_recipients([_member(1, "m@example.org")]) == []
