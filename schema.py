"""JSON-vector record schema for the walkie-talkie protocol.

A record is the wire format between agent capability tiers. It carries
position in colorspace, not identity. PII is stripped at the encoder
boundary; what remains is auditable structural geometry.

The record is plain-record (not cipher): anyone can read it, but the
original input is not reconstructable from the position. Lossy by design.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

SCHEMA_VERSION = 1
ENCODER_VERSION = "0.1.0"


@dataclass
class Band:
    """A contiguous interval on a continuous axis. See GEOMETRIC_PRIMITIVES.md #1."""
    axis: str
    centroid: float
    width: float
    phase_deg: float


@dataclass
class Basin:
    """An attractor region. See GEOMETRIC_PRIMITIVES.md #7."""
    centroid_hex: str
    size: float


@dataclass
class Primitives:
    """The geometric content. Bands + phase + coherence + basin."""
    basis: str
    phase_deg: float
    coherence: float
    bands: list[Band] = field(default_factory=list)
    basin: Basin | None = None


@dataclass
class BoundaryReport:
    """What the policy boundary did at encode time. Visible to auditors."""
    policies_applied: list[str] = field(default_factory=list)
    stripped_count: int = 0
    refused: bool = False
    refused_reason: str = ""


@dataclass
class Auditability:
    """Invariants the record claims to satisfy. Verifiable by inspection."""
    encoder_version: str = ENCODER_VERSION
    round_trip_lossy: bool = True
    no_pii_invariant: bool = True


@dataclass
class Record:
    """A walkie-talkie wire record."""
    version: int = SCHEMA_VERSION
    encoded_at: str = ""
    primitives: Primitives = field(default_factory=lambda: Primitives(
        basis="vrgb-default",
        phase_deg=0.0,
        coherence=0.0,
    ))
    hex_addresses: list[str] = field(default_factory=list)
    structural_fields: dict[str, Any] = field(default_factory=dict)
    boundary: BoundaryReport = field(default_factory=BoundaryReport)
    auditability: Auditability = field(default_factory=Auditability)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def record_from_dict(data: dict[str, Any]) -> Record:
    """Reconstruct a Record from a JSON-loaded dict. Tolerant of missing fields."""
    prim_data = data.get("primitives", {})
    bands = [Band(**b) for b in prim_data.get("bands", [])]
    basin_data = prim_data.get("basin")
    basin = Basin(**basin_data) if basin_data else None

    primitives = Primitives(
        basis=prim_data.get("basis", "vrgb-default"),
        phase_deg=prim_data.get("phase_deg", 0.0),
        coherence=prim_data.get("coherence", 0.0),
        bands=bands,
        basin=basin,
    )

    boundary = BoundaryReport(**data.get("boundary", {}))
    auditability = Auditability(**data.get("auditability", {}))

    return Record(
        version=data.get("version", SCHEMA_VERSION),
        encoded_at=data.get("encoded_at", ""),
        primitives=primitives,
        hex_addresses=data.get("hex_addresses", []),
        structural_fields=data.get("structural_fields", {}),
        boundary=boundary,
        auditability=auditability,
    )
