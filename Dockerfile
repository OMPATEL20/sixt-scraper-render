FROM python:3.11-slim

WORKDIR /app

# Install only essential system packages
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and Chromium (without install-deps)
RUN pip install playwright && \
    playwright install chromium

# Copy the rest of the application
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
