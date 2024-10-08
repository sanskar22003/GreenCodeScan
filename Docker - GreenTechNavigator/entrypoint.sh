#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Read user password from environment variable
USER_PASSWORD=${ENTER_PASSWORD}

# Read expected password from environment variable
EXPECTED_PASSWORD=${EXPECTED_PASSWORD}

# Check if both passwords are provided
if [ -z "$USER_PASSWORD" ] || [ -z "$EXPECTED_PASSWORD" ]; then
    echo "Error: USER_PASSWORD and EXPECTED_PASSWORD environment variables must be set."
    exit 1
fi

# Verify the password
if [ "$USER_PASSWORD" != "$EXPECTED_PASSWORD" ]; then
    echo "Incorrect password. Exiting."
    exit 1
fi

# Confirm project directory
read -p "Is this your root project directory? Y/N: " CONFIRM
case "$CONFIRM" in
    [yY][eE][sS]|[yY])
        echo "Proceeding with processing..."
        ;;
    *)
        echo "Directory confirmation failed. Exiting."
        exit 1
        ;;
esac

# Function to run Python scripts
run_scripts() {
    echo "Running server_emissions.py..."
    python /app/server_emissions.py

    echo "Running GreenCodeRefiner.py..."
    python /app/GreenCodeRefiner.py

    echo "Running track_emissions.py..."
    python /app/track_emissions.py

    echo "Processing complete."
}

# Set environment variables
export DOTENV_PATH="/app/.env"

run_scripts
