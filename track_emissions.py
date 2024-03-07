import os
import subprocess
import csv
from codecarbon import EmissionsTracker
from datetime import datetime
import time
import pandas as pd

# Directory containing the scripts
scripts_dir = r"C:\ProgramData\Jenkins\.jenkins\workspace\GreenCodeScanPipeline"

# Directory containing the tests
tests_dir = r"C:\ProgramData\Jenkins\.jenkins\workspace\GreenCodeScanPipeline\tests"

# Path to pytest executable
pytest_path = r"C:\Users\sansk\AppData\Local\Programs\Python\Python312\Scripts\pytest.exe"

# Create a CSV file to store emissions data
with open('emissions_data.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Customer Name","Application name", "Timestamp", "Emissions (kgCO2)", "Duration", "emissions_rate", "CPU Power", "GPU Power", "RAM Power", "CPU Energy", "GPU Energy", "RAM Energy", "Energy Consumed", "Test Results"])

# Iterate over each script in the directory
for script in os.listdir(scripts_dir):
    if script.endswith('.py') and script != 'track_emissions.py':
        # Create a new EmissionsTracker for each script
        tracker = EmissionsTracker()

        # Start the emissions tracker
        tracker.start()

        # Initialize duration
        duration = None
        Customer_name = "ZF"
        # Execute the script with a timeout
        try:
            start_time = time.time()
            subprocess.run(['python', os.path.join(scripts_dir, script)], timeout=60)
            duration = time.time() - start_time
        except subprocess.TimeoutExpired:
            print(f"Script {script} exceeded the timeout limit.")

        # Stop the emissions tracker
        tracker.stop()

        # Run the tests for the script
        test_script = os.path.join(tests_dir, 'test_' + script)
        if os.path.exists(test_script):
            test_result = subprocess.run([pytest_path, '-q', '-rA', test_script], capture_output=True, text=True)
            test_output = 'Pass' if test_result.returncode == 0 else 'Fail'
        else:
            test_output = 'No tests found for script.'

        # Check if the emissions.csv file is empty
        if os.stat('C:/ProgramData/Jenkins/.jenkins/workspace/GreenCodeScanPipeline/emissions.csv').st_size != 0:
            # Read the emissions data from the CSV file
            emissions_data = pd.read_csv('C:/ProgramData/Jenkins/.jenkins/workspace/GreenCodeScanPipeline/emissions.csv').iloc[-1]

            # Retrieve and format the emissions data
            data = [
                Customer_name,
                script,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                emissions_data['emissions'],
                duration,
                emissions_data['emissions_rate'],
                emissions_data['cpu_power'],
                emissions_data['gpu_power'],
                emissions_data['ram_power'],
                emissions_data['cpu_energy'],
                emissions_data['gpu_energy'],
                emissions_data['ram_energy'],
                emissions_data['energy_consumed'],
                test_output
            ]

            # Write the data to the CSV file
            with open('emissions_data.csv', 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(data)
                file.flush()

print("Emissions data and test results written to emissions_data.csv")
