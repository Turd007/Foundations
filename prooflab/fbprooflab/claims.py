from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict

@dataclass
class ClaimResult:
    id: str
    type: str
    status: str  # "proved" | "rejected" | "inconclusive"
    details: Dict[str, Any] = field(default_factory=dict)
