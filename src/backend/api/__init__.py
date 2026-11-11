"""REST API, one router per area."""
from backend.api import auth, capabilities, chat, documents, findings, governance, logs, observability, plugins, projects, repository, runs, settings, skill_studio, skills, templates, traces, mcp

ROUTERS = [
    auth.router,
    capabilities.router,
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
    traces.router,
    mcp.router,
]
