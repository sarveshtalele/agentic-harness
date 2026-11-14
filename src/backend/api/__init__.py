"""REST API, one router per area."""
from backend.api import atlassian, auth, capabilities, chat, documents, features, findings, governance, logs, observability, plugins, projects, qe_trace, rag, repository, run_tests, runs, settings, skill_studio, skills, templates, traces, mcp

ROUTERS = [
    atlassian.router,
    auth.router,
    capabilities.router,
    chat.router,
    documents.router,
    features.router,
    findings.router,
    governance.router,
    logs.router,
    observability.router,
    plugins.router,
    projects.router,
    qe_trace.router,
    rag.router,
    repository.router,
    run_tests.router,
    runs.router,
    settings.router,
    skill_studio.router,
    skills.router,
    templates.router,
    traces.router,
    mcp.router,
]
