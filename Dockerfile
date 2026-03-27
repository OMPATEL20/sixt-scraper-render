FROM python:3.11-slim

# Install minimal dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and its dependencies
RUN pip install playwright
RUN playwright install chromium
RUN playwright install-deps

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
