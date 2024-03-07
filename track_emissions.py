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
    # Write the header row with the column names
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

            # Execute the script with a timeout of 60 seconds
            try:
                start_time = time.time()
                subprocess.run(['python', os.path.join(scripts_dir, script)], timeout=60)
                duration = time.time() - start_time
            except subprocess.TimeoutExpired:
                # If the script exceeds the timeout, log a message and terminate its execution
                print(f"Script {script} exceeded the timeout limit.")

            # Stop the emissions tracker
            tracker.stop()

            # Retrieve emissions data from the EmissionsTracker object
            emissions_data = tracker.final_emissions_data # Use the property instead of the attribute
            print(emissions_data)
            # Format the data and timestamp for logging
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            duration = emissions_data.duration
            cpu_power = emissions_data.cpu_power
            ram_power = emissions_data.ram_power
            energy_consumed = emissions_data.energy_consumed

            # Write the data to the CSV file
   writer.writerow([script, timestamp, emissions_data.emissions, duration, cpu_power, ram_power, energy_consumed, test_results])

# Print a message indicating the completion of the script
print("Emissions data written to emissions_data.csv")
