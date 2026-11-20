"""Clock abstraction: deterministic for reproducible demos and tests, live for real use."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


class Clock:
    def now(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class DeterministicClock(Clock):
    """Starts at a fixed instant and advances one second per call."""

    def __init__(self, start: str = "2026-11-02T09:00:00Z") -> None:
        self._t = datetime.strptime(start, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

    def now(self) -> str:
        out = self._t.strftime("%Y-%m-%dT%H:%M:%SZ")
        self._t += timedelta(seconds=1)
        return out
