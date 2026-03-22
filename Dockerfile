FROM python:3.11-slim

WORKDIR /app

# Install necessary system dependencies for the MVP (like curl, etc. so the agent can use them)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt httpx

COPY src/ ./src/
COPY test_clutch.py .

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
