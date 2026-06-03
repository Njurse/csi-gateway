import asyncio
import os
import time

UDP_PORT = int(os.getenv("UDP_PORT", "5005"))


async def start_udp_listener(queue: asyncio.Queue):
    print(f"[UDP] Listening on {UDP_PORT}")

    loop = asyncio.get_event_loop()

    transport, protocol = await loop.create_datagram_endpoint(
        lambda: CSIProtocol(queue),
        local_addr=("0.0.0.0", UDP_PORT),
    )

    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        transport.close()


class CSIProtocol:
    def __init__(self, queue: asyncio.Queue):
        self.queue = queue

    def datagram_received(self, data: bytes, addr):
        # Attach minimal metadata required by the pipeline
        try:
            msg = {
                "timestamp": time.time(),
                "src": addr[0],
                "len": len(data),
                "raw": data,  # keep as bytes for downstream processing
            }
            # Use put_nowait so the UDP callback never blocks
            self.queue.put_nowait(msg)
        except Exception:
            pass