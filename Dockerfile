# Production-ready Dockerfile for A2A Agent
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements_ap2.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements_ap2.txt

# Install additional production dependencies
RUN pip install --no-cache-dir \
    sqlalchemy==2.0.23 \
    pydantic==2.5.0 \
    slowapi==0.1.9

# Copy application code
COPY config.py .
COPY models.py .
COPY database.py .
COPY logger.py .
COPY middleware.py .
COPY agent_production.py .

# Create directory for logs and database
RUN mkdir -p /app/data /app/logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV LOG_FILE=/app/logs/agent.log
ENV DATABASE_URL=sqlite:////app/data/agent.db

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run the application
CMD ["python", "agent_production.py"]
