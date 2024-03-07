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
    writer.writerow(["Script Name", "Timestamp", "CO2 Emissions (kg)", "Duration (s)", "CPU Power (W)", "RAM Power (W)", "Total Energy (kWh)", "Cloud Provider", "Cloud Region", "Cloud Emissions (kgCO2)", "Country Name", "Country ISO Code", "Country Emissions (kgCO2)", "Region", "Region Emissions (kgCO2)"])

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
            emissions_data = tracker._emissions # Use the property instead of the attribute

            # Format the data and timestamp for logging
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            emissions = f"{emissions_data._emissions}" # Use the emissions attribute instead of the _emissions attribute
            duration = f"{emissions_data.run_time}" # Use the run_time attribute instead of the duration attribute
            cpu_power = f"{emissions_data.cpu_power}"
            ram_power = f"{emissions_data.ram_power}"
            energy_consumed = f"{emissions_data.energy_consumed}"
            cloud_provider = f"{emissions_data.cloud_provider}"
            cloud_region = f"{emissions_data.cloud_region}"
            cloud_emissions = f"{emissions_data.cloud_emissions}"
            country_name = f"{emissions_data.country_name}"
            country_iso_code = f"{emissions_data.country_iso_code}"
            country_emissions = f"{emissions_data.country_emissions}"
            region = f"{emissions_data.region}"
            region_emissions = f"{emissions_data.region_emissions}"

            # Write the data to the CSV file
            writer.writerow([script, timestamp, emissions, duration, cpu_power, ram_power, energy_consumed, cloud_provider, cloud_region, cloud_emissions, country_name, country_iso_code, country_emissions, region, region_emissions])

# Print a message indicating the completion of the script
print("Emissions data written to emissions_data.csv")
