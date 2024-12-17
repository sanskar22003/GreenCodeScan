import os
import json
import subprocess
import csv
from codecarbon import EmissionsTracker
from datetime import datetime
import time
import pandas as pd
import shutil
from dotenv import load_dotenv
import plotly.graph_objects as go
from xhtml2pdf import pisa
from jinja2 import Environment, FileSystemLoader, Template
import plotly.io as pio
import plotly.express as px
import plotly.graph_objs as go
import logging
import sqlite3
from datetime import datetime, timedelta
from TrackerFunction import (
    prepare_detailed_data,
    create_energy_graphs,
    create_emissions_graphs,
    create_embedded_code_graphs,
    create_top_five_tables
)

# Load environment variables
env_path = os.path.abspath(".env")
load_dotenv(dotenv_path=env_path, verbose=True, override=True)
SOURCE_DIRECTORY = os.path.dirname(env_path)

GREEN_REFINED_DIRECTORY = os.path.join(SOURCE_DIRECTORY, 'GreenCode')
RESULT_DIR = os.path.join(SOURCE_DIRECTORY, 'Result')
REPORT_DIR = os.path.join(SOURCE_DIRECTORY, 'Report')

# List of files and directories to exclude from processing
EXCLUDED_FILES = [file.strip() for file in os.getenv('EXCLUDED_FILES', '').split(',') if file.strip()]
EXCLUDED_DIRECTORIES = [file.strip() for file in os.getenv('EXCLUDED_DIRECTORIES', '').split(',') if file.strip()]

def process_emissions_for_file(tracker, script_path, emissions_csv, file_type, result_dir, test_command):
    # If no test command (not a test file), return immediately
    if not test_command:
        return
   
    emissions_data = None
    duration = 0
    test_output = 'Unknown'
    script_name = os.path.basename(script_path)

    # Extract 'solution dir' (immediate parent directory)
    solution_dir = os.path.basename(os.path.dirname(script_path))
    is_green_refined = os.path.commonpath([script_path, GREEN_REFINED_DIRECTORY]) == GREEN_REFINED_DIRECTORY

    tracker_started = False
    try:
        # Start the emissions tracking ONLY for test files
        tracker.start()
        tracker_started = True

        start_time = time.time()
        try:
            # Run test command for test files
            test_result = subprocess.run(test_command, capture_output=True, text=True, timeout=20)
            duration = time.time() - start_time
            test_output = 'Pass' if test_result.returncode == 0 else 'Fail'
        except subprocess.TimeoutExpired:
            test_output = 'Timeout'
    
    except Exception as e:
        logging.error(f"An error occurred while processing {script_name}: {e}")
        test_output = 'Error'

    finally:
        try:
            if tracker_started:
                emissions_data = tracker.stop()  # Stop the emissions tracking
        except Exception as e:
            logging.error(f"Error stopping the tracker for {script_name}: {e}")

    if emissions_data is not None:
        emissions_csv_default_path = 'emissions.csv'
        emissions_csv_target_path = os.path.join(result_dir, 'emissions.csv')
        try:
            if os.path.exists(emissions_csv_default_path):
                shutil.move(emissions_csv_default_path, emissions_csv_target_path)

            if os.stat(emissions_csv_target_path).st_size != 0:
                emissions_data = pd.read_csv(emissions_csv_target_path).iloc[-1]
                data = [
                    os.path.basename(script_path),
                    file_type,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    f"{emissions_data['emissions'] * 1000:.6f}",
                    f"{duration:.2f}",
                    f"{emissions_data['emissions_rate'] * 1000:.6f}",
                    f"{emissions_data['cpu_power']:.6f}",
                    f"{emissions_data['gpu_power']:.6f}",
                    f"{emissions_data['ram_power']:.6f}",
                    f"{emissions_data['cpu_energy'] * 1000:.6f}",
                    f"{emissions_data['gpu_energy']:.6f}",
                    f"{emissions_data['ram_energy'] * 1000:.6f}",
                    f"{emissions_data['energy_consumed'] * 1000:.6f}",
                    test_output,
                    solution_dir,
                    is_green_refined
                ]
                with open(emissions_csv, 'a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(data)
                    file.flush()
            else:
                logging.error(f"No emissions data found for {script_path}")
        except Exception as e:
            logging.error(f"Error processing emissions data for {script_path}: {e}")
    else:
        logging.error(f"Emissions data collection failed for {script_name}")

# Function to process test execution for different file types
def process_files_by_type(base_dir, emissions_data_csv, result_dir, file_extension, excluded_files, excluded_dirs, tracker, test_command_generator):
    files = []
    for root, dirs, file_list in os.walk(base_dir):
        # Exclude specified directories
        dirs[:] = [d for d in dirs if d not in excluded_dirs]

        # Additional check to ensure we're only processing files in the correct directory
        if base_dir == SOURCE_DIRECTORY:
            # For SOURCE_DIRECTORY, exclude files in GREEN_REFINED_DIRECTORY
            file_list = [f for f in file_list if GREEN_REFINED_DIRECTORY not in root]
        elif base_dir == GREEN_REFINED_DIRECTORY:
            # For GREEN_REFINED_DIRECTORY, only process files within this directory
            file_list = [f for f in file_list if GREEN_REFINED_DIRECTORY in root]

        for script in file_list:
            if script.endswith(file_extension) and script not in excluded_files:
                script_path = os.path.join(root, script)
                # Only add files that have a test command
                test_command = test_command_generator(script_path)
                if test_command:
                    files.append((script_path, test_command))
    
    # Process test files
    for script_path, test_command in files:
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
    return [os.getenv('PYTEST_PATH'), script_path] if 'test' in script_path.lower() else None
def get_java_test_command(script_path):
    return [os.getenv('MAVEN_PATH'), '-Dtest=' + os.path.splitext(os.path.basename(script_path))[0] + 'Test', 'test'] if 'test' in script_path.lower() else None
def get_cpp_test_command(script_path):
    if 'test' in script_path.lower():
        # Assuming a standard project structure
        test_file_name = os.path.basename(script_path).replace('.cpp', '_test.cpp')
        test_dir = os.path.join(os.path.dirname(script_path), 'test')
        test_file_path = os.path.join(test_dir, test_file_name)

        # Verify test file exists
        if not os.path.exists(test_file_path):
            logging.info(f"Warning: Test file {test_file_path} does not exist")
            return None
        
        # Create a temporary build directory
        build_dir = os.path.join(test_dir, 'build')
        os.makedirs(build_dir, exist_ok=True)
        
        # CMake command to configure the project
        cmake_config_command = [
            os.getenv('GTEST_CMAKE_PATH', 'cmake'), 
            f'-S{test_dir}', 
            f'-B{build_dir}', 
            '-DCMAKE_PREFIX_PATH=/usr/local',  # Ensure GTest can be found
            '-G', 'Unix Makefiles'
        ]
        
        # CMake build command
        cmake_build_command = [
            os.getenv('GTEST_CMAKE_PATH', 'cmake'), 
            '--build', 
            build_dir
        ]
        
        # Test run command
        test_executable = os.path.join(build_dir, f'{os.path.splitext(test_file_name)[0]}')
        run_test_command = [test_executable]
        
        return cmake_config_command + cmake_build_command + run_test_command
    
    return None
def get_cs_test_command(script_path):
    return [os.getenv('NUNIT_PATH'), 'test', os.path.splitext(os.path.basename(script_path))[0] + '.dll'] if 'test' in script_path.lower() else None

# Refactored process_folder function
def process_folder(base_dir, emissions_data_csv, result_dir, suffix, excluded_dirs):
    # Ensure the 'result' directory exists
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
        logging.info(f"Directory '{result_dir}' created successfully!")
    else:
        logging.info(f"Directory '{result_dir}' already exists.")
    
    # Check if the CSV file exists, if not, create it and write the header
    if not os.path.exists(emissions_data_csv):
        with open(emissions_data_csv, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([
                "Application name", "File Type", "Timestamp", "Emissions (gCO2eq)",
                "Duration", "emissions_rate", "CPU Power (KWh)", "GPU Power (KWh)", "RAM Power (KWh)",
                "CPU Energy (Wh)", "GPU Energy (KWh)", "RAM Energy (Wh)", "Energy Consumed (Wh)", "Test Results", "solution dir", "Is Green Refined"
            ])
        logging.info(f"CSV file '{emissions_data_csv}' created with headers.")
    tracker = EmissionsTracker()

    # Process files for each language
    process_files_by_type(
        base_dir=base_dir,
        emissions_data_csv=emissions_data_csv,
        result_dir=result_dir,
        file_extension='.py',
        excluded_files=EXCLUDED_FILES,
        excluded_dirs=EXCLUDED_DIRECTORIES,
        tracker=tracker,
        test_command_generator=get_python_test_command
    )
    process_files_by_type(
        base_dir=base_dir,
        emissions_data_csv=emissions_data_csv,
        result_dir=result_dir,
        file_extension='.java',
        excluded_files=EXCLUDED_FILES,
        excluded_dirs=EXCLUDED_DIRECTORIES,
        tracker=tracker,
        test_command_generator=get_java_test_command
    )
    process_files_by_type(
        base_dir=base_dir,
        emissions_data_csv=emissions_data_csv,
        result_dir=result_dir,
        file_extension='.cpp',
        excluded_files=EXCLUDED_FILES,
        excluded_dirs=EXCLUDED_DIRECTORIES,
        tracker=tracker,
        test_command_generator=get_cpp_test_command
    )
    process_files_by_type(
        base_dir=base_dir,
        emissions_data_csv=emissions_data_csv,
        result_dir=result_dir,
        file_extension='.cs',
        excluded_files=EXCLUDED_FILES,
        excluded_dirs=EXCLUDED_DIRECTORIES,
        tracker=tracker,
        test_command_generator=get_cs_test_command
    )

    logging.info(f"Emissions data and test results written to {emissions_data_csv}")

# Call process_folder for 'before' and 'after' emissions data
process_folder(
    base_dir=SOURCE_DIRECTORY,
    emissions_data_csv=os.path.join(RESULT_DIR, 'main_before_emissions_data.csv'),
    result_dir=RESULT_DIR,
    suffix='before-in-detail',
    excluded_dirs=EXCLUDED_DIRECTORIES
)
process_folder(
    base_dir=GREEN_REFINED_DIRECTORY,
    emissions_data_csv=os.path.join(RESULT_DIR, 'main_after_emissions_data.csv'),
    result_dir=RESULT_DIR,
    suffix='after-in-detail',
    excluded_dirs=EXCLUDED_DIRECTORIES
)
logging.info("Emissions data processed successfully.")


# Compare emissions logic
def compare_emissions():
    # Load environment variables again (if needed)
    load_dotenv(dotenv_path=env_path, verbose=True, override=True)

    # Define paths to the before and after CSV files
    result_source_dir = os.path.join(SOURCE_DIRECTORY, 'Result', 'main_before_emissions_data.csv')
    result_green_refined_dir = os.path.join(SOURCE_DIRECTORY, 'Result', 'main_after_emissions_data.csv')

    # Check if both CSV files exist
    if not os.path.isfile(result_source_dir):
        logging.info(f"Source emissions data file not found: {result_source_dir}")
        return
    if not os.path.isfile(result_green_refined_dir):
        logging.info(f"Refined emissions data file not found: {result_green_refined_dir}")
        return

    # Read CSV files
    emissions_df = pd.read_csv(result_source_dir)
    emissions_after_df = pd.read_csv(result_green_refined_dir)

    # Merge dataframes on common columns
    try:
        merged_df = emissions_df.merge(
            emissions_after_df,
            on=["Application name", "File Type"],
            suffixes=('_before', '_after')
        )
    except KeyError as e:
        logging.info(f"Merge failed due to missing columns: {e}")
        return

    # Calculate the difference in emissions and determine the result
    merged_df['final emission'] = merged_df['Emissions (gCO2eq)_before'] - merged_df['Emissions (gCO2eq)_after']
    merged_df['Result'] = merged_df['final emission'].apply(lambda x: 'Improved' if x > 0 else 'Need improvement')

    # Select and rename columns
    result_df = merged_df[[
        "Application name",
        "File Type",
        "Timestamp_before",
        "Timestamp_after",
        "Emissions (gCO2eq)_before",
        "Emissions (gCO2eq)_after",
        "final emission",
        "Result"
    ]]
    result_df.columns = [
        "Application name",
        "File Type",
        "Timestamp (Before)",
        "Timestamp (After)",
        "Before",
        "After",
        "Final Emission",
        "Result"
    ]

    # Create 'Result' folder if it doesn't exist
    if not os.path.exists(RESULT_DIR):
        os.makedirs(RESULT_DIR)
        logging.info(f"Directory '{RESULT_DIR}' created successfully!")
    else:
        logging.info(f"Directory '{RESULT_DIR}' already exists.")

    # Write to new CSV file
    result_file_path = os.path.join(RESULT_DIR, "comparison_results.csv")
    result_df.to_csv(result_file_path, index=False)

    logging.info(f"Comparison results saved to {result_file_path}")

# Call the compare_emissions function
compare_emissions()

def generate_html_report(result_dir):
    """Generate HTML reports for emissions data."""
    # Initialize Jinja2 environment
    env = Environment(loader=FileSystemLoader(SOURCE_DIRECTORY))
    
    # Load templates
    templates = load_templates(env)
    if not templates:
        return
    
    # Read CSV files
    csv_data = read_csv_files(result_dir)
    if not csv_data:
        return
    
    before_df, after_df, comparison_df, server_df = csv_data
    
    # Generate report content
    report_content = generate_report_content(
        before_df, after_df, comparison_df, server_df,
        templates, result_dir
    )
    
    # Save reports
    save_reports(report_content)

def load_templates(env):
    """Load all required Jinja2 templates."""
    template_files = {
        'main': 'report_template.html',
        'details': 'details_template.html',
        'last_run': 'last_run_report_template.html',
        'last_run_details': 'last_run_details_template.html'
    }
    
    templates = {}
    for key, filename in template_files.items():
        try:
            templates[key] = env.get_template(filename)
            logging.info(f"Loaded template: {filename}")
        except Exception as e:
            logging.error(f"Failed to load template {filename}: {e}")
            return None
    
    return templates

def read_csv_files(result_dir):
    """Read all required CSV files."""
    csv_files = {
        'before': 'main_before_emissions_data.csv',
        'after': 'main_after_emissions_data.csv',
        'comparison': 'comparison_results.csv',
        'server': 'server_data.csv'
    }
    
    dataframes = {}
    for key, filename in csv_files.items():
        file_path = os.path.join(result_dir, filename)
        try:
            dataframes[key] = pd.read_csv(file_path)
        except Exception as e:
            logging.error(f"Failed to read {filename}: {e}")
            return None
    
    return (
        dataframes['before'],
        dataframes['after'],
        dataframes['comparison'],
        dataframes['server']
    )

def generate_report_content(before_df, after_df, comparison_df, server_df, templates, result_dir):
    """Generate all report content using the tracker functions."""
    # Get current timestamp
    last_run_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Prepare data
    solution_dirs, detailed_data = prepare_detailed_data(before_df, after_df, comparison_df)
    
    # Create graphs
    energy_graphs = create_energy_graphs(before_df, after_df)
    emissions_graphs = create_emissions_graphs(before_df, after_df)
    embedded_graphs = create_embedded_code_graphs(before_df, after_df)
    
    # Create tables
    energy_table, emissions_table = create_top_five_tables(before_df)
    
    # Calculate totals
    total_before = before_df['Energy Consumed (Wh)'].astype(float).sum()
    total_after = after_df['Energy Consumed (Wh)'].astype(float).sum()
    total_emissions_before = before_df['Emissions (gCO2eq)'].astype(float).sum()
    total_emissions_after = after_df['Emissions (gCO2eq)'].astype(float).sum()
    
    return {
        'timestamp': last_run_timestamp,
        'solution_dirs': solution_dirs,
        'detailed_data': detailed_data,
        'energy_graphs': energy_graphs,
        'emissions_graphs': emissions_graphs,
        'embedded_graphs': embedded_graphs,
        'energy_table': energy_table,
        'emissions_table': emissions_table,
        'totals': {
            'before': total_before,
            'after': total_after,
            'emissions_before': total_emissions_before,
            'emissions_after': total_emissions_after
        }
    }

def save_reports(content):
    """Save all generated reports to their respective locations."""
    # Create report directories
    current_date = datetime.now().strftime('%Y-%m-%d')
    current_time = datetime.now().strftime('%H-%M')
    date_folder_path = os.path.join(REPORT_DIR, current_date)
    time_folder_path = os.path.join(date_folder_path, current_time)
    
    os.makedirs(time_folder_path, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)
    
    # Save reports
    report_paths = {
        'main': os.path.join(REPORT_DIR, 'emissions_report.html'),
        'details': os.path.join(REPORT_DIR, 'details_report.html'),
        'timestamp_main': os.path.join(time_folder_path, 'emissions_report.html'),
        'timestamp_details': os.path.join(time_folder_path, 'details_report.html')
    }
    
    for path_key, file_path in report_paths.items():
        try:
            with open(file_path, 'w') as f:
                f.write(content[path_key])
            logging.info(f"Report saved: {file_path}")
        except Exception as e:
            logging.error(f"Failed to save report {path_key}: {e}")

if __name__ == "__main__":
    generate_html_report(RESULT_DIR)
