from pydantic import BaseModel
from typing import Any

class SourceResult(BaseModel):
    source: str
    status: str
    items: list[dict[str, Any]] = []
    message: str | None = None

class Signal(BaseModel):
    token: str
    mint: str | None = None
    action: str
    confidence: float
    reasons: list[str]
    sources: list[str]
    observed_at: str
