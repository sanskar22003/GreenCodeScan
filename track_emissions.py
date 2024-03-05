import os
import subprocess
import csv
from codecarbon import EmissionsTracker
import datetime
from subprocess import TimeoutExpired
import xml.etree.ElementTree as ET

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
    writer.writerow(["Filename", "Timestamp", "Emissions (kgCO2)", "Duration", "CPU Power", "RAM Power", "Energy Consumed", "Test Results"])

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

                # Get the emissions for this script
                emissions_data = tracker.final_emissions_data

                # Get additional data
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                duration = emissions_data.duration
                cpu_power = emissions_data.cpu_power
                ram_power = emissions_data.ram_power
                energy_consumed = emissions_data.energy_consumed
                # Parse the report.xml file to get the test results
                # Parse the report.xml file to get the test results
                tree = ET.parse('report.xml')
                root = tree.getroot()
                tests = root.attrib.get('tests', '0')
                errors = root.attrib.get('errors', '0')
                failures = root.attrib.get('failures', '0')
                skipped = root.attrib.get('skipped', '0')

                # Add the test results to the CSV file
                writer.writerow([filename, timestamp, emissions_data.emissions, duration, cpu_power, emissions_data.ram_power, emissions_data.energy_consumed, f"Tests: {tests}, Errors: {errors}, Failures: {failures}, Skipped: {skipped}"])

print("Emissions data written to", csv_file)
