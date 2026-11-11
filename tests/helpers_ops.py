"""Shared helpers for the operations tests."""

from backend.db import db, new_id, now


# ---- one active run -----------------------------------------------------------

def insert_run(project_id, workflow, status):
    run_id = new_id("run")
    with db() as con:
        con.execute("INSERT INTO runs (id, project_id, workflow, status, input, state, started_at) VALUES (?,?,?,?,'{}','{}',?)", (run_id, project_id, workflow, status, now()))
    return run_id
