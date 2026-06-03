import struct
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class CSIPacket:
    timestamp: float
    node_id: str
    rssi: Optional[int]
    channel: Optional[int]
    raw: str

    header: bytes
    payload: bytes


def decode_hex_raw(raw_hex: str) -> bytes:
    return bytes.fromhex(raw_hex)


def split_header_payload(data: bytes, header_size: int = 20):
    """
    Most CSI formats use a small fixed header + payload.
    Adjust header_size if your firmware differs.
    """
    if len(data) <= header_size:
        return data, b""
    return data[:header_size], data[header_size:]


def decode_iq(payload: bytes) -> List[tuple]:
    """
    Decode CSI-style I/Q pairs (int16 little-endian).
    Returns [(i, q), ...]
    """
    iq = []
    for i in range(0, len(payload) - 1, 4):
        try:
            i_val, q_val = struct.unpack("<hh", payload[i:i+4])
            iq.append((i_val, q_val))
        except struct.error:
            break
    return iq


def estimate_size(packet: Dict[str, Any]) -> Dict[str, int]:
    raw_len = len(packet.get("raw", "")) // 2
    return {
        "raw_bytes": raw_len,
        "estimated_iq_pairs": max((raw_len - 20) // 4, 0)
    }


def decode_packet(packet: Dict[str, Any], header_size: int = 20) -> Dict[str, Any]:
    raw_bytes = decode_hex_raw(packet["raw"])
    header, payload = split_header_payload(raw_bytes, header_size)

    iq = decode_iq(payload)

    return {
        "timestamp": packet.get("timestamp"),
        "node_id": packet.get("node_id"),
        "rssi": packet.get("rssi"),
        "channel": packet.get("channel"),
        "header": header,
        "iq": iq,
        "size": {
            "raw": len(raw_bytes),
            "payload": len(payload),
        }
    }