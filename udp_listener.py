import asyncio
import os

UDP_PORT = int(os.getenv("UDP_PORT", "5005"))

async def start_udp_listener(queue: asyncio.Queue):
    print(f"[UDP] Listening on {UDP_PORT}")

    loop = asyncio.get_event_loop()

    transport, protocol = await loop.create_datagram_endpoint(
        lambda: CSIProtocol(queue),
        local_addr=("0.0.0.0", UDP_PORT),
    )

    while True:
        await asyncio.sleep(3600)

class CSIProtocol:
    def __init__(self, queue):
        self.queue = queue

    def datagram_received(self, data, addr):
        # raw packet from ESP32
        try:
            self.queue.put_nowait({
                "raw": data.hex(),
                "len": len(data),
                "src": addr[0],
            })
        except:
            pass