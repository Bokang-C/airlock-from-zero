from typing import Literal
from pydantic import BaseModel, Field, model_validator


class ScanRequest(BaseModel):
    content: str | None = Field(default=None, max_length=750_000)
    url: str | None = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def choose_one(self):
        if bool(self.content) == bool(self.url):
            raise ValueError("Provide exactly one of 'content' or 'url'")
        return self


class Segment(BaseModel):
    text: str
    visibility: Literal["visible", "hidden", "nonvisual"]
    reasons: list[str] = []
    suspicious: bool = False
    signals: list[str] = []
    source: str = "dom"


class Finding(BaseModel):
    reason: str
    severity: Literal["info", "warning", "high"]
    excerpt: str


class ScanResult(BaseModel):
    verdict: Literal["allow", "sanitize", "block"]
    reason: str
    escalate: bool
    findings: list[Finding]
    segments: list[Segment]
    human_view: str
    agent_view: str
    sanitized_text: str
    stats: dict[str, int]


class DemoRequest(BaseModel):
    scenario_id: str
    firewall_on: bool = True
