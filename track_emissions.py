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
    ".py": "python",
    ".cpp": "g++",  # Assumes the g++ compiler
    ".cs": "csc",  # Assumes the .NET Compiler
    ".java": "java",  # Assumes the Java compiler
}

# Create a CSV file to store emissions data
csv_file = "emissions_data.csv"
with open(csv_file, 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Filename", "Timestamp", "Emissions (kgCO2)", "Duration", "CPU Power", "RAM Power", "Energy Consumed"])

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

                # Write emissions data to CSV
                writer.writerow([filename, timestamp, emissions_data.emissions, duration, cpu_power, ram_power, energy_consumed])

print("Emissions data written to", csv_file)
