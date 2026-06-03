import asyncio
from udp_listener import start_udp_listener
from ws_server import start_ws_server

async def main():
    ws_queue = asyncio.Queue()

    await asyncio.gather(
        start_udp_listener(ws_queue),
        start_ws_server(ws_queue),
    )

if __name__ == "__main__":
    asyncio.run(main())