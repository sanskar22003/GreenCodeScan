import os
import subprocess
import csv
from codecarbon import EmissionsTracker
from datetime import datetime
import time
import pandas as pd

# Directory containing the scripts
scripts_dir = r"C:\ProgramData\Jenkins\.jenkins\workspace\GreenCodeScanPipeline"

# Create a CSV file to store emissions data
with open('emissions_data.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Script Name", "Timestamp", "CO2 Emissions (kg)", "Duration (s)", "CPU Power (W)", "RAM Power (W)", "Total Energy (kWh)"])

# Iterate over each script in the directory
for script in os.listdir(scripts_dir):
    if script.endswith('.py'):
        # Create a new EmissionsTracker for each script
        tracker = EmissionsTracker()

        # Start the emissions tracker
        tracker.start()

        # Execute the script with a timeout
        try:
            start_time = time.time()
            subprocess.run(['python', os.path.join(scripts_dir, script)], timeout=60)
            duration = time.time() - start_time
        except subprocess.TimeoutExpired:
            print(f"Script {script} exceeded the timeout limit.")

        # Stop the emissions tracker
        tracker.stop()

        # Read the emissions data from the CSV file
        emissions_data = pd.read_csv('C:/ProgramData/Jenkins/.jenkins/workspace/GreenCodeScanPipeline/emissions.csv').iloc[-1]

        # Retrieve and format the emissions data
        data = [
            script,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            emissions_data['emissions'],
            duration,
            emissions_data['cpu_power'],
            emissions_data['ram_power'],
            emissions_data['energy_consumed']
        ]

        # Write the data to the CSV file
        with open('emissions_data.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(data)
print("Emissions data written to emissions_data.csv")
