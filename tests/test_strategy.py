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
