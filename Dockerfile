FROM python:3.12-slim

# Set workdir inside the container
WORKDIR /app

# Copy dependency list first (for caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy actual source code
COPY src/ ./src/

# Set the default command (automatically starts your script)
CMD ["python", "src/main.py"]
