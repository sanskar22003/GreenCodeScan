
import os
import subprocess
import csv
from codecarbon import EmissionsTracker
from datetime import datetime
import time
import pandas as pd
import sys
import shutil
from dotenv import load_dotenv
# Load environment variables
env_path = os.path.abspath(".env")
load_dotenv(dotenv_path=env_path, verbose=True, override=True)
# Remove the '.env' part to get the SOURCE_DIRECTORY
SOURCE_DIRECTORY = os.path.dirname(env_path)
GREEN_REFINED_DIRECTORY = os.path.join(SOURCE_DIRECTORY, 'Green_Refined_Files')
RESULT_DIR = os.path.join(SOURCE_DIRECTORY, 'Green_Refined_Files', 'Result')
def process_folder(BASE_DIR, EMISSIONS_DATA_CSV, RESULT_DIR, suffix):
    PYTEST_PATH = os.getenv('PYTEST_PATH')
    MAVEN_PATH = os.getenv('MAVEN_PATH')
    CUSTOMER_NAME = "ZF"
    javac_path = os.getenv('JAVAC_PATH')
    
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
    # **1. Python Unit Test Execution with Pytest**
    if os.path.exists(BASE_DIR):
        excluded_items = {'server_emissions.py', 'GreenCodeRefiner.py', 'compare_emissions.py', 'Green_Refined_Files'}
        # Exclude specific files and folders for pytest
        pytest_cmd = [PYTEST_PATH, BASE_DIR]
        pytest_env = os.environ.copy()
        pytest_env['PYTEST_ADDOPTS'] = ' '.join(f'--ignore={os.path.join(BASE_DIR, item)}' for item in excluded_items)
        tracker = EmissionsTracker()
        tracker.start()
        try:
            start_time = time.time()
            test_result = subprocess.run(pytest_cmd, capture_output=True, text=True, env=pytest_env)
            duration = time.time() - start_time
            test_output = 'Pass' if test_result.returncode == 0 else 'Fail'
        except subprocess.TimeoutExpired:
            print(f"Pytest execution exceeded the timeout limit.")
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
                "Python Tests",
                ".py",
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
    # **2. Java Unit Test Execution**
    java_files = []
    for root, dirs, files in os.walk(BASE_DIR):
        for script in files:
            if script.endswith('.java') and script not in excluded_items:
                java_files.append(os.path.join(root, script))
    for script_path in java_files:
        tracker = EmissionsTracker()
        tracker.start()
        try:
            start_time = time.time()
            os.chdir(os.path.dirname(script_path))
            test_result = subprocess.run([MAVEN_PATH, '-Dtest=' + os.path.splitext(os.path.basename(script_path))[0] + 'Test', 'test'], capture_output=True, text=True)
            duration = time.time() - start_time
            test_output = 'Pass' if test_result.returncode == 0 else 'Fail'
        except subprocess.TimeoutExpired:
            print(f"Java test execution exceeded the timeout limit.")
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
                os.path.basename(script_path),
                ".java",
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
    # **3. Placeholders for Future `.cpp` and `.cs` Testing**
    # Placeholder for `.cpp` files testing
    # TODO: Implement unit test execution for `.cpp` files if needed in the future.
    # Placeholder for `.cs` files testing
    # TODO: Implement unit test execution for `.cs` files if needed in the future.
    print(f"Emissions data and test results written to {EMISSIONS_DATA_CSV}")
# Process each folder with suffix
process_folder(SOURCE_DIRECTORY, os.path.join(RESULT_DIR, 'main_before_emissions_data.csv'), RESULT_DIR, 'before-in-detail')
process_folder(GREEN_REFINED_DIRECTORY, os.path.join(RESULT_DIR, 'main_after_emissions_data.csv'), RESULT_DIR, 'after-in-detail')
