"""Stub the bits of Arches that the notification modules import at
module-load time so the pure-logic unit tests don't need a configured
Arches/Django environment.

Mirrors arches-id-generator/tests/conftest.py. Real Arches is still
required for ORM-level tests; this only covers the import-time surface
touched by notification_config / notification_base_strategy /
functions.notify_function.
"""
import sys
import types


def _stub(name):
    mod = sys.modules.get(name)
    if mod is None:
        mod = types.ModuleType(name)
        sys.modules[name] = mod
    return mod


try:
    from arches.app.models import models  # noqa: F401
    from arches.app.models.resource import Resource  # noqa: F401
    from arches.app.functions.base import BaseFunction  # noqa: F401
except Exception:
    _stub("arches")
    _stub("arches.app")
    _stub("arches.app.models")
    _stub("arches.app.functions")

    models_mod = _stub("arches.app.models.models")
    # Notification code references these as models.<X>; bare placeholders
    # are enough for the import + the unit tests patch around the ORM.
    for cls_name in ("Tile", "Notification", "UserXNotification", "Node"):
        setattr(models_mod, cls_name, type(cls_name, (), {"objects": None}))
    # `from arches.app.models import models` resolves the submodule.
    sys.modules["arches.app.models"].models = models_mod

    resource_mod = _stub("arches.app.models.resource")
    resource_mod.Resource = type("Resource", (), {"objects": None})

    base_mod = _stub("arches.app.functions.base")
    base_mod.BaseFunction = type(
        "BaseFunction",
        (),
        {"__init__": lambda self, config=None, nodegroup_id=None: None},
    )
