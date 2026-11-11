#!/usr/bin/env python3
"""Check an environment's settings without printing any value.

  python scripts/dev.py env-check --env local    reads .env and the process environment
  python scripts/dev.py env-check --env azure    checks the process environment (run inside the App Service SSH console)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "local": ["ATLAS_ADMIN_USERNAME", "ATLAS_ADMIN_PASSWORD", "ATLAS_DATABASE_URL"],
    "azure": ["ATLAS_PROFILE", "ATLAS_DATA_DIR", "ATLAS_DATABASE_URL", "ATLAS_ADMIN_USERNAME", "ATLAS_ADMIN_PASSWORD", "ATLAS_SECRET_KEY",
              "ATLAS_ALLOWED_HOSTS", "ATLAS_ALLOWED_ORIGINS"],
}
EXPECTED = {"azure": {"ATLAS_PROFILE": "web"}, "local": {}}


def _dotenv() -> dict[str, str]:
    path = ROOT / ".env"
    found = {}
    for line in path.read_text(encoding="utf-8").splitlines() if path.is_file() else []:
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            found[key.strip()] = value.strip().strip('"\'')
    return found


def main() -> int:

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", choices=["local", "azure"], required=True)
    which = parser.parse_args().env
    vault = []
    if os.environ.get("ATLAS_KEY_VAULT_URL"):  # the same Key Vault read the app does at startup; names only are reported
        sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
        from backend import keyvault
        try:
            vault = keyvault.load()
        except keyvault.KeyVaultError as exc:
            print(f"{which}: {exc}")
            return 1
    values = {**(_dotenv() if which == "local" else {}), **os.environ}
    problems = [f"missing {k}" for k in REQUIRED[which] if not values.get(k)]
    problems += [f"{k} should be {v}" for k, v in EXPECTED[which].items() if values.get(k) and values[k] != v]
    password, username = values.get("ATLAS_ADMIN_PASSWORD", ""), values.get("ATLAS_ADMIN_USERNAME", "")
    if password and (len(password) < 12 or password.lower() == username.lower()):
        problems.append("ATLAS_ADMIN_PASSWORD is weak: use 12+ characters, different from the username")
    if which == "local" and any(k.startswith("WEBSITE_") for k in os.environ):
        problems.append("Azure App Service variables are present: the local environment must not run with Azure settings")
    if vault:
        print(f"From Key Vault: {', '.join(vault)}")
    print(f"{which}: " + ("OK" if not problems else "; ".join(problems)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
