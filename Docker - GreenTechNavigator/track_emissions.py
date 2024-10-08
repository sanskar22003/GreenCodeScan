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

# Load environment variables
# Define Base Directory
BASE_DIR = '/app/project'
TEMP_DIR = '/app/'
# Load environment variables
env_path = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=env_path, verbose=True, override=True)

# Define directories based on BASE_DIR
SOURCE_DIRECTORY = BASE_DIR
GREEN_REFINED_DIRECTORY = os.path.join(SOURCE_DIRECTORY, 'GreenCode')
RESULT_DIR = os.path.join(SOURCE_DIRECTORY, 'Result')
REPORT_DIR = os.path.join(SOURCE_DIRECTORY, 'Report')

# List of files and directories to exclude from processing
EXCLUDED_FILES = {
    'server_emissions.py',
    'GreenCodeRefiner.py',
    'track_emissions.py',
    'RefinerFunction.py',
    'report_template.html',
    'details_template.html'
}
EXCLUDED_DIRECTORIES = {'GreenCode'}

# Function to process emissions for a single file
def process_emissions_for_file(tracker, script_path, emissions_csv, file_type, result_dir, test_command):
    emissions_data = None
    duration = 0
    test_output = 'Unknown'
    script_name = os.path.basename(script_path)
    # Extract 'solution dir' (immediate parent directory)
    solution_dir = os.path.basename(os.path.dirname(script_path))
    try:
        tracker.start()  # Start the emissions tracking
        start_time = time.time()
        # Run the test command
        if test_command:
            test_result = subprocess.run(test_command, capture_output=True, text=True, timeout=20)
            duration = time.time() - start_time
            test_output = 'Pass' if test_result.returncode == 0 else 'Fail'
        else:
            # No test command, skip test execution
            test_output = 'Not a test file'
            print(f"Skipping test execution for {script_name} as it is a normal programming file.")
    
    except subprocess.TimeoutExpired:
        test_output = 'Timeout'
        print(f"Test execution for {script_path} exceeded the timeout limit.")
    
    except Exception as e:
        test_output = 'Error'
        print(f"An error occurred for {script_path}: {e}")
    
    finally:
        # Ensure tracker stop is always called
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
                test_output,
                solution_dir
            ]
            with open(emissions_csv, 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(data)
                file.flush()
        else:
            print(f"No emissions data found for {script_path}")
    else:
        print(f"Emissions data collection failed for {script_name}")

# # Function to process test execution for different file types
# def process_files_by_type(base_dir, emissions_data_csv, result_dir, file_extension, excluded_files, tracker, test_command_generator):
#     files = []
#     for root, dirs, file_list in os.walk(base_dir):
#         for script in file_list:
#             if script.endswith(file_extension) and script not in excluded_files:
#                 files.append(os.path.join(root, script))

# Function to process test execution for different file types
def process_files_by_type(base_dir, emissions_data_csv, result_dir, file_extension, excluded_files, excluded_dirs, tracker, test_command_generator):
    files = []
    for root, dirs, file_list in os.walk(base_dir):
        # Exclude specified directories
        dirs[:] = [d for d in dirs if d not in excluded_dirs]
        for script in file_list:
            if script.endswith(file_extension) and script not in excluded_files:
                files.append(os.path.join(root, script))
    
    for script_path in files:
        test_command = test_command_generator(script_path) if 'test' in script_path.lower() else None
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
        test_file_name = os.path.basename(script_path).replace('.cpp', '_test.cpp')
        test_file_path = os.path.join('test', test_file_name)
        compile_command = ['g++', '-o', 'test_output', test_file_path, '-lgtest', '-lgtest_main', '-pthread']
        run_command = ['./test_output']
        return compile_command + run_command
    return None
def get_cs_test_command(script_path):
    return [os.getenv('NUNIT_PATH'), 'test', os.path.splitext(os.path.basename(script_path))[0] + '.dll'] if 'test' in script_path.lower() else None
# # Refactored process_folder function
# def process_folder(base_dir, emissions_data_csv, result_dir, suffix):
#     excluded_files = ['server_emissions.py', 'GreenCodeRefiner.py', 'track_emissions.py', 'compare_emissions.py', 'GreenCode']
#     # Ensure the 'result' directory exists
#     if not os.path.exists(result_dir):
#         os.makedirs(result_dir)

# Refactored process_folder function
def process_folder(base_dir, emissions_data_csv, result_dir, suffix, excluded_dirs):
    # Ensure the 'result' directory exists
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
        print(f"Directory '{result_dir}' created successfully!")
    else:
        print(f"Directory '{result_dir}' already exists.")
    
    # # Adjust the path for emissions.csv to be within the 'result' directory with suffix
    # emissions_csv = os.path.join(result_dir, f'emissions_{suffix}.csv')
    # # Check if the CSV file exists, if not, create it and write the header
    # if not os.path.exists(emissions_data_csv):
    #     with open(emissions_data_csv, 'w', newline='') as file:
    #         writer = csv.writer(file)
    #         writer.writerow([
    #             "Application name", "File Type", "Timestamp", "Emissions (gCO2eq)",
    #             "Duration", "emissions_rate", "CPU Power (KWh)", "GPU Power (KWh)", "RAM Power (KWh)",
    #             "CPU Energy (Wh)", "GPU Energy (KWh)", "RAM Energy (Wh)", "Energy Consumed (Wh)", "Test Results", "solution dir"
    #         ])
    # tracker = EmissionsTracker()
        # Check if the CSV file exists, if not, create it and write the header
    if not os.path.exists(emissions_data_csv):
        with open(emissions_data_csv, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([
                "Application name", "File Type", "Timestamp", "Emissions (gCO2eq)",
                "Duration", "emissions_rate", "CPU Power (KWh)", "GPU Power (KWh)", "RAM Power (KWh)",
                "CPU Energy (Wh)", "GPU Energy (KWh)", "RAM Energy (Wh)", "Energy Consumed (Wh)", "Test Results", "solution dir"
            ])
        print(f"CSV file '{emissions_data_csv}' created with headers.")
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

    print(f"Emissions data and test results written to {emissions_data_csv}")

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
print("Emissions data processed successfully.")


# Compare emissions logic
def compare_emissions():
    # Load environment variables again (if needed)
    load_dotenv(dotenv_path=env_path, verbose=True, override=True)

    # Define paths to the before and after CSV files
    result_source_dir = os.path.join(SOURCE_DIRECTORY, 'Result', 'main_before_emissions_data.csv')
    result_green_refined_dir = os.path.join(SOURCE_DIRECTORY, 'Result', 'main_after_emissions_data.csv')

    # Check if both CSV files exist
    if not os.path.isfile(result_source_dir):
        print(f"Source emissions data file not found: {result_source_dir}")
        return
    if not os.path.isfile(result_green_refined_dir):
        print(f"Refined emissions data file not found: {result_green_refined_dir}")
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
        print(f"Merge failed due to missing columns: {e}")
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
        print(f"Directory '{RESULT_DIR}' created successfully!")
    else:
        print(f"Directory '{RESULT_DIR}' already exists.")

    # Write to new CSV file
    result_file_path = os.path.join(RESULT_DIR, "comparison_results.csv")
    result_df.to_csv(result_file_path, index=False)

    print(f"Comparison results saved to {result_file_path}")

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

# === Function to Generate HTML Reports ===
# Function to generate HTML report with Plotly
def generate_html_report(result_dir):
    # Initialize Jinja2 environment
    env = Environment(loader=FileSystemLoader(TEMP_DIR))
    template_path = 'report_template.html'
    details_template_path = 'details_template.html'

    # Prepare detailed data
    solution_dirs, detailed_data = prepare_detailed_data(result_dir)
    
    # Check if the templates exist
    if not os.path.isfile(os.path.join(TEMP_DIR, details_template_path)):
        print(f"Detailed HTML template file not found: {details_template_path}")
        print(f"Looking in: {os.path.join(TEMP_DIR, details_template_path)}")
        return 
    if not os.path.isfile(os.path.join(TEMP_DIR, template_path)):
        print(f"HTML template file not found: {template_path}")
        print(f"Looking in: {os.path.join(TEMP_DIR, template_path)}")
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


    # template = env.get_template(template_path)
    # details_template = env.get_template(details_template_path)

    before_csv = os.path.join(result_dir, 'main_before_emissions_data.csv')
    after_csv = os.path.join(result_dir, 'main_after_emissions_data.csv')
    comparison_csv = os.path.join(result_dir, 'comparison_results.csv')

    # Check if CSV files exist
    if not os.path.exists(before_csv):
        print(f"Before emissions data file not found: {before_csv}")
        return
    if not os.path.exists(after_csv):
        print(f"After emissions data file not found: {after_csv}")
        return
    if not os.path.exists(comparison_csv):
        print(f"Comparison results file not found: {comparison_csv}")
        return

    # Read CSVs and sum 'Energy Consumed (Wh)'
    comparison_df = pd.read_csv(comparison_csv)
    before_df = pd.read_csv(before_csv)
    after_df = pd.read_csv(after_csv)

    total_before = before_df['Energy Consumed (Wh)'].sum()
    total_after = after_df['Energy Consumed (Wh)'].sum()

        # Prepare lists for before and after details to pass to the template
    before_details = before_df[['Application name', 'File Type', 'Duration', 'Emissions (gCO2eq)', 'Energy Consumed (Wh)', 'solution dir']].to_dict(orient='records')
    after_details = after_df[['Application name', 'File Type', 'Duration', 'Emissions (gCO2eq)', 'Energy Consumed (Wh)', 'solution dir']].to_dict(orient='records')

    # Capture the current timestamp for the report
    last_run_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Create Plotly Indicator for Before
    indicator_before = go.Figure(go.Indicator(
        mode="number",
        value=total_before,
        title={"text": "Total Energy Consumed Before Refinement (Wh)"},
        number={'font': {'size': 30}},
        domain={'x': [0, 1], 'y': [0, 1]}
    ))
    indicator_before.update_layout(
        margin=dict(l=10, r=10, t=20, b=10)
    )

    # Create Plotly Indicator for After
    indicator_after = go.Figure(go.Indicator(
        mode="number",
        value=total_after,
        title={"text": "Total Energy Consumed After Refinement (Wh)"},
        number={'font': {'size': 30}},
        domain={'x': [0, 1], 'y': [0, 1]}
    ))
    indicator_after.update_layout(
        margin=dict(l=10, r=10, t=20, b=10)
    )

    # Read CSVs and group by 'solution dir'
    before_file_type = before_df.groupby('solution dir')['Energy Consumed (Wh)'].sum().reset_index()
    after_file_type = after_df.groupby('solution dir')['Energy Consumed (Wh)'].sum().reset_index()

    # Sort the data by energy consumed (descending for top 5)
    before_file_type_sorted = before_file_type.sort_values('Energy Consumed (Wh)', ascending=False)
    after_file_type_sorted = after_file_type.sort_values('Energy Consumed (Wh)', ascending=False)

    # Determine unique solution dirs
    unique_solution_dirs = sorted(set(before_file_type_sorted['solution dir']).union(after_file_type_sorted['solution dir']))

    # Assign colors to solution dirs
    color_palette = px.colors.qualitative.Plotly  # Choose a qualitative color palette
    color_mapping = {}
    for i, solution_dir in enumerate(unique_solution_dirs):
        color_mapping[solution_dir] = color_palette[i % len(color_palette)]  # Cycle through palette if needed

    # Create Plotly Horizontal Bar Graph for Before Emissions with consistent colors
    bar_graph_before = go.Figure()
    for _, row in before_file_type_sorted.iterrows():
        bar_graph_before.add_trace(go.Bar(
            x=[row['Energy Consumed (Wh)']],
            y=[row['solution dir']],
            orientation='h',
            name=row['solution dir'],
            marker=dict(color=color_mapping.get(row['solution dir'], 'blue'))
        ))

    bar_graph_before.update_layout(
        barmode='stack',
        title='Solution Based(Wh) Before',
        xaxis_title='Energy Consumed (Wh)',
        yaxis_title='Solution Dir',
        xaxis=dict(range=[0, int(max(before_file_type_sorted['Energy Consumed (Wh)'].max(), after_file_type_sorted['Energy Consumed (Wh)'].max()) * 1.1)]),
        margin=dict(l=150, r=50, t=50, b=50),
        showlegend=False
    )

    # Create Plotly Horizontal Bar Graph for After Emissions with consistent colors
    bar_graph_after = go.Figure()
    for _, row in after_file_type_sorted.iterrows():
        bar_graph_after.add_trace(go.Bar(
            x=[row['Energy Consumed (Wh)']],
            y=[row['solution dir']],
            orientation='h',
            name=row['solution dir'],
            marker=dict(color=color_mapping.get(row['solution dir'], 'blue'))
        ))

    bar_graph_after.update_layout(
        barmode='stack',
        title='Solution Based (Wh) After',
        xaxis_title='Energy Consumed (Wh)',
        yaxis_title='Solution Dir',
        xaxis=dict(range=[0, int(max(before_file_type_sorted['Energy Consumed (Wh)'].max(), after_file_type_sorted['Energy Consumed (Wh)'].max()) * 1.1)]),
        margin=dict(l=150, r=50, t=50, b=50),
        showlegend=False
    )

    # Convert figures to HTML div
    div_before = pio.to_html(indicator_before, include_plotlyjs=False, full_html=False)
    div_after = pio.to_html(indicator_after, include_plotlyjs=False, full_html=False)
    div_bar_graph_before = pio.to_html(bar_graph_before, include_plotlyjs=False, full_html=False)
    div_bar_graph_after = pio.to_html(bar_graph_after, include_plotlyjs=False, full_html=False)

    # Read comparison_results.csv to get total 'Before' and 'After'
    comparison_df = pd.read_csv(comparison_csv)
    total_emissions_before = comparison_df['Before'].sum()
    total_emissions_after = comparison_df['After'].sum()

    # Create Plotly Indicators for total emissions from comparison_results.csv
    indicator_total_before = go.Figure(go.Indicator(
        mode="number",
        value=total_emissions_before,
        title={"text": "Total Emissions of Entire Project Before Refinement (gCO2eq)"},
        number={'font': {'size': 30}},
        domain={'x': [0, 1], 'y': [0, 1]}
    ))
    indicator_total_before.update_layout(
        margin=dict(l=10, r=10, t=20, b=10)
    )

    indicator_total_after = go.Figure(go.Indicator(
        mode="number",
        value=total_emissions_after,
        title={"text": "Total Emissions of Entire Project After Refinement (gCO2eq)"},
        number={'font': {'size': 30}},
        domain={'x': [0, 1], 'y': [0, 1]}
    ))
    indicator_total_after.update_layout(
        margin=dict(l=10, r=10, t=20, b=10)
    )

    # Convert total indicators to HTML divs
    div_total_before = pio.to_html(indicator_total_before, include_plotlyjs=False, full_html=False)
    div_total_after = pio.to_html(indicator_total_after, include_plotlyjs=False, full_html=False)

    # === Feature 1: Horizontal Bar Graphs for Emissions (gCO2eq) by Solution Dir ===
    # Group by 'solution dir' and sum 'Emissions (gCO2eq)'
    before_gco2eq = before_df.groupby('solution dir')['Emissions (gCO2eq)'].sum().reset_index()
    after_gco2eq = after_df.groupby('solution dir')['Emissions (gCO2eq)'].sum().reset_index()

    # Sort the data by emissions (descending for top 5)
    before_gco2eq_sorted = before_gco2eq.sort_values('Emissions (gCO2eq)', ascending=False)
    after_gco2eq_sorted = after_gco2eq.sort_values('Emissions (gCO2eq)', ascending=False)

    # Create Plotly Horizontal Bar Graph for Before Emissions (gCO2eq)
    bar_graph_before_gco2eq = go.Figure()
    for _, row in before_gco2eq_sorted.iterrows():
        bar_graph_before_gco2eq.add_trace(go.Bar(
            x=[row['Emissions (gCO2eq)']],
            y=[row['solution dir']],
            orientation='h',
            name=row['solution dir'],
            marker=dict(color=color_mapping.get(row['solution dir'], 'blue'))
        ))

    bar_graph_before_gco2eq.update_layout(
        barmode='stack',
        title='Solution Based (gCO2eq) Before',
        xaxis_title='Emissions (gCO2eq)',
        yaxis_title='Solution Dir',
        xaxis=dict(range=[0, int(max(before_gco2eq_sorted['Emissions (gCO2eq)'].max(), after_gco2eq_sorted['Emissions (gCO2eq)'].max()) * 1.1)]),
        margin=dict(l=150, r=50, t=50, b=50),
        showlegend=False
    )

    # Create Plotly Horizontal Bar Graph for After Emissions (gCO2eq)
    bar_graph_after_gco2eq = go.Figure()
    for _, row in after_gco2eq_sorted.iterrows():
        bar_graph_after_gco2eq.add_trace(go.Bar(
            x=[row['Emissions (gCO2eq)']],
            y=[row['solution dir']],
            orientation='h',
            name=row['solution dir'],
            marker=dict(color=color_mapping.get(row['solution dir'], 'blue'))
        ))

    bar_graph_after_gco2eq.update_layout(
        barmode='stack',
        title='Solution Based (gCO2eq) After',
        xaxis_title='Emissions (gCO2eq)',
        yaxis_title='Solution Dir',
        xaxis=dict(range=[0, int(max(before_gco2eq_sorted['Emissions (gCO2eq)'].max(), after_gco2eq_sorted['Emissions (gCO2eq)'].max()) * 1.1)]),
        margin=dict(l=150, r=50, t=50, b=50),
        showlegend=False
    )

    # Convert figures to HTML div
    div_bar_graph_before_gco2eq = pio.to_html(bar_graph_before_gco2eq, include_plotlyjs=False, full_html=False)
    div_bar_graph_after_gco2eq = pio.to_html(bar_graph_after_gco2eq, include_plotlyjs=False, full_html=False)

    # === Feature 2: Top Five Tables ===
    # Top Five Files Generating Most Energy (Before Refinement)
    top_five_energy_before = before_df.sort_values('Energy Consumed (Wh)', ascending=False).head(5)[['Application name', 'Energy Consumed (Wh)']]
    top_five_energy_before.rename(columns={'Application name': 'File Name', 'Energy Consumed (Wh)': 'Energy Consumed (Wh)'}, inplace=True)
    energy_table_html = top_five_energy_before.to_html(index=False, classes='table', border=0)

    # Top Five Files Generating Most Emissions (Before Refinement)
    top_five_emissions_before = before_df.sort_values('Emissions (gCO2eq)', ascending=False).head(5)[['Application name', 'Emissions (gCO2eq)']]
    top_five_emissions_before.rename(columns={'Application name': 'File Name', 'Emissions (gCO2eq)': 'Emissions (gCO2eq)'}, inplace=True)
    emissions_table_html = top_five_emissions_before.to_html(index=False, classes='table', border=0)

    # === Feature 3: Emissions for Embedded and Non-Embedded Code ===
    # Define embedded and non-embedded file extensions
    embedded_types = ['.html', '.css', '.xml', '.php', '.ts']
    non_embedded_types = ['.py', '.java', '.cpp', '.rb']

    # Filter comparison_df for embedded and non-embedded types
    # Assuming comparison_results.csv has columns: 'File Type', 'Before', 'After'
    embedded_df = comparison_df[comparison_df['File Type'].isin(embedded_types)]
    non_embedded_df = comparison_df[comparison_df['File Type'].isin(non_embedded_types)]

    # Sum 'Before' and 'After' emissions for embedded and non-embedded
    total_embedded_before = embedded_df['Before'].sum()
    total_embedded_after = embedded_df['After'].sum()

    total_non_embedded_before = non_embedded_df['Before'].sum()
    total_non_embedded_after = non_embedded_df['After'].sum()

    # Check if there are any embedded code files
    if embedded_df.empty:
        div_bar_graph_embedded = "<p>No embedded code files found for generating the Embedded Code Emissions graph.</p>"
    else:
        # Create Plotly Horizontal Bar Graph for Embedded Code Emissions
        bar_graph_embedded = go.Figure()

        bar_graph_embedded.add_trace(go.Bar(
            x=[total_embedded_before],
            y=['Embedded Code'],
            orientation='h',
            name='Before',
            marker=dict(color='red')
        ))

        bar_graph_embedded.add_trace(go.Bar(
            x=[total_embedded_after],
            y=['Embedded Code'],
            orientation='h',
            name='After',
            marker=dict(color='green')
        ))

        bar_graph_embedded.update_layout(
            barmode='group',
            title='Emissions for Embedded Code (gCO2eq)',
            xaxis_title='Emissions (gCO2eq)',
            yaxis_title='Code Type',
            margin=dict(l=100, r=50, t=50, b=50),
            showlegend=True
        )

        # Convert embedded bar graph to HTML div
        div_bar_graph_embedded = pio.to_html(bar_graph_embedded, include_plotlyjs=False, full_html=False)

    # Check if there are any non-embedded code files
    if non_embedded_df.empty:
        div_bar_graph_non_embedded = "<p>No non-embedded code files found for generating the Non-Embedded Code Emissions graph.</p>"
    else:
        # Create Plotly Horizontal Bar Graph for Non-Embedded Code Emissions
        bar_graph_non_embedded = go.Figure()

        bar_graph_non_embedded.add_trace(go.Bar(
            x=[total_non_embedded_before],
            y=['Non-Embedded Code'],
            orientation='h',
            name='Before',
            marker=dict(color='red')
        ))

        bar_graph_non_embedded.add_trace(go.Bar(
            x=[total_non_embedded_after],
            y=['Non-Embedded Code'],
            orientation='h',
            name='After',
            marker=dict(color='green')
        ))

        bar_graph_non_embedded.update_layout(
            barmode='group',
            title='Emissions for Non-Embedded Code (gCO2eq)',
            xaxis_title='Emissions (gCO2eq)',
            yaxis_title='Code Type',
            margin=dict(l=150, r=50, t=50, b=50),
            showlegend=True
        )

        # Convert non-embedded bar graph to HTML div
        div_bar_graph_non_embedded = pio.to_html(bar_graph_non_embedded, include_plotlyjs=False, full_html=False)

    # # === Generate the Report using Jinja2 Template ===
    # # Initialize Jinja2 environment
    # env = Environment(loader=FileSystemLoader(SOURCE_DIRECTORY))
    # template_path = 'report_template.html'

    # # Check if the template exists
    # if not os.path.isfile(os.path.join(SOURCE_DIRECTORY, template_path)):
    #     print(f"HTML template file not found: {template_path}")
    #     return

    # template = env.get_template(template_path)

    # Render the template with dynamic data
    html_content = template.render(
        total_before=total_before,
        total_after=total_after,
        energy_table_html=energy_table_html,
        emissions_table_html=emissions_table_html,
        div_bar_graph_before=div_bar_graph_before,
        div_bar_graph_after=div_bar_graph_after,
        total_emissions_before=total_emissions_before,
        total_emissions_after=total_emissions_after,
        div_bar_graph_before_gco2eq=div_bar_graph_before_gco2eq,
        div_bar_graph_after_gco2eq=div_bar_graph_after_gco2eq,
        div_bar_graph_embedded=div_bar_graph_embedded,
        div_bar_graph_non_embedded=div_bar_graph_non_embedded,
        last_run_timestamp=last_run_timestamp  # Pass the timestamp
    )

    # Render the template with all solution dirs and details
    html_details_content = details_template.render(
        solution_dirs=solution_dirs,
        before_details=before_details,
        after_details=after_details
    )

    # === Finalizing the HTML Content ===

    # Create the report directory if it doesn't exist
    if not os.path.exists(REPORT_DIR):
        os.makedirs(REPORT_DIR)
        print(f"Directory '{REPORT_DIR}' created successfully!")
    else:
        print(f"Directory '{REPORT_DIR}' already exists.")

    # Save the HTML report
    report_path = os.path.join(REPORT_DIR, 'emissions_report.html')
    with open(report_path, 'w') as f:
        f.write(html_content)

    print(f"HTML report generated at {report_path}")

        # Save the detailed HTML report
    detailed_report_path = os.path.join(REPORT_DIR, 'details_report.html')
    with open(detailed_report_path, 'w') as f:
        f.write(html_details_content)
    
    print(f"Detailed HTML report generated at {detailed_report_path}")

# Generate HTML report
generate_html_report(RESULT_DIR)

