"""Roles: every route has a rule, the access matrix, and what a viewer may do."""
import re

import pytest

from backend.app import PUBLIC_PATHS, app
from backend.core import auth
from tests.helpers_access import IDS, World, account, world  # noqa: F401 - fixtures
from tests.helpers_api import USER_PASSWORD, client, make_user, sign_in, unique  # noqa: F401 - fixtures


# ---- every route has a rule, and the rule gives the right answer to each kind of person ----

def routes():
    return [(method.upper(), path) for path, methods in app.openapi()["paths"].items() if path.startswith(("/api/", "/agui/")) and path not in PUBLIC_PATHS for method in methods]


def test_every_route_has_an_access_rule():
    missing = [f"{m} {p}" for m, p in routes() if not auth.rule_of(p)]
    assert not missing, f"No access rule for {missing}. Add the path to ADMIN_ONLY, ADMIN_WRITES, OWNED_PATHS, or SESSION_ONLY in core/auth.py"
    assert len(routes()) > 70


def test_every_route_names_its_feature_or_is_core():
    from backend.core.auth import features

    loose = [f"{m} {p}" for m, p in routes() if not features.feature_of(p) and not features.CORE.match(p)]
    assert not loose, f"Name a feature for {loose} in core/auth/features.py (ROUTES), or list it in CORE"


def test_every_workflow_names_its_feature():
    from backend.core.auth import features
    from backend.maf.engine import REGISTRY
    from backend.maf import workflows  # noqa: F401 - registers them

    assert set(REGISTRY) <= set(features.WORKFLOWS), f"Name a feature for {set(REGISTRY) - set(features.WORKFLOWS)} in features.WORKFLOWS"


def test_a_path_with_no_rule_is_refused_for_everyone_but_the_admin():
    user = {"id": "usr_x", "role": "user", "account_role": "developer"}
    assert auth.access_problem("GET", "/api/brand-new-thing", user)[0] == 403
    assert auth.access_problem("GET", "/api/brand-new-thing", {"id": "admin", "role": "admin", "account_role": "admin"}) is None


ADMIN_ONLY = ("/api/users", "/api/connections", "/api/logs", "/api/auth/events", "/api/models", "/api/usage", "/api/agents/guardrail-events", "/api/capabilities/sync")
ADMIN_WRITE = ("/api/settings", "/api/prompts", "/api/agents", "/api/evals")
# R2 features, written out from the plan's table (12.3): which routes need which feature, and each role's defaults
FEATURE_ROUTES = (("/agui/harness", "harness"), ("/api/chats/{thread_id}/todos", "harness"), ("/api/chats/{thread_id}/terminal", "harness"),
                  ("/api/projects/{project_id}/sources", "ba"), ("/api/findings", "bugs"), ("/api/projects/{project_id}/findings", "bugs"),
                  ("/api/skill-studio", "skills"), ("/api/mcp", "mcp"), ("/api/documents", "docs"), ("/api/projects/{project_id}/documents", "docs"),
                  ("/api/templates", "docs"), ("/api/projects/{project_id}/templates", "docs"), ("/api/traces", "traces"), ("/api/observability", "traces"),
                  ("/api/projects/{project_id}/observability", "traces"), ("/api/usage", "usage"))
ROLE_FEATURES = {"developer": {"harness", "qe", "bugs", "docs", "downloads", "traces"}, "viewer": {"docs"}}  # runs: by workflow, in the handler
PERSONA_ROLE = {"viewer": "viewer"}  # every other persona is a developer account
VIEWER_MAY_WRITE = ("/api/auth/logout", "/api/auth/desktop-session", "/api/account/password", "/api/account/email")  # a viewer may use the desktop app, read-only


def expected(persona, method, template):
    """Written out on its own, not read from core/auth.py."""
    write = method != "GET"
    scoped = any("{" + i + "}" in template for i in IDS)
    if persona == "admin":
        return None
    feature = next((f for prefix, f in FEATURE_ROUTES if template == prefix or template.startswith(prefix + "/")), None)
    if feature and feature not in ROLE_FEATURES[PERSONA_ROLE.get(persona, "developer")]:
        return 403
    if template.startswith("/api/features") and template != "/api/features/me":
        return 403
    if template.startswith(ADMIN_ONLY) or template.endswith(("/repo/local", "/transfer", "/workspace")):
        return 403
    if write and (template.startswith(ADMIN_WRITE) or template == "/api/skills/{name}/health"):  # checking runs skill scripts
        return 403
    if write and persona == "viewer" and template not in VIEWER_MAY_WRITE:
        return 403
    if scoped:
        if persona == "stranger":
            return 404
        if persona != "owner" and ("/members" in template or (method == "DELETE" and template == "/api/projects/{project_id}")):
            return 403
        if write and persona == "viewer-member":
            return 403
    return None


@pytest.mark.parametrize("persona", ["viewer", "developer", "viewer-member", "stranger", "owner", "admin"])
def test_access_matrix_over_every_route(world, persona):
    user, wrong = world.persona(persona), []
    for method, template in routes():
        path = re.sub(r"\{(\w+)\}", lambda m: world.ids.get(m.group(1), "1" if m.group(1) in {"gate", "version"} else "x"), template)
        found = auth.access_problem(method, path, user)
        want = expected(persona, method, template)
        if (found[0] if found else None) != want:
            wrong.append((persona, method, template, found, want))
    assert not wrong, wrong


def test_anonymous_gets_401_on_the_new_routes(world):
    from fastapi.testclient import TestClient

    anonymous = TestClient(app)
    pid = world.project["id"]
    for method, url in (("GET", f"/api/projects/{pid}/members"), ("POST", f"/api/projects/{pid}/transfer"), ("POST", "/api/account/password"), ("PUT", "/api/settings/gate-roles")):
        assert anonymous.request(method, url).status_code == 401


def test_viewer_reads_but_cannot_write_and_the_message_names_the_role(world):
    pid = world.project["id"]
    assert world.viewer.get(f"/api/projects/{pid}/overview").status_code == 200
    refused = world.viewer.post(f"/api/projects/{pid}/runs", json={"workflow": "ba", "input": {}})
    assert refused.status_code == 403 and "viewer" in refused.json()["message"]
    assert world.viewer.post("/api/projects", json={"name": "Mine"}).status_code == 403
    assert world.viewer.post(f"/api/approvals/{world.ids['approval_id']}/decide", json={"approved": True}).status_code == 403
    assert world.viewer.post(f"/api/projects/{pid}/gates/0/decision", json={"approved": True}).status_code == 403
    assert world.viewer.post("/api/auth/logout").status_code == 204
    demoted = world.demoted.patch(f"/api/projects/{pid}", json={"description": "x"})
    assert demoted.status_code == 403 and "project is viewer" in demoted.json()["message"].replace("in this ", "")
    assert world.dev.patch(f"/api/projects/{pid}", json={"description": "by a member"}).status_code == 200
