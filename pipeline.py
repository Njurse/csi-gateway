import asyncio
import time
import json
import os
from collections import deque, defaultdict
from typing import Deque

LOG_DIR = os.getenv("LOG_DIR", "logs")
RAW_LOG = os.path.join(LOG_DIR, "raw.log")
PROC_LOG = os.path.join(LOG_DIR, "processed.log")

os.makedirs(LOG_DIR, exist_ok=True)


class NodeInfo:
    def __init__(self):
        self.last_seen = 0.0
        self.rssi = None
        self.timestamps: Deque[float] = deque()

    def seen(self, ts: float):
        self.last_seen = ts
        self.timestamps.append(ts)
        # keep only last 120 seconds
        cutoff = ts - 120
        while self.timestamps and self.timestamps[0] < cutoff:
            self.timestamps.popleft()

    def packet_rate_per_minute(self, now: float) -> float:
        # packets per minute over last 60 seconds
        cutoff = now - 60
        count = sum(1 for t in self.timestamps if t >= cutoff)
        return count / 1.0  # packets per last minute (count)


def simple_features(raw: bytes):
    if not raw:
        return {"len": 0, "mean": 0.0, "std": 0.0}
    arr = list(raw)
    n = len(arr)
    mean = sum(arr) / n
    var = sum((x - mean) ** 2 for x in arr) / n
    std = var ** 0.5
    return {"len": n, "mean": mean, "std": std}


async def start_pipeline(in_queue: asyncio.Queue, out_queue: asyncio.Queue):
    """
    Consume raw UDP messages from `in_queue`, normalize into CSI_Packet schema,
    update node health, compute simple features and heuristics, log raw+processed,
    and push processed messages to `out_queue` for broadcasting.
    """

    nodes = defaultdict(NodeInfo)

    # open log files in append mode
    raw_f = open(RAW_LOG, "a", buffering=1)
    proc_f = open(PROC_LOG, "a", buffering=1)

    try:
        while True:
            msg = await in_queue.get()
            ts = msg.get("timestamp", time.time())
            src = msg.get("src", "unknown")
            raw = msg.get("raw", b"")
            pkt_len = msg.get("len", len(raw) if raw else 0)

            # Normalize into schema
            csi_packet = {
                "timestamp": ts,
                "node_id": src,
                "rssi": None,
                "channel": None,
                "raw": raw.hex() if isinstance(raw, (bytes, bytearray)) else str(raw),
                "len": pkt_len,
            }

            # log raw (json line)
            try:
                raw_f.write(json.dumps(csi_packet) + "\n")
            except Exception:
                pass

            # Update health
            node = nodes[src]
            node.seen(ts)

            pkt_rate = node.packet_rate_per_minute(ts)

            # Compute simple features
            features = simple_features(raw if isinstance(raw, (bytes, bytearray)) else bytes())

            # Heuristic motion score: normalized stddev
            motion_score = features["std"] / 128.0
            presence = motion_score > 0.05 or pkt_rate > 0.1

            processed = {
                "timestamp": ts,
                "node_id": src,
                "packet_rate": pkt_rate,
                "rssi": node.rssi,
                "features": features,
                "motion": motion_score,
                "presence": presence,
                # breathing estimation placeholder (None)
                "breathing": None,
            }

            # log processed
            try:
                proc_f.write(json.dumps(processed) + "\n")
            except Exception:
                pass

            # push to out queue for websocket broadcasting
            try:
                out_queue.put_nowait(processed)
            except asyncio.QueueFull:
                # if downstream is slow, drop the message
                pass
    finally:
        raw_f.close()
        proc_f.close()
*** End Patch