"""Response-shape templates: pre-canned prose forms with slots.

Per the substrate-worker pattern (dumb model + tool manifest + canned
response shapes): semantic content travels through the *shape*, not
through model generation. Each shape is a template; slots get filled
from the VRGB record + scrubbed prose. The library of shapes is the
authored, defensible artifact -- 3DMATH IP at the prose layer.

A shape declares:
- name: identifier
- when: predicate that decides if this shape applies to a given record
- render: callable (record, scrubbed_prose) -> str

The library is ordered. The first shape whose `when` predicate fires
is selected. The last entry is always a default fallback so emission
never returns empty.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from schema import Record


@dataclass
class ResponseShape:
    name: str
    when: Callable[[Record], bool]
    render: Callable[[Record, str], str]


def _phase_label(deg: float) -> str:
    p = deg % 360.0
    if 100.0 <= p <= 140.0:
        return "forward"
    if 220.0 <= p <= 260.0:
        return "steady"
    if p >= 350.0 or p <= 10.0:
        return "halted"
    if p < 100.0:
        return "trailing"
    if p < 220.0:
        return "ascending"
    return "receding"


def _polarity_label(p: float) -> str:
    if p > 0.3:
        return "positive"
    if p < -0.3:
        return "negative"
    return "neutral"


def _coherence_label(c: float) -> str:
    if c >= 0.75:
        return "tight"
    if c >= 0.5:
        return "aligned"
    if c >= 0.25:
        return "loose"
    return "scattered"


def _structural_header(record: Record) -> str:
    """The geometric one-liner prepended to scrubbed prose. Encodes
    primitives so a fresh reader (human or model) gets the structural
    frame without having to parse the full record.
    """
    prim = record.primitives
    sf = record.structural_fields
    basin_hex = prim.basin.centroid_hex if prim.basin else "#000000"
    parts = [
        f"basin={basin_hex}",
        f"phase={prim.phase_deg:.0f}° ({_phase_label(prim.phase_deg)})",
        f"coherence={prim.coherence:.2f} ({_coherence_label(prim.coherence)})",
        f"polarity={_polarity_label(float(sf.get('polarity', 0.0)))}",
    ]
    regime = sf.get("regime", "")
    if regime:
        parts.append(f"regime={regime}")
    topic = sf.get("topic_band", "")
    if topic:
        parts.append(f"topic={topic}")
    return "[" + " ".join(parts) + "]"


# ---------------------------------------------------------------------------
# Shape implementations
# ---------------------------------------------------------------------------


def _shape_refused(record: Record) -> bool:
    return record.boundary.refused


def _render_refused(record: Record, prose: str) -> str:
    reason = record.boundary.refused_reason or "policy"
    return f"[refused at boundary: {reason}]"


def _shape_breakdown(record: Record) -> bool:
    return record.structural_fields.get("regime") == "breakdown"


def _render_breakdown(record: Record, prose: str) -> str:
    header = _structural_header(record)
    return f"{header}\n[breakdown signal] {prose}"


def _shape_strongly_polarized(record: Record) -> bool:
    p = float(record.structural_fields.get("polarity", 0.0))
    return abs(p) >= 0.5


def _render_strongly_polarized(record: Record, prose: str) -> str:
    header = _structural_header(record)
    p = float(record.structural_fields.get("polarity", 0.0))
    direction = "forward" if p > 0 else "halted"
    return f"{header}\n[{direction}] {prose}"


def _shape_default(record: Record) -> bool:
    return True


def _render_default(record: Record, prose: str) -> str:
    return f"{_structural_header(record)}\n{prose}"


SHAPE_LIBRARY: list[ResponseShape] = [
    ResponseShape("refused", _shape_refused, _render_refused),
    ResponseShape("breakdown", _shape_breakdown, _render_breakdown),
    ResponseShape("strongly_polarized", _shape_strongly_polarized, _render_strongly_polarized),
    ResponseShape("default", _shape_default, _render_default),
]


def select_shape(record: Record) -> ResponseShape:
    """Return the first shape whose `when` predicate fires.
    The default shape always matches, so this never returns None.
    """
    for shape in SHAPE_LIBRARY:
        if shape.when(record):
            return shape
    return SHAPE_LIBRARY[-1]


def render(record: Record, scrubbed_prose: str) -> str:
    """Render a record + scrubbed prose using the matching response shape."""
    shape = select_shape(record)
    return shape.render(record, scrubbed_prose)
