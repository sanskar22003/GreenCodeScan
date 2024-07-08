import os
import subprocess
import csv
from codecarbon import EmissionsTracker
from datetime import datetime
import time
import pandas as pd
import sys

def process_folder(BASE_DIR, EMISSIONS_DATA_CSV):
    SCRIPTS_DIR = os.path.join(BASE_DIR)
    TESTS_DIR = os.path.join(BASE_DIR, "tests")
    PYTEST_PATH = r"C:\Users\sansk\AppData\Local\Programs\Python\Python312\Scripts\pytest.exe"
    MAVEN_PATH = r"C:\Users\sansk\Downloads\apache-maven-3.9.6\bin\mvn.cmd"
    EMISSIONS_CSV = os.path.join(BASE_DIR, 'emissions.csv')
    CUSTOMER_NAME = "ZF"

    # Check if the CSV file exists, if not create it and write the header
    if not os.path.exists(EMISSIONS_DATA_CSV):
        with open(EMISSIONS_DATA_CSV, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Customer Name", "Application name", "File Type", "Timestamp", "Emissions (gCO2eq)", "Duration", "emissions_rate", "CPU Power (KWh)", "GPU Power (KWh)", "RAM Power (KWh)", "CPU Energy (Wh)", "GPU Energy (KWh)", "RAM Energy (Wh)", "Energy Consumed (Wh)", "Test Results"])

    # Before accessing EMISSIONS_CSV, ensure it exists to avoid FileNotFoundError
    if not os.path.exists(EMISSIONS_CSV):
        with open(EMISSIONS_CSV, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Customer Name", "Application name", "File Type", "Timestamp", "Emissions (gCO2eq)", "Duration", "emissions_rate", "CPU Power (KWh)", "GPU Power (KWh)", "RAM Power (KWh)", "CPU Energy (Wh)", "GPU Energy (KWh)", "RAM Energy (Wh)", "Energy Consumed (Wh)", "Test Results"])
            
    # Iterate over each script in the directory
    for script in os.listdir(SCRIPTS_DIR):
        if script.endswith(('.py', '.java', '.cpp', '.cs')) and script != 'track_emissions.py' and script != 'product_detailsTest.java' and script != 'server_emissions.py' and script != 'update_google_sheets.py':
            tracker = EmissionsTracker()
            duration = None
            _, file_type = os.path.splitext(script)
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

            tracker.start()

            try:
                start_time = time.time()
                if script.endswith('.py'):
                    subprocess.run(['python', os.path.join(SCRIPTS_DIR, script)], timeout=60)
                elif script.endswith('.java'):
                    subprocess.run(['javac', os.path.join(SCRIPTS_DIR, script)], timeout=60)
                    subprocess.run(['java', '-cp', SCRIPTS_DIR, os.path.splitext(script)[0]], timeout=60)
                duration = time.time() - start_time
            except subprocess.TimeoutExpired:
                print(f"Script {script} exceeded the timeout limit.")

            tracker.stop()

            if os.stat(EMISSIONS_CSV).st_size != 0:
                emissions_data = pd.read_csv(EMISSIONS_CSV).iloc[-1]
                data = [
                    CUSTOMER_NAME,
                    script,
                    file_type,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    emissions_data['emissions'] * 1000,
                    duration,
                    emissions_data['emissions_rate'] * 1000,
                    emissions_data['cpu_power'],
                    emissions_data['gpu_power'],
                    emissions_data['ram_power'],
                    emissions_data['cpu_energy'] * 1000,
                    emissions_data['gpu_energy'],
                    emissions_data['ram_energy'] * 1000,
                    emissions_data['energy_consumed'] * 1000,
                    test_output
                ]

                with open(EMISSIONS_DATA_CSV, 'a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(data)
                    file.flush()

    print(f"Emissions data and test results written to {EMISSIONS_DATA_CSV}")

# Define paths
source_folder = r"C:\ProgramData\Jenkins\.jenkins\workspace\GreenCodeScanPipeline\tests2"
refined_folder = r"C:\ProgramData\Jenkins\.jenkins\workspace\GreenCodeScanPipeline\Refined files"

# Process each folder
process_folder(source_folder, os.path.join(source_folder, 'before_emissions_data.csv'))
process_folder(refined_folder, os.path.join(refined_folder, 'after_emissions_data.csv'))
