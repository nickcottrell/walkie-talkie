"""High-level helper for token-emission integrations.

This is the wire-through point for callers like cue-vox that want to
emit tokens with PII scrubbed structurally + a VRGB record attached as
metadata. The helper composes boundary + encoder + response-shape
rendering into one call so the caller does not need to know about the
walkie-talkie internals.

Usage from cue-vox web.py (at conversation-summary token creation):

    from emit import emit_token_value
    rendered, walkie_record = emit_token_value(summary_text)
    cue_mem_create_token(
        label=...,
        value=rendered,
        metadata={..., "walkie_record": walkie_record},
        ...
    )

The rendered string is the new token value: structural header + scrubbed
prose. The walkie_record dict is the full VRGB record, attached to the
token's metadata for audit + future cross-tier routing.

Per substrate-worker doctrine: semantic content travels through the
response shape (which carries the prose body), not through the model's
generation. The shape library in shapes.py is the authored artifact.
"""

from __future__ import annotations

from typing import Any

from boundary import apply_boundary
from encoder import encode_from_scrubbed
from shapes import render


def emit_token_value(
    prose: str,
    extra_blacklist: list[str] | None = None,
    basis: str = "vrgb-default",
) -> tuple[str, dict[str, Any]]:
    """Wire prose through the walkie-talkie pipeline for token emission.

    Args:
        prose: The raw text being summarized into a token value.
        extra_blacklist: Optional caller-supplied blacklist words
            (e.g., NDA-specific terms for a given engagement).
        basis: Which axis vocabulary to encode against. Default
            "vrgb-default" -- callers can pin a specialized basis.

    Returns:
        (rendered, record_dict) where:
          rendered: structural header + scrubbed prose, ready to use
                    as a token value. Human-readable, semantically
                    intact (because the prose body fills slots that
                    the encoder did not compress away).
          record_dict: full VRGB record as a dict, for inclusion in
                       token metadata.

    Notes:
        - PII never lives in the rendered output; it is stripped at
          boundary time before the encoder sees it.
        - The boundary report (counts, policies applied, refusal
          status) is part of the record_dict, so audit trails carry
          across into the token metadata.
        - If the boundary refuses (e.g., PEM private key block), the
          rendered value is "[refused at boundary: <reason>]" -- the
          caller may choose to skip token creation entirely in that
          case, but emission does not crash.
    """
    # Boundary runs once. The encoder consumes the result directly via
    # encode_from_scrubbed() so we never re-pattern-match the same text.
    boundary_result = apply_boundary(prose, extra_blacklist=extra_blacklist)
    record = encode_from_scrubbed(boundary_result.scrubbed_text, boundary_result, basis)
    record_dict = record.to_dict()

    rendered = render(record, boundary_result.scrubbed_text)
    return rendered, record_dict


def emit_audit_summary(record_dict: dict[str, Any]) -> str:
    """Compact audit one-liner from a record dict. Useful for logs."""
    boundary = record_dict.get("boundary", {})
    sf = record_dict.get("structural_fields", {})
    primitives = record_dict.get("primitives", {})
    basin = primitives.get("basin", {}) or {}
    return (
        f"walkie:emit "
        f"basin={basin.get('centroid_hex', '?')} "
        f"topic={sf.get('topic_band', '')} "
        f"polarity={sf.get('polarity', 0)} "
        f"stripped={boundary.get('stripped_count', 0)} "
        f"policies={','.join(boundary.get('policies_applied', []))}"
    )
