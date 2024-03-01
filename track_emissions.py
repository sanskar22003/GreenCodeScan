import os
import subprocess
from codecarbon import EmissionsTracker

# Directory containing the scripts
repository_directory = "track_emissions.py"

# Command to run scripts for each language
commands = {
    ".py": "python",  # For Python files
    ".c": "gcc",      # For C files (replace with appropriate compiler)
    ".cpp": "g++",    # For C++ files (replace with appropriate compiler)
    # Add more commands for other languages as needed
}

# Create a new EmissionsTracker
tracker = EmissionsTracker()

# Iterate over the files in the repository directory
for filename in os.listdir(repository_directory):
    for extension, command in commands.items():
        if filename.endswith(extension):
            filepath = os.path.join(repository_directory, filename)
            
            # Start tracking emissions
            tracker.start()
            
            # Run the script using the appropriate command
            subprocess.run([command, filepath])
            
            # Stop tracking emissions
            tracker.stop()
            
            # Print emissions for the current file
            print(f"Emissions for {filename}: {tracker.emissions}")
