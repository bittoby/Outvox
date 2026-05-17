# This Dockerfile creates a containerized voice agent with:
#   - Python 3.13 runtime
#   - All required dependencies
#   - Health checks for monitoring
#   - Optimized layer caching
#   - NO database dependencies (talks to db_service via API)

FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# - gcc/g++: Required for some Python packages
# - curl: Used for health checks
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
# This layer is only rebuilt when requirements.txt changes
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application code
# This includes:
#   - outbound_main.py
#   - config.py
#   - utils/ directory
#   - prompts/ directory
COPY . .

# Expose port 5001 (internal container port)
EXPOSE 5001

# Health check configuration
# Kubernetes/Docker will use this to determine if container is healthy
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

# Command to run the voice agent
# Note: Use outbound_main.py
CMD ["python", "outbound_main.py"]
