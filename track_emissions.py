import os
import subprocess
import csv
from codecarbon import EmissionsTracker
from datetime import datetime
import time
import pandas as pd
import sys
import shutil

def process_folder(BASE_DIR, EMISSIONS_DATA_CSV, RESULT_DIR, suffix):
    SCRIPTS_DIR = os.path.join(BASE_DIR)
    TESTS_DIR = os.path.join(BASE_DIR, "tests")
    PYTEST_PATH = r"C:\Users\sansk\AppData\Local\Programs\Python\Python312\Scripts\pytest.exe"
    MAVEN_PATH = r"C:\Users\sansk\Downloads\apache-maven-3.9.6\bin\mvn.cmd"
    CUSTOMER_NAME = "ZF"

    # Ensure the 'result' directory exists
    if not os.path.exists(RESULT_DIR):
        os.makedirs(RESULT_DIR)

    # Adjust the path for emissions.csv to be within the 'result' directory with suffix
    EMISSIONS_CSV = os.path.join(RESULT_DIR, f'emissions_{suffix}.csv')

    # Check if the CSV file exists, if not create it and write the header
    if not os.path.exists(EMISSIONS_DATA_CSV):
        with open(EMISSIONS_DATA_CSV, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Customer Name", "Application name", "File Type", "Timestamp", "Emissions (gCO2eq)", "Duration", "emissions_rate", "CPU Power (KWh)", "GPU Power (KWh)", "RAM Power (KWh)", "CPU Energy (Wh)", "GPU Energy (KWh)", "RAM Energy (Wh)", "Energy Consumed (Wh)", "Test Results"])

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

            emissions_csv_default_path = 'emissions.csv'  # Default path where codecarbon saves the file
            emissions_csv_target_path = EMISSIONS_CSV  # Adjusted target path within 'result' directory with suffix

            # Check if the file exists at the default location and move it
            if os.path.exists(emissions_csv_default_path):
                shutil.move(emissions_csv_default_path, emissions_csv_target_path)

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
result_dir = r"C:\ProgramData\Jenkins\.jenkins\workspace\GreenCodeScanPipeline\Refined files\Result"

# Process each folder with suffix
process_folder(source_folder, os.path.join(result_dir, 'before_emissions_data.csv'), result_dir, 'before')
process_folder(refined_folder, os.path.join(result_dir, 'after_emissions_data.csv'), result_dir, 'after')
