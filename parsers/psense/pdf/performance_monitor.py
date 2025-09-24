"""Context‑manager that records execution time of arbitrary code‑blocks."""
from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Dict, Generator


class PerformanceMonitor:
    """Simple per‑operation timing utility."""

    def __init__(self) -> None:
        self._timers: Dict[str, float] = {}

    # -------------- Public API --------------
    def start(self, name: str) -> None:
        self._timers[name] = time.perf_counter()

    def stop(self, name: str) -> None:
        if name in self._timers:
            self._timers[name] = time.perf_counter() - self._timers[name]

    def metrics(self) -> Dict[str, float]:
        return self._timers.copy()

    # -------------- Context style --------------
    @contextmanager
    def track(self, name: str) -> Generator[None, None, None]:
        self.start(name)
        try:
            yield
        finally:
            self.stop(name)
