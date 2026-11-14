"""What the document-analyst agent returns. Code drops chunk ids it was not given and quotes that are not in the saved source."""
from __future__ import annotations

from pydantic import BaseModel, Field


class RankedIds(BaseModel):
    ids: list[str] = Field(default_factory=list)


class Cited(BaseModel):
    chunk: str = Field(min_length=1)
    quote: str = Field(min_length=1)


class DocumentAnswer(BaseModel):
    found: bool
    answer: str = ""
    citations: list[Cited] = Field(default_factory=list)
