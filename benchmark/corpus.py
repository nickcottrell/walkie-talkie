"""Paraphrase corpus for round-trip semantic-preservation benchmark.

Each entry is a ParaphraseCluster: a label + 2-4 surface paraphrases
expressing the same underlying content. The encoder should produce
similar geometric records across paraphrases in a cluster (high
within-cluster similarity) and dissimilar records across clusters
(low between-cluster similarity).

The corpus is curated by hand to span:
- Topic bands (policy, build, design, review, memory, vrgb, client)
- Polarity directions (positive, negative, neutral)
- Regimes (risk_on, risk_off, breakdown, none)
- Coherence levels (tight aligned vs scattered)
- Refusal cases (PEM key blocks etc. should refuse uniformly)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ParaphraseCluster:
    label: str
    expected_topic: str        # "" if unknown / mixed
    expected_polarity: str     # "positive" | "negative" | "neutral"
    expected_regime: str       # "" if none expected
    paraphrases: list[str]


CORPUS: list[ParaphraseCluster] = [
    ParaphraseCluster(
        label="policy_drafting_positive",
        expected_topic="policy",
        expected_polarity="positive",
        expected_regime="",
        paraphrases=[
            "We drafted three policies and synced them clean. Doctrine landed great.",
            "The doctrine and statute work shipped successfully today, all green.",
            "Three new policies are ready, the routing table is updated, success.",
        ],
    ),
    ParaphraseCluster(
        label="build_shipping_positive",
        expected_topic="build",
        expected_polarity="positive",
        expected_regime="risk_on",
        paraphrases=[
            "We shipped the encoder and the build is ready to deploy.",
            "Build green, encoder deployed, we are ready to ship the next piece.",
            "The code shipped clean, we are expanding into the next deploy phase.",
        ],
    ),
    ParaphraseCluster(
        label="build_failure_breakdown",
        expected_topic="build",
        expected_polarity="negative",
        expected_regime="breakdown",
        paraphrases=[
            "The build broke, the deploy halted, the encoder is broken.",
            "Build failed, deploy halted, the system crashed, everything regressed.",
            "Crash on deploy, the build halted, regress in the encoder.",
        ],
    ),
    ParaphraseCluster(
        label="design_review_neutral",
        expected_topic="design",
        expected_polarity="neutral",
        expected_regime="",
        paraphrases=[
            "Reviewing the design pattern and the schema for the doctrine.",
            "Design review pass on the schema and the architecture pattern.",
            "We are reviewing the doctrine schema and the architectural shape.",
        ],
    ),
    ParaphraseCluster(
        label="vrgb_geometric_neutral",
        expected_topic="vrgb",
        expected_polarity="neutral",
        expected_regime="",
        paraphrases=[
            "The VRGB hex basin band phase coherence are the geometric primitives.",
            "Hex addresses, basins, bands, phase, and coherence form the VRGB layer.",
            "VRGB geometric primitives include hex, basin, band, phase, coherence.",
        ],
    ),
    ParaphraseCluster(
        label="memory_token_neutral",
        expected_topic="memory",
        expected_polarity="neutral",
        expected_regime="",
        paraphrases=[
            "The token memory carries context across sessions for recent recall.",
            "Recent context tokens persist across sessions in the memory layer.",
            "Session tokens carry context summary into recent memory each time.",
        ],
    ),
    ParaphraseCluster(
        label="client_engagement_neutral",
        expected_topic="client",
        expected_polarity="neutral",
        expected_regime="",
        paraphrases=[
            "Scoping the client engagement under the NDA contract this week.",
            "The client engagement is in NDA scoping at the contract layer.",
            "Contract scope on the client NDA engagement this week.",
        ],
    ),
    ParaphraseCluster(
        label="review_audit_positive",
        expected_topic="review",
        expected_polarity="positive",
        expected_regime="",
        paraphrases=[
            "Audit verified the approval, review is good, all checks pass.",
            "The review approved the audit, verify checks all pass green.",
            "Verify and check the audit approve as a successful review pass.",
        ],
    ),
]


REFUSAL_CASES: list[str] = [
    "Here is the key: -----BEGIN RSA PRIVATE KEY-----\nMIIabc...",
    "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXkt",
    "-----BEGIN EC PRIVATE KEY-----\nMHcCAQEE",
]
