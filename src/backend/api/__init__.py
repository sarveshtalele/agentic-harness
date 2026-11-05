"""REST API, one router per area."""
from backend.api import auth, chat, documents, findings, governance, harness, logs, observability, projects, repository, runs, settings, skills, templates, mcp

ROUTERS = [
    harness.router,
    auth.router,
    chat.router,
    documents.router,
    findings.router,
    governance.router,
    logs.router,
    observability.router,
    projects.router,
    repository.router,
    runs.router,
    settings.router,
    skills.router,
    templates.router,
    mcp.router,
]
