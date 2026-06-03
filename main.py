import asyncio
import logging
import os
from udp_listener import start_udp_listener
from ws_server import start_ws_server
from pipeline import start_pipeline


def configure_logging():
    log_dir = os.getenv("LOG_DIR", "logs")
    os.makedirs(log_dir, exist_ok=True)
    app_log = os.path.join(log_dir, "app.log")

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    root.addHandler(sh)

    fh = logging.FileHandler(app_log)
    fh.setFormatter(fmt)
    root.addHandler(fh)


async def main():
    configure_logging()
    logging.getLogger(__name__).info("Starting CSI Gateway...")

    ingest_queue = asyncio.Queue()
    ws_queue = asyncio.Queue()

    await asyncio.gather(
        start_udp_listener(ingest_queue),
        start_pipeline(ingest_queue, ws_queue),
        start_ws_server(ws_queue),
    )


if __name__ == "__main__":
    asyncio.run(main())