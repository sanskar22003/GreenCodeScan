
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
SOURCE_DIRECTORY = os.path.dirname(env_path)
GREEN_REFINED_DIRECTORY = os.path.join(SOURCE_DIRECTORY, 'GreenCode')
RESULT_DIR = os.path.join(SOURCE_DIRECTORY, 'GreenCode', 'Result')
def process_folder(BASE_DIR, EMISSIONS_DATA_CSV, RESULT_DIR, suffix):
    PYTEST_PATH = os.getenv('PYTEST_PATH')
    MAVEN_PATH = os.getenv('MAVEN_PATH')
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
    # **1. Python Unit Test Execution for each Python file**
    python_files = []
    for root, dirs, files in os.walk(BASE_DIR):
        for script in files:
            if script.endswith('.py') and script not in {'server_emissions.py', 'GreenCodeRefiner.py', 'compare_emissions.py', 'GreenCode'}:
                python_files.append(os.path.join(root, script))
    for script_path in python_files:
        tracker = EmissionsTracker()
        tracker.start()
        # Initialize variables
        duration = 0
        test_output = 'Unknown'
        try:
            start_time = time.time()
            test_result = subprocess.run([PYTEST_PATH, script_path], capture_output=True, text=True, timeout=20)  # 10 minutes timeout
            duration = time.time() - start_time
            test_output = 'Pass' if test_result.returncode == 0 else 'Fail'
        except subprocess.TimeoutExpired:
            test_output = 'Timeout'
            print(f"Pytest execution for {script_path} exceeded the timeout limit.")
        except Exception as e:
            test_output = 'Error'
            print(f"An error occurred for {script_path}: {e}")
        finally:
            tracker.stop()
        emissions_csv_default_path = 'emissions.csv'  # Default path where CodeCarbon saves the file
        emissions_csv_target_path = EMISSIONS_CSV  # Adjusted target path within 'result' directory with suffix
        # Check if the file exists at the default location and move it
        if os.path.exists(emissions_csv_default_path):
            shutil.move(emissions_csv_default_path, emissions_csv_target_path)
        
        if os.stat(EMISSIONS_CSV).st_size != 0:
            emissions_data = pd.read_csv(EMISSIONS_CSV).iloc[-1]
            data = [
                CUSTOMER_NAME,
                os.path.basename(script_path),
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
    # **2. Java Unit Test Execution remains unchanged**
    java_files = []
    for root, dirs, files in os.walk(BASE_DIR):
        for script in files:
            if script.endswith('.java') and script not in {'server_emissions.py', 'GreenCodeRefiner.py', 'compare_emissions.py', 'GreenCode'}:
                java_files.append(os.path.join(root, script))
    for script_path in java_files:
        tracker = EmissionsTracker()
        tracker.start()
        try:
            start_time = time.time()
            os.chdir(os.path.dirname(script_path))
            test_result = subprocess.run([MAVEN_PATH, '-Dtest=' + os.path.splitext(os.path.basename(script_path))[0] + 'Test', 'test'], capture_output=True, text=True, timeout=20)  # 10 minutes timeout
            duration = time.time() - start_time
            test_output = 'Pass' if test_result.returncode == 0 else 'Fail'
        except subprocess.TimeoutExpired:
            test_output = 'Timeout'
            print(f"Java test execution for {script_path} exceeded the timeout limit.")
        except Exception as e:
            test_output = 'Error'
            print(f"An error occurred for {script_path}: {e}")
        finally:
            tracker.stop()
        emissions_csv_default_path = 'emissions.csv'
        emissions_csv_target_path = EMISSIONS_CSV
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
    print(f"Emissions data and test results written to {EMISSIONS_DATA_CSV}")
# Process each folder with suffix
process_folder(SOURCE_DIRECTORY, os.path.join(RESULT_DIR, 'main_before_emissions_data.csv'), RESULT_DIR, 'before-in-detail')
process_folder(GREEN_REFINED_DIRECTORY, os.path.join(RESULT_DIR, 'main_after_emissions_data.csv'), RESULT_DIR, 'after-in-detail')
