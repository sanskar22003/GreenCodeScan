# Use a base image with Python installed
FROM python:3.9-slim

# Install PowerShell and Java
RUN apt-get update && apt-get install -y wget apt-transport-https software-properties-common \
    && wget -q https://packages.microsoft.com/config/debian/10/packages-microsoft-prod.deb \
    && dpkg -i packages-microsoft-prod.deb \
    && apt-get update \
    && apt-get install -y powershell \
    openjdk-17-jdk \
    maven 


# Install any additional tools (if needed)
# RUN apt-get install -y <tool>

# Set environment variables
ENV SOURCE_DIRECTORY=/app
ENV GREEN_REFINED_DIRECTORY=/app/Green_Refined_Files
ENV AZURE_API_KEY=eadf76dd169e4172a463e7375946835f
ENV AZURE_API_VERSION=2024-02-15-preview
ENV AZURE_ENDPOINT=https://green-code-uks.openai.azure.com
ENV PYTEST_PATH=/usr/local/bin/pytest
ENV MAVEN_PATH=/usr/local/bin/mvn
ENV RESULT_DIR=/app/Green_Refined_Files/Result
ENV RESULT_SOURCE_DIR=/app/Green_Refined_Files/Result/main_before_emissions_data.csv
ENV RESULT_GREEN_REFINED_DIRECTORY=/app/Green_Refined_Files/Result/main_after_emissions_data.csv


# Copy files
COPY . /app

# Set working directory
WORKDIR /app

# Install Python dependencies
RUN pip install -r requirements.txt

# Run scripts sequentially
CMD ["sh", "-c", "python server_emissions.py && python GreenCodeRefiner.py && python track_emissions.py && python compare_emissions.py && pwsh upload_to_sharepoint.ps1"]
