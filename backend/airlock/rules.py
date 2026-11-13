"""Simple, inspectable heuristics. Not a complete prompt-injection detector."""
import base64
import re
import unicodedata

PATTERNS = [
    ("instruction override", re.compile(r"(?:ignore|disregard|forget)\s+(?:all\s+)?(?:previous|prior|above|system|developer)\s+(?:instructions?|prompts?|messages?|rules?)", re.I)),
    ("role spoofing", re.compile(r"(?:\[\s*system\s*\]|<\s*/?system\s*>|you are now (?:the|a)|new system instruction)", re.I)),
    ("unauthorized action", re.compile(r"(?:send|forward|email|upload|post|exfiltrate|transmit)\b.{0,125}\b(?:secret|password|token|api.?key|private|confidential|inbox|account|data|email|address|attacker|evil|report)\b", re.I | re.S)),
    ("agent-directed command", re.compile(r"(?:assistant|agent|llm|ai|model)[,:]?\s+(?:you must|must|should|do not|ignore|send|forward|execute)", re.I)),
]

ZERO_WIDTH = re.compile(r"[\u200b-\u200f\u2060\ufeff]")
UNICODE_TAGS = re.compile(r"[\U000e0000-\U000e007f]")
BASE64_CANDIDATES = re.compile(r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{24,}={0,2}(?![A-Za-z0-9+/=])")


def normalize(text: str) -> str:
    # Preserve underlying text but erase common invisible separators for matching.
    text = ZERO_WIDTH.sub("", text)
    text = "".join(chr(ord(ch) - 0xE0000) if 0xE0020 <= ord(ch) <= 0xE007E else ch for ch in text)
    return unicodedata.normalize("NFKC", text)


def signals(text: str) -> list[str]:
    candidate = normalize(text)
    found = [label for label, regex in PATTERNS if regex.search(candidate)]
    if ZERO_WIDTH.search(text) and any(regex.search(candidate) for _, regex in PATTERNS):
        found.append("invisible Unicode obfuscation")
    if UNICODE_TAGS.search(text):
        found.append("Unicode tag characters")
    for match in BASE64_CANDIDATES.finditer(text[:12000]):
        try:
            decoded = base64.b64decode(match.group(0), validate=True).decode("utf-8", errors="ignore")
        except (ValueError, UnicodeDecodeError):
            continue
        if any(regex.search(decoded) for _, regex in PATTERNS):
            found.append("base64-encoded instruction")
            break
    return list(dict.fromkeys(found))
