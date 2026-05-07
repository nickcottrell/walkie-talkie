# Walkie-Talkie

Bidirectional translation between natural language and VRGB JSON-vector
records. The wire format is plain-record (auditable, not cipher); PII is
stripped at the encoder boundary so it never enters the geometric layer.

## Why

Agent stacks now run at multiple capability tiers — large-context models
at the top, small local models in the middle, chip-resident or edge
models at the bottom. Prose does not compress to the bottom of that
ladder. **VRGB primitives do.** Walkie-talkie is the encoder/decoder
pair that lets agents at any tier exchange the same content over a
shared geometric substrate.

- **Encoder:** natural language → VRGB record (with policy boundary)
- **Decoder:** VRGB record → natural language prose (via response shapes)
- **Substrate:** the JSON record format, readable by any agent that knows the schema

The substrate is the wire format. The encoder and decoder are the radios.

## Properties

| Property | Value |
|---|---|
| Determinism | Same input → same record (modulo timestamp) |
| Loss | Round-trip is lossy by design — only structural geometry survives |
| PII | Stripped at boundary; counts surfaced, values discarded |
| Cipher | None — records are plain JSON, no key, original not reconstructable |
| Audit | All records carry the policy list applied + stripped_count |
| Refusal | Hard patterns (private key blocks, etc.) refuse encoding entirely |

## Install

Stdlib only. Python 3.10+. No external dependencies.

```
git clone https://github.com/nickcottrell/walkie-talkie.git
cd walkie-talkie
python3 cli.py roundtrip "your text here"
```

## CLI

```
python3 cli.py encode "your text here" [--basis NAME] [--blacklist WORD ...]
python3 cli.py decode <record.json> [--mode prose|primitive|both]
python3 cli.py decode - < record.json
python3 cli.py roundtrip "your text here"
```

`roundtrip` shows the record + both decoder modes for inspection.

## Module surface

| Module | Purpose |
|---|---|
| `schema.py` | Record / Primitives / Band / Basin / BoundaryReport / Auditability dataclasses |
| `boundary.py` | PII pattern catalog + `apply_boundary` + `verify_no_pii` |
| `encoder.py` | `encode` (text → record) + `encode_from_scrubbed` (already-scrubbed → record) |
| `decoder.py` | `decode` (record → prose / primitive / both) |
| `shapes.py` | Response-shape library (refused / breakdown / strongly_polarized / default) |
| `emit.py` | `emit_token_value` — composes boundary + encode + render for one-call use |
| `json_boundary.py` | `scrub_json` / `scrub_json_file` — walk a JSON tree and scrub all string leaves |
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

Stripped at encode time:
- emails, US phones, SSNs, credit-card numbers, IPv4 addresses
- street addresses (`123 Main Street` form)
- API-key-like tokens (`sk_…`, `pk_…`, `api_…`, `key_…` with 16+ chars)
- caller-supplied blacklist words (case-insensitive, whole-word)

Refused at encode time (record emitted with `refused=true`, no primitives):
- PEM private key blocks (`-----BEGIN ... PRIVATE KEY-----`)

## Tests

```
python3 tests/test_walkie_talkie.py     # 34 tests: encoder, decoder, shapes, emit, schema
python3 tests/test_json_boundary.py     # 11 tests: JSON-tree boundary walker
```

## Benchmark

The load-bearing artifact for this repo: a round-trip semantic-preservation
harness that measures how much structural meaning survives encode → decode
across paraphrase pairs.

```
python3 benchmark/run.py                # writes benchmark/output/score.json + report.md
```

See `benchmark/README.md` for corpus, metrics, and methodology.

## Doctrine

`docs/substrate-worker.md` describes the design pattern walkie-talkie
implements: dumb model + tool manifest + canned response shapes. The
doctrine generalizes beyond walkie-talkie itself; any small-model
integration that follows the three-property contract qualifies.

## Provenance

Walkie-talkie originated inside the maestro chassis (a personal ops
engine) as the bridge between natural-language conversation and VRGB
geometric primitives. It was extracted into its own repository in
2026-05 once the protocol stabilized and the round-trip benchmark
became the load-bearing piece.

VRGB (object-into-colorspace immersion) is 3DMATH IP. The hue ontology,
spectral binding, and geometric primitives that walkie-talkie operates
on are documented in the VRGB-benchmarks repo and adjacent material.

## License

MIT. See `LICENSE`.
