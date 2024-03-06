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
            emissions_data = tracker._emissions # Use the attribute instead of the property

            # Format the data and timestamp for logging
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            emissions = f"{emissions_data._emissions}" # Use the _emissions attribute instead of the emissions attribute
            duration = f"{emissions_data.duration}"
            cpu_power = f"{emissions_data.cpu_power}"
            ram_power = f"{emissions_data.ram_power}"
            energy_consumed = f"{emissions_data.energy_consumed}"

            # Write the data to the CSV file
            writer.writerow([script, timestamp, emissions, duration, cpu_power, ram_power, energy_consumed])

# Print a message indicating the completion of the script
print("Emissions data written to emissions_data.csv")
