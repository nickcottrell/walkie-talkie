# Walkie-Talkie

A small, dependency-free Python library that turns natural language into
**auditable JSON records** with **PII stripped at the boundary**, and
turns those records back into prose. Think of it as a structural radio:
two ends, plain-text wire format, nothing reconstructable from what
travels in between.

```
Input:    "Email me at nick@example.com about the build."
                                ↓ encode
Record:   {
            primitives: { phase_deg: 240, coherence: 0.83,
                          basin: { centroid_hex: "#cc3832", size: 0.07 } },
            hex_addresses: ["#73d826", "#32cc77"],
            structural_fields: { polarity: 0.0, topic_band: "build", ... },
            boundary: { stripped_count: 1,
                        policies_applied: ["data-sensitivity:email"] }
          }
                                ↓ decode (default shape)
Output:   "[basin=#cc3832 phase=240° (steady) coherence=0.83 (tight)
            polarity=neutral topic=build]
            Email me at [EMAIL] about the build."
```

The email is gone, replaced by a marker. The structural shape of the
content (topic, polarity, regime, basin) survives. The wire record is
plain JSON — anyone can read it, but the original input isn't
reconstructable from what's there.

## What you get

- **Structural PII stripping**, not honor-system. 7 regex patterns
  (emails, US phones, SSNs, credit cards, IPs, street addresses, API-
  key-like tokens) plus caller-supplied blacklists, applied at the
  encoder boundary. Counts and policies surfaced in the record so
  audits don't depend on trust.
- **Auditable wire format.** No cipher, no key — records are plain
  JSON. The information that's gone is structurally absent (compressed
  to coordinates), not encrypted away. This matters for compliance
  contexts where "we encrypted it" is a weaker answer than "we
  literally don't have it."
- **Cross-tier agent communication.** Big models, small local models,
  and chip-resident models all consume the same record format. Prose
  doesn't compress to the bottom of the capability ladder; geometric
  primitives do. Walkie-talkie is the wire between them.
- **Deterministic.** Same input always produces the same record
  (modulo timestamp). Useful for tests, reproducible audits, content-
  addressable storage.
- **Stdlib only.** Python 3.10+, zero dependencies. Drop in anywhere.
  No supply-chain surface to worry about.
- **Hard refusal for high-risk inputs.** PEM private key blocks etc.
  refuse encoding entirely; the record is emitted with `refused=true`
  and no primitives, so callers can quarantine without crashing.
- **Doctrine and benchmark, not just code.** The repo includes the
  substrate-worker design pattern (see `docs/substrate-worker.md`) and
  a round-trip semantic-preservation benchmark with a measurable
  composite score, so you can verify the encoder is actually doing
  its job.

## Quickstart

```bash
git clone https://github.com/nickcottrell/walkie-talkie.git
cd walkie-talkie
python3 cli.py roundtrip "We shipped the build, deploy is green."
```

For programmatic use:

```python
from emit import emit_token_value

rendered, record = emit_token_value(
    "Sync with alice@example.com about the contract.",
    extra_blacklist=["Project Falcon"],  # optional, case-insensitive
)
# rendered: structural header + scrubbed prose, ready to log/store/display
# record:   full VRGB record dict, ready to attach as audit metadata
```

## Properties at a glance

| Property | Value |
|---|---|
| Determinism | Same input → same record (modulo timestamp) |
| Round-trip loss | Lossy by design — only structural geometry survives |
| PII | Stripped at boundary; counts surfaced, values discarded |
| Cipher | None — records are plain JSON, no key |
| Audit | Every record carries the policy list applied + stripped_count |
| Refusal | Hard patterns (PEM private key blocks, etc.) refuse outright |
| Dependencies | None. Stdlib only. |
| Python | 3.10+ |

## CLI

```
python3 cli.py encode "your text here" [--basis NAME] [--blacklist WORD ...]
python3 cli.py decode <record.json> [--mode prose|primitive|both]
python3 cli.py decode - < record.json
python3 cli.py roundtrip "your text here"
```

`roundtrip` shows the record + both decoder modes, useful for inspection.

## Module surface

| Module | Purpose |
|---|---|
| `schema.py` | Record / Primitives / Band / Basin / BoundaryReport / Auditability dataclasses |
| `boundary.py` | PII pattern catalog + `apply_boundary` + `verify_no_pii` |
| `encoder.py` | `encode` (text → record) + `encode_from_scrubbed` (already-scrubbed → record) |
| `decoder.py` | `decode` (record → prose / primitive / both) |
| `shapes.py` | Response-shape library (refused / breakdown / strongly_polarized / default) |
| `emit.py` | `emit_token_value` — composes boundary + encode + render in one call |
| `json_boundary.py` | `scrub_json` / `scrub_json_file` — walk a JSON tree, scrub all string leaves |
| `cli.py` | Command-line entry point |

## Schema

```
Record
├── version          (int)
├── encoded_at       (ISO timestamp)
├── primitives
│   ├── basis        (str — which axes)
│   ├── phase_deg    (0–360)
│   ├── coherence    (0–1)
│   ├── bands        (list of {axis, centroid, width, phase_deg})
│   └── basin        ({centroid_hex, size})
├── hex_addresses    (list of #rrggbb)
├── structural_fields
│   ├── polarity     (-1 to 1)
│   ├── regime       (risk_on / risk_off / breakdown / "")
│   ├── topic_band   (policy / build / design / review / memory / vrgb / client / "")
│   ├── word_count
│   └── sentence_count
├── boundary
│   ├── policies_applied   (list of "policy:pattern")
│   ├── stripped_count
│   ├── refused
│   └── refused_reason
└── auditability
    ├── encoder_version
    ├── round_trip_lossy   (always true)
    └── no_pii_invariant   (always true)
```

## Boundary patterns

Stripped at encode time: emails, US phones, SSNs, credit-card numbers,
IPv4 addresses, street addresses (`123 Main Street` form), API-key-like
tokens (`sk_…`, `pk_…`, `api_…`, `key_…` with 16+ chars), and any
caller-supplied blacklist words (case-insensitive, whole-word).

Refused at encode time (record emitted with `refused=true`, no
primitives): PEM private key blocks (`-----BEGIN ... PRIVATE KEY-----`).

## Tests

```
python3 tests/test_walkie_talkie.py     # 34 tests: encoder, decoder, shapes, emit, schema
python3 tests/test_json_boundary.py     # 11 tests: JSON-tree boundary walker
```

## Benchmark

The load-bearing artifact for this repo: a round-trip semantic-
preservation harness that measures how much structural meaning survives
encode → decode across paraphrase pairs.

```
python3 benchmark/run.py                # writes benchmark/output/score.json + report.md
```

The composite score is the mean of: topic agreement, polarity-sign
agreement, regime agreement, basin stability, and refusal uniformity.
v0.1.0 ships with a composite of **0.755** on a curated 8-cluster +
3-refusal corpus. See `benchmark/README.md` for methodology.

## Doctrine

`docs/substrate-worker.md` describes the design pattern walkie-talkie
implements: **dumb model + tool manifest + canned response shapes**.
Output is templated, not composed; semantic content travels through
the *shape*, not through the model's generative capacity. The doctrine
generalizes — any small-model integration that follows the three-
property contract qualifies.

## Provenance

Walkie-talkie originated inside the maestro chassis (a personal ops
engine) as the bridge between natural-language conversation and VRGB
geometric primitives. It was extracted into its own repository in
2026-05 once the protocol stabilized and the round-trip benchmark
became the load-bearing piece.

VRGB (object-into-colorspace immersion) is 3DMATH IP. The hue ontology,
spectral binding, and geometric primitives that walkie-talkie operates
on are documented in adjacent material.

## License

MIT. See `LICENSE`.
