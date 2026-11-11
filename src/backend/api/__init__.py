"""REST API, one router per area."""
from backend.api import auth, chat, documents, findings, governance, logs, observability, plugins, projects, repository, runs, settings, skill_studio, skills, templates, mcp

ROUTERS = [
    auth.router,
    chat.router,
    documents.router,
    findings.router,
    governance.router,
    logs.router,
    observability.router,
    plugins.router,
    projects.router,
    repository.router,
    runs.router,
    settings.router,
    skill_studio.router,
    skills.router,
    templates.router,
    mcp.router,
]
