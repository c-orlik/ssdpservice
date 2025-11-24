FROM python:3.12-slim

# Set workdir inside the container
WORKDIR /app

# Install build dependencies required by netifaces
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libc-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency list first (for caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy actual source code
COPY src/ ./src/

# Set the default command (automatically starts your script)
CMD ["python", "src/main.py"]

FROM python:3.12-slim
