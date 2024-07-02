import os
import subprocess
import csv
from codecarbon import EmissionsTracker
from datetime import datetime
import time
import pandas as pd
import sys

# Define all paths and constants here
BASE_DIR = r"C:\ProgramData\Jenkins\.jenkins\workspace\GreenCodeScanPipeline\tests2"    #Modified: BASE_DIR = r"C:\ProgramData\Jenkins\.jenkins\workspace\GreenCodeScanPipeline"
SCRIPTS_DIR = os.path.join(BASE_DIR)
TESTS_DIR = os.path.join(BASE_DIR, "tests2")        #modified: TESTS_DIR = os.path.join(BASE_DIR, "tests")
PYTEST_PATH = r"C:\Users\sansk\AppData\Local\Programs\Python\Python312\Scripts\pytest.exe"
MAVEN_PATH = r"C:\Users\sansk\Downloads\apache-maven-3.9.6\bin\mvn.cmd"
EMISSIONS_CSV = os.path.join(BASE_DIR, 'emissions.csv')
EMISSIONS_DATA_CSV = 'emissions_data_before.csv'        #Modified: EMISSIONS_DATA_CSV = 'emissions_data.csv'
CUSTOMER_NAME = "ZF"

#Added \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# Ensure the EMISSIONS_CSV file exists, if not create it and write the header
if not os.path.exists(EMISSIONS_CSV):
    with open(EMISSIONS_CSV, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Customer Name", "Application name", "File Type", "Timestamp", "Emissions (gCO2eq)", "Duration", "emissions_rate", "CPU Power (KWh)", "GPU Power (KWh)", "RAM Power (KWh)", "CPU Energy (Wh)", "GPU Energy (KWh)", "RAM Energy (Wh)", "Energy Consumed (Wh)", "Test Results"])

#\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\


# Check if the CSV file exists, if not create it and write the header
if not os.path.exists(EMISSIONS_DATA_CSV):
    with open(EMISSIONS_DATA_CSV, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Customer Name", "Application name", "File Type", "Timestamp", "Emissions (gCO2eq)", "Duration", "emissions_rate", "CPU Power (KWh)", "GPU Power (KWh)", "RAM Power (KWh)", "CPU Energy (Wh)", "GPU Energy (KWh)", "RAM Energy (Wh)", "Energy Consumed (Wh)", "Test Results"])

# Iterate over each script in the directory
for script in os.listdir(SCRIPTS_DIR):
    if script.endswith(('.py', '.java', '.cpp', '.cs')) and script != 'track_emissions.py' and script != 'product_detailsTest.java' and script != 'server_emissions.py' and script != 'update_google_sheets.py':
        # Rest of the code...
        # Create a new EmissionsTracker for each script
        tracker = EmissionsTracker()

        # Initialize duration
        duration = None

        # Get the file type
        _, file_type = os.path.splitext(script)
        # Run the tests for the script
        test_script = os.path.join(TESTS_DIR if script.endswith('.py') else SCRIPTS_DIR, os.path.splitext(script)[0] + 'Test')
        if os.path.exists(test_script + '.py') or os.path.exists(test_script + '.java'):
            if script.endswith('.py'):
                sys.path.append(SCRIPTS_DIR)
                test_result = subprocess.run([PYTEST_PATH, test_script + '.py'], capture_output=True, text=True)
            elif script.endswith('.java'):
                os.chdir(SCRIPTS_DIR)
                test_result = subprocess.run([MAVEN_PATH, '-Dtest=' + os.path.splitext(script)[0] + 'Test', 'test'], capture_output=True, text=True)
            test_output = 'Pass' if test_result.returncode == 0 else 'Fail'
        else:
            test_output = 'No tests found for script.'

        # Start the emissions tracker
        tracker.start()

        # Execute the script with a timeout
        try:
            start_time = time.time()
            if script.endswith('.py'):
                subprocess.run(['python', os.path.join(SCRIPTS_DIR, script)], timeout=60)
            elif script.endswith('.java'):
                subprocess.run(['javac', os.path.join(SCRIPTS_DIR, script)], timeout=60)
                subprocess.run(['java', '-cp', SCRIPTS_DIR, os.path.splitext(script)[0]], timeout=60)
            # Add commands to run .NET and C++ files here
            duration = time.time() - start_time
        except subprocess.TimeoutExpired:
            print(f"Script {script} exceeded the timeout limit.")

        # Stop the emissions tracker
        tracker.stop()

        emissions_df = pd.read_csv(EMISSIONS_CSV)
        if not emissions_df.empty:
                emissions_data = emissions_df.iloc[-1]
        # Check if the emissions.csv file is empty                            #/////////////////MODIFIED////////////////////////////
        '''if os.stat(EMISSIONS_CSV).st_size != 0:
            # Read the emissions data from the CSV file
            emissions_data = pd.read_csv(EMISSIONS_CSV).iloc[-1]'''

            # Retrieve and format the emissions data
            data = [
                CUSTOMER_NAME,
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
        else:
            print("EMISSIONS_CSV is empty. No emissions data to process.")

        # Write the data to the CSV file
        with open(EMISSIONS_DATA_CSV, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(data)
            file.flush()

print("Emissions data and test results written to emissions_data.csv")
