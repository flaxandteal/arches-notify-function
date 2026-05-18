"""NotifyFunction._node_changed change-detection logic.

_resolve_node_alias hits the ORM; patch it to a fixed node id so the test
exercises only the before/after comparison."""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

pytest.importorskip("django")

from arches_notifications.functions import notify_function as nf

NODE_ID = "node-uuid"


def _fn():
    fn = nf.NotifyFunction()
    fn._resolve_node_alias = lambda alias, graph_slug: NODE_ID
    return fn


def _tile(pre_save, data):
    return SimpleNamespace(_notify_pre_save_data=pre_save, data=data)


def test_node_changed_true_when_value_differs():
    tile = _tile({NODE_ID: "draft"}, {NODE_ID: "final"})
    assert _fn()._node_changed(tile, "status", "g") is True


def test_node_changed_false_when_value_same():
    tile = _tile({NODE_ID: "draft"}, {NODE_ID: "draft"})
    assert _fn()._node_changed(tile, "status", "g") is False


def test_node_changed_true_when_newly_set():
    tile = _tile({}, {NODE_ID: "final"})
    assert _fn()._node_changed(tile, "status", "g") is True


def test_node_changed_true_when_cleared():
    tile = _tile({NODE_ID: "draft"}, {})
    assert _fn()._node_changed(tile, "status", "g") is True


def test_node_changed_false_when_absent_both_sides():
    tile = _tile({}, {})
    assert _fn()._node_changed(tile, "status", "g") is False


def test_node_changed_handles_missing_presave_attr():
    # save() skips stashing _notify_pre_save_data when no rule wants change
    # detection; getattr default must not blow up.
    tile = SimpleNamespace(data={NODE_ID: "x"})
    assert _fn()._node_changed(tile, "status", "g") is True


def test_node_changed_handles_none_data():
    tile = _tile(None, None)
    assert _fn()._node_changed(tile, "status", "g") is False
