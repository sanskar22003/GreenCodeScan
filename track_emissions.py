import os
import subprocess
import csv
from codecarbon import EmissionsTracker
from datetime import datetime
import time
import pandas as pd
import sys

# Directory containing the scripts
scripts_dir = r"C:\ProgramData\Jenkins\.jenkins\workspace\GreenCodeScanPipeline"

# Directory containing the Python tests
tests_dir = r"C:\ProgramData\Jenkins\.jenkins\workspace\GreenCodeScanPipeline\tests"

# Path to pytest executable
pytest_path = r"C:\Users\sansk\AppData\Local\Programs\Python\Python312\Scripts\pytest.exe"

# Check if the CSV file exists, if not create it and write the header
if not os.path.exists('emissions_data.csv'):
    with open('emissions_data.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Customer Name", "Application name", "File Type", "Timestamp", "Emissions (kgCO2)", "Duration", "emissions_rate", "CPU Power", "GPU Power", "RAM Power", "CPU Energy", "GPU Energy", "RAM Energy", "Energy Consumed", "Test Results"])

# Iterate over each script in the directory
for script in os.listdir(scripts_dir):
    if script.endswith(('.py', '.java', '.cpp', '.cs')) and script != 'track_emissions.py' and script != 'product_detailsTest.java' and script != 'server_emissions.py':
        # Rest of the code...
        # Create a new EmissionsTracker for each script
        tracker = EmissionsTracker()

        # Initialize duration
        duration = None
        Customer_name = "ZF"

        # Get the file type
        _, file_type = os.path.splitext(script)
        # Run the tests for the script
        test_script = os.path.join(tests_dir if script.endswith('.py') else scripts_dir, os.path.splitext(script)[0] + 'Test')
        if os.path.exists(test_script + '.py') or os.path.exists(test_script + '.java'):
            if script.endswith('.py'):
                sys.path.append(scripts_dir)
                test_result = subprocess.run([pytest_path, test_script + '.py'], capture_output=True, text=True)
            elif script.endswith('.java'):
                os.chdir(scripts_dir)
                #print('Running command: mvn -Dtest=' + os.path.splitext(script)[0] + 'Test test')
                #print('Current PATH: ' + os.environ['PATH'])
                test_result = subprocess.run(['C:\\Users\\sansk\\Downloads\\apache-maven-3.9.6\\bin\\mvn.cmd', '-Dtest=' + os.path.splitext(script)[0] + 'Test', 'test'], capture_output=True, text=True)
            test_output = 'Pass' if test_result.returncode == 0 else 'Fail'
        else:
            test_output = 'No tests found for script.'

        # Start the emissions tracker
        tracker.start()

        # Execute the script with a timeout
        try:
            start_time = time.time()
            if script.endswith('.py'):
                subprocess.run(['python', os.path.join(scripts_dir, script)], timeout=60)
            elif script.endswith('.java'):
                subprocess.run(['javac', os.path.join(scripts_dir, script)], timeout=60)
                subprocess.run(['java', '-cp', scripts_dir, os.path.splitext(script)[0]], timeout=60)
            # Add commands to run .NET and C++ files here
            duration = time.time() - start_time
        except subprocess.TimeoutExpired:
            print(f"Script {script} exceeded the timeout limit.")

        # Stop the emissions tracker
        tracker.stop()

        # Check if the emissions.csv file is empty
        if os.stat('C:/ProgramData/Jenkins/.jenkins/workspace/GreenCodeScanPipeline/emissions.csv').st_size != 0:
            # Read the emissions data from the CSV file
            emissions_data = pd.read_csv('C:/ProgramData/Jenkins/.jenkins/workspace/GreenCodeScanPipeline/emissions.csv').iloc[-1]

            # Retrieve and format the emissions data
            # Retrieve and format the emissions data
            # Retrieve and format the emissions data
            data = [
                Customer_name,
                script,
                file_type,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                emissions_data['emissions'] * 1000,  # Convert from kgCO2eq to gCO2eq
                duration,
                emissions_data['emissions_rate'] * 1000,  # Convert from kgCO2eq to gCO2eq
                emissions_data['cpu_power'],  # Convert from kWh to Wh
                emissions_data['gpu_power'],  # Convert from kWh to Wh
                emissions_data['ram_power'],  # Convert from kWh to Wh
                emissions_data['cpu_energy'] * 1000,  # Convert from kWh to Wh
                emissions_data['gpu_energy'],  # Convert from kWh to Wh
                emissions_data['ram_energy'] * 1000,  # Convert from kWh to Wh
                emissions_data['energy_consumed'] * 1000,  # Convert from kWh to Wh
                test_output
            ]

        # Write the data to the CSV file
        with open('emissions_data.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(data)
            file.flush()

print("Emissions data and test results written to emissions_data.csv")
