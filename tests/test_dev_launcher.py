"""`dev.py db` and `dev.py up` keep .env's database URL right (Windows setup, 2026-11-13): a stale or empty local URL is
replaced, a commented one is ignored, and a remote (Azure) one is never touched."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import pg_local  # noqa: E402


def test_a_stale_local_url_is_replaced_and_a_remote_one_kept(tmp_path):
    env = tmp_path / ".env"
    env.write_text("A=1\n# ATLAS_DATABASE_URL=postgresql://old\nATLAS_DATABASE_URL=postgresql://u:p@127.0.0.1:5000/x\n", encoding="utf-8")
    pg_local.write_url(env, "postgresql://u:q@127.0.0.1:6000/y")
    lines = env.read_text(encoding="utf-8").splitlines()
    assert lines == ["A=1", "# ATLAS_DATABASE_URL=postgresql://old", "ATLAS_DATABASE_URL=postgresql://u:q@127.0.0.1:6000/y"]
    env.write_text("ATLAS_DATABASE_URL=\n", encoding="utf-8")
    pg_local.write_url(env, "postgresql://u:q@localhost:6000/y")
    assert env.read_text(encoding="utf-8") == "ATLAS_DATABASE_URL=postgresql://u:q@localhost:6000/y\n"
    remote = "ATLAS_DATABASE_URL=postgresql://u:p@aqe.postgres.database.azure.com:5432/x\n"
    env.write_text(remote, encoding="utf-8")
    assert "left as is" in pg_local.write_url(env, "postgresql://u:q@127.0.0.1:6000/y")
    assert env.read_text(encoding="utf-8") == remote
