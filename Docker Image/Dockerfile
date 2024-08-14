# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Set working directory in the container
WORKDIR /app

# Copy Python scripts into the container
COPY server_emissions.py /app/
COPY GreenCodeRefiner.py /app/
COPY track_emissions.py /app/
COPY compare_emissions.py /app/
COPY upload_to_sharePoint.ps1 /app/
COPY .env /app/

# Install Python dependencies (if any)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Install PowerShell
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    powershell && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set the entry point for the container
ENTRYPOINT ["python", "/app/server_emissions.py"]
