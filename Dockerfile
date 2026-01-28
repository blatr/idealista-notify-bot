FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Expose port for web app
EXPOSE 8000

# Default: run web app
CMD ["uvicorn", "webapp.main:app", "--host", "0.0.0.0", "--port", "8000"]
