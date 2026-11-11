"""Who may do what in the Skill Studio. A plan belongs to a project: unseen projects answer not found, viewers may only read."""
from __future__ import annotations

from backend.core import auth
from backend.core.skill_studio import plans

AUTHOR_ROLES = {"ba", "developer", "qe_lead"}


def author(admin_only: bool = False) -> dict:
    """The signed-in admin, or for non-admin steps a BA, developer or QE lead. Anyone else gets 403."""
    user = auth.current_user.get() or {}
    if user.get("role") == "admin":
        return user
    if admin_only or user.get("account_role") not in AUTHOR_ROLES:
        raise auth.Forbidden("Only an administrator" + ("" if admin_only else " or a BA, developer or QE lead") + " can do this in the Skill Studio")
    return user


def project(project_id: str, write: bool) -> None:
    if not auth.can_see_project(project_id):
        raise KeyError(f"project {project_id}")
    if write and not auth.can_write(project_id):
        raise auth.Forbidden("Your role in this project is viewer")


def plan(plan_id: str, write: bool = True) -> dict:
    if write:
        author()
    found = plans.get(plan_id)  # KeyError answers 404
    project(found["project_id"], write)
    return found
