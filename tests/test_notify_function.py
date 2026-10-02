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


# --- fire_on / saved_by gating and per-transaction coalescing in post_save ------

def _post_save_sends(event, user=None, saves=1, **rule):
    from arches_notifications.notification_config import NotificationConfig
    sent = []

    class RecordingStrategy:
        def __init__(self, tile, request, user, config):
            pass

        def send_notification(self):
            sent.append(True)

    fn = nf.NotifyFunction()
    fn._configs_for_tile = lambda ng, slug: [NotificationConfig(nodegroup_alias="a", message="m", **rule)]
    fn._get_user = staticmethod(lambda request: user)
    tile = SimpleNamespace(
        nodegroup_id="ng", resourceinstance_id="r1",
        resourceinstance=SimpleNamespace(graph=SimpleNamespace(slug="g")),
    )
    state = {"txid": 1, "created": set(), "queued": set()}
    queued = []
    with patch.object(nf, "NotificationStrategy", RecordingStrategy), patch.object(
        nf.NotifyFunction, "_resource_event", staticmethod(lambda rid, st: event)
    ), patch("arches_notifications.transaction_events.transaction_state", lambda: state), patch.object(
        nf.transaction, "on_commit", queued.append
    ):
        for _ in range(saves):
            fn.post_save(tile, None)
        assert not sent, "must not send before commit"
        for callback in queued:
            callback()
    return len(sent)


def test_fire_on_any_sends_for_every_event():
    for event in ("created", "updated", "copied"):
        assert _post_save_sends(event) == 1


def test_fire_on_created_skips_updates_and_copies():
    assert _post_save_sends("created", fire_on="created") == 1
    assert _post_save_sends("updated", fire_on="created") == 0
    assert _post_save_sends("copied", fire_on="created") == 0


def test_saved_by_system_only_when_no_user():
    assert _post_save_sends("updated", user=None, saved_by="system") == 1
    assert _post_save_sends("updated", user=object(), saved_by="system") == 0
    assert _post_save_sends("updated", user=object(), saved_by="user") == 1


def test_repeat_saves_in_one_transaction_send_once():
    assert _post_save_sends("created", saves=3) == 1


def test_copy_made_during_creation_only_matches_any():
    assert _post_save_sends(nf.COPIED_DURING_CREATE, fire_on="copied") == 0
    assert _post_save_sends(nf.COPIED_DURING_CREATE, fire_on="created") == 0
    assert _post_save_sends(nf.COPIED_DURING_CREATE, fire_on="any") == 1
