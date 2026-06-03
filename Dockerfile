FROM python:3.11-slim

WORKDIR /app

# Copy the repository contents into the container's /app directory
# Use a simple dot copy so builds don't fail when there's no local `app` folder
COPY . /app

# Install dependencies (asyncio is in stdlib, but kept here if additional packages are added)
RUN pip install websockets

CMD ["python", "main.py"]