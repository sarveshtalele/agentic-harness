"""Make the first admin's password (docs/PHASE2_PLAN.md R6): random, printed once, only its hash kept.

    python scripts/dev.py admin-password

Set the printed hash as ATLAS_ADMIN_PASSWORD_HASH (in .env locally, or a Key Vault reference in the App Service
settings on Azure) and remove ATLAS_ADMIN_PASSWORD. If ATLAS_PASSWORD_PEPPER is set, run this with the same pepper the
server uses, or the hash will not match. The password is shown here only; nothing writes it to a file.
"""
import secrets
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / "src")]

from backend.core.auth.passwords import hash_password  # noqa: E402


def main() -> None:
    password = secrets.token_urlsafe(18)  # 24 characters, about 144 bits
    print("Admin password (shown once, store it in your password manager):")
    print(f"  {password}")
    print("Set this in the server's settings, then restart:")
    print(f"  ATLAS_ADMIN_PASSWORD_HASH={hash_password(password)}")


if __name__ == "__main__":
    main()
