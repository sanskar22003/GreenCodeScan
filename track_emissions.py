import os
import subprocess
import csv
from codecarbon import EmissionsTracker
import datetime
from subprocess import TimeoutExpired

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
    writer.writerow(["Filename", "Timestamp", "Emissions (kgCO2)", "Duration (s)", "CPU Power (W)", "RAM Power (W)", "Energy Consumed (kWh)"])

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
                # Stop tracking
# Stop tracking
                # Stop tracking
                tracker.stop()

# Get the emissions data
                emissions_data = tracker._emissions 

# Get additional data
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Write emissions data to CSV
                writer.writerow([filename, timestamp, emissions_data._emissions, emissions_data.duration, emissions_data.cpu_power, emissions_data.ram_power, emissions_data.energy_consumed])
print("Emissions data written to emissions_data.csv")
