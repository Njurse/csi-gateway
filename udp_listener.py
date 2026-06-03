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
    def __init__(self, queue):
        self.queue = queue
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        print("[UDP] connection made")

    def datagram_received(self, data, addr):
        try:
            self.queue.put_nowait({
                "raw": data.hex(),
                "len": len(data),
                "src": addr[0],
            })
        except Exception as e:
            print("queue error:", e)

    def error_received(self, exc):
        print("[UDP] error:", exc)

    def connection_lost(self, exc):
        print("[UDP] connection lost")