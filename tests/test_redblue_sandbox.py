"""Red and blue team: sandbox escape, argument safety and environment secrets."""

from __future__ import annotations

import pytest

from backend.core import security

from backend.repos import sandbox

from tests.conftest import connect_test_repo

pytest_plugins = ["tests.helpers_api"]


# ==============================================================================
# 3. SANDBOX COMMAND ISOLATION & PATH TRAVERSAL DEFENSE
# ==============================================================================

def test_sandbox_working_directory_escape_prevented(project):
    """Verify that sandbox.execute_command refuses execution if cwd is outside the project sandbox."""
    proj_id = project["id"] if isinstance(project, dict) else project
    connect_test_repo(proj_id)
    # Attempting to execute with cwd pointing to /etc or arbitrary host root
    result = sandbox.execute_command(proj_id, ["ls"], cwd="/etc")
    assert result["status"] == "error"
    assert "escapes project sandbox boundary" in result["message"]

    # Traversal cwd outside project
    result = sandbox.execute_command(proj_id, ["ls"], cwd="../../..")
    assert result["status"] == "error"
    assert "escapes project sandbox boundary" in result["message"]


def test_sandbox_command_argument_sanitization(project):
    """Verify command sanitization prevents NUL bytes and argument injection."""
    proj_id = project["id"] if isinstance(project, dict) else project
    connect_test_repo(proj_id)
    # Command containing NUL byte
    result = sandbox.execute_command(proj_id, ["ls\x00-la"])
    assert result["status"] == "error"
    assert "NUL byte" in result["message"]

    # npx command with dangerous shell escape flags
    npx_res = sandbox.run_npx(proj_id, ["--shell", "/bin/sh"])
    assert npx_res["status"] == "error"
    assert "Disallowed argument or shell escape" in npx_res["message"]


def test_security_safe_path_strict_traversal_defense(tmp_path):
    """Verify security.safe_path strictly defends against symlinks and path traversals."""
    root = tmp_path / "workspace"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()

    # Traversal attempts
    with pytest.raises(security.PathEscape):
        security.safe_path(root, "../../outside/secret.txt")

    with pytest.raises(security.PathEscape):
        security.safe_path(root, "subdir/../../../etc/passwd")

    with pytest.raises(security.PathEscape):
        security.safe_path(root, "/etc/shadow")

    # Symlink escape attempt
    try:
        (root / "symlink_out").symlink_to(outside)
        with pytest.raises(security.PathEscape):
            security.safe_path(root, "symlink_out/data.txt")
    except OSError:
        pass  # Skip symlink check on systems lacking symlink privileges

    # Write protection on protected directories
    for protected in [".git/config", "node_modules/pkg", ".venv/bin/activate"]:
        with pytest.raises(security.PathEscape):
            security.safe_path(root, protected, for_write=True)


# ==============================================================================
# 4. ENVIRONMENT CREDENTIAL ISOLATION
# ==============================================================================

def test_clean_sandbox_env_strips_ambient_secrets(monkeypatch):
    """Verify that ambient credentials and API keys in os.environ are never leaked into sandbox env."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-super-secret-123456789")
    monkeypatch.setenv("ATLAS_SECRET_KEY", "atlas-master-credential-xyz")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_123456789012345678901234567890")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret_aws_access_key_abcdef")

    clean_env = sandbox.clean_sandbox_env()

    assert "OPENAI_API_KEY" not in clean_env
    assert "ATLAS_SECRET_KEY" not in clean_env
    assert "GITHUB_TOKEN" not in clean_env
    assert "AWS_SECRET_ACCESS_KEY" not in clean_env
    assert clean_env.get("PYTHONDONTWRITEBYTECODE") == "1"


def test_clean_sandbox_env_filters_extra_env_secrets():
    """Verify that extra_env explicitly filters out sensitive tokens, passwords, and keys."""
    extra = {
        "MY_CUSTOM_TOKEN": "token_1234567",
        "DATABASE_PASSWORD": "supersecretpassword",
        "CLIENT_SECRET": "oauth-client-secret-xyz",
        "ALLOWED_BUILD_FLAG": "RELEASE",
        "PORT": "8080",
    }
    cleaned = sandbox.clean_sandbox_env(extra)

    assert "MY_CUSTOM_TOKEN" not in cleaned
    assert "DATABASE_PASSWORD" not in cleaned
    assert "CLIENT_SECRET" not in cleaned
    assert cleaned.get("ALLOWED_BUILD_FLAG") == "RELEASE"
    assert cleaned.get("PORT") == "8080"
