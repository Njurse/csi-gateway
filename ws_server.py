import asyncio
import websockets
import os

WS_PORT = int(os.getenv("WS_PORT", "8000"))

clients = set()

async def start_ws_server(queue: asyncio.Queue):
    async def handler(ws):
        clients.add(ws)
        try:
            while True:
                await asyncio.sleep(1)
        finally:
            clients.remove(ws)

    async def broadcaster():
        while True:
            msg = await queue.get()
            dead = []

            for c in clients:
                try:
                    await c.send(str(msg))
                except:
                    dead.append(c)

            for d in dead:
                clients.discard(d)

    server = await websockets.serve(handler, "0.0.0.0", WS_PORT)

    await asyncio.gather(
        server.wait_closed(),
        broadcaster()
    )