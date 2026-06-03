import asyncio
import time
import json
import os
import logging
from collections import deque, defaultdict
from typing import Deque

from csi_decoder import decode_packet, estimate_size

LOG_DIR = os.getenv("LOG_DIR", "logs")
RAW_LOG = os.path.join(LOG_DIR, "raw.log")
PROC_LOG = os.path.join(LOG_DIR, "processed.log")

os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger(__name__)


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

    logger.info("Pipeline started, logging raw -> %s, processed -> %s", RAW_LOG, PROC_LOG)

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

            # Normalize into schema: ensure raw is hex string
            raw_hex = raw.hex() if isinstance(raw, (bytes, bytearray)) else str(raw)
            csi_packet = {
                "timestamp": ts,
                "node_id": src,
                "rssi": None,
                "channel": None,
                "raw": raw_hex,
                "len": pkt_len,
            }

            logger.info("Received packet from %s len=%d\n%s", src, pkt_len,json.dumps(csi_packet))

            # log raw (json line)
            try:
                raw_f.write(json.dumps(csi_packet) + "\n")
            except Exception:
                logger.exception("Failed to write raw log for %s", src)

            # Update health
            node = nodes[src]
            node.seen(ts)

            pkt_rate = node.packet_rate_per_minute(ts)

            # Attempt to decode using csi_decoder
            try:
                decoded = decode_packet({"raw": raw_hex, "timestamp": ts, "node_id": src})
                iq = decoded.get("iq") or []
                iq_count = len(iq)
                payload_size = decoded.get("size", {}).get("payload", 0)
                logger.info("Decoded packet %s: iq_pairs=%d payload=%d", src, iq_count, payload_size)
            except Exception:
                decoded = {"iq": [], "size": {}, "header": b""}
                iq = []
                iq_count = 0
                payload_size = 0
                logger.exception("CSI decode failed for packet from %s", src)

            # Compute simple features on raw bytes (if available)
            try:
                raw_bytes = bytes.fromhex(raw_hex)
            except Exception:
                raw_bytes = bytes()

            features = simple_features(raw_bytes)

            # Heuristic motion score: normalized stddev or amplitude std if available
            if decoded.get("iq"):
                # use amplitude std if present
                amplitudes = [ (i*i + q*q)**0.5 for i, q in decoded["iq"] ]
                motion_score = (sum((a - (sum(amplitudes)/len(amplitudes)))**2 for a in amplitudes) / len(amplitudes)) ** 0.5 if amplitudes else features["std"] / 128.0
            else:
                motion_score = features["std"] / 128.0

            presence = motion_score > 0.05 or pkt_rate > 0.1

            processed = {
                "timestamp": ts,
                "node_id": src,
                "packet_rate": pkt_rate,
                "rssi": decoded.get("rssi") or node.rssi,
                "features": features,
                "motion": motion_score,
                "presence": presence,
                "iq_count": iq_count,
                "payload_size": payload_size,
                "decoded_notes": decoded.get("notes"),
                # breathing estimation placeholder (None)
                "breathing": None,
            }
            logger.info("Processed the heuristic motion score and results are:\n%s", json.dumps(processed))
            # log processed
            try:
                proc_f.write(json.dumps(processed) + "\n")
            except Exception:
                logger.exception("Failed to write processed log for %s", src)

            # push to out queue for websocket broadcasting
            try:
                out_queue.put_nowait(processed)
                logger.debug("Enqueued processed message for %s (rate=%.2f motion=%.3f iq=%d)", src, pkt_rate, motion_score, iq_count)
            except asyncio.QueueFull:
                # if downstream is slow, drop the message
                logger.warning("Out queue full, dropping processed message for %s", src)
    finally:
        raw_f.close()
        proc_f.close()
