"""Round-trip semantic-preservation metrics.

Given a ParaphraseCluster (multiple surface forms of the same content),
encode each paraphrase and score how well the geometric record agrees
across them. Aggregate across the corpus to produce a composite score.

Four metrics:

1. Topic agreement: do all paraphrases in a cluster get the same topic_band?
2. Polarity-sign agreement: do they get the same polarity sign (pos/neg/neutral)?
3. Regime agreement: do they get the same regime label?
4. Basin stability: how close (in shortest-arc hue distance) are the
   basin centroid hues across paraphrases? Lower is better.

Metrics 1-3 are categorical (% of clusters with full agreement).
Metric 4 is continuous (mean basin-hue dispersion in degrees, lower=stable).

The composite score is the mean of the three categorical rates plus
a basin-stability score (1 - dispersion/180), clipped to [0, 1].
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean

from corpus import REFUSAL_CASES, ParaphraseCluster
from encoder import encode


def _hex_to_hue(hex_str: str) -> float:
    """Recover the hue angle from a #rrggbb hex string. Inverse of the
    encoder's _hsl_to_hex (lossy on saturation/lightness, but hue is
    what we need for stability scoring)."""
    import colorsys
    if not hex_str.startswith("#") or len(hex_str) != 7:
        return 0.0
    r = int(hex_str[1:3], 16) / 255.0
    g = int(hex_str[3:5], 16) / 255.0
    b = int(hex_str[5:7], 16) / 255.0
    h, _, _ = colorsys.rgb_to_hls(r, g, b)
    return h * 360.0


def _shortest_arc(a: float, b: float) -> float:
    """Shortest-arc distance between two angles on the 360° wheel."""
    d = abs((a - b) % 360.0)
    return min(d, 360.0 - d)


def _polarity_sign(p: float) -> str:
    if p > 0.3:
        return "positive"
    if p < -0.3:
        return "negative"
    return "neutral"


@dataclass
class ClusterScore:
    label: str
    topic_match: bool
    polarity_match: bool
    regime_match: bool
    basin_dispersion_deg: float

    # Per-paraphrase fields for inspection
    topics_seen: list[str] = field(default_factory=list)
    polarities_seen: list[str] = field(default_factory=list)
    regimes_seen: list[str] = field(default_factory=list)
    basin_hues: list[float] = field(default_factory=list)


@dataclass
class BenchmarkScore:
    cluster_scores: list[ClusterScore]
    topic_agreement_rate: float
    polarity_agreement_rate: float
    regime_agreement_rate: float
    mean_basin_dispersion_deg: float
    refusal_uniformity: float
    composite: float


def score_cluster(cluster: ParaphraseCluster) -> ClusterScore:
    records = [encode(p) for p in cluster.paraphrases]

    topics = [r.structural_fields.get("topic_band", "") for r in records]
    polarities = [_polarity_sign(float(r.structural_fields.get("polarity", 0.0))) for r in records]
    regimes = [r.structural_fields.get("regime", "") for r in records]
    basin_hues = [
        _hex_to_hue(r.primitives.basin.centroid_hex)
        if r.primitives.basin else 0.0
        for r in records
    ]

    topic_match = len(set(topics)) == 1 and topics[0] == cluster.expected_topic
    polarity_match = len(set(polarities)) == 1 and polarities[0] == cluster.expected_polarity
    if cluster.expected_regime:
        regime_match = len(set(regimes)) == 1 and regimes[0] == cluster.expected_regime
    else:
        regime_match = len(set(regimes)) == 1  # any regime, as long as agreed

    # Basin dispersion: max pairwise shortest-arc distance.
    if len(basin_hues) > 1:
        max_arc = max(
            _shortest_arc(basin_hues[i], basin_hues[j])
            for i in range(len(basin_hues))
            for j in range(i + 1, len(basin_hues))
        )
    else:
        max_arc = 0.0

    return ClusterScore(
        label=cluster.label,
        topic_match=topic_match,
        polarity_match=polarity_match,
        regime_match=regime_match,
        basin_dispersion_deg=max_arc,
        topics_seen=topics,
        polarities_seen=polarities,
        regimes_seen=regimes,
        basin_hues=basin_hues,
    )


def score_corpus(corpus: list[ParaphraseCluster]) -> BenchmarkScore:
    cs = [score_cluster(c) for c in corpus]

    topic_rate = sum(1 for s in cs if s.topic_match) / len(cs)
    polarity_rate = sum(1 for s in cs if s.polarity_match) / len(cs)
    regime_rate = sum(1 for s in cs if s.regime_match) / len(cs)
    mean_basin = mean(s.basin_dispersion_deg for s in cs)

    # Refusal uniformity: every refusal-case input should yield a refused record.
    refused = [encode(t).boundary.refused for t in REFUSAL_CASES]
    refusal_rate = sum(1 for r in refused if r) / len(refused)

    # Composite score: simple mean of the three agreement rates,
    # the basin-stability score (1 - dispersion/180), and refusal uniformity.
    basin_stability = max(0.0, 1.0 - mean_basin / 180.0)
    composite = mean([
        topic_rate,
        polarity_rate,
        regime_rate,
        basin_stability,
        refusal_rate,
    ])

    return BenchmarkScore(
        cluster_scores=cs,
        topic_agreement_rate=topic_rate,
        polarity_agreement_rate=polarity_rate,
        regime_agreement_rate=regime_rate,
        mean_basin_dispersion_deg=mean_basin,
        refusal_uniformity=refusal_rate,
        composite=composite,
    )
