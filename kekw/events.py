from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class MarketEvent:
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class Headline:
    headlines: tuple[str, ...]
    analyst: str
    bias: float
    trigger: str = "interval"
