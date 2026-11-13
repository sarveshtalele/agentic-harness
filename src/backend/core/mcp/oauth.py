"""OAuth 2.1 with PKCE for remote MCP servers, one member at a time (docs/PHASE2_PLAN.md R4), as the MCP authorization spec
describes: protected-resource metadata (RFC 9728) names the authorization server, its metadata (RFC 8414) gives the
endpoints, dynamic client registration (RFC 7591) gives a public client id, and the resource indicator (RFC 8707) binds
the token to this MCP server. Each member signs in once; their tokens are encrypted in mcp_tokens, refreshed when they
expire, and never logged or put in a URL. The sign-in in progress is a single-use state of 10 minutes.
"""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
from urllib.parse import urlencode, urlparse

import httpx

from backend.core.mcp import registry
from backend.core.mcp.registry import McpProblem
from backend.core.security import decrypt, encrypt, register_secret
from backend.db import db, now, row

PENDING_SECONDS = 600


def _https(url: str) -> str:
    parsed = urlparse(url or "")
    if parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname in registry.LOOPBACK):
        raise McpProblem(400, f"OAuth endpoints must use https:// (got {parsed.scheme or 'no scheme'})")
    return url


def _get_json(client: httpx.Client, url: str) -> dict | None:
    response = client.get(_https(url), headers={"Accept": "application/json"})
    return response.json() if response.status_code == 200 else None


def discover(server: dict, redirect_uri: str) -> dict:
    """The server's endpoints and our registered client, found once and kept on the server row."""
    if server.get("oauth_client"):
        saved = json.loads(server["oauth_client"])
        if saved.get("redirect_uri") == redirect_uri:
            return saved
    origin = "{0.scheme}://{0.netloc}".format(urlparse(server["url"]))
    with httpx.Client(timeout=20, follow_redirects=False) as client:
        resource = _get_json(client, f"{origin}/.well-known/oauth-protected-resource{urlparse(server['url']).path}") \
            or _get_json(client, f"{origin}/.well-known/oauth-protected-resource") or {}
        issuer = (resource.get("authorization_servers") or [origin])[0].rstrip("/")
        meta = _get_json(client, f"{issuer}/.well-known/oauth-authorization-server") or _get_json(client, f"{issuer}/.well-known/openid-configuration")
        if not meta or not meta.get("authorization_endpoint") or not meta.get("token_endpoint"):
            raise McpProblem(502, f"{issuer} publishes no OAuth authorization server metadata")
        if "S256" not in meta.get("code_challenge_methods_supported", ["S256"]):
            raise McpProblem(502, "The authorization server does not support PKCE with S256")
        if not meta.get("registration_endpoint"):
            raise McpProblem(502, "The authorization server has no dynamic client registration; ask its administrator for a client id")
        registered = client.post(_https(meta["registration_endpoint"]), json={
            "client_name": "Agentic QE Platform", "redirect_uris": [redirect_uri], "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"], "token_endpoint_auth_method": "none"})
        if registered.status_code not in (200, 201) or not registered.json().get("client_id"):
            raise McpProblem(502, f"Client registration was refused (HTTP {registered.status_code})")
    found = {"authorization_endpoint": _https(meta["authorization_endpoint"]), "token_endpoint": _https(meta["token_endpoint"]),
             "client_id": registered.json()["client_id"], "redirect_uri": redirect_uri, "resource": resource.get("resource") or server["url"],
             "scopes": resource.get("scopes_supported") or []}
    with db() as con:
        con.execute("UPDATE mcp_servers SET oauth_client=? WHERE id=?", (json.dumps(found), server["id"]))
    return found


def start(server_id: str, user_id: str, redirect_uri: str, return_to: str = "/") -> str:
    """The provider's sign-in URL for this member. Only the PKCE challenge and an opaque state travel in it."""
    server = registry.get(server_id)
    if server.get("auth") != "oauth":
        raise McpProblem(400, "This server does not use OAuth sign-in")
    client = discover(server, redirect_uri)
    verifier, state = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    with db() as con:
        con.execute("DELETE FROM mcp_oauth_pending WHERE created_at < ?", (time.time() - PENDING_SECONDS,))
        con.execute("INSERT INTO mcp_oauth_pending (state, server_id, user_id, verifier_enc, return_to, created_at) VALUES (?,?,?,?,?,?)",
                    (state, server_id, user_id, encrypt(verifier).decode(), return_to if return_to.startswith("/") and not return_to.startswith("//") else "/", time.time()))
    query = {"response_type": "code", "client_id": client["client_id"], "redirect_uri": redirect_uri, "state": state,
             "code_challenge": challenge, "code_challenge_method": "S256", "resource": client["resource"]}
    if client["scopes"]:
        query["scope"] = " ".join(client["scopes"])
    return f"{client['authorization_endpoint']}?{urlencode(query)}"


def _save(server_id: str, user_id: str, answer: dict, old_refresh: str = "") -> None:
    if not answer.get("access_token"):
        raise McpProblem(502, "The authorization server returned no access token")
    tokens = {"access_token": answer["access_token"], "refresh_token": answer.get("refresh_token") or old_refresh}
    for value in tokens.values():
        register_secret(value)
    expires = time.time() + float(answer.get("expires_in") or 3600) - 60
    with db() as con:
        con.execute("INSERT OR REPLACE INTO mcp_tokens (server_id, user_id, token_enc, expires_at, updated_at) VALUES (?,?,?,?,?)",
                    (server_id, user_id, encrypt(json.dumps(tokens)).decode(), expires, now()))


def finish(state: str, code: str) -> tuple[str, str]:
    """Exchange the code for this member's tokens. Returns (server_id, return_to)."""
    with db() as con:
        pending = row(con.execute("SELECT * FROM mcp_oauth_pending WHERE state=?", (state,)))
        con.execute("DELETE FROM mcp_oauth_pending WHERE state=?", (state,))  # single use, whatever happens next
    if not pending or pending["created_at"] < time.time() - PENDING_SECONDS:
        raise McpProblem(400, "This sign-in link has expired or was already used. Start the sign-in again")
    client = json.loads(registry.get(pending["server_id"])["oauth_client"])
    with httpx.Client(timeout=20) as http:
        answer = http.post(client["token_endpoint"], data={"grant_type": "authorization_code", "code": code, "redirect_uri": client["redirect_uri"],
                                                           "client_id": client["client_id"], "code_verifier": decrypt(pending["verifier_enc"].encode()),
                                                           "resource": client["resource"]})
    if answer.status_code != 200:
        raise McpProblem(502, f"The authorization server refused the sign-in (HTTP {answer.status_code})")
    _save(pending["server_id"], pending["user_id"], answer.json())
    from backend.core.auth.base import _event

    _event(pending["user_id"], f"mcp.oauth_connected:{pending['server_id']}")  # the member's own sign-in, in the auth events
    return pending["server_id"], pending["return_to"]


def connected(server_id: str, user_id: str) -> bool:
    with db() as con:
        return bool(con.execute("SELECT 1 FROM mcp_tokens WHERE server_id=? AND user_id=?", (server_id, user_id)).fetchone())


def disconnect(server_id: str, user_id: str) -> None:
    with db() as con:
        con.execute("DELETE FROM mcp_tokens WHERE server_id=? AND user_id=?", (server_id, user_id))


def bearer(server_id: str, user_id: str) -> str:
    """This member's access token for the server, refreshed when it has expired; McpProblem 401 when they must sign in."""
    with db() as con:
        found = row(con.execute("SELECT * FROM mcp_tokens WHERE server_id=? AND user_id=?", (server_id, user_id)))
    if not found:
        raise McpProblem(401, "Sign in to this server first (Connect)")
    tokens = json.loads(decrypt(found["token_enc"].encode()))
    for value in tokens.values():
        register_secret(value)
    if found["expires_at"] > time.time():
        return tokens["access_token"]
    client = json.loads(registry.get(server_id)["oauth_client"])
    if not tokens.get("refresh_token"):
        disconnect(server_id, user_id)
        raise McpProblem(401, "Your sign-in to this server has ended. Connect again")
    with httpx.Client(timeout=20) as http:
        answer = http.post(client["token_endpoint"], data={"grant_type": "refresh_token", "refresh_token": tokens["refresh_token"],
                                                           "client_id": client["client_id"], "resource": client["resource"]})
    if answer.status_code != 200:
        disconnect(server_id, user_id)
        raise McpProblem(401, "Your sign-in to this server has ended. Connect again")
    _save(server_id, user_id, answer.json(), tokens["refresh_token"])
    return answer.json()["access_token"]
