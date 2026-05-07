"""Natural language → VRGB JSON record.

Deterministic stdlib encoder. Same input always produces the same record.
The encoder reads scrubbed text (after the boundary pass) and emits
geometric primitives + hex addresses + structural fields.

This is v0: the geometric mapping is intentionally crude. The point is
a fixed, auditable function from text to colorspace, not a perfect
semantic model. Refinement comes once the protocol stabilizes.
"""

from __future__ import annotations

import hashlib
import re
import statistics
from datetime import datetime, timezone

from boundary import BoundaryResult, apply_boundary
from schema import (
    Auditability,
    Band,
    Basin,
    BoundaryReport,
    Primitives,
    Record,
)


POSITIVE_WORDS = frozenset({
    "good", "great", "yes", "agree", "love", "happy", "win", "success",
    "positive", "up", "progress", "ship", "land", "done", "ready",
})

NEGATIVE_WORDS = frozenset({
    "bad", "no", "fail", "loss", "down", "wrong", "broken", "stuck",
    "negative", "blocked", "stale", "stop", "halt",
})

REGIME_KEYWORDS = {
    "risk_on": frozenset({"buy", "long", "ship", "expand", "grow"}),
    "risk_off": frozenset({"sell", "short", "hold", "wait", "pause"}),
    "breakdown": frozenset({"crash", "broken", "fail", "halt", "regress"}),
}

# Topic bands: rough domain detection from keyword presence. Used to fill
# topic_band slot in response shapes. Falls back to "" if nothing matches.
TOPIC_KEYWORDS = {
    "policy": frozenset({"policy", "policies", "doctrine", "statute", "regulation", "constitution"}),
    "build": frozenset({"build", "ship", "deploy", "commit", "code", "encoder", "decoder"}),
    "design": frozenset({"design", "architecture", "shape", "schema", "pattern", "doctrine"}),
    "review": frozenset({"review", "audit", "verify", "check", "approve", "yes_no"}),
    "memory": frozenset({"token", "memory", "context", "summary", "recent", "session"}),
    "vrgb": frozenset({"vrgb", "hex", "basin", "band", "phase", "coherence", "geometric"}),
    "client": frozenset({"client", "engagement", "scope", "contract", "nda"}),
}


def _hash_to_hue(text: str) -> float:
    """Stable text → hue (0-360) via SHA-256 prefix.

    Used to assign hex addresses deterministically. Same string always
    maps to the same hue.
    """
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    raw = int.from_bytes(digest[:4], "big")
    return (raw % 36000) / 100.0


def _hsl_to_hex(h: float, s: float, l: float) -> str:
    """HSL (h in 0-360, s/l in 0-1) → #rrggbb. Stdlib only."""
    import colorsys
    r, g, b = colorsys.hls_to_rgb(h / 360.0, l, s)
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


def _stem(word: str) -> str:
    """Strip common English suffixes for keyword matching. Crude but
    enough to fold past-tense and plural forms into base.
    """
    for suffix in ("ing", "ed", "es", "s"):
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def _word_matches(text: str, vocab: frozenset[str]) -> int:
    """Count word matches against a vocab, with light stemming."""
    words = re.findall(r"\b\w+\b", text.lower())
    return sum(1 for w in words if w in vocab or _stem(w) in vocab)


def _polarity(text: str) -> float:
    """Return polarity score in [-1, 1] from word counts."""
    if not text.strip():
        return 0.0
    pos = _word_matches(text, POSITIVE_WORDS)
    neg = _word_matches(text, NEGATIVE_WORDS)
    if pos + neg == 0:
        return 0.0
    return (pos - neg) / (pos + neg)


def _coherence(text: str) -> float:
    """Sentence-length variance as inverse coherence proxy.

    High variance (mixed long/short) = low coherence (scattered).
    Low variance (uniform) = high coherence (aligned).
    Bounded [0, 1].
    """
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    if len(sentences) < 2:
        return 0.5
    lengths = [len(s.split()) for s in sentences]
    if not lengths or statistics.mean(lengths) == 0:
        return 0.5
    cv = statistics.pstdev(lengths) / statistics.mean(lengths)
    return max(0.0, min(1.0, 1.0 - cv))


def _detect_regime(text: str) -> str:
    """Identify dominant regime keyword family. Returns regime label or empty."""
    scores = {regime: _word_matches(text, kws) for regime, kws in REGIME_KEYWORDS.items()}
    best = max(scores.items(), key=lambda kv: kv[1])
    return best[0] if best[1] > 0 else ""


def _detect_topic_band(text: str) -> str:
    """Identify dominant topic-domain keyword family. Returns topic label or empty.

    Used to fill the topic_band slot in response shapes -- gives the
    structural header a domain hint without exposing original content.
    """
    scores = {topic: _word_matches(text, kws) for topic, kws in TOPIC_KEYWORDS.items()}
    best = max(scores.items(), key=lambda kv: kv[1])
    return best[0] if best[1] > 0 else ""


def _bands(text: str, basis: str) -> list[Band]:
    """Decompose text into 1-3 named bands by sentence chunk."""
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    if not sentences:
        return []
    bands: list[Band] = []
    for i, s in enumerate(sentences[:3]):
        hue = _hash_to_hue(s)
        bands.append(Band(
            axis=basis,
            centroid=hue,
            width=max(5.0, len(s.split()) * 1.5),
            phase_deg=hue,
        ))
    return bands


def encode_from_scrubbed(
    scrubbed: str,
    boundary_result: BoundaryResult,
    basis: str = "vrgb-default",
) -> Record:
    """Build a Record from already-boundary-passed text.

    Use this when the caller has already run apply_boundary() and wants
    to avoid re-running it. emit.py uses this path so the boundary pass
    only runs once per token-emission cycle.

    Args:
        scrubbed: text after PII stripping (boundary_result.scrubbed_text)
        boundary_result: the BoundaryResult that produced `scrubbed`
        basis: axis vocabulary identifier
    """
    record = Record(
        encoded_at=datetime.now(timezone.utc).isoformat(),
        boundary=BoundaryReport(
            policies_applied=boundary_result.policies_applied,
            stripped_count=boundary_result.stripped_count,
            refused=boundary_result.refused,
            refused_reason=boundary_result.refused_reason,
        ),
        auditability=Auditability(),
    )

    if boundary_result.refused:
        return record

    polarity = _polarity(scrubbed)
    coherence = _coherence(scrubbed)
    regime = _detect_regime(scrubbed)
    bands = _bands(scrubbed, basis)

    # Phase: positive polarity → 120° (green/forward), neutral → 240°
    # (blue/steady), negative → 0° (red/halt). Continuous along the wheel.
    if polarity >= 0:
        phase_deg = 240.0 - (polarity * 120.0)  # 240 → 120 as polarity climbs
    else:
        phase_deg = 240.0 + (abs(polarity) * 120.0)  # 240 → 360 (=0) as polarity drops
    phase_deg = phase_deg % 360.0

    # Basin: stable hash of full scrubbed text, anchored at the polarity hex.
    basin_hue = _hash_to_hue(scrubbed)
    basin_hex = _hsl_to_hex(basin_hue, 0.6, 0.5)
    basin_size = float(len(scrubbed.split())) / 100.0

    record.primitives = Primitives(
        basis=basis,
        phase_deg=phase_deg,
        coherence=coherence,
        bands=bands,
        basin=Basin(centroid_hex=basin_hex, size=min(1.0, basin_size)),
    )

    # Hex addresses: one per band, plus the basin centroid.
    addresses: list[str] = [_hsl_to_hex(b.centroid, 0.7, 0.5) for b in bands]
    addresses.append(basin_hex)
    record.hex_addresses = addresses

    record.structural_fields = {
        "polarity": round(polarity, 3),
        "regime": regime,
        "topic_band": _detect_topic_band(scrubbed),
        "word_count": len(scrubbed.split()),
        "sentence_count": len([s for s in re.split(r"[.!?]+", scrubbed) if s.strip()]),
    }

    return record


def encode(
    text: str,
    basis: str = "vrgb-default",
    extra_blacklist: list[str] | None = None,
) -> Record:
    """Encode natural language to a VRGB JSON-vector record.

    Convenience wrapper: runs the boundary pass, then encodes. For
    callers that need both the scrubbed text and the record, use
    apply_boundary() + encode_from_scrubbed() directly to avoid a
    redundant boundary pass.
    """
    boundary_result = apply_boundary(text, extra_blacklist=extra_blacklist)
    return encode_from_scrubbed(boundary_result.scrubbed_text, boundary_result, basis)
