# Use a newer Python base image
FROM python:3.11-slim

# Install Playwright dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright and browsers
RUN pip install playwright==1.40.0
RUN playwright install chromium
RUN playwright install-deps

# Set working directory
WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

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
