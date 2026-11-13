-- R4 (docs/PHASE2_PLAN.md): MCP servers that sign in each member with OAuth 2.1 (PKCE), such as the Atlassian remote MCP.
ALTER TABLE mcp_servers ADD COLUMN auth TEXT NOT NULL DEFAULT 'none';           -- 'none' (headers, if any) or 'oauth'
ALTER TABLE mcp_servers ADD COLUMN oauth_client TEXT NOT NULL DEFAULT '';     -- discovered endpoints and the registered client id (JSON)

CREATE TABLE mcp_tokens (                                                      -- one member's tokens for one server, encrypted
  server_id TEXT NOT NULL REFERENCES mcp_servers(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  token_enc TEXT NOT NULL,
  expires_at DOUBLE PRECISION NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (server_id, user_id)
);

CREATE TABLE mcp_oauth_pending (                                               -- a sign-in in progress: single use, 10 minutes
  state TEXT PRIMARY KEY,
  server_id TEXT NOT NULL REFERENCES mcp_servers(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  verifier_enc TEXT NOT NULL,
  return_to TEXT NOT NULL DEFAULT '/',
  created_at DOUBLE PRECISION NOT NULL
);
