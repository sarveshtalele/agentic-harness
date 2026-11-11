"""Pre-run checks for generated tests. Port of the idea behind emit-tests.ts: nothing a model wrote is run to find out it was wrong.

Python tests are read with `ast` only. Imports must resolve, imported names must exist, calls must fit the real signatures,
and third-party packages must be installed in the sandbox. When something cannot be known, nothing is reported: a false alarm
would send a correct test back to the model.
"""
from __future__ import annotations

from .inventory import (
    SIGNATURE_BUDGET,
    ALIASES,
    INVENTORY,
    inventory,
    _normal,
    declared_dependencies,
)
from .sigs import (
    PASS_THROUGH,
    RAISES,
    Sig,
    _sig,
    _decorator_names,
    _transparent,
    _function_sig,
    _class_sig,
    _method_sig,
    call_problem,
    _shallow,
)
from .project import (
    _parse_cached,
    _parsed,
    Project,
    signatures,
)
from .python import (
    _guarded_imports,
    _chain,
    check_python,
    _third_party,
)
from .checks import (
    JS_EXTENSIONS,
    JS_IMPORT,
    check_js,
    check,
)
