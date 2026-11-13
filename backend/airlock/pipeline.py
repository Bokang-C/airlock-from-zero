from .models import Segment, ScanResult, Finding
from .rules import signals
from .visibility import analyze_html


async def scan_html(content: str) -> tuple[ScanResult, str]:
    raw_segments, screenshot = await analyze_html(content)
    segments = []
    findings = []
    high = False
    sanitized = False
    escalate = False
    for raw in raw_segments:
        sig = signals(raw["text"])
        seg = Segment(**raw, suspicious=bool(sig), signals=sig)
        segments.append(seg)
        if seg.visibility == "hidden":
            sanitized = True
            if sig:
                high = True
                findings.append(Finding(reason=f"Hidden instruction ({', '.join(sig)}) · {', '.join(seg.reasons)}",
                                        severity="high", excerpt=seg.text[:190]))
        elif seg.visibility == "nonvisual":
            if sig:
                escalate = True
                findings.append(Finding(reason="Instruction-like accessibility or attribute content (review)",
                                        severity="warning", excerpt=seg.text[:190]))
        elif sig:
            escalate = True
            findings.append(Finding(reason=f"Visible instruction-like content ({', '.join(sig)})",
                                    severity="warning", excerpt=seg.text[:190]))
    # If an attacker splits a hidden sentence across multiple text nodes, check the joined text too.
    hidden_text = " ".join(s.text for s in segments if s.visibility == "hidden")
    if hidden_text and signals(hidden_text) and not high:
        high = True
        findings.append(Finding(reason="Instruction-like language across multiple hidden segments",
                                severity="high", excerpt=hidden_text[:190]))
    verdict = "block" if high else "sanitize" if sanitized else "allow"
    if high:
        reason = "Instruction-like content was hidden from the rendered human view. Agent access denied."
    elif sanitized:
        reason = "Non-visible DOM content was removed from the text supplied to an agent."
    elif escalate:
        reason = "Visible instruction-like content was identified for review; it was not automatically blocked."
    else:
        reason = "No hidden instruction indicators were found in the rendered page."
    clean_segments = [s.text for s in segments if s.visibility != "hidden"]
    return ScanResult(
        verdict=verdict, reason=reason, escalate=escalate,
        findings=findings[:40], segments=segments,
        human_view="\n".join(s.text for s in segments if s.visibility == "visible"),
        agent_view="\n".join(s.text for s in segments),
        sanitized_text="\n".join(clean_segments),
        stats={"visible":sum(s.visibility == "visible" for s in segments),
               "hidden":sum(s.visibility == "hidden" for s in segments),
               "nonvisual":sum(s.visibility == "nonvisual" for s in segments),
               "suspicious":sum(s.suspicious for s in segments)}
    ), screenshot
