FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install numpy and pandas first to avoid binary incompatibility
COPY requirements.txt .
RUN pip install --no-cache-dir numpy==1.24.3
RUN pip install --no-cache-dir pandas==2.0.3
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and Chromium
RUN pip install playwright==1.40.0
RUN playwright install chromium

# Copy application
COPY . .

# Create necessary directories
RUN mkdir -p scrapers/generated scrapers/outputs scrapers/debug

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV HEADLESS_MODE=true

# Expose port
EXPOSE 5000

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
