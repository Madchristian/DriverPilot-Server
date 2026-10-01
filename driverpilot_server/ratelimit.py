"""Anfragelimits im Speicher. Keine dauerhafte IP-Protokollierung.

Schluessel sind Client-IDs oder IP-Adressen; sie leben nur im Prozess und
verschwinden mit dem Neustart. Fuer den Pilot ist das ausreichend und
entspricht der Vorgabe, IPs nicht dauerhaft zu speichern.
"""

from __future__ import annotations

import threading
import time
from collections import deque


class SlidingWindow:
    """Hoechstens `limit` Ereignisse je `window` Sekunden und Schluessel."""

    def __init__(self, limit: int, window: float):
        self.limit = limit
        self.window = window
        self._events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        self._last_sweep = time.monotonic()

    def _sweep(self, now: float) -> None:
        if now - self._last_sweep < 60:
            return
        self._last_sweep = now
        for key in list(self._events):
            events = self._events[key]
            while events and now - events[0] > self.window:
                events.popleft()
            if not events:
                del self._events[key]

    def check(self, key: str) -> int | None:
        """Zaehlt ein Ereignis. None = erlaubt, sonst Sekunden bis zum naechsten Versuch."""
        now = time.monotonic()
        with self._lock:
            self._sweep(now)
            events = self._events.setdefault(key, deque())
            while events and now - events[0] > self.window:
                events.popleft()
            if len(events) >= self.limit:
                return max(1, int(self.window - (now - events[0])) + 1)
            events.append(now)
            return None

    def record(self, key: str) -> None:
        """Zaehlt ein Ereignis ohne Pruefung (z.B. Fehlversuch beim Pairing)."""
        now = time.monotonic()
        with self._lock:
            self._events.setdefault(key, deque()).append(now)

    def blocked(self, key: str) -> int | None:
        """Nur pruefen, ohne zu zaehlen."""
        now = time.monotonic()
        with self._lock:
            events = self._events.get(key)
            if not events:
                return None
            while events and now - events[0] > self.window:
                events.popleft()
            if len(events) >= self.limit:
                return max(1, int(self.window - (now - events[0])) + 1)
            return None

    def reset(self) -> None:
        with self._lock:
            self._events.clear()
