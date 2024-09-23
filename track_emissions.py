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

# Compare emissions logic
def compare_emissions():
    # Load environment variables again (if needed)
    load_dotenv(dotenv_path=env_path, verbose=True, override=True)

    # Remove the '.env' part to get the SOURCE_DIRECTORY
    result_source_dir = os.path.join(SOURCE_DIRECTORY, 'Result', 'main_before_emissions_data.csv')
    result_green_refined_directory = os.path.join(SOURCE_DIRECTORY, 'Result', 'main_after_emissions_data.csv')

    # Read CSV files
    emissions_df = pd.read_csv(result_source_dir)
    emissions_after_df = pd.read_csv(result_green_refined_directory)

    # Merge dataframes on common columns
    merged_df = emissions_df.merge(emissions_after_df, on=["Application name", "File Type"], suffixes=('_before', '_after'))

    # Calculate the difference in emissions and determine the result
    merged_df['final emission'] = merged_df['Emissions (gCO2eq)_before'] - merged_df['Emissions (gCO2eq)_after']
    merged_df['Result'] = merged_df['final emission'].apply(lambda x: 'Improved' if x > 0 else 'Need improvement')

    # Select and rename columns
    result_df = merged_df[["Application name", "File Type", "Timestamp_before", "Timestamp_after", "Emissions (gCO2eq)_before", "Emissions (gCO2eq)_after", "final emission", "Result"]]
    result_df.columns = ["Application name", "File Type", "Timestamp (Before)", "Timestamp (After)", "Before", "After", "Final Emission", "Result"]

    # Create 'Result' folder if it doesn't exist
    if not os.path.exists(RESULT_DIR):
        os.makedirs(RESULT_DIR)

    # Write to new CSV file
    result_file_path = os.path.join(RESULT_DIR, "comparison_results.csv")
    result_df.to_csv(result_file_path, index=False)

    print(f"Comparison results saved to {result_file_path}")

# Call the compare_emissions function
compare_emissions()
