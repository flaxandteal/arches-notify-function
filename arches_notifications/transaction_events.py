"""Per-transaction bookkeeping: which resources were created in the current
database transaction, and which (rule, resource) sends are already queued."""
from django.db import connection

from arches.app.models.models import ResourceInstance


def transaction_state() -> dict:
    # Keyed on the top-level transaction id so a rolled-back transaction's
    # entries can't leak into the next one (Django has no on_rollback hook).
    with connection.cursor() as cursor:
        cursor.execute("SELECT txid_current()")
        txid = cursor.fetchone()[0]
    state = getattr(connection, "_arches_notifications_txn", None)
    if state is None or state["txid"] != txid:
        state = {"txid": txid, "created": set(), "queued": set()}
        connection._arches_notifications_txn = state
    return state


def record_created_resource(sender, instance, created, **kwargs) -> None:
    if created and isinstance(instance, ResourceInstance):
        transaction_state()["created"].add(str(instance.pk))
