"""Secrets from Azure Key Vault (MASTER_PLAN Part 3, G7), read once at startup before any setting is read.

When `ATLAS_KEY_VAULT_URL` is set (`https://<name>.vault.azure.net`), each secret named in `ATLAS_KEY_VAULT_SECRETS`
is read with the App Service managed identity and put in the process environment under its setting name
(`atlas-admin-password` becomes `ATLAS_ADMIN_PASSWORD`). The vault wins over a value already in the environment.
The token comes from the platform's identity endpoint (`IDENTITY_ENDPOINT` and `IDENTITY_HEADER`, set by App Service),
over `httpx`, so no Azure SDK is needed. A set vault that cannot be read stops startup with a clear message: the app
never starts on stale or missing secrets. Values are never logged, never put in argv or a URL; only names are reported.
Without `ATLAS_KEY_VAULT_URL` nothing happens, and local runs keep `.env`.
"""
from __future__ import annotations

import os
import re
from urllib.parse import quote

import httpx

DEFAULT_SECRETS = "atlas-admin-password,atlas-secret-key,atlas-database-url,atlas-storage-url"
VAULT = re.compile(r"^https://[a-z0-9-]{3,24}\.vault\.azure\.net/?$")
NAME = re.compile(r"^[A-Za-z0-9-]{1,127}$")
API = "7.4"


class KeyVaultError(RuntimeError):
    pass


def setting_name(secret: str) -> str:
    return secret.upper().replace("-", "_")


def _token(client: httpx.Client) -> str:
    endpoint, header = os.environ.get("IDENTITY_ENDPOINT"), os.environ.get("IDENTITY_HEADER")
    if not endpoint or not header:
        raise KeyVaultError("ATLAS_KEY_VAULT_URL is set but this machine has no managed identity (IDENTITY_ENDPOINT and IDENTITY_HEADER "
                            "are missing). Turn on the web app's system-assigned identity, or remove ATLAS_KEY_VAULT_URL to use app settings.")
    params = {"resource": "https://vault.azure.net", "api-version": "2019-08-01"}
    if os.environ.get("AZURE_CLIENT_ID"):  # a user-assigned identity instead of the system-assigned one
        params["client_id"] = os.environ["AZURE_CLIENT_ID"]
    got = client.get(endpoint, params=params, headers={"X-IDENTITY-HEADER": header})
    if got.status_code != 200:
        raise KeyVaultError(f"The managed identity endpoint refused a Key Vault token (HTTP {got.status_code}).")
    return got.json()["access_token"]


def load(transport: httpx.BaseTransport | None = None) -> list[str]:
    """Read the vault's secrets into the environment. Returns the setting names loaded (never values)."""
    vault = os.environ.get("ATLAS_KEY_VAULT_URL", "").strip()
    if not vault:
        return []
    if not VAULT.match(vault):
        raise KeyVaultError("ATLAS_KEY_VAULT_URL must look like https://<name>.vault.azure.net")
    names = [n.strip() for n in os.environ.get("ATLAS_KEY_VAULT_SECRETS", DEFAULT_SECRETS).split(",") if n.strip()]
    if bad := [n for n in names if not NAME.match(n)]:
        raise KeyVaultError(f"Not a Key Vault secret name: {', '.join(bad)}")
    loaded = []
    with httpx.Client(timeout=15, transport=transport) as client:
        bearer = {"Authorization": f"Bearer {_token(client)}"}
        for name in names:
            got = client.get(f"{vault.rstrip('/')}/secrets/{quote(name)}", params={"api-version": API}, headers=bearer)
            if got.status_code == 404:
                continue  # not every deployment has every secret (for example atlas-storage-url before Blob is used)
            if got.status_code != 200:
                raise KeyVaultError(f"Key Vault refused the secret {name} (HTTP {got.status_code}). Give the web app's identity the role Key Vault Secrets User.")
            os.environ[setting_name(name)] = got.json()["value"]
            loaded.append(setting_name(name))
    return loaded
