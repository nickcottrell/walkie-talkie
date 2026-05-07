#!/usr/bin/env python3
"""Round-trip semantic-preservation benchmark runner.

Encodes each paraphrase in the corpus, computes per-cluster agreement
metrics, and writes:

  benchmark/output/score.json   — machine-readable metrics + per-cluster detail
  benchmark/output/report.md    — human-readable summary

Exit code is the number of clusters that failed any agreement metric
(useful for CI gating). Composite score is also surfaced on stdout.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

# Path bootstrap: walkie-talkie modules live one level up from benchmark/
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))           # local benchmark/ modules
sys.path.insert(0, str(_HERE.parent))    # walkie-talkie root

from corpus import CORPUS                 # noqa: E402
from metrics import score_corpus          # noqa: E402


def _fmt_pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def write_score_json(score, out_path: Path) -> None:
    payload = {
        "summary": {
            "topic_agreement_rate": score.topic_agreement_rate,
            "polarity_agreement_rate": score.polarity_agreement_rate,
            "regime_agreement_rate": score.regime_agreement_rate,
            "mean_basin_dispersion_deg": score.mean_basin_dispersion_deg,
            "refusal_uniformity": score.refusal_uniformity,
            "composite": score.composite,
        },
        "clusters": [asdict(c) for c in score.cluster_scores],
        "corpus_size": len(score.cluster_scores),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2))


def write_report_md(score, out_path: Path) -> None:
    lines = [
        "# Walkie-Talkie Round-Trip Benchmark",
        "",
        f"Corpus: {len(score.cluster_scores)} paraphrase clusters",
        "",
        "## Summary",
        "",
        f"- **Composite score:** {_fmt_pct(score.composite)}",
        f"- Topic agreement: {_fmt_pct(score.topic_agreement_rate)}",
        f"- Polarity-sign agreement: {_fmt_pct(score.polarity_agreement_rate)}",
        f"- Regime agreement: {_fmt_pct(score.regime_agreement_rate)}",
        f"- Mean basin dispersion: {score.mean_basin_dispersion_deg:.1f}° "
        f"(stability {_fmt_pct(max(0.0, 1.0 - score.mean_basin_dispersion_deg / 180.0))})",
        f"- Refusal uniformity: {_fmt_pct(score.refusal_uniformity)}",
        "",
        "## Per-cluster detail",
        "",
        "| Cluster | Topic | Polarity | Regime | Basin dispersion |",
        "|---|---|---|---|---|",
    ]
    for c in score.cluster_scores:
        topic = "✓" if c.topic_match else "✗"
        polarity = "✓" if c.polarity_match else "✗"
        regime = "✓" if c.regime_match else "✗"
        lines.append(
            f"| {c.label} | {topic} | {polarity} | {regime} | "
            f"{c.basin_dispersion_deg:.1f}° |"
        )

    lines.extend([
        "",
        "## Failure detail (where any metric was ✗)",
        "",
    ])
    failures = [c for c in score.cluster_scores
                if not (c.topic_match and c.polarity_match and c.regime_match)]
    if not failures:
        lines.append("_No failures._")
    else:
        for c in failures:
            lines.append(f"### `{c.label}`")
            if not c.topic_match:
                lines.append(f"- Topic: {c.topics_seen} (expected uniform)")
            if not c.polarity_match:
                lines.append(f"- Polarity: {c.polarities_seen}")
            if not c.regime_match:
                lines.append(f"- Regime: {c.regimes_seen}")
            lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n")


def main() -> int:
    score = score_corpus(CORPUS)

    out_dir = _HERE / "output"
    write_score_json(score, out_dir / "score.json")
    write_report_md(score, out_dir / "report.md")

    print(f"composite={score.composite:.3f}")
    print(f"  topic_agreement={score.topic_agreement_rate:.3f}")
    print(f"  polarity_agreement={score.polarity_agreement_rate:.3f}")
    print(f"  regime_agreement={score.regime_agreement_rate:.3f}")
    print(f"  basin_dispersion={score.mean_basin_dispersion_deg:.1f}°")
    print(f"  refusal_uniformity={score.refusal_uniformity:.3f}")
    print(f"  → {out_dir / 'score.json'}")
    print(f"  → {out_dir / 'report.md'}")

    failures = [c for c in score.cluster_scores
                if not (c.topic_match and c.polarity_match and c.regime_match)]
    return len(failures)


if __name__ == "__main__":
    sys.exit(main())
