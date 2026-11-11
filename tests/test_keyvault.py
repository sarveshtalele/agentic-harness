"""Key Vault secrets at startup (MASTER_PLAN Part 3, G7). Azure's two HTTP endpoints are played by httpx's own test
transport, so the real request shapes are checked: the identity header, the vault resource, the bearer token."""
import httpx
import pytest

from backend import keyvault

VAULT = "https://kv-agentic-qe.vault.azure.net"


def azure(secrets: dict, seen: list, vault_status: int = 200):
    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.host == "identity.local":
            assert request.headers["X-IDENTITY-HEADER"] == "id-header" and request.url.params["resource"] == "https://vault.azure.net"
            return httpx.Response(200, json={"access_token": "tok"})
        assert request.headers["Authorization"] == "Bearer tok" and request.url.params["api-version"] == keyvault.API
        if vault_status != 200:
            return httpx.Response(vault_status, json={})
        name = request.url.path.rsplit("/", 1)[1]
        return httpx.Response(200, json={"value": secrets[name]}) if name in secrets else httpx.Response(404, json={})
    return httpx.MockTransport(handle)


@pytest.fixture
def identity(monkeypatch):
    monkeypatch.setenv("IDENTITY_ENDPOINT", "http://identity.local/msi/token")
    monkeypatch.setenv("IDENTITY_HEADER", "id-header")
    monkeypatch.setenv("ATLAS_KEY_VAULT_URL", VAULT)
    for name in keyvault.DEFAULT_SECRETS.split(","):
        monkeypatch.delenv(keyvault.setting_name(name), raising=False)


def test_without_a_vault_nothing_is_read(monkeypatch):
    monkeypatch.delenv("ATLAS_KEY_VAULT_URL", raising=False)
    seen = []
    assert keyvault.load(azure({}, seen)) == [] and seen == []


def test_secrets_become_settings_and_a_missing_one_is_skipped(identity, monkeypatch):
    import os
    monkeypatch.setenv("ATLAS_ADMIN_PASSWORD", "value-from-app-settings")
    seen = []
    loaded = keyvault.load(azure({"atlas-admin-password": "from-the-vault-123", "atlas-secret-key": "k" * 48}, seen))
    assert loaded == ["ATLAS_ADMIN_PASSWORD", "ATLAS_SECRET_KEY"]  # names only; the database and storage secrets are not in this vault
    assert os.environ["ATLAS_ADMIN_PASSWORD"] == "from-the-vault-123" and os.environ["ATLAS_SECRET_KEY"] == "k" * 48  # the vault wins
    assert all("from-the-vault" not in str(r.url) for r in seen)  # values travel only in response bodies


@pytest.mark.parametrize("change, message", [
    ({"ATLAS_KEY_VAULT_URL": "https://evil.example.com"}, "must look like"),
    ({"IDENTITY_ENDPOINT": ""}, "no managed identity"),
    ({"ATLAS_KEY_VAULT_SECRETS": "atlas_admin/password"}, "Not a Key Vault secret name"),
])
def test_a_set_vault_that_cannot_be_used_stops_startup(identity, monkeypatch, change, message):
    for key, value in change.items():
        monkeypatch.setenv(key, value)
    with pytest.raises(keyvault.KeyVaultError, match=message):
        keyvault.load(azure({}, []))


def test_a_refused_secret_names_the_role_to_grant(identity):
    with pytest.raises(keyvault.KeyVaultError, match="Key Vault Secrets User"):
        keyvault.load(azure({}, [], vault_status=403))
