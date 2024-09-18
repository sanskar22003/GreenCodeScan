import os
import subprocess
import csv
from codecarbon import EmissionsTracker
from datetime import datetime
import time
import pandas as pd
import shutil
from dotenv import load_dotenv
# Load environment variables
env_path = os.path.abspath(".env")
load_dotenv(dotenv_path=env_path, verbose=True, override=True)
SOURCE_DIRECTORY = os.path.dirname(env_path)
GREEN_REFINED_DIRECTORY = os.path.join(SOURCE_DIRECTORY, 'GreenCode')
RESULT_DIR = os.path.join(SOURCE_DIRECTORY, 'Result')

ExcludedFiles = ['server_emissions.py', 'GreenCodeRefiner.py', 'track_emissions.py', 'compare_emissions.py', 'GreenCode']

# Function to process emissions for a single file
def process_emissions_for_file(tracker, script_path, emissions_csv, file_type, result_dir, test_command):
    emissions_data = None
    duration = 0
    test_output = 'Unknown'
    script_name = os.path.basename(script_path)
    
    try:
        tracker.start()  # Start the emissions tracking
        
        if 'test' in script_name.lower():
            start_time = time.time()
            test_result = subprocess.run(test_command, capture_output=True, text=True, timeout=20)  # Run the test
            duration = time.time() - start_time
            test_output = 'Pass' if test_result.returncode == 0 else 'Fail'
        else:
            # This is a normal programming file (not a test)
            test_output = 'Not a test file'
            print(f"Skipping test execution for {script_name} as it is a normal programming file.")
    
    
    except subprocess.TimeoutExpired:
        test_output = 'Timeout'
        print(f"Test execution for {script_path} exceeded the timeout limit.")
    
    except Exception as e:
        test_output = 'Error'
        print(f"An error occurred for {script_path}: {e}")
    
    finally:
        emissions_data = tracker.stop()  # Stop the emissions tracking
    
    # If emissions data was collected, save it
    if emissions_data is not None:
        emissions_csv_default_path = 'emissions.csv'  # Default location for emissions.csv
        emissions_csv_target_path = os.path.join(result_dir, 'emissions.csv')  # Target location
        # Move the emissions.csv to the result directory
        if os.path.exists(emissions_csv_default_path):
            shutil.move(emissions_csv_default_path, emissions_csv_target_path)
        # Read the latest emissions data from the moved CSV
        if os.stat(emissions_csv_target_path).st_size != 0:
            emissions_data = pd.read_csv(emissions_csv_target_path).iloc[-1]
            data = [
                #customer_name,
                os.path.basename(script_path),
                file_type,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                emissions_data['emissions'] * 1000,  # Convert to gCO2eq
                duration,
                emissions_data['emissions_rate'] * 1000,  # Convert to gCO2eq/s
                emissions_data['cpu_power'],
                emissions_data['gpu_power'],
                emissions_data['ram_power'],
                emissions_data['cpu_energy'] * 1000,  # Convert to Wh
                emissions_data['gpu_energy'],
                emissions_data['ram_energy'] * 1000,  # Convert to Wh
                emissions_data['energy_consumed'] * 1000,  # Convert to Wh
                test_output
            ]
            with open(emissions_csv, 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(data)
                file.flush()
        else:
            print(f"No emissions data found for {script_path}")


# Function to process test execution for different file types
def process_files_by_type(base_dir, emissions_data_csv, result_dir, file_extension, excluded_files, tracker, test_command_generator):
    files = []
    for root, dirs, file_list in os.walk(base_dir):
        for script in file_list:
            if script.endswith(file_extension) and script not in excluded_files:
                files.append(os.path.join(root, script))
    
    for script_path in files:
        test_command = test_command_generator(script_path)
        process_emissions_for_file(
            tracker=tracker,
            script_path=script_path,
            emissions_csv=emissions_data_csv,
            file_type=file_extension,
            result_dir=result_dir,
            test_command=test_command
        )

# Generate test commands for each language
def get_python_test_command(script_path):
    return [os.getenv('PYTEST_PATH'), script_path]

def get_java_test_command(script_path):
    return [os.getenv('MAVEN_PATH'), '-Dtest=' + os.path.splitext(os.path.basename(script_path))[0] + 'Test', 'test']

def get_cpp_test_command(script_path):
    test_file_name = os.path.basename(script_path).replace('.cpp', '_test.cpp')
    test_file_path = os.path.join('test', test_file_name)
    compile_command = ['g++', '-o', 'test_output', test_file_path, '-lgtest', '-lgtest_main', '-pthread']
    run_command = ['./test_output']
    return compile_command + run_command

def get_cs_test_command(script_path):
    return [os.getenv('NUNIT_PATH'), 'test', os.path.splitext(os.path.basename(script_path))[0] + '.dll']

# Refactored process_folder function
def process_folder(base_dir, emissions_data_csv, result_dir, suffix):
    excluded_files = ['server_emissions.py', 'GreenCodeRefiner.py', 'track_emissions.py', 'compare_emissions.py', 'GreenCode']

    # Ensure the 'result' directory exists
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
    
    # Adjust the path for emissions.csv to be within the 'result' directory with suffix
    emissions_csv = os.path.join(result_dir, f'emissions_{suffix}.csv')

    # Check if the CSV file exists, if not, create it and write the header
    if not os.path.exists(emissions_data_csv):
        with open(emissions_data_csv, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([
                "Application name", "File Type", "Timestamp", "Emissions (gCO2eq)",
                "Duration", "emissions_rate", "CPU Power (KWh)", "GPU Power (KWh)", "RAM Power (KWh)",
                "CPU Energy (Wh)", "GPU Energy (KWh)", "RAM Energy (Wh)", "Energy Consumed (Wh)", "Test Results"
            ])

    tracker = EmissionsTracker()

    # Process files for each language
    process_files_by_type(base_dir, emissions_data_csv, result_dir, '.py', excluded_files, tracker, get_python_test_command)
    process_files_by_type(base_dir, emissions_data_csv, result_dir, '.java', excluded_files, tracker, get_java_test_command)
    process_files_by_type(base_dir, emissions_data_csv, result_dir, '.cpp', excluded_files, tracker, get_cpp_test_command)
    process_files_by_type(base_dir, emissions_data_csv, result_dir, '.cs', excluded_files, tracker, get_cs_test_command)

    print(f"Emissions data and test results written to {emissions_data_csv}")

# Call process_folder for 'before' and 'after' emissions data
process_folder(SOURCE_DIRECTORY, os.path.join(RESULT_DIR, 'main_before_emissions_data.csv'), RESULT_DIR, 'before-in-detail')
process_folder(GREEN_REFINED_DIRECTORY, os.path.join(RESULT_DIR, 'main_after_emissions_data.csv'), RESULT_DIR, 'after-in-detail')


# # Process the folder and run the tests
# def process_folder(BASE_DIR, EMISSIONS_DATA_CSV, RESULT_DIR, suffix):
#     PYTEST_PATH = os.getenv('PYTEST_PATH')
#     MAVEN_PATH = os.getenv('MAVEN_PATH')
#     NUNIT_PATH = os.getenv('NUNIT_PATH')
#     #CUSTOMER_NAME = "ZF"
   
#     # Ensure the 'result' directory exists
#     if not os.path.exists(RESULT_DIR):
#         os.makedirs(RESULT_DIR)
    
#     # Adjust the path for emissions.csv to be within the 'result' directory with suffix
#     EMISSIONS_CSV = os.path.join(RESULT_DIR, f'emissions_{suffix}.csv')
#     # Check if the CSV file exists, if not create it and write the header
#     if not os.path.exists(EMISSIONS_DATA_CSV):
#         with open(EMISSIONS_DATA_CSV, 'w', newline='') as file:
#             writer = csv.writer(file)
#             writer.writerow([
#                 "Application name", "File Type", "Timestamp", "Emissions (gCO2eq)",
#                 "Duration", "emissions_rate", "CPU Power (KWh)", "GPU Power (KWh)", "RAM Power (KWh)",
#                 "CPU Energy (Wh)", "GPU Energy (KWh)", "RAM Energy (Wh)", "Energy Consumed (Wh)", "Test Results"
#             ])
#     # **1. Python Unit Test Execution for each Python file**
#     python_files = []
#     for root, dirs, files in os.walk(BASE_DIR):
#         for script in files:
#             if script.endswith('.py') and script not in ExcludedFiles:
#                 python_files.append(os.path.join(root, script))
#     for script_path in python_files:
#         tracker = EmissionsTracker()
#         process_emissions_for_file(
#             tracker=tracker,
#             script_path=script_path,
#             emissions_csv=EMISSIONS_DATA_CSV,  # <-- Make sure this path is passed here
#             #customer_name=CUSTOMER_NAME,
#             file_type=".py",
#             result_dir=RESULT_DIR,
#             test_command=[PYTEST_PATH, script_path]
#         )
#     # **2. Java Unit Test Execution remains unchanged**
#     java_files = []
#     for root, dirs, files in os.walk(BASE_DIR):
#         for script in files:
#             if script.endswith('.java') and script not in ExcludedFiles:
#                 java_files.append(os.path.join(root, script))
#     for script_path in java_files:
#         tracker = EmissionsTracker()
#         process_emissions_for_file(
#             tracker=tracker,
#             script_path=script_path,
#             emissions_csv=EMISSIONS_DATA_CSV,  # <-- Ensure this is passed here as well
#             #customer_name=CUSTOMER_NAME,
#             file_type=".java",
#             result_dir=RESULT_DIR,
#             test_command=[MAVEN_PATH, '-Dtest=' + os.path.splitext(os.path.basename(script_path))[0] + 'Test', 'test']
#         )

#     # **C++ Unit Test Execution**
#     cpp_files = []
#     for root, dirs, files in os.walk(BASE_DIR):
#         for script in files:
#             if script.endswith('.cpp') and script not in ExcludedFiles:
#                 cpp_files.append(os.path.join(root, script))
#     for script_path in cpp_files:
#         tracker = EmissionsTracker()
#         # Define the test command (assuming the test file has the same name as the source file but in the 'test' folder)
#         test_file_name = os.path.basename(script_path).replace('.cpp', '_test.cpp')
#         test_file_path = os.path.join('test', test_file_name)
#         # Compile and run Google Test
#         test_command = ['g++', '-o', 'test_output', test_file_path, '-lgtest', '-lgtest_main', '-pthread']
#         run_test_command = ['./test_output']
#         process_emissions_for_file(
#             tracker=tracker,
#             script_path=script_path,
#             emissions_csv=EMISSIONS_DATA_CSV,
#             #customer_name=CUSTOMER_NAME,
#             file_type=".cpp",
#             result_dir=RESULT_DIR,
#             test_command=test_command + run_test_command
#         )

#     # **C# Unit Test Execution**
#     cs_files = []
#     for root, dirs, files in os.walk(BASE_DIR):
#         for script in files:
#             if script.endswith('.cs') and script not in ExcludedFiles:
#                 cs_files.append(os.path.join(root, script))

#     for script_path in cs_files:
#         tracker = EmissionsTracker()
#         process_emissions_for_file(
#             tracker=tracker,
#             script_path=script_path,
#             emissions_csv=EMISSIONS_DATA_CSV,
#             #customer_name=CUSTOMER_NAME,
#             file_type=".cs",
#             result_dir=RESULT_DIR,
#             test_command=[NUNIT_PATH, 'test', os.path.splitext(os.path.basename(script_path))[0] + '.dll']
#         )

# # **3. Placeholders for Future `.cpp` and `.cs` Testing**
#     print(f"Emissions data and test results written to {EMISSIONS_DATA_CSV}")
# # Process each folder with suffix
# process_folder(SOURCE_DIRECTORY, os.path.join(RESULT_DIR, 'main_before_emissions_data.csv'), RESULT_DIR, 'before-in-detail')
# process_folder(GREEN_REFINED_DIRECTORY, os.path.join(RESULT_DIR, 'main_after_emissions_data.csv'), RESULT_DIR, 'after-in-detail')
