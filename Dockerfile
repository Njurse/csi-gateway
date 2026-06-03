FROM python:3.11-slim

WORKDIR /app

# Copy the repository contents into the container's /app directory
# Use a simple dot copy so builds don't fail when there's no local `app` folder
COPY . /app

# Ensure Python output is unbuffered for real-time logs
ENV PYTHONUNBUFFERED=1

# Install dependencies from requirements.txt if present
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

CMD ["python", "main.py"]