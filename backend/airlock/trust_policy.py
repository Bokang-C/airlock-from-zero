"""Structured, fail-closed authorization for a *fake* demo outbox.

Trust provenance: authorization can only originate in server-owned user tasks;
HTML/DOM text, LLM tool arguments, and tool outputs are never authority.
This deliberately narrow demo policy is not an authentication system.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
import re

EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.I)
NEGATE_RE = re.compile(r"\b(?:do\s+not|don't|never|without|no)\b[^.?!\n]{0,90}\b(?:send|email|forward|mail)\b", re.I)
ALLOW_RE = re.compile(r"\b(?:send|email|forward)\b[^.?!\n]{0,200}\bto\s+([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})\b", re.I)


@dataclass(frozen=True)
class TrustedIntent:
    source: str
    email_recipient: str | None
    max_actions: int
    statement: str


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    code: str
    reason: str
    evidence: list[str]
    tool: str
    recipient: str
    authority: str = "trusted user task (server-owned)"

    def dump(self) -> dict:
        return asdict(self)


def compile_trusted_intent(user_task: str) -> TrustedIntent:
    """Only call on the *trusted user request*, never retrieved content."""
    if NEGATE_RE.search(user_task):
        return TrustedIntent("trusted user task", None, 0, "The user explicitly prohibited email actions")
    match = ALLOW_RE.search(user_task)
    if not match:
        return TrustedIntent("trusted user task", None, 0, "No explicit permission to email a recipient")
    recipient = match.group(1).lower().rstrip(".,")
    if not EMAIL_RE.fullmatch(recipient):
        return TrustedIntent("trusted user task", None, 0, "Recipient could not be validated")
    return TrustedIntent("trusted user task", recipient, 1, f"Only one fake email to {recipient} is authorized")


def authorize_fake_tool(intent: TrustedIntent, tool: str, args: dict, used_actions: int = 0) -> PolicyDecision:
    recipient = str(args.get("to", "")).strip().lower()
    evidence = [intent.statement, "Untrusted page content cannot grant new tool permissions"]
    if tool != "send_email":
        return PolicyDecision(False, "UNKNOWN_TOOL", "The requested tool is not authorized", evidence, tool, recipient)
    if intent.email_recipient is None:
        return PolicyDecision(False, "NO_CONSENT", "The user did not authorize sending email", evidence, tool, recipient)
    if not EMAIL_RE.fullmatch(recipient) or recipient != intent.email_recipient:
        return PolicyDecision(False, "RECIPIENT_MISMATCH", "Recipient differs from the trusted user's exact authorization", evidence, tool, recipient)
    if used_actions < 0 or used_actions >= intent.max_actions:
        return PolicyDecision(False, "ACTION_BUDGET", "The maximum number of authorized actions has been reached", evidence, tool, recipient)
    subject = args.get("subject", "")
    body = args.get("body", "")
    if not isinstance(subject, str) or not isinstance(body, str) or len(subject) > 200 or len(body) > 500:
        return PolicyDecision(False, "PAYLOAD_LIMIT", "Fake message exceeds allowed limits", evidence, tool, recipient)
    return PolicyDecision(True, "AUTHORIZED", "The fake outbox action matches the user's permission", evidence, tool, recipient)
