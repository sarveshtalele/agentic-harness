"""Helpers shared by routers."""
from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, UploadFile
from pydantic import BaseModel, Field

from backend import config
from backend.db import db, row


def _project(project_id: str) -> dict:
    with db() as con:
        found = row(con.execute("SELECT * FROM projects WHERE id=?", (project_id,)))
    if not found:
        raise HTTPException(404, f"Project not found: {project_id}")
    return found


async def _save_upload(upload: UploadFile, target: Path) -> int:
    size = 0
    with target.open("wb") as sink:
        while chunk := await upload.read(1024 * 1024):
            size += len(chunk)
            if size > config.MAX_UPLOAD_BYTES:
                raise HTTPException(413, f"Upload exceeds {config.MAX_UPLOAD_BYTES // (1024 * 1024)} MB")
            sink.write(chunk)
    return size


class BrainstormAnswer(BaseModel):
    """What an analyst sends with a brainstorm step (R3): the answer, the question and play-back as edited, the chosen
    approach, or the builder-check answers. Redacted before it reaches the workflow, the run log and a prompt."""
    action: str = Field(default="", pattern=r"^(|answer|skip|propose)$")
    answer: str = Field(default="", max_length=4000)
    question: str = Field(default="", max_length=1000)
    understood: str = Field(default="", max_length=4000)
    choice: int | None = Field(default=None, ge=0, le=5)
    answers: list[str] = Field(default=[], max_length=5)

    def redacted(self) -> dict:
        from backend.core.security import redact

        return {"action": self.action, "answer": redact(self.answer), "question": redact(self.question), "understood": redact(self.understood),
                "choice": self.choice, "answers": [redact(a[:2000]) for a in self.answers]}
