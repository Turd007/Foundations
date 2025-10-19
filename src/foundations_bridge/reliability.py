from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Deque, Optional

@dataclass
class ReliabilityConfig:
    window: int = 200
    log_path: str = "reports/reliability_log.jsonl"

class ReliabilityTracker:
    def __init__(self, config: Optional[ReliabilityConfig] = None):
        self.cfg = config or ReliabilityConfig()
        self._hits: Deque[bool] = deque(maxlen=self.cfg.window)
        # ensure reports directory exists
        Path(self.cfg.log_path).parent.mkdir(parents=True, exist_ok=True)

    def record(self, success: bool, *, label: str = "run", meta: Optional[dict] = None) -> float:
        \"\"\"Record a boolean outcome and return the current rolling reliability.\"\"\"
        self._hits.append(bool(success))
        self._append_jsonl({
            "ts": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "label": label,
            "success": bool(success),
            "rolling_reliability": self.rolling(),
            "window": self.cfg.window,
            "meta": meta or {}
        })
        return self.rolling()

    def rolling(self) -> float:
        if not self._hits:
            return 0.0
        return sum(self._hits) / len(self._hits)

    # convenience
    def passed(self) -> bool:
        return self._hits and self._hits[-1] is True

    def _append_jsonl(self, obj: dict) -> None:
        with open(self.cfg.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\\n")
