"""JSON-tree boundary pass.

Generic helper that walks a JSON-decoded structure (dict / list / scalar)
and runs the walkie-talkie boundary on every string leaf. PII is stripped
in place; an aggregate report rolls up the per-leaf BoundaryResults.

Used by inbound and outbound boundary wirings:
- inbound: pull-agent sanitize (Zapier payloads → tokens)
- outbound: CueSync egress (request bodies → wire)

The walker is conservative: it visits every string, regardless of key
name. Refusal patterns (e.g., PEM private key blocks) trigger refusal
on the *whole* artifact -- the caller decides what to do with a refused
payload (drop, quarantine, alert).

Returns a JsonBoundaryResult that is JSON-serializable so it can attach
as audit metadata to tokens or egress logs.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from boundary import apply_boundary


@dataclass
class JsonBoundaryResult:
    """Aggregate report from walking a JSON tree through the boundary."""
    scrubbed: Any
    stripped_count: int = 0
    leaves_scanned: int = 0
    leaves_scrubbed: int = 0
    policies_applied: list[str] = field(default_factory=list)
    refused: bool = False
    refused_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # `scrubbed` is the in-place-modified payload; sometimes it's
        # not JSON-serializable (e.g., contains None deep in a tree
        # that was already a dict of dicts). Round-trip via json to
        # ensure the report itself is always JSON-safe.
        d["scrubbed"] = json.loads(json.dumps(d["scrubbed"], default=str))
        return d


def _walk(node: Any, agg: JsonBoundaryResult, extra_blacklist: list[str] | None) -> Any:
    """Recursively walk node; scrub string leaves; mutate-by-return.

    On refusal, sets agg.refused and short-circuits further descent.
    The returned tree may be partially scrubbed at the point of refusal;
    callers should check agg.refused before using the result.
    """
    if agg.refused:
        return node

    if isinstance(node, dict):
        return {k: _walk(v, agg, extra_blacklist) for k, v in node.items()}

    if isinstance(node, list):
        return [_walk(v, agg, extra_blacklist) for v in node]

    if isinstance(node, str):
        agg.leaves_scanned += 1
        result = apply_boundary(node, extra_blacklist=extra_blacklist)
        if result.refused:
            agg.refused = True
            agg.refused_reason = result.refused_reason
            return node  # leave as-is; caller decides
        if result.stripped_count > 0:
            agg.leaves_scrubbed += 1
            agg.stripped_count += result.stripped_count
            for p in result.policies_applied:
                if p not in agg.policies_applied:
                    agg.policies_applied.append(p)
        return result.scrubbed_text

    # numbers, bool, None -- pass through
    return node


def scrub_json(
    payload: Any,
    extra_blacklist: list[str] | None = None,
) -> JsonBoundaryResult:
    """Walk a JSON-decoded payload and scrub all string leaves.

    Args:
        payload: the JSON-decoded artifact (dict, list, or scalar)
        extra_blacklist: optional caller-supplied blacklist words

    Returns:
        JsonBoundaryResult with scrubbed payload + aggregate report.
        If `refused` is True, the payload at that point is the original
        (un-scrubbed) value -- the caller must handle it.
    """
    agg = JsonBoundaryResult(scrubbed=None)
    agg.scrubbed = _walk(payload, agg, extra_blacklist)
    agg.policies_applied.sort()
    return agg


def scrub_json_file(
    path: str,
    extra_blacklist: list[str] | None = None,
    in_place: bool = True,
) -> JsonBoundaryResult:
    """Convenience: load a JSON file, scrub it, optionally write back.

    If the file is not valid JSON, the whole-file content is treated
    as a single string leaf (so plain-text payloads are handled too).
    """
    with open(path, "r") as f:
        raw = f.read()

    try:
        payload = json.loads(raw)
        was_json = True
    except json.JSONDecodeError:
        payload = raw
        was_json = False

    result = scrub_json(payload, extra_blacklist=extra_blacklist)

    if in_place and not result.refused:
        with open(path, "w") as f:
            if was_json:
                json.dump(result.scrubbed, f, indent=2)
            else:
                f.write(result.scrubbed)

    return result
