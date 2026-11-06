"""MAF Quality Engineering workflow entry point."""
from backend.maf.workflows.qe.definition import REGISTRY, qe_definition

REGISTRY["qe"] = qe_definition
