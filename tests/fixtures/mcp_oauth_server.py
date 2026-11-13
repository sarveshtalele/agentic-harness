"""A real MCP server behind OAuth 2.1 with PKCE, for the R4 tests: the stand-in for the Atlassian remote MCP (tests only).

It publishes protected-resource and authorization-server metadata, registers clients dynamically, approves every
sign-in at once (no login page), checks the PKCE verifier and the resource, issues and refreshes tokens, and serves two
tools over streamable HTTP only with a valid bearer token: `search(query)` returns JSON results and `fetch(id)` the text.
`app(base)` builds it for a base URL; `TOKENS` and `REGISTERED` let a test look inside.
"""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
from urllib.parse import urlencode

from mcp.server.mcpserver import MCPServer
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Route

PAGES = {"PAY-142": ("PAY-142 Refund rules", "Refunds above 500 EUR need finance approval. Card orders only."),
         "CONF-9": ("Payments v2 spec", "Partial refunds are allowed within 30 days of delivery.")}
TOKENS: dict[str, str] = {}  # access token -> "valid" | "expired"
REGISTERED: list[dict] = []
_codes: dict[str, dict] = {}
_refresh: set[str] = set()


def app(base: str):
    server = MCPServer("atlassian-stand-in")

    @server.tool()
    def search(query: str) -> str:
        """Search Jira issues and Confluence pages."""
        hits = [{"id": k, "title": t, "url": f"{base}/browse/{k}"} for k, (t, body) in PAGES.items() if query.lower() in f"{t} {body}".lower()]
        return json.dumps({"results": hits})

    @server.tool()
    def fetch(id: str) -> str:  # noqa: A002 - the tool's argument name
        """Fetch one issue or page by id."""
        return PAGES[id][1]

    web = server.streamable_http_app(streamable_http_path="/mcp")

    async def resource(_: Request):
        return JSONResponse({"resource": f"{base}/mcp", "authorization_servers": [base]})

    async def metadata(_: Request):
        return JSONResponse({"issuer": base, "authorization_endpoint": f"{base}/authorize", "token_endpoint": f"{base}/token",
                             "registration_endpoint": f"{base}/register", "code_challenge_methods_supported": ["S256"]})

    async def register(request: Request):
        body = await request.json()
        REGISTERED.append(body)
        return JSONResponse({"client_id": f"client-{len(REGISTERED)}", **body}, status_code=201)

    async def authorize(request: Request):
        q = request.query_params
        assert q["code_challenge_method"] == "S256" and q["resource"] == f"{base}/mcp"
        code = secrets.token_urlsafe(16)
        _codes[code] = {"challenge": q["code_challenge"], "client": q["client_id"], "redirect": q["redirect_uri"]}
        return RedirectResponse(f"{q['redirect_uri']}?{urlencode({'code': code, 'state': q['state']})}", status_code=302)

    async def token(request: Request):
        form = await request.form()
        if form["grant_type"] == "refresh_token":
            if form["refresh_token"] not in _refresh:
                return JSONResponse({"error": "invalid_grant"}, status_code=400)
        else:
            issued = _codes.pop(form["code"], None)
            digest = base64.urlsafe_b64encode(hashlib.sha256(form["code_verifier"].encode()).digest()).decode().rstrip("=")
            if not issued or issued["challenge"] != digest or issued["redirect"] != form["redirect_uri"]:
                return JSONResponse({"error": "invalid_grant"}, status_code=400)
        access, refresh = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
        TOKENS[access], _ = "valid", _refresh.add(refresh)
        return JSONResponse({"access_token": access, "refresh_token": refresh, "expires_in": 3600, "token_type": "Bearer"})

    web.router.routes[0:0] = [Route("/.well-known/oauth-protected-resource/mcp", resource), Route("/.well-known/oauth-protected-resource", resource),
                              Route("/.well-known/oauth-authorization-server", metadata), Route("/register", register, methods=["POST"]),
                              Route("/authorize", authorize), Route("/token", token, methods=["POST"])]

    async def guarded(scope, receive, send):
        if scope["type"] == "http" and scope["path"].startswith("/mcp"):
            header = dict(scope["headers"]).get(b"authorization", b"").decode()
            if TOKENS.get(header.removeprefix("Bearer ")) != "valid":
                await JSONResponse({"error": "invalid_token"}, status_code=401)(scope, receive, send)
                return
        await web(scope, receive, send)

    return guarded
