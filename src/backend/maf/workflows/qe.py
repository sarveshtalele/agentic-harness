"""QE lifecycle: requirements to signed release, with human gates G0 to G5.
Modularized into backend.maf.workflows.qe package.
"""
from __future__ import annotations

from backend.maf.workflows.qe import *
from backend.maf.workflows.qe.definition import qe_definition, REGISTRY

REGISTRY["qe"] = qe_definition
