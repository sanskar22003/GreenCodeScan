# Use a base image with Python installed
FROM python:3.9-slim

# Set working directory in the container
WORKDIR /app

# Copy all necessary files into the container
COPY server_emissions.py GreenCodeRefiner.py track_emissions.py compare_emissions.py .env requirements.txt /app/

# Set the environment variable to specify the source directory
ENV SOURCE_DIRECTORY=/app/source

# Install required dependencies for PowerShell
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl apt-transport-https gnupg && \
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/microsoft-prod.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    powershell && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install required Python packages from requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Command to conditionally copy scripts and then run them
CMD ["bash", "-c", "\
    mkdir -p ${SOURCE_DIRECTORY} && \
    for file in /app/*.py /app/.env; do \
        if [ ! -f ${SOURCE_DIRECTORY}/$(basename $file) ]; then \
            cp $file ${SOURCE_DIRECTORY}/; \
        fi; \
    done && \
    cd ${SOURCE_DIRECTORY} && \
    python server_emissions.py && \
    python GreenCodeRefiner.py && \
    python track_emissions.py && \
    python compare_emissions.py"]
