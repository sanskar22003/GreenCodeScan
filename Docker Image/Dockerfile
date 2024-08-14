# Use a base image with Python installed
FROM python:3.9-slim

# Set working directory in the container
WORKDIR /app

# Copy the .env file into the container
COPY .env .env

# Copy all Python scripts and the PowerShell script into the container
COPY server_emissions.py GreenCodeRefiner.py track_emissions.py compare_emissions.py upload_to_sharepoint.ps1 /app/

# Install required Python packages (assume you have a requirements.txt if needed)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Install PowerShell for running PowerShell scripts
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

# Run the scripts in sequence
CMD ["bash", "-c", "python server_emissions.py && python GreenCodeRefiner.py && python track_emissions.py && python compare_emissions.py && pwsh upload_to_sharePoint.ps1"]
