from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Deque


@dataclass
class GatewayState:
    max_recent: int = 200
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)
    _nodes: dict[str, dict[str, Any]] = field(default_factory=dict, init=False, repr=False)
    _recent: Deque[dict[str, Any]] = field(init=False, repr=False)
    _total_packets: int = field(default=0, init=False, repr=False)
    _started_at: float = field(default_factory=time.time, init=False, repr=False)

    def __post_init__(self):
        self._recent = deque(maxlen=self.max_recent)

    def update_packet(self, packet: dict[str, Any]):
        node_id = str(packet.get("node_id") or "unknown")
        snapshot = dict(packet)
        snapshot["node_id"] = node_id
        snapshot["received_at"] = time.time()

        with self._lock:
            self._total_packets += 1
            self._nodes[node_id] = snapshot
            self._recent.append(snapshot)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            nodes = sorted(
                self._nodes.values(),
                key=lambda item: str(item.get("node_id") or ""),
            )
            return {
                "generated_at": time.time(),
                "uptime_seconds": round(time.time() - self._started_at, 2),
                "total_packets": self._total_packets,
                "total_nodes": len(nodes),
                "nodes": [dict(node) for node in nodes],
                "recent_packets": [dict(packet) for packet in list(self._recent)],
            }
