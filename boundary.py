"""Policy boundary: strip PII before geometric encoding.

This is where data-sensitivity and data-blacklist policies fire. Anything
that survives this pass enters the geometric layer; anything stripped is
counted but not preserved.

Strategy is conservative: regex-detect common PII patterns (emails, phones,
addresses, names with capitalized first+last) and replace with a marker.
The encoder only sees the scrubbed text; the boundary report records
what was removed at the structural level (counts only, no values).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Pattern catalog. Each entry: (name, regex, replacement_marker)
PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[EMAIL]"),
    ("phone_us", re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[PHONE]"),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN]"),
    ("credit_card", re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"), "[CARD]"),
    ("ipv4", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[IP]"),
    ("street_address", re.compile(r"\b\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way)\b"), "[ADDR]"),
    ("api_key_like", re.compile(r"\b(?:sk|pk|api|key)[-_][A-Za-z0-9]{16,}\b"), "[KEY]"),
]

# Hard-refuse patterns: if any of these match, the encoder refuses to emit.
# These represent material that should never enter the geometric layer
# even in scrubbed form.
REFUSE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA|EC|OPENSSH|DSA|PGP) PRIVATE KEY-----")),
]


@dataclass
class BoundaryResult:
    scrubbed_text: str
    stripped_count: int
    policies_applied: list[str]
    refused: bool
    refused_reason: str


def apply_boundary(text: str, extra_blacklist: list[str] | None = None) -> BoundaryResult:
    """Run the policy boundary over input text.

    Returns the scrubbed text and a structural report. The original text
    is not preserved or returned.
    """
    extra_blacklist = extra_blacklist or []

    for name, pattern in REFUSE_PATTERNS:
        if pattern.search(text):
            return BoundaryResult(
                scrubbed_text="",
                stripped_count=0,
                policies_applied=["refuse:" + name],
                refused=True,
                refused_reason=name,
            )

    scrubbed = text
    stripped_count = 0
    applied: list[str] = []

    for name, pattern, marker in PATTERNS:
        new_scrubbed, n = pattern.subn(marker, scrubbed)
        if n > 0:
            stripped_count += n
            applied.append("data-sensitivity:" + name)
        scrubbed = new_scrubbed

    for needle in extra_blacklist:
        if not needle:
            continue
        # Case-insensitive whole-word match.
        pattern = re.compile(r"\b" + re.escape(needle) + r"\b", re.IGNORECASE)
        new_scrubbed, n = pattern.subn("[REDACTED]", scrubbed)
        if n > 0:
            stripped_count += n
            applied.append("data-blacklist:custom")
        scrubbed = new_scrubbed

    return BoundaryResult(
        scrubbed_text=scrubbed,
        stripped_count=stripped_count,
        policies_applied=sorted(set(applied)),
        refused=False,
        refused_reason="",
    )


def verify_no_pii(text: str) -> bool:
    """Verify a string has no recognizable PII patterns. Used in tests
    and as a runtime invariant check on encoder output.
    """
    for _, pattern, _ in PATTERNS:
        if pattern.search(text):
            return False
    return True
