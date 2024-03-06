import os
import subprocess
import csv
from codecarbon import EmissionsTracker
import datetime
from subprocess import TimeoutExpired
import pandas as pd

# Directory containing the scripts
directory = r"C:\ProgramData\Jenkins\.jenkins\workspace\GreenCodeScanPipeline"

# Command to run scripts for each language
commands = {
    ".py": "python",  # Use the Python interpreter to run Python scripts
    # Add other commands for other languages as needed
}

# Create a CSV file to store emissions data
csv_file = "emissions_data.csv"
with open(csv_file, 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Filename", "Timestamp", "Project Name", "Run ID", "Duration (s)", "Emissions (kgCO2)", "Emissions Rate"])

# Iterate over the scripts in the directory
for filename in os.listdir(directory):
    for extension, command in commands.items():
        if filename.endswith(extension):
            filepath = os.path.join(directory, filename)

            # Print the name of the file being scanned
            print(f"Scanning file: {filename}")

            # Create a new EmissionsTracker for each script
            tracker = EmissionsTracker()

            # Start tracking
            tracker.start()

            # Run the script with a timeout
            try:
                subprocess.run([command, filepath], timeout=60)
            except TimeoutExpired:
                print(f"Script {filename} took too long to run and was terminated.")

            # Stop tracking
            tracker.stop()
            
            # Read the emissions data from the CSV file
            emissions_data = pd.read_csv('C:/ProgramData/Jenkins/.jenkins/workspace/GreenCodeScanPipeline/emissions.csv').iloc[-1]
            print(emissions_data)
            # Get additional data
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Write emissions data to CSV
            with open(csv_file, 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([filename, timestamp, emissions_data['project_name'], emissions_data['run_id'], emissions_data['duration'], emissions_data['emissions'], emissions_data['emissions_rate']])

print("Emissions data written to emissions_data.csv")
