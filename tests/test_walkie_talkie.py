"""Walkie-talkie test suite.

Covers:
- Determinism: same input → same record
- Boundary: PII patterns stripped, counts reported
- Refusal: hard-refuse patterns block emission
- Auditability: no PII in encoded output
- Roundtrip: decode produces structurally consistent prose
- Schema: records survive json round-trip
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from boundary import apply_boundary, verify_no_pii
from decoder import decode
from emit import emit_token_value, emit_audit_summary
from encoder import encode
from schema import record_from_dict
from shapes import render, select_shape


def _record_minus_timestamp(record_dict: dict) -> dict:
    """Drop the encoded_at field for determinism comparisons."""
    out = dict(record_dict)
    out.pop("encoded_at", None)
    return out


def test_determinism_same_input_same_record():
    text = "Yeah, the build shipped clean. We are aligned and forward."
    r1 = encode(text)
    r2 = encode(text)
    assert _record_minus_timestamp(r1.to_dict()) == _record_minus_timestamp(r2.to_dict()), (
        "Encoder must be deterministic"
    )


def test_boundary_strips_email():
    text = "Contact me at john.doe@example.com for the project status."
    record = encode(text)
    assert record.boundary.stripped_count >= 1
    assert "data-sensitivity:email" in record.boundary.policies_applied
    assert "@example.com" not in json.dumps(record.to_dict())


def test_boundary_strips_phone():
    text = "Call me at 555-123-4567 tomorrow."
    record = encode(text)
    assert record.boundary.stripped_count >= 1
    assert any("phone" in p for p in record.boundary.policies_applied)


def test_boundary_strips_ssn():
    text = "SSN on file is 123-45-6789."
    record = encode(text)
    assert record.boundary.stripped_count >= 1
    assert "123-45-6789" not in json.dumps(record.to_dict())


def test_boundary_strips_credit_card():
    text = "Card 4111 1111 1111 1111 declined."
    record = encode(text)
    assert record.boundary.stripped_count >= 1
    assert "4111 1111 1111 1111" not in json.dumps(record.to_dict())


def test_boundary_strips_street_address():
    text = "Meeting at 123 Main Street next Tuesday."
    record = encode(text)
    assert record.boundary.stripped_count >= 1
    assert "123 Main Street" not in json.dumps(record.to_dict())


def test_boundary_refuses_private_key():
    text = "Here's the key: -----BEGIN RSA PRIVATE KEY-----\nMIIabc..."
    record = encode(text)
    assert record.boundary.refused
    assert record.boundary.refused_reason == "private_key_block"
    assert record.primitives.bands == []


def test_boundary_extra_blacklist():
    text = "Project Codename Falcon launches Tuesday."
    record = encode(text, extra_blacklist=["Falcon"])
    assert record.boundary.stripped_count >= 1
    assert "Falcon" not in json.dumps(record.to_dict())
    assert "data-blacklist:custom" in record.boundary.policies_applied


def test_no_pii_invariant_in_output():
    """Encoder output should never contain recognizable PII patterns."""
    text = "John Doe at john@example.com called 555-867-5309 from 192.168.1.1."
    record = encode(text)
    serialized = json.dumps(record.to_dict())
    assert verify_no_pii(serialized), "Encoded record contains PII patterns"


def test_polarity_positive():
    record = encode("We shipped the build, the deploy was a great success.")
    assert record.structural_fields["polarity"] > 0


def test_polarity_negative():
    record = encode("The build broke, the deploy was a fail, everything stuck.")
    assert record.structural_fields["polarity"] < 0


def test_coherence_high_for_uniform_sentences():
    text = "Build green. Deploy clean. Tests pass. Ship done."
    record = encode(text)
    assert record.primitives.coherence >= 0.5


def test_record_roundtrips_through_json():
    text = "Yeah, the architecture holds. Let it ship."
    original = encode(text)
    serialized = json.dumps(original.to_dict())
    reconstructed = record_from_dict(json.loads(serialized))
    assert reconstructed.primitives.basis == original.primitives.basis
    assert reconstructed.primitives.phase_deg == original.primitives.phase_deg
    assert len(reconstructed.primitives.bands) == len(original.primitives.bands)
    assert reconstructed.hex_addresses == original.hex_addresses


def test_decode_prose_mode():
    record = encode("Forward and clean.")
    text = decode(record, mode="prose")
    assert "basin" in text.lower()
    assert "#" in text  # hex address surfaced


def test_decode_primitive_mode():
    record = encode("Forward and clean.")
    text = decode(record, mode="primitive")
    assert "basis=" in text
    assert "phase=" in text
    assert "coherence=" in text


def test_decode_refused_record():
    record = encode("-----BEGIN RSA PRIVATE KEY-----\nabc")
    text = decode(record)
    assert "refused" in text.lower()


def test_decode_reports_boundary_strip():
    record = encode("Email me at a@b.com please.")
    text = decode(record)
    assert "stripped" in text.lower()


def test_apply_boundary_directly():
    """Boundary module is callable independently of the encoder."""
    result = apply_boundary("a@b.com and 555-867-5309")
    assert result.stripped_count == 2
    assert not result.refused
    assert verify_no_pii(result.scrubbed_text)


# ----------------------------------------------------------------------------
# Slot extraction (topic_band)
# ----------------------------------------------------------------------------


def test_topic_band_policy():
    record = encode("We synced the policy doctrine and statute today.")
    assert record.structural_fields["topic_band"] == "policy"


def test_topic_band_build():
    record = encode("Shipped the encoder, deployed the build, committed the code.")
    assert record.structural_fields["topic_band"] == "build"


def test_topic_band_vrgb():
    record = encode("VRGB hex basin band phase coherence.")
    assert record.structural_fields["topic_band"] == "vrgb"


def test_topic_band_empty_when_unknown():
    record = encode("The cat sat on the mat and looked outside.")
    assert record.structural_fields["topic_band"] == ""


# ----------------------------------------------------------------------------
# Response shapes
# ----------------------------------------------------------------------------


def test_shape_default_carries_structural_header():
    record = encode("Aligned and steady today.")
    rendered = render(record, "Aligned and steady today.")
    assert rendered.startswith("[")
    assert "basin=" in rendered
    assert "phase=" in rendered
    assert "Aligned and steady today." in rendered


def test_shape_breakdown_when_breakdown_regime():
    record = encode("The system crashed, the build failed, everything halted.")
    shape = select_shape(record)
    assert shape.name == "breakdown"
    rendered = render(record, "scrubbed prose here")
    assert "breakdown signal" in rendered


def test_shape_strongly_polarized_positive():
    record = encode("Great win, success, great progress, ready to ship!")
    shape = select_shape(record)
    assert shape.name in {"strongly_polarized", "breakdown"}


def test_shape_refused_for_private_key():
    record = encode("-----BEGIN RSA PRIVATE KEY-----\nabc")
    rendered = render(record, "")
    assert "refused at boundary" in rendered


# ----------------------------------------------------------------------------
# emit.py — high-level integration helper
# ----------------------------------------------------------------------------


def test_emit_token_value_returns_pair():
    rendered, record_dict = emit_token_value("Aligned and forward today.")
    assert isinstance(rendered, str)
    assert isinstance(record_dict, dict)
    assert "primitives" in record_dict
    assert "boundary" in record_dict


def test_emit_token_value_strips_pii_in_rendered():
    """The rendered token value must not contain PII patterns."""
    rendered, record_dict = emit_token_value(
        "Email me at nick@example.com about the build."
    )
    assert "@example.com" not in rendered
    assert "[EMAIL]" in rendered  # marker present in scrubbed prose
    assert verify_no_pii(rendered)


def test_emit_token_value_preserves_semantic_prose():
    """Rendered value must carry the original prose (scrubbed) so
    fresh readers can understand what was discussed."""
    rendered, _ = emit_token_value(
        "We discussed the walkie-talkie encoder architecture today."
    )
    assert "walkie-talkie" in rendered
    assert "encoder" in rendered
    assert "architecture" in rendered


def test_emit_token_value_has_structural_header():
    rendered, _ = emit_token_value("Some text.")
    first_line = rendered.split("\n")[0]
    assert first_line.startswith("[")
    assert first_line.endswith("]")
    assert "basin=" in first_line


def test_emit_token_value_blacklist_propagates():
    rendered, record_dict = emit_token_value(
        "Project Falcon launches Tuesday.",
        extra_blacklist=["Falcon"],
    )
    assert "Falcon" not in rendered
    assert record_dict["boundary"]["stripped_count"] >= 1


def test_emit_audit_summary_one_liner():
    _, record_dict = emit_token_value("Aligned, ready, shipping.")
    summary = emit_audit_summary(record_dict)
    assert summary.startswith("walkie:emit")
    assert "basin=" in summary
    assert "stripped=" in summary


def test_emit_token_refused_returns_structured_refusal():
    rendered, record_dict = emit_token_value(
        "-----BEGIN RSA PRIVATE KEY-----\nabc"
    )
    assert "refused at boundary" in rendered
    assert record_dict["boundary"]["refused"] is True


# ----------------------------------------------------------------------------
# Refactor regression: encode() and encode_from_scrubbed() agree
# ----------------------------------------------------------------------------


def test_encode_and_encode_from_scrubbed_agree():
    """Convenience wrapper encode() must produce the same record as
    apply_boundary() + encode_from_scrubbed() called directly. Guards
    against drift if the two paths get out of sync.
    """
    from encoder import encode_from_scrubbed

    text = "We shipped the substrate-worker doctrine and it landed clean."
    via_wrapper = encode(text)
    boundary = apply_boundary(text)
    via_split = encode_from_scrubbed(boundary.scrubbed_text, boundary)

    a = _record_minus_timestamp(via_wrapper.to_dict())
    b = _record_minus_timestamp(via_split.to_dict())
    assert a == b, "encode() and encode_from_scrubbed() must agree"


if __name__ == "__main__":
    import traceback
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_") and callable(v)]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL {t.__name__}: {e}")
            traceback.print_exc()
            failed += 1
        except Exception as e:
            print(f"ERROR {t.__name__}: {e}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
