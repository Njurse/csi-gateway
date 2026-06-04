import asyncio
import websockets
import os
import logging

logger = logging.getLogger(__name__)

WS_PORT = int(os.getenv("WS_PORT", "4000"))

clients = set()


async def start_ws_server(queue: asyncio.Queue):
    async def handler(ws):
        clients.add(ws)
        peer = getattr(ws, 'remote_address', None)
        logger.info("WebSocket client connected: %s", peer)
        try:
            while True:
                await asyncio.sleep(1)
        finally:
            clients.remove(ws)
            logger.info("WebSocket client disconnected: %s", peer)

    async def broadcaster():
        while True:
            msg = await queue.get()
            dead = []

            for c in list(clients):
                try:
                    await c.send(str(msg))
                except Exception:
                    logger.exception("Failed to send WS message, removing client")
                    dead.append(c)

            for d in dead:
                clients.discard(d)

    server = await websockets.serve(handler, "0.0.0.0", WS_PORT)
    logger.info("WebSocket server listening on 0.0.0.0:%s", WS_PORT)

    await asyncio.gather(
        server.wait_closed(),
        broadcaster()
    )