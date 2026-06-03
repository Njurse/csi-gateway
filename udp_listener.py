import asyncio
import os
import time
import logging

logger = logging.getLogger(__name__)

UDP_PORT = int(os.getenv("UDP_PORT", "5005"))


async def start_udp_listener(queue: asyncio.Queue):
    logger.info("Listening for UDP CSI on 0.0.0.0:%s", UDP_PORT)

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
        logger.info("UDP listener cancelled, transport closed")


class CSIProtocol:
    def __init__(self, queue):
        self.queue = queue
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        logger.debug("UDP connection made")

    def datagram_received(self, data, addr):
        src = addr[0] if addr else "unknown"
        try:
            self.queue.put_nowait({
                "raw": data.hex(),
                "len": len(data),
                "src": src,
            })
            logger.debug("Received UDP packet from %s (%d bytes)", src, len(data))
        except Exception as e:
            logger.exception("Failed to enqueue UDP packet from %s: %s", src, e)

    def error_received(self, exc):
        logger.error("UDP error received: %s", exc)

    def connection_lost(self, exc):
        logger.info("UDP connection lost: %s", exc)