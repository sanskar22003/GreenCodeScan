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
    writer.writerow(["Filename", "Timestamp", "Emissions (kgCO2)", "Duration", "CPU Power", "RAM Power", "Energy Consumed", "Test Results"])

# Iterate over each script in the directory
for script in os.listdir(scripts_dir):
    if script.endswith('.py'):
        # Create a new EmissionsTracker for each script
        tracker = EmissionsTracker()

        # Start the emissions tracker
        tracker.start()

        # Initialize duration
        duration = None

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
        # Read the emissions data from the CSV file
        emissions_data = pd.read_csv('C:/ProgramData/Jenkins/.jenkins/workspace/GreenCodeScanPipeline/emissions.csv')

# Check if the DataFrame is empty
        if emissions_data.empty:
            print(f"No emissions data generated for script {script}.")
        else:
    # Retrieve the last row of emissions data
            emissions_data = emissions_data.iloc[-1]

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
        print(data)
    # Write the data to the CSV file
        with open('emissions_data.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(data)
            file.flush()
            
print("Emissions data written to emissions_data.csv")
