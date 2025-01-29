# Standard library imports
import os
import subprocess
import csv
import time
import logging
import shutil
from datetime import datetime

# Third-party library imports
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from codecarbon import EmissionsTracker
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
from plotly.subplots import make_subplots


# Load environment variables
env_path = os.path.abspath(".env")
load_dotenv(dotenv_path=env_path, verbose=True, override=True)
SOURCE_DIRECTORY = os.path.dirname(env_path)

GREEN_REFINED_DIRECTORY = os.path.join(SOURCE_DIRECTORY, "GreenCode")
RESULT_DIR = os.path.join(SOURCE_DIRECTORY, "Result")
REPORT_DIR = os.path.join(SOURCE_DIRECTORY, "Report")

# List of files and directories to exclude from processing
EXCLUDED_FILES = [
    file.strip() for file in os.getenv("EXCLUDED_FILES", "").split(",") if file.strip()
]
EXCLUDED_DIRECTORIES = [
    file.strip()
    for file in os.getenv("EXCLUDED_DIRECTORIES", "").split(",")
    if file.strip()
]

def is_test_file(file_path):
    """
    Check if a file is a test file based on its name and content.
    """
    file_name = os.path.basename(file_path).lower()
    return ('test' in file_name or 
            file_name.startswith('test_') or 
            file_name.endswith('_test.py') or
            file_name.endswith('test.java') or
            file_name.endswith('test.cpp') or
            file_name.endswith('test.cs'))

def count_lines_of_code(file_path, language="python"):
    """
    Count the number of lines of code in a file, excluding blank lines and comments,
    for multiple programming languages.
    
    Args:
        file_path (str): Path to the file to count lines.
        language (str): Programming language of the file (default: 'python').
    
    Returns:
        int: Number of lines of code.
    """
    # Define comment styles for supported languages
    comment_styles = {
        "python": {"single": "#", "multi_start": ('"""', "'''"), "multi_end": ('"""', "'''")},
        "javascript": {"single": "//", "multi_start": ("/*",), "multi_end": ("*/",)},
        "java": {"single": "//", "multi_start": ("/*",), "multi_end": ("*/",)},
        "c": {"single": "//", "multi_start": ("/*",), "multi_end": ("*/",)},
        "cpp": {"single": "//", "multi_start": ("/*",), "multi_end": ("*/",)},
    }
    
    if language not in comment_styles:
        raise ValueError(f"Unsupported language: {language}")
    
    styles = comment_styles[language]
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            
        # Initialize counter
        loc = 0
        in_multiline_comment = False
        
        for line in lines:
            # Remove leading/trailing whitespace
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Handle multiline comments
            if in_multiline_comment:
                if any(line.endswith(end) for end in styles["multi_end"]):
                    in_multiline_comment = False
                continue
            
            if any(line.startswith(start) for start in styles["multi_start"]):
                if not any(line.endswith(end) for end in styles["multi_end"]):
                    in_multiline_comment = True
                continue
                
            # Skip single-line comments
            if line.startswith(styles["single"]):
                continue
            
            loc += 1
        
        return loc
    except Exception as e:
        logging.error(f"Error counting lines of code in {file_path}: {e}")
        return 0

def process_emissions_for_file(tracker, script_path, emissions_csv, file_type, result_dir, test_command):
    # First check if it's a test file
    if not is_test_file(script_path):
        return
    
    # If no test command, return immediately
    if not test_command:
        return
   
    emissions_data = None
    duration = 0
    test_output = 'Unknown'
    script_name = os.path.basename(script_path)

    # Count lines of code
    loc = count_lines_of_code(script_path)

    # Extract 'solution dir' (immediate parent directory)
    solution_dir = os.path.basename(os.path.dirname(script_path))
    is_green_refined = os.path.commonpath([script_path, GREEN_REFINED_DIRECTORY]) == GREEN_REFINED_DIRECTORY

    tracker_started = False
    try:
        # Start the emissions tracking ONLY for test files
        tracker = EmissionsTracker(allow_multiple_runs=True)
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
                    is_green_refined,
                    loc  # Add the LOC count to the data
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
            if (script.endswith(file_extension) and 
                script not in excluded_files and 
                is_test_file(os.path.join(root, script))):  # Only add test files
                script_path = os.path.join(root, script)
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
    return [os.getenv('PYTEST_PATH', 'pytest'), script_path] if 'test' in script_path.lower() else None

# --------------- Improved version of get_java_test_command ----------------
def get_java_test_command(script_path):
    maven_path = os.getenv('MAVEN_PATH', 'mvn')
    test_name = os.path.splitext(os.path.basename(script_path))[0] + 'Test'
    return [maven_path, '-Dtest=' + test_name, 'test'] if 'test' in script_path.lower() else None
# ------------------------------------------------------------------------  

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
        cmake_path = os.getenv('GTEST_CMAKE_PATH', 'cmake')
        cmake_config_command = [
            cmake_path,
            f'-S{test_dir}',
            f'-B{build_dir}',
            '-DCMAKE_PREFIX_PATH=/usr/local',
            '-G', 'Unix Makefiles'
        ]
        
        # CMake build command
        cmake_build_command = [cmake_path, '--build', build_dir]
        
        # Test run command
        test_executable = os.path.join(build_dir, os.path.splitext(test_file_name)[0])        
        if not os.path.exists(test_executable):
            logging.warning(f"Test executable {test_executable} not found")
            return None
        
        return cmake_config_command + cmake_build_command + [test_executable]    
    return None

# ------------------ improved version of get_cs_test_command --------------
def get_cs_test_command(script_path):
    test_project = os.path.splitext(os.path.basename(script_path))[0]
    test_command = ['dotnet', 'test', test_project] if 'test' in script_path.lower() else None
    return test_command
# --------------------------------------------------------------------------


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
                "CPU Energy (Wh)", "GPU Energy (KWh)", "RAM Energy (Wh)", "Energy Consumed (Wh)", "Test Results", "solution dir", "Is Green Refined", "Lines of Code"
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

def generate_file_overview():
    """
    Generate an overview of files in GREEN_REFINED_DIRECTORY including file counts by type
    and extract 'overview' comments from each file.
    """
    # Ensure the result directory exists
    if not os.path.exists(RESULT_DIR):
        os.makedirs(RESULT_DIR)

    # Initialize dictionary to store file type counts
    file_type_counts = {}
    overview_data = []

    # Walk through all files in GREEN_REFINED_DIRECTORY
    for root, _, files in os.walk(GREEN_REFINED_DIRECTORY):
        for file in files:
            file_path = os.path.join(root, file)
            
            # Get file extension
            _, extension = os.path.splitext(file)
            if extension:  # Only count files with extensions
                extension = extension.lower()
                file_type_counts[extension] = file_type_counts.get(extension, 0) + 1

            # Read file content and look for overview comment
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    overview_comment = None
                    
                    # Look for the overview comment in the last few lines
                    for line in reversed(lines):
                        line = line.strip()
                        # Check for different comment styles
                        if 'overview:' in line.lower():
                            # Remove common comment markers
                            overview_comment = line.replace('//', '').replace('#', '').replace('/*', '').replace('*/', '').strip()
                            # Extract the part after 'overview:'
                            overview_comment = overview_comment[overview_comment.lower().index('overview:') + 9:].strip()
                            break
                    
                    if overview_comment:
                        relative_path = os.path.relpath(file_path, GREEN_REFINED_DIRECTORY)
                        overview_data.append({
                            'file_path': relative_path,
                            'file_type': extension,
                            'overview_comment': overview_comment
                        })
            except Exception as e:
                logging.error(f"Error processing file {file_path}: {e}")

    # Write results to CSV
    csv_path = os.path.join(RESULT_DIR, 'final_overview.csv')
    
    # Write the data to CSV
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        writer.writerow(['Section', 'Information'])
        
        # Write file type counts
        writer.writerow(['File Type Statistics', ''])
        for ext, count in file_type_counts.items():
            writer.writerow(['', f'{ext}: {count} files'])
        
        # Add a blank row for separation
        writer.writerow(['', ''])
        
        # Write file overviews
        writer.writerow(['File Overview Comments', ''])
        writer.writerow(['File Path', 'File Type', 'Overview Comment'])
        for data in overview_data:
            writer.writerow([
                data['file_path'],
                data['file_type'],
                data['overview_comment']
            ])

    logging.info(f"File overview report generated at {csv_path}")

# Call the function at the end of the script
generate_file_overview()

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

def prepare_detailed_data(result_dir):
    comparison_csv = os.path.join(result_dir, "comparison_results.csv")
    before_csv = os.path.join(result_dir, 'main_before_emissions_data.csv')
    after_csv = os.path.join(result_dir, 'main_after_emissions_data.csv')
    
    # Read CSV files
    comparison_df = pd.read_csv(comparison_csv)
    before_df = pd.read_csv(before_csv)
    after_df = pd.read_csv(after_csv)
    
    # Merge before and after data
    merged_before = before_df[['Application name', 'File Type', 'Duration', 'Emissions (gCO2eq)', 'Energy Consumed (Wh)', 'solution dir']]
    merged_after = after_df[['Application name', 'File Type', 'Duration', 'Emissions (gCO2eq)', 'Energy Consumed (Wh)', 'solution dir']]
    
    # Group by 'solution dir'
    solution_dirs = sorted(comparison_df['Application name'].unique())  # Adjust as needed
    
    # Get unique solution directories
    solution_dirs = sorted(set(before_df['solution dir']).union(after_df['solution dir']))
    
    # Prepare data for each solution dir
    detailed_data = {}
    for dir in solution_dirs:
        before_details = merged_before[merged_before['solution dir'] == dir].to_dict(orient='records')
        after_details = merged_after[merged_after['solution dir'] == dir].to_dict(orient='records')
        detailed_data[dir] = {
            'before': before_details,
            'after': after_details
        }
    
    return solution_dirs, detailed_data

def generate_html_report(result_dir):
    # Initialize Jinja2 environment
    env = Environment(loader=FileSystemLoader(SOURCE_DIRECTORY))
    template_path = 'report_template.html'
    last_run_template_path = 'last_run_report_template.html'
    details_template_path = 'details_template.html'
    last_run_details_template_path = 'last_run_details_template.html'
    details_server_template_path = 'details_server_template.html'
    recommendations_template_path = 'recommendations_template.html'

    # Prepare detailed data
    solution_dirs, detailed_data = prepare_detailed_data(result_dir)
    
    # Check if the templates exist
    if not os.path.isfile(os.path.join(SOURCE_DIRECTORY, details_template_path)):
        logging.error(f"Detailed HTML template file not found: {details_template_path}")
        logging.error(f"Looking in: {os.path.join(SOURCE_DIRECTORY, details_template_path)}")
        return 
    if not os.path.isfile(os.path.join(SOURCE_DIRECTORY, template_path)):
        logging.error(f"HTML template file not found: {template_path}")
        logging.error(f"Looking in: {os.path.join(SOURCE_DIRECTORY, template_path)}")
        return
    
    # Check if the last run templates exist
    if not os.path.isfile(os.path.join(SOURCE_DIRECTORY, last_run_details_template_path)):
        logging.error(f"Last Run Detailed HTML template file not found: {last_run_details_template_path}")
        logging.error(f"Looking in: {os.path.join(SOURCE_DIRECTORY, last_run_details_template_path)}")
        return 
    if not os.path.isfile(os.path.join(SOURCE_DIRECTORY, last_run_template_path)):
        logging.error(f"Last Run HTML template file not found: {last_run_template_path}")
        logging.error(f"Looking in: {os.path.join(SOURCE_DIRECTORY, last_run_template_path)}")
        return

    if not os.path.isfile(os.path.join(SOURCE_DIRECTORY, details_server_template_path)):
        logging.error(f"Detailed server template file not found: {details_server_template_path}")
        logging.error(f"Looking in: {os.path.join(SOURCE_DIRECTORY, details_server_template_path)}")
        return
    if not os.path.isfile(os.path.join(SOURCE_DIRECTORY, recommendations_template_path)):
        logging.error(f"Recommendations template file not found: {recommendations_template_path}")
        logging.error(f"Looking in: {os.path.join(SOURCE_DIRECTORY, recommendations_template_path)}")
        return

    
    # Load the templates
    try:
        template = env.get_template(template_path)
        logging.info(f"Loaded template: {template_path}")
    except Exception as e:
        logging.error(f"Failed to load template {template_path}: {e}")
        return
    
    try:
        details_template = env.get_template(details_template_path)
        logging.info(f"Loaded template: {details_template_path}")
    except Exception as e:
        logging.error(f"Failed to load template {details_template_path}: {e}")
        return
    
    # Load the last run templates
    try:
        lastrun_template = env.get_template(last_run_template_path)
        logging.info(f"Loaded template: {last_run_template_path}")
    except Exception as e:
        logging.error(f"Failed to load template {last_run_template_path}: {e}")
        return
    
    try:
        lastrun_details_template = env.get_template(last_run_details_template_path)
        logging.info(f"Loaded template: {last_run_details_template_path}")
    except Exception as e:
        logging.error(f"Failed to load template {last_run_details_template_path}: {e}")
        return

    try:
        details_server_template = env.get_template(details_server_template_path)
        logging.info(f"Loaded template: {details_server_template_path}")
    except Exception as e:
        logging.error(f"Failed to load template {details_server_template_path}: {e}")
        return
    
    try:
        recommendations_template = env.get_template(recommendations_template_path)
        logging.info(f"Loaded template: {recommendations_template_path}")
    except Exception as e:
        logging.error(f"Failed to load template {recommendations_template_path}: {e}")
        return
    
    before_csv = os.path.join(result_dir, 'main_before_emissions_data.csv')
    after_csv = os.path.join(result_dir, 'main_after_emissions_data.csv')
    comparison_csv = os.path.join(result_dir, 'comparison_results.csv')
    server_csv = os.path.join(result_dir, 'server_data.csv')
    mul_server_csv = os.path.join(result_dir, 'multiple_server_data.csv')
    recommendations_csv = os.path.join(result_dir, 'modification_overview.csv')

    # Check if CSV files exist
    if not os.path.exists(before_csv):
        logging.error(f"Before emissions data file not found: {before_csv}")
        return
    if not os.path.exists(after_csv):
        logging.error(f"After emissions data file not found: {after_csv}")
        return
    if not os.path.exists(comparison_csv):
        logging.error(f"Comparison results file not found: {comparison_csv}")
        return
    if not os.path.exists(server_csv):
        logging.error(f"Server data file not found: {server_csv}")
        return
    if not os.path.exists(mul_server_csv):
        logging.error(f"Multiple server data file not found: {mul_server_csv}")
        return
    if not os.path.exists(recommendations_csv):
        logging.error(f"Recommendations data file not found: {recommendations_csv}")
        return

    # Read CSVs
    before_df = pd.read_csv(before_csv)
    after_df = pd.read_csv(after_csv)
    comparison_df = pd.read_csv(comparison_csv)
    server_df = pd.read_csv(server_csv)
    mul_server_df = pd.read_csv(mul_server_csv)
    recommendations_df = pd.read_csv(recommendations_csv)

    # -----------------Componentes for server details report -----------------

    # Calculate unique hosts and average CO2 emissions
    unique_hosts = server_df['Host-name'].nunique()  # Count of unique host names
    average_co2_emission = server_df['CO2 emission (Metric Tons)'].sum() / unique_hosts  # Average CO2 emissions
    average_energy_consumption = server_df['Energy consumption (KWH)'].sum() / unique_hosts  # Average Energy consumption

    # Calculate averages for additional metrics
    average_cpu_usage = server_df['CPU usage (%)'].mean()
    average_ram_usage = server_df['RAM usage (%)'].mean()
    average_disk_usage = server_df['Disk usage (%)'].mean()
    average_network_usage = server_df['Network usage (bytes)'].mean()
    average_disk_write = mul_server_df['disk_write_bytes'].mean()
    average_disk_read = mul_server_df['disk_read_bytes'].mean()

    cpu_data = server_df['CPU usage (%)'].tail(10).tolist()
    ram_data = server_df['RAM usage (%)'].tail(10).tolist()
    disk_data = server_df['Disk usage (%)'].tail(10).tolist()
    network_data = server_df['Network usage (bytes)'].tail(10).tolist()
    disk_write = mul_server_df['disk_write_bytes'].tail(10).tolist()
    disk_read = mul_server_df['disk_read_bytes'].tail(10).tolist()

    # Calculate max network value for scaling
    max_network = max(network_data)

    # ---------------- Prepare the data for critical server lists -------------

    # Filter servers with CO2 emissions > 50 metric tons
    # critical_servers = server_df[server_df['CO2 emission (Metric Tons)'] > 50][['Host-name', 'CO2 emission (Metric Tons)']]

    critical_servers = mul_server_df[mul_server_df['total_co2'] > 0.000001][['hostname', 'total_co2']]

    # Sort by emission value in descending order
    critical_servers = critical_servers.sort_values(by='total_co2', ascending=False)

    # Remove duplicate hostnames, keeping the first occurrence
    critical_servers = critical_servers.drop_duplicates(subset='hostname')

    # Store the count of critical servers after removing duplicates
    critical_server_count = len(critical_servers)

    # Convert the DataFrame to a list of dictionaries for Jinja2
    critical_servers_list = critical_servers.to_dict(orient='records') if not critical_servers.empty else None

    # ------------------- Prepare data for the last run report -------------------

    # Convert the 'timestamp' column to datetime for accurate sorting
    # Handle the correct format and microseconds in the timestamp
    mul_server_df['timestamp'] = pd.to_datetime(
        mul_server_df['timestamp'], 
        format='%Y-%m-%d %H:%M:%S.%f',  # Matches "2025-01-08 10:22:29.187180"
        errors='coerce'  # Gracefully handle invalid or mismatched formats
    )

    # Drop rows with invalid or missing timestamps after conversion
    mul_server_df = mul_server_df.dropna(subset=['timestamp'])

    # Find the maximum timestamp in the DataFrame
    latest_timestamp = mul_server_df['timestamp'].max()

    # Filter the DataFrame to include only records from the last run
    last_run_records = mul_server_df[mul_server_df['timestamp'] == latest_timestamp]

    # Calculate the total CO2 and total power for the last run
    total_last_run_co2 = last_run_records['total_co2'].sum()
    total_last_run_power = last_run_records['total_power'].sum()

    # Optional: Format the timestamp as a string for easier display
    formatted_timestamp = latest_timestamp.strftime('%d-%m-%Y %H:%M:%S')

    # ------------------- Prepare data for the server details report -------------------

    # Count of servers by 'os_type'
    os_type_counts = mul_server_df['os_type'].value_counts()

    # Count of servers by 'os_type' and 'os_version'
    os_version_counts = mul_server_df.groupby(['os_type', 'os_version']).size().reset_index(name='count')

    # Define color palette
    color_palette = px.colors.qualitative.Light24

    # Plot 1: Bar graph for 'os_type'
    fig1 = go.Figure(data=[
        go.Bar(
            x=os_type_counts.index,
            y=os_type_counts.values,
            text=os_type_counts.values,
            textposition='inside',  # Place text inside the bar
            textfont=dict(size=16),  # Slightly larger font size
            marker=dict(color=color_palette[:len(os_type_counts)])  # Use color palette
        )
    ])
    fig1.update_layout(
        title="Count of Servers by OS Type",
        xaxis_title="OS Type",
        yaxis_title="Count of Servers",
        template="plotly_white",
        width=600,  # Set combined width
        height=300  # Set combined height
    )

    # Plot 2: Bar graph for 'os_version' grouped by 'os_type'
    fig2 = go.Figure()
    for i, os_type in enumerate(os_version_counts['os_type'].unique()):
        os_data = os_version_counts[os_version_counts['os_type'] == os_type]
        fig2.add_trace(
            go.Bar(
                x=os_data['os_version'],
                y=os_data['count'],
                name=os_type,
                text=os_data['count'],
                textposition='inside',  # Place text inside the bar
                textfont=dict(size=16),  # Slightly larger font size
                marker=dict(color=color_palette[i])  # Use color palette for each OS type
            )
        )
    # Update layout
    fig2.update_layout(
        title="Count of Servers by OS Version (Grouped by OS Type)",
        xaxis_title="OS Version",
        yaxis_title="Count of Servers",
        barmode='stack',  # Stacked bar chart to represent subtypes clearly
        template="plotly_white",
        width=650,  # Set combined width
        height=400,  # Set combined height
        xaxis_tickangle=-45,  # Rotate x-axis labels for better fit
        xaxis=dict(tickvals=os_version_counts['os_version'],
                ticktext=[os.replace(' ', '<br>') for os in os_version_counts['os_version']])
    )
    server_os_type_fig = pio.to_html(fig1, include_plotlyjs=False, full_html=False)
    server_os_version_fig = pio.to_html(fig2, include_plotlyjs=False, full_html=False)
    
    # Create figure with secondary y-axis
    # fig = make_subplots(
    #     rows=2, cols=1,
    #     subplot_titles=('Energy Consumption Over Time', 'CO2 Emissions Over Time'),
    #     vertical_spacing=0.30
    # )

    # # Add area plot for energy consumption
    # fig.add_trace(
    #     go.Scatter(
    #         x=server_df['Date'],
    #         y=server_df['Energy consumption (KWH)'],
    #         fill='tozeroy',
    #         name='Energy Consumption (KWH)',
    #         line=dict(color='#4A90E2'),  # Blue color
    #         fillcolor='rgba(74, 144, 226, 0.3)',  # Transparent blue
    #     ),
    #     row=1, col=1
    # )

    # # Add area plot for CO2 emissions
    # fig.add_trace(
    #     go.Scatter(
    #         x=server_df['Date'],
    #         y=server_df['CO2 emission (Metric Tons)'],
    #         fill='tozeroy',
    #         name='CO2 Emissions (Metric Tons)',
    #         line=dict(color='#50C878'),  # Green color
    #         fillcolor='rgba(80, 200, 120, 0.3)',  # Transparent green
    #     ),
    #     row=2, col=1
    # )

    # # Update layout with modern styling
    # fig.update_layout(
    #     title=dict(
    #         text='Server Analysis: Energy Consumption and CO2 Emissions',
    #         y=1,
    #         x=0.5,
    #         xanchor='center',
    #         yanchor='top',
    #         font=dict(size=18)
    #     ),
    #     showlegend=True,
    #     legend=dict(
    #         orientation="h",
    #         yanchor="top",
    #         y=-0.2,
    #         xanchor="center",
    #         x=0.5
    #     ),
    #     width=600,
    #     height=500,
    #     paper_bgcolor='white',
    #     plot_bgcolor='rgba(240,240,240,0.3)',  # Light gray background
    # )

    # # Update axes
    # fig.update_xaxes(
    #     title_text="Date",
    #     showgrid=True,
    #     gridwidth=1,
    #     gridcolor='rgba(128,128,128,0.2)',
    #     row=1, col=1
    # )

    # fig.update_xaxes(
    #     title_text="Date",
    #     showgrid=True,
    #     gridwidth=1,
    #     gridcolor='rgba(128,128,128,0.2)',
    #     row=2, col=1
    # )

    # fig.update_yaxes(
    #     title_text="Kilowatt-hour",
    #     showgrid=True,
    #     gridwidth=1,
    #     gridcolor='rgba(128,128,128,0.2)',
    #     row=1, col=1
    # )

    # fig.update_yaxes(
    #     title_text="Metric Tons",
    #     showgrid=True,
    #     gridwidth=1,
    #     gridcolor='rgba(128,128,128,0.2)',
    #     row=2, col=1
    # )

    # # Convert to HTML
    # div_faceted_area_charts = pio.to_html(fig, include_plotlyjs=False, full_html=False)


    # ------------------- Prepare data for the detailed server report -------------------

    # Multi-server data:
    # unique_servers = mul_server_df['hostname'].unique()  # Get unique host names
    # Get unique hostnames
    unique_servers = mul_server_df['hostname'].unique().tolist()

    # # Convert DataFrame to list of dictionaries with explicit type conversion and sanitization
    # server_details = []
    # for _, row in mul_server_df.iterrows():
    #     server_dict = {
    #         'hostname': str(row['hostname']),
    #         'os_version': str(row.get('os_version', 'N/A')).replace('\n', ' ').replace('\r', ''),
    #         'os_type': str(row.get('os_type', 'N/A')).replace('\n', ' ').replace('\r', ''),
    #         'region': str(row.get('region', 'N/A')).replace('\n', ' ').replace('\r', ''),
    #         'total_co2': float(row.get('total_co2', 0)),
    #         'cpu_co2': float(row.get('cpu_co2', 0)),
    #         'ram_co2': float(row.get('ram_co2', 0)),
    #         'ram_total': float(row.get('ram_total', 0)),
    #         'ram_used': float(row.get('ram_used', 0)),
    #         'ram_percent': float(row.get('ram_percent', 0)),
    #         'total_power': float(row.get('total_power', 0)),
    #         'cpu_power': float(row.get('cpu_power', 0)),
    #         'ram_power': float(row.get('ram_power', 0)),
    #         'disk_read_bytes': float(row.get('disk_read_bytes', 0)),
    #         'disk_write_bytes': float(row.get('disk_write_bytes', 0)),
    #         'disk_base_co2': float(row.get('disk_base_co2', 0)),
    #         'disk_io_co2': float(row.get('disk_io_co2', 0)),
    #         'storage_device_count': int(row.get('storage_device_count', 0)),
    #         'storage_devices': str(row.get('storage_devices', '')).replace('\n', ' ').replace('\r', ''),
    #         'co2_factor': float(row.get('co2_factor', 0))
    #     }
    #     server_details.append(server_dict)

    # # Safely convert to JSON string
    # server_details_json = json.dumps(server_details, ensure_ascii=True)

    # --------------------- Try 1 ---------------------

    # Prepare lists for before and after details to pass to the template
    # server_details = mul_server_df[['os_version','storage_device_count','storage_devices','cpu_percent','ram_total','ram_used','ram_percent','disk_read_bytes','disk_write_bytes','timestamp','hostname','os_type','total_power','cpu_power','ram_power','disk_base_power','disk_io_power','total_co2','cpu_co2','ram_co2','disk_base_co2','disk_io_co2','co2_factor','region']].to_dict(orient='records')
    
    # --------------------- Try 2 ---------------------
    # Convert DataFrame to list of dictionaries
    # Create a copy of the DataFrame to avoid modifying the original
    df = mul_server_df.copy()
    
    # Define columns by type
    numeric_columns = [
        'cpu_percent', 'ram_total', 'ram_used', 'ram_percent', 
        'disk_read_bytes', 'disk_write_bytes', 'total_power', 
        'cpu_power', 'ram_power', 'disk_base_power', 'disk_io_power',
        'total_co2', 'cpu_co2', 'ram_co2', 'disk_base_co2', 
        'disk_io_co2', 'co2_factor', 'storage_device_count'
    ]
    
    string_columns = [
        'hostname', 'os_version', 'os_type', 'region', 
        'storage_devices', 'timestamp'
    ]
    
    # Convert numeric columns to float
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Ensure string columns are properly formatted
    for col in string_columns:
        if col in df.columns:
            df[col] = df[col].astype(str)
    
    # Handle any missing columns
    required_columns = numeric_columns + string_columns
    for col in required_columns:
        if col not in df.columns:
            if col in numeric_columns:
                df[col] = 0
            else:
                df[col] = 'N/A'
    
    # Convert DataFrame to list of dictionaries
    server_details = df.to_dict(orient='records')

    # --------------------- Prepare data for Recommendations ---------------------

    # Ensure Modification Timestamp is in datetime format
    recommendations_df['Modification Timestamp'] = pd.to_datetime(recommendations_df['Modification Timestamp'], errors='coerce')

    # Drop rows where the timestamp could not be parsed
    recommendations_df = recommendations_df.dropna(subset=['Modification Timestamp'])

    # Extract unique dates
    unique_dates = recommendations_df['Modification Timestamp'].dt.date.unique().tolist()

    # Prepare recommendations details grouped by date
    recommendations_details = {}
    for date in unique_dates:
        date_records = recommendations_df[recommendations_df['Modification Timestamp'].dt.date == date]
        # Convert the DataFrame to a dictionary and ensure timestamps are strings
        recommendations_details[str(date)] = date_records.assign(
            **{"Modification Timestamp": date_records['Modification Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')}
        ).to_dict(orient='records')

    # Before rendering, add these debug print statements
    print("Total Rows:", len(recommendations_df))
    print("Unique Dates Found:", unique_dates)
    print("Recommendations Details Keys:", recommendations_details.keys())
    for date, recs in recommendations_details.items():
        print(f"Date {date} has {len(recs)} records")
    
    # Check if DataFrames are not empty before getting the latest record
    if not before_df.empty:
        latest_before_df = before_df.loc[[before_df['Timestamp'].idxmax()]]
    else:
        latest_before_df = pd.DataFrame()  # Create an empty DataFrame

    if not after_df.empty:
        latest_after_df = after_df.loc[[after_df['Timestamp'].idxmax()]]
    else:
        latest_after_df = pd.DataFrame()  # Create an empty DataFrame


    # Prepare lists for before and after details to pass to the template
    latest_before_details = [latest_before_df[['Application name', 'File Type', 'Duration', 'Emissions (gCO2eq)', 'Energy Consumed (Wh)', 'solution dir']].to_dict()]
    latest_after_details = [latest_after_df[['Application name', 'File Type', 'Duration', 'Emissions (gCO2eq)', 'Energy Consumed (Wh)', 'solution dir']].to_dict()]

    # Function to filter for test applications
    def is_test_application(app_name):
        return 'test' in str(app_name).lower()

    # Sum 'Energy Consumed (Wh)' for before and after, including ONLY test applications
    total_before = before_df[before_df['Application name'].apply(is_test_application)]['Energy Consumed (Wh)'].astype(float).sum()
    total_after = after_df[after_df['Application name'].apply(is_test_application)]['Energy Consumed (Wh)'].astype(float).sum()

    # Sum 'Energy Consumed (Wh)' for latest records, including ONLY test applications
    latest_total_before = latest_before_df[latest_before_df['Application name'].apply(is_test_application)]['Energy Consumed (Wh)'].astype(float).sum()
    latest_total_after = latest_after_df[latest_after_df['Application name'].apply(is_test_application)]['Energy Consumed (Wh)'].astype(float).sum()

    # Prepare lists for before and after details to pass to the template
    before_details = before_df[['Application name', 'File Type', 'Duration', 'Emissions (gCO2eq)', 'Energy Consumed (Wh)', 'solution dir']].to_dict(orient='records')
    after_details = after_df[['Application name', 'File Type', 'Duration', 'Emissions (gCO2eq)', 'Energy Consumed (Wh)', 'solution dir']].to_dict(orient='records')
    
    # Capture the current timestamp for the report
    last_run_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Read comparison_results.csv to get total 'Before' and 'After', only for test applications
    total_emissions_before = comparison_df[comparison_df['Application name'].apply(is_test_application)]['Before'].astype(float).sum()
    total_emissions_after = comparison_df[comparison_df['Application name'].apply(is_test_application)]['After'].astype(float).sum()

    # Read comparison_results.csv to get total 'Before' and 'After' for latest records, only for test applications
    latest_total_emissions_before = latest_before_df[latest_before_df['Application name'].apply(is_test_application)]['Emissions (gCO2eq)'].astype(float).sum()
    latest_total_emissions_after = latest_after_df[latest_after_df['Application name'].apply(is_test_application)]['Emissions (gCO2eq)'].astype(float).sum()

    # Read CSVs and group by 'solution dir'
    before_file_type = before_df.groupby('solution dir')['Energy Consumed (Wh)'].sum().reset_index()
    after_file_type = after_df.groupby('solution dir')['Energy Consumed (Wh)'].sum().reset_index()
    
    # Group by 'solution dir' and calculate sum of 'Energy Consumed (Wh)'
    latest_before_file_type = latest_before_df.groupby('solution dir')['Energy Consumed (Wh)'].sum().reset_index()
    latest_after_file_type = latest_after_df.groupby('solution dir')['Energy Consumed (Wh)'].sum().reset_index()

    # Sort the data by energy consumed (descending for top 5)
    before_file_type_sorted = before_file_type.sort_values('Energy Consumed (Wh)', ascending=False)
    after_file_type_sorted = after_file_type.sort_values('Energy Consumed (Wh)', ascending=False)

    # Sort the data by energy consumed (descending for top 5)
    latest_before_file_type_sorted = latest_before_file_type.sort_values('Energy Consumed (Wh)', ascending=False)
    latest_after_file_type_sorted = latest_after_file_type.sort_values('Energy Consumed (Wh)', ascending=False)

    # Determine unique solution dirs
    unique_solution_dirs = sorted(set(before_file_type_sorted['solution dir']).union(after_file_type_sorted['solution dir']))

    # Determine unique solution dirs
    latest_unique_solution_dirs = sorted(set(latest_before_file_type_sorted['solution dir']).union(latest_after_file_type_sorted['solution dir']))

    # Create a color palette with distinct colors
    colors = px.colors.qualitative.Light24

    # Create a dictionary to store colors for each solution dir
    color_mapping = {
        solution_dir: colors[i % len(colors)]
        for i, solution_dir in enumerate(before_file_type_sorted['solution dir'].unique())
    }

    # Create figure
    fig = go.Figure()

    # Add traces for "Before" data
    for i, (_, row) in enumerate(before_file_type_sorted.iterrows()):
        fig.add_trace(go.Bar(
            x=[row['solution dir']],
            y=[row['Energy Consumed (Wh)']],
            name='Before',  # Simplified name
            marker=dict(
                color=color_mapping.get(row['solution dir'], 'grey'),  # Safe lookup
                opacity=0.9
            ),

            offsetgroup=0,
            showlegend=True if i == 0 else False  # Show legend only for first "Before" bar
        ))

    # Add traces for "After" data
    for i, (_, row) in enumerate(after_file_type_sorted.iterrows()):
        fig.add_trace(go.Bar(
            x=[row['solution dir']],
            y=[row['Energy Consumed (Wh)']],
            name='After',  # Simplified name
            marker=dict(
                color=color_mapping.get(row['solution dir'], 'grey'),  # Safe lookup
                opacity=0.6,
                pattern=dict(shape="/", solidity=0.7)
            ),
            offsetgroup=1,
            showlegend=True if i == 0 else False  # Show legend only for first "After" bar
        ))

    # Update layout
    fig.update_layout(
        title={
            'text': 'Source Code Directory Level Energy Consumption (Wh) - Before vs After Optimization',
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        xaxis_title='Solution Dir',
        yaxis_title='Energy Consumed (Wh)',
        barmode='group',
        xaxis=dict(
            tickangle=45,
            tickformat=".6f"
        ),
        yaxis=dict(
            range=[0, max(
                before_file_type_sorted['Energy Consumed (Wh)'].max(),
                after_file_type_sorted['Energy Consumed (Wh)'].max()
            ) * 1.1],
            tickformat=".6f"
        ),
        margin=dict(l=50, r=50, t=100, b=120),
        showlegend=False,  # Disable the legend
        width=700,
        height=400,
        plot_bgcolor='white',
        paper_bgcolor='white'
    )


    # Add grid lines for better readability
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGrey')

    # Convert to HTML
    div_combined_graph = pio.to_html(fig, include_plotlyjs=False, full_html=False)

    # === Feature 1: Horizontal Bar Graphs for Emissions (gCO2eq) by Solution Dir ===
    # Group by 'solution dir' and sum 'Emissions (gCO2eq)'
    before_gco2eq = before_df.groupby('solution dir')['Emissions (gCO2eq)'].sum().reset_index()
    after_gco2eq = after_df.groupby('solution dir')['Emissions (gCO2eq)'].sum().reset_index()

    latest_before_gco2eq = latest_before_df.groupby('solution dir')['Emissions (gCO2eq)'].sum().reset_index()
    latest_after_gco2eq = latest_after_df.groupby('solution dir')['Emissions (gCO2eq)'].sum().reset_index()

    # Sort the data by emissions (descending for top 5)
    before_gco2eq_sorted = before_gco2eq.sort_values('Emissions (gCO2eq)', ascending=False)
    after_gco2eq_sorted = after_gco2eq.sort_values('Emissions (gCO2eq)', ascending=False)

    # Sort the data by emissions (descending for top 5)
    latest_before_gco2eq_sorted = latest_before_gco2eq.sort_values('Emissions (gCO2eq)', ascending=False)
    latest_after_gco2eq_sorted = latest_after_gco2eq.sort_values('Emissions (gCO2eq)', ascending=False)

    unique_solution_dirs_gco2eq = sorted(set(before_gco2eq_sorted['solution dir']).union(after_gco2eq_sorted['solution dir']))

    latest_unique_solution_dirs_gco2eq = sorted(set(latest_before_gco2eq_sorted['solution dir']).union(latest_after_gco2eq_sorted['solution dir']))

   # Create a dictionary to store colors for each solution dir
    color_mapping = {
        solution_dir: colors[i % len(colors)]
        for i, solution_dir in enumerate(before_file_type_sorted['solution dir'].unique())
    }

    # Create figure
    fig = go.Figure()

    # Add traces for "Before" data
    for i, (_, row) in enumerate(before_gco2eq_sorted.iterrows()):
        fig.add_trace(go.Bar(
            x=[row['solution dir']],
            y=[row['Emissions (gCO2eq)']],
            name='Before',  # Simplified name
            marker=dict(
                color=color_mapping.get(row['solution dir'], 'grey'),  # Safe lookup
                opacity=0.9
            ),
            offsetgroup=0,
            showlegend=True if i == 0 else False  # Show legend only for first "Before" bar
        ))

    # Add traces for "After" data
    for i, (_, row) in enumerate(after_gco2eq_sorted.iterrows()):
        fig.add_trace(go.Bar(
            x=[row['solution dir']],
            y=[row['Emissions (gCO2eq)']],
            name='After',  # Simplified name
            marker=dict(
                color=color_mapping.get(row['solution dir'], 'grey'),  # Safe lookup
                opacity=0.6,
                pattern=dict(shape="/", solidity=0.7)
            ),
            offsetgroup=1,
            showlegend=True if i == 0 else False  # Show legend only for first "After" bar
        ))

    # Update layout
    fig.update_layout(
        title={
            'text': 'Source Code Directory Level Emissions (gCO2eq) - Before vs After Optimization',
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        xaxis_title='Solution Dir',
        yaxis_title='Emissions (gCO2eq)',
        barmode='group',
        xaxis=dict(
            tickangle=45,
            tickformat=".6f"
        ),
        yaxis=dict(
            range=[0, max(
                before_gco2eq_sorted['Emissions (gCO2eq)'].max(),
                after_gco2eq_sorted['Emissions (gCO2eq)'].max()
            ) * 1.1],
            tickformat=".6f"
        ),
        margin=dict(l=50, r=50, t=100, b=120),
        showlegend=False,
        width=700,
        height=400,
        plot_bgcolor='white',
        paper_bgcolor='white'
    )

    # Add grid lines for better readability
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGrey')

    # Convert to HTML
    div_emissions_combined_graph = pio.to_html(fig, include_plotlyjs=False, full_html=False)

    # === Feature 2: Top Five Tables ===
    # Top Five Files Generating Most Energy (Before Refinement)
    top_five_energy_before = before_df.sort_values('Energy Consumed (Wh)', ascending=False).head(5)[['Application name', 'Timestamp', 'Energy Consumed (Wh)']]
    top_five_energy_before.rename(columns={'Application name': 'File Name', 'Timestamp': 'Timestamp', 'Energy Consumed (Wh)': 'Energy Consumed (Wh)'}, inplace=True)
    energy_table_html = top_five_energy_before.to_html(index=False, classes='table', border=0, float_format=lambda x: f"{x:.6f}")

    # Top Five Files Generating Most Emissions (Before Refinement)
    top_five_emissions_before = before_df.sort_values('Emissions (gCO2eq)', ascending=False).head(5)[['Application name', 'Timestamp', 'Emissions (gCO2eq)']]
    top_five_emissions_before.rename(columns={'Application name': 'File Name', 'Timestamp': 'Timestamp', 'Emissions (gCO2eq)': 'Emissions (gCO2eq)'}, inplace=True)
    emissions_table_html = top_five_emissions_before.to_html(index=False, classes='table', border=0, float_format=lambda x: f"{x:.6f}")

# --------------------------------------------------------------------------------------------

    latest_top_five_energy_before = latest_before_df.sort_values('Energy Consumed (Wh)', ascending=False).head(5)[['Application name', 'Timestamp', 'Energy Consumed (Wh)']]
    latest_top_five_energy_before.rename(columns={'Application name': 'File Name', 'Timestamp': 'Timestamp', 'Energy Consumed (Wh)': 'Energy Consumed (Wh)'}, inplace=True)
    latest_energy_table_html = latest_top_five_energy_before.to_html(index=False, classes='table', border=0, float_format=lambda x: f"{x:.6f}")

    # Top Five Files Generating Most Emissions (Before Refinement)
    latest_top_five_emissions_before = latest_before_df.sort_values('Emissions (gCO2eq)', ascending=False).head(5)[['Application name', 'Timestamp', 'Emissions (gCO2eq)']]
    latest_top_five_emissions_before.rename(columns={'Application name': 'File Name', 'Timestamp': 'Timestamp', 'Emissions (gCO2eq)': 'Emissions (gCO2eq)'}, inplace=True)
    latest_emissions_table_html = latest_top_five_emissions_before.to_html(index=False, classes='table', border=0, float_format=lambda x: f"{x:.6f}")

    # === Feature 3: Emissions for Embedded and Non-Embedded Code ===
    # Define embedded and non-embedded file extensions
    embedded_types = ['.html', '.css', '.xml', '.php', '.ts']
    non_embedded_types = ['.py', '.java', '.cpp', '.rb']

    # Filter comparison_df for embedded and non-embedded types
    # Assuming comparison_results.csv has columns: 'File Type', 'Before', 'After'
    embedded_df = comparison_df[comparison_df['File Type'].isin(embedded_types)]
    non_embedded_df = comparison_df[comparison_df['File Type'].isin(non_embedded_types)]

    # Sum 'Before' and 'After' emissions for embedded and non-embedded
    total_embedded_before = embedded_df['Before'].astype(float).sum()
    total_embedded_after = embedded_df['After'].astype(float).sum()

    total_non_embedded_before = non_embedded_df['Before'].astype(float).sum()
    total_non_embedded_after = non_embedded_df['After'].astype(float).sum()

    # --------------------------------------------------------------------------------------------

    before_embedded_df = latest_before_df[latest_before_df['File Type'].isin(embedded_types)]
    before_non_embedded_df = latest_before_df[latest_before_df['File Type'].isin(non_embedded_types)]

    after_embedded_df = latest_after_df[latest_after_df['File Type'].isin(embedded_types)]
    after_non_embedded_df = latest_after_df[latest_after_df['File Type'].isin(non_embedded_types)]

    # Combine the two filtered DataFrames into a single DataFrame
    latest_emissions_df = pd.concat([before_embedded_df, after_embedded_df], ignore_index=True)
    latest_non_emissions_df = pd.concat([before_non_embedded_df, after_non_embedded_df], ignore_index=True)

    # Sum 'Before' and 'After' emissions for embedded and non-embedded
    latest_total_embedded_before = before_embedded_df['Emissions (gCO2eq)'].astype(float).sum()
    latest_total_embedded_after = after_embedded_df['Emissions (gCO2eq)'].astype(float).sum()

    latest_total_non_embedded_before = before_non_embedded_df['Emissions (gCO2eq)'].astype(float).sum()
    latest_total_non_embedded_after = after_non_embedded_df['Emissions (gCO2eq)'].astype(float).sum()
# --------------------------------------------------------------------------------------------

    # Check if there are any embedded code files
    if embedded_df.empty:
        div_pie_chart_embedded = "<p>No embedded code files found: ['.html', '.css', '.xml', '.php', '.ts']</p>"
    else:
        # Create a single figure
        fig = go.Figure()

        # Add a single pie chart with both values
        fig.add_trace(
            go.Pie(
                values=[total_embedded_before, total_embedded_after],
                labels=['Before', 'After'],
                name="Emissions",
                marker=dict(colors=['#FF6B6B', '#4ECDC4']),  # Red for before, Teal for after
                textinfo='label+value',
                textposition='outside',
                texttemplate='%{label}<br>%{value:.6f} gCO2eq',
                hovertemplate="<b>%{label}</b><br>Emissions: %{value:.6f} gCO2eq<br>%{percent}<extra></extra>",
                hole=0.7,  # Large hole for the percentage
                direction='clockwise',
                showlegend=False
            )
        )

        # Calculate reduction percentage
        reduction_percentage = ((total_embedded_before - total_embedded_after) / total_embedded_before * 100)

        # Update layout with modern styling
        fig.update_layout(
            title=dict(
                text='Embedded Code Emissions (gCO2eq)<br>[".html",".css",".xml",".php",".ts"]',
                y=0.95,
                x=0.5,
                xanchor='center',
                yanchor='top',
                font=dict(size=18)
            ),
            annotations=[
                # Add reduction percentage in the middle
                dict(
                    text=f"↓{reduction_percentage:.1f}%",
                    x=0.5,
                    y=0.5,
                    font=dict(size=24, color='green'),
                    showarrow=False
                ),
                # Add "Reduction" label below the percentage
                dict(
                    text="Reduction",
                    x=0.5,
                    y=0.42,
                    font=dict(size=14, color='green'),
                    showarrow=False
                )
            ],
            width=600,
            height=400,
            paper_bgcolor='white',
            plot_bgcolor='white',
            showlegend=False,
        )
        # Convert to HTML
        div_pie_chart_embedded = pio.to_html(fig, include_plotlyjs=False, full_html=False)

    # Check if there are any non-embedded code files
    if non_embedded_df.empty:
        div_pie_chart_non_embedded = "<p>No non-embedded code files found: ['.py', '.java', '.cpp', '.rb']</p>"
    else:
        # Create a single figure
        fig = go.Figure()

        # Add a single pie chart with both values
        fig.add_trace(
            go.Pie(
                values=[total_non_embedded_before, total_non_embedded_after],
                labels=['Before', 'After'],
                name="Emissions",
                marker=dict(colors=['#FF6B6B', '#4ECDC4']),  # Red for before, Teal for after
                textinfo='label+value',
                textposition='outside',
                texttemplate='%{label}<br>%{value:.6f} gCO2eq',
                hovertemplate="<b>%{label}</b><br>Emissions: %{value:.6f} gCO2eq<br>%{percent}<extra></extra>",
                hole=0.7,  # Large hole for the percentage
                direction='clockwise',
                showlegend=False
            )
        )

        # Calculate reduction percentage
        reduction_percentage = ((total_non_embedded_before - total_non_embedded_after) / total_non_embedded_before * 100)

        # Update layout with modern styling
        fig.update_layout(
            title=dict(
                text='Non-Embedded Code Emissions (gCO2eq)<br>[".py", ".java", ".cpp", ".rb"]',
                y=0.95,
                x=0.5,
                xanchor='center',
                yanchor='top',
                font=dict(size=18)
            ),
            annotations=[
                # Add reduction percentage in the middle
                dict(
                    text=f"↓{reduction_percentage:.1f}%",
                    x=0.5,
                    y=0.5,
                    font=dict(size=24, color='green'),
                    showarrow=False
                ),
                # Add "Reduction" label below the percentage
                dict(
                    text="Reduction",
                    x=0.5,
                    y=0.38,
                    font=dict(size=14, color='green'),
                    showarrow=False
                )
            ],
            width=600,
            height=400,
            paper_bgcolor='white',
            plot_bgcolor='white',
            showlegend=False,
        )
        # Convert to HTML
        div_pie_chart_non_embedded = pio.to_html(fig, include_plotlyjs=False, full_html=False)

# --------------------------------------------------------------------------------------------


    # Render the template with dynamic data
    html_content = template.render(
        total_before=f"{total_before:.6f}",
        total_after=f"{total_after:.6f}",
        energy_table_html=energy_table_html,
        emissions_table_html=emissions_table_html,
        total_emissions_before=f"{total_emissions_before:.6f}",
        total_emissions_after=f"{total_emissions_after:.6f}",
        # div_bar_graph_embedded=div_bar_graph_embedded,
        # div_bar_graph_non_embedded=div_bar_graph_non_embedded,
        last_run_timestamp=last_run_timestamp,  # Pass the timestamp
        # div_line_chart=div_faceted_area_charts,
        server_os_type_fig=server_os_type_fig,
        server_os_version_fig=server_os_version_fig,
        unique_hosts=unique_hosts,
        average_co2_emission=round(average_co2_emission, 4),  # Round for better display
        average_energy_consumption=round(average_energy_consumption, 4),  # Round for better display
        average_cpu_usage=round(average_cpu_usage, 2),
        average_ram_usage=round(average_ram_usage, 2),
        average_disk_usage=round(average_disk_usage, 2),
        average_network_usage=round(average_network_usage, 2),
        average_disk_read=round(average_disk_read, 2),
        average_disk_write=round(average_disk_write, 2),
        cpu_usage_data=cpu_data,
        ram_usage_data=ram_data,
        disk_usage_data=disk_data,
        network_usage_data=network_data,
        disk_read_data=disk_read,
        disk_write_data=disk_write,
        max_network=max_network,
        critical_servers=critical_servers_list,
        div_combined_graph=div_combined_graph,
        div_emissions_combined_graph=div_emissions_combined_graph,
        div_pie_chart_non_embedded=div_pie_chart_non_embedded,
        div_pie_chart_embedded=div_pie_chart_embedded,
        unique_servers=unique_servers,
        critical_server_count=critical_server_count,
        total_last_run_co2=f"{total_last_run_co2:.6f}",
        total_last_run_power=f"{total_last_run_power:.6f}",
        formatted_timestamp=formatted_timestamp,
    )

    # Render the details template with detailed data
    html_details_content = details_template.render(
        solution_dirs=solution_dirs,
        before_details=before_details,
        after_details=after_details
    )

        # Render the template with dynamic data
    timestamp_html_content = lastrun_template.render(
        latest_total_before=f"{latest_total_before:.2f}",
        latest_total_after=f"{latest_total_after:.2f}",
        latest_energy_table_html=latest_energy_table_html,
        latest_emissions_table_html=latest_emissions_table_html,
        latest_total_emissions_before=f"{latest_total_emissions_before:.2f}",
        latest_total_emissions_after=f"{latest_total_emissions_after:.2f}",
        last_run_timestamp=last_run_timestamp,  # Pass the timestamp
        # div_line_chart=div_faceted_area_charts,
        unique_hosts=unique_hosts,
        average_co2_emission=round(average_co2_emission, 4),  # Round for better display
        average_energy_consumption=round(average_energy_consumption, 4),  # Round for better display
    )

        # Render the timestamp-based report template
    timestamp_html_details_content = lastrun_details_template.render(
        solution_dirs=solution_dirs,
        latest_before_details=latest_before_details,
        latest_after_details=latest_after_details
    )

    server_details = details_server_template.render(
        unique_servers=unique_servers,
        server_details=server_details
    )

    recommendations_detalis = recommendations_template.render(
            unique_dates=unique_dates,
            recommendations_details=recommendations_details
    )


    # === Finalizing the HTML Content ===
    current_date = datetime.now().strftime('%Y-%m-%d')
    current_time = datetime.now().strftime('%H-%M')
    date_folder_path = os.path.join(REPORT_DIR, current_date)
    time_folder_path = os.path.join(date_folder_path, current_time)

    # Create both date and time folders if they don't exist
    os.makedirs(time_folder_path, exist_ok=True)
    logging.info(f"Directory '{time_folder_path}' is ready for use!")

    # Save the timestamp-based HTML report
    details_report_path = os.path.join(time_folder_path, 'details_report.html')
    with open(details_report_path, 'w', encoding="utf-8") as f:
        f.write(timestamp_html_details_content)
    logging.info(f"Last Run Detailed HTML report generated at {details_report_path}")

    emissions_report_path = os.path.join(time_folder_path, 'emissions_report.html')
    with open(emissions_report_path, 'w', encoding="utf-8") as f:
        f.write(timestamp_html_content)
    logging.info(f"Last Run Emissions HTML report generated at {emissions_report_path}")

    servers_report_path = os.path.join(time_folder_path, 'server_report.html')
    with open(servers_report_path, 'w', encoding="utf-8") as f:
        f.write(server_details)
    logging.info(f"Server Details HTML report generated at {servers_report_path}")

    recommendations_report_path = os.path.join(time_folder_path, 'recommendations_report.html')
    with open(recommendations_report_path, 'w', encoding="utf-8") as f:
        f.write(recommendations_detalis)
    logging.info(f"Recommendations HTML report generated at {recommendations_report_path}") 

    # Create the report directory if it doesn't exist
    os.makedirs(REPORT_DIR, exist_ok=True)
    logging.info(f"Directory '{REPORT_DIR}' is ready for use!")

    # Save the main HTML report
    report_path = os.path.join(REPORT_DIR, 'emissions_report.html')
    with open(report_path, 'w', encoding="utf-8") as f:
        f.write(html_content)
    logging.info(f"HTML report generated at {report_path}")

    # Save the detailed HTML report
    detailed_report_path = os.path.join(REPORT_DIR, 'details_report.html')
    with open(detailed_report_path, 'w', encoding="utf-8") as f:
        f.write(html_details_content)
    logging.info(f"Detailed HTML report generated at {detailed_report_path}")

    server_report_path = os.path.join(REPORT_DIR, 'server_report.html')
    with open(server_report_path, 'w', encoding="utf-8") as f:
        f.write(server_details)
    logging.info(f"Server Details HTML report generated at {server_report_path}")

    recommendations_report_path = os.path.join(REPORT_DIR, 'recommendations_report.html')
    with open(recommendations_report_path, 'w', encoding="utf-8") as f:
        f.write(recommendations_detalis)
    logging.info(f"Recommendations HTML report generated at {recommendations_report_path}")


# Generate HTML report
generate_html_report(RESULT_DIR)
