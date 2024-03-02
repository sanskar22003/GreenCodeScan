import os
import subprocess
import csv
from codecarbon import EmissionsTracker

# Directory containing the scripts
directory = r"C:\Users\sansk\OneDrive\Desktop\StaticCodeAnalysis"

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
    writer.writerow(["File Name", "Emissions (kgCO2)"])

    # Iterate over the scripts in the directory
    for filename in os.listdir(directory):
        for extension, command in commands.items():
            if filename.endswith(extension):
                filepath = os.path.join(directory, filename)

                # Create a new EmissionsTracker for each script
                tracker = EmissionsTracker()

                # Start tracking
                tracker.start()

                # Run the script
                subprocess.run([command, filepath])

                # Stop tracking
                tracker.stop()

                # Get the emissions for this script
                emissions = tracker.emissions

                # Write emissions data to CSV
                writer.writerow([filename, emissions])

print("Emissions data written to", csv_file)
