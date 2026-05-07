"""Tests for json_boundary.scrub_json + scrub_json_file.

Covers:
- Walks dict / list / nested structures, scrubs string leaves
- Numbers, bools, None pass through untouched
- Aggregate report counts strips + leaves correctly
- Refusal short-circuits and surfaces in the report
- File mode reads JSON, writes JSON; falls back to plain-text on parse error
- No-PII-invariant on the scrubbed output
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from boundary import verify_no_pii
from json_boundary import scrub_json, scrub_json_file


def test_scrub_simple_dict():
    payload = {"name": "ok", "email": "nick@example.com"}
    result = scrub_json(payload)
    assert result.refused is False
    assert result.scrubbed["email"] == "[EMAIL]"
    assert result.scrubbed["name"] == "ok"
    assert result.stripped_count == 1
    assert result.leaves_scanned == 2
    assert result.leaves_scrubbed == 1


def test_scrub_nested_structure():
    payload = {
        "subject": "Re: meeting",
        "body": {
            "from": "alice@example.com",
            "phone": "555-867-5309",
            "attachments": ["doc.pdf", "card 4111 1111 1111 1111"],
        },
    }
    result = scrub_json(payload)
    assert result.refused is False
    serialized = json.dumps(result.scrubbed)
    assert "@example.com" not in serialized
    assert "555-867-5309" not in serialized
    assert "4111 1111 1111 1111" not in serialized
    assert result.stripped_count == 3
    assert verify_no_pii(serialized)


def test_scrub_passes_through_non_strings():
    payload = {"count": 42, "active": True, "ratio": 0.5, "missing": None}
    result = scrub_json(payload)
    assert result.scrubbed["count"] == 42
    assert result.scrubbed["active"] is True
    assert result.scrubbed["ratio"] == 0.5
    assert result.scrubbed["missing"] is None
    assert result.stripped_count == 0
    assert result.leaves_scanned == 0


def test_scrub_list_of_strings():
    payload = ["a@b.com", "ok", "c@d.com"]
    result = scrub_json(payload)
    assert result.scrubbed[0] == "[EMAIL]"
    assert result.scrubbed[1] == "ok"
    assert result.scrubbed[2] == "[EMAIL]"
    assert result.stripped_count == 2
    assert result.leaves_scrubbed == 2


def test_scrub_refusal_short_circuits():
    payload = {
        "ok": "fine",
        "leak": "-----BEGIN RSA PRIVATE KEY-----\nMIIabc...",
    }
    result = scrub_json(payload)
    assert result.refused is True
    assert result.refused_reason == "private_key_block"


def test_scrub_extra_blacklist():
    payload = {"project": "Falcon launches Tuesday", "lead": "ok"}
    result = scrub_json(payload, extra_blacklist=["Falcon"])
    assert "Falcon" not in json.dumps(result.scrubbed)
    assert result.stripped_count >= 1


def test_scrub_aggregates_policies_unique_sorted():
    payload = {
        "a": "alice@example.com",
        "b": "bob@example.com",
        "c": "555-867-5309",
    }
    result = scrub_json(payload)
    assert result.stripped_count == 3
    # Two emails + one phone -> two distinct policies, sorted
    assert "data-sensitivity:email" in result.policies_applied
    assert "data-sensitivity:phone_us" in result.policies_applied
    assert result.policies_applied == sorted(result.policies_applied)


def test_scrub_to_dict_is_json_safe():
    payload = {"hello": "world", "email": "x@y.com"}
    result = scrub_json(payload)
    d = result.to_dict()
    # Should round-trip through json.dumps without error
    json.dumps(d)


def test_scrub_file_json_mode():
    payload = {"to": "u@example.com", "body": "Call 555-867-5309"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(payload, f)
        tmp = f.name

    try:
        result = scrub_json_file(tmp, in_place=True)
        assert result.refused is False
        with open(tmp) as f:
            written = json.load(f)
        assert "@example.com" not in json.dumps(written)
        assert "555-867-5309" not in json.dumps(written)
    finally:
        Path(tmp).unlink(missing_ok=True)


def test_scrub_file_plain_text_fallback():
    """If file is not JSON, treat the whole thing as one string leaf."""
    text = "Email me at u@example.com and call 555-867-5309."
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(text)
        tmp = f.name

    try:
        result = scrub_json_file(tmp, in_place=True)
        assert result.refused is False
        assert result.stripped_count == 2
        with open(tmp) as f:
            written = f.read()
        assert "@example.com" not in written
        assert "555-867-5309" not in written
    finally:
        Path(tmp).unlink(missing_ok=True)


def test_scrub_file_does_not_write_on_refusal():
    """Refused payloads must leave the file untouched."""
    payload = "ok line\n-----BEGIN RSA PRIVATE KEY-----\nabc"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(payload)
        tmp = f.name

    try:
        result = scrub_json_file(tmp, in_place=True)
        assert result.refused is True
        with open(tmp) as f:
            written = f.read()
        assert written == payload  # untouched
    finally:
        Path(tmp).unlink(missing_ok=True)


if __name__ == "__main__":
    import traceback

    tests = [v for k, v in dict(globals()).items()
             if k.startswith("test_") and callable(v)]
    passed = failed = 0
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
