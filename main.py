import asyncio
from udp_listener import start_udp_listener
from ws_server import start_ws_server
from pipeline import start_pipeline


async def main():
    ingest_queue = asyncio.Queue()
    ws_queue = asyncio.Queue()

    await asyncio.gather(
        start_udp_listener(ingest_queue),
        start_pipeline(ingest_queue, ws_queue),
        start_ws_server(ws_queue),
    )


if __name__ == "__main__":
    asyncio.run(main())