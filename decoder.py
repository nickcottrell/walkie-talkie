"""VRGB JSON record → natural language.

Reads a record and narrates the geometric content in English. The
narration is structural: position, regime, basin, polarity. The
original input is not reconstructable -- only its shape in colorspace.

Output is intentionally bilingual where useful: the geometric primitive
is named, then glossed in English. Per the c2d2-architecture doctrine,
the primitive form is the compression layer, the prose is comprehension.
"""

from __future__ import annotations

from schema import Record


def _phase_label(phase_deg: float) -> str:
    """Map angular phase to a regime label."""
    p = phase_deg % 360.0
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


def _coherence_label(c: float) -> str:
    if c >= 0.75:
        return "tight"
    if c >= 0.5:
        return "aligned"
    if c >= 0.25:
        return "loose"
    return "scattered"


def _polarity_label(p: float) -> str:
    if p > 0.3:
        return "positive"
    if p < -0.3:
        return "negative"
    return "neutral"


def decode(record: Record, mode: str = "prose") -> str:
    """Render a record as text. Modes: 'prose' (default), 'primitive', 'both'."""
    if record.boundary.refused:
        return f"[refused: {record.boundary.refused_reason}]"

    prim = record.primitives
    sf = record.structural_fields
    basin_hex = prim.basin.centroid_hex if prim.basin else "#000000"

    phase_label = _phase_label(prim.phase_deg)
    coh_label = _coherence_label(prim.coherence)
    pol_label = _polarity_label(float(sf.get("polarity", 0.0)))
    regime = sf.get("regime", "")

    primitive_form = (
        f"basis={prim.basis} "
        f"phase={prim.phase_deg:.1f}° ({phase_label}) "
        f"coherence={prim.coherence:.2f} ({coh_label}) "
        f"basin={basin_hex} (size={prim.basin.size if prim.basin else 0:.2f}) "
        f"polarity={sf.get('polarity', 0.0):+.2f} ({pol_label})"
    )
    if regime:
        primitive_form += f" regime={regime}"

    band_count = len(prim.bands)
    stripped = record.boundary.stripped_count
    boundary_note = (
        f" [boundary stripped {stripped} pattern{'s' if stripped != 1 else ''}]"
        if stripped > 0 else ""
    )

    article = "An" if coh_label[0] in "aeiou" else "A"
    prose_form = (
        f"{article} {coh_label}, {pol_label} signal in the {basin_hex} basin, "
        f"phase {phase_label} ({prim.phase_deg:.0f}°) on the {prim.basis} basis. "
        f"{band_count} band{'s' if band_count != 1 else ''} resolved."
    )
    if regime:
        prose_form += f" Regime reads as {regime}."
    prose_form += boundary_note

    if mode == "primitive":
        return primitive_form
    if mode == "both":
        return f"{primitive_form}\n  → {prose_form}"
    return prose_form
