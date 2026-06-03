FROM python:3.11-slim

WORKDIR /app

COPY app /app

RUN pip install asyncio websockets

CMD ["python", "main.py"]