import os
import json
import dotenv
import uuid  # Import UUID module
import time
from dotenv import load_dotenv
from openai import AzureOpenAI

# Define directories
source_directory = 'C:\\ProgramData\\Jenkins\\.jenkins\\workspace\\GreenCodeScanPipeline\\tests2'
download_directory = "C:\\ProgramData\\Jenkins\\.jenkins\\workspace\\GreenCodeScanPipeline\\Refined Files"

#//////////////////////////////////////////
file_path = os.path.join(download_directory, "track_emissions_after.py")
# Check if the folder exists
if not os.path.exists(download_directory):
    os.makedirs(download_directory)
    print(f"Folder '{download_directory}' created.")
    # Since the folder did not exist, we can safely assume the file needs to be created.
    file_needs_creation = True
else:
    # If the folder exists, check if the file already exists
    file_needs_creation = not os.path.exists(file_path)
# Only create the file if it does not exist
if file_needs_creation:
    # Code content to write in the Python file
    code_content = r"""
    import os
    import subprocess
    import csv
    from codecarbon import EmissionsTracker
    from datetime import datetime
    import time
    import pandas as pd
    import sys
    
    # Define all paths and constants here
    BASE_DIR = r"C:\ProgramData\Jenkins\.jenkins\workspace\GreenCodeScanPipeline\Refined Files"
    SCRIPTS_DIR = os.path.join(BASE_DIR)
    TESTS_DIR_PATH = r"C:\ProgramData\Jenkins\.jenkins\workspace\GreenCodeScanPipeline"
    TESTS_DIR = os.path.join(TESTS_DIR_PATH, 'tests')
    PYTEST_PATH = r"C:\Users\sansk\AppData\Local\Programs\Python\Python312\Scripts\pytest.exe"
    MAVEN_PATH = r"C:\Users\sansk\Downloads\apache-maven-3.9.6\bin\mvn.cmd"
    EMISSIONS_CSV = os.path.join(BASE_DIR, 'emissions.csv')
    EMISSIONS_DATA_CSV = 'emissions_data_after.csv'
    CUSTOMER_NAME = "ZF"
    
    #Added \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    '''# Ensure the EMISSIONS_CSV file exists, if not create it and write the header
    if not os.path.exists(EMISSIONS_CSV):
        with open(EMISSIONS_CSV, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Customer Name", "Application name", "File Type", "Timestamp", "Emissions (gCO2eq)", "Duration", "emissions_rate", "CPU Power (KWh)", "GPU Power (KWh)", "RAM Power (KWh)", "CPU Energy (Wh)", "GPU Energy (KWh)", "RAM Energy (Wh)", "Energy Consumed (Wh)", "Test Results"])
    '''
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
    
        # Check if the emissions.csv file is empty
            if os.stat(EMISSIONS_CSV).st_size != 0:
            # Read the emissions data from the CSV file
                emissions_data = pd.read_csv(EMISSIONS_CSV).iloc[-1]
        
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
    
        # Write the data to the CSV file
            with open(EMISSIONS_DATA_CSV, 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(data)
                file.flush()
    
    print("Emissions data and test results written to emissions_data_after.csv")
    """
    with open(file_path, 'w') as file:
        file.write(code_content)
        print(f"File '{file_path}' created with initial content.")
else:
    print(f"File '{file_path}' already exists. No action taken.")

#//////////////////////////////////////////


#////////////////////////////////
# Check if the download directory exists, if not, create it
if not os.path.exists(download_directory):
    os.makedirs(download_directory)
#///////////////////////////////

# Load environment variables
load_dotenv(dotenv_path=".env", verbose=True, override=True)

# Initialize AzureOpenAI client
client = AzureOpenAI(
    api_key="eadf76dd169e4172a463e7375946835f",
    api_version="2024-02-15-preview",
    azure_endpoint="https://green-code-uks.openai.azure.com"
)
unique_name = f"GreenCodeRefiner {uuid.uuid4()}"
# Create an assistant
assistant = client.beta.assistants.create(
    name=unique_name,
    instructions=("You are a helpful AI assistant who re-factors the code from an uploaded file to make it more efficient"
                  "You have access to a sandboxed environment for writing and testing code."
                  "1. Re-write the code in the same language as the original code."
                  "2. Test the re-written code and ensure it functions correctly and same as the original code."
                  "3. Run the code to confirm that it runs successfully"
                  "4. If the code runs successfully, share the code as a file that can be downloaded"
                  "5. If the code is unsuccessful display the error message and try to revise the code and rerun."),
    model="code",
    tools=[{"type": "code_interpreter"}]
)

# Create a thread
thread = client.beta.threads.create()
print(thread)

# Log file creation
log_file_path = os.path.join(download_directory, "upload_log.txt")
if not os.path.exists(log_file_path):
    with open(log_file_path, 'w') as log_file:
        log_file.write("")

# Step 1: Read the log file into a set
uploaded_files = set()
if os.path.exists(log_file_path):
    with open(log_file_path, 'r') as log_file:
        uploaded_files = {line.strip() for line in log_file}

# Upload a reference file
file_processed = False  # Flag to indicate if a new file has been processed
for file_name in os.listdir(source_directory):
    if file_name.endswith('.py') or file_name.endswith('.java'):
        # Check if the current file is in the set
        if file_name in uploaded_files:
            print(f"{file_name} has already been uploaded. Skipping.")
            continue  # Skip this file and move to the next one

        file_path = os.path.join(source_directory, file_name)
        with open(file_path, "rb") as file:
            uploaded_file = client.files.create(
                file=file,
                purpose='assistants'
            )
        # Write uploaded file name to log file and add to the set
        with open(log_file_path, 'a') as log_file:
            log_file.write(f"{file_name}\n")
        uploaded_files.add(file_name)
        file_processed = True  # Set the flag to True as a file has been processed

        # Pass a message to thread for the uploaded file
        thread = client.beta.threads.create(
            messages=[
                {
                    "role": "user",
                    "content": "Make the code energy efficient",
                    "file_ids": [uploaded_file.id]
                }
            ]
        )
        break  # Process one file at a time

if not file_processed:
    print("No new files were processed.")

#Check messages in the thread
thread_messages = client.beta.threads.messages.list(thread.id)
print(thread_messages.model_dump_json(indent=2))

run = client.beta.threads.runs.create(
  thread_id=thread.id,
  assistant_id=assistant.id
)

# Retrieve the status of the run
while True:
    # Retrieve the status of the run
    run_status = client.beta.threads.runs.retrieve(
      thread_id=thread.id,
      run_id=run.id
    ).status
    print(f"Current status: {run_status}")
    
    # Check if the status is 'completed'
    if run_status == 'completed':
        break  # Exit the loop if completed
    else:
        time.sleep(5)  # Wait for 5 seconds before checking again
      
#Print messages in the thread post run
messages = client.beta.threads.messages.list(
  thread_id=thread.id
)

# Extract the content of the latest question only, with safety checks
data = json.loads(messages.model_dump_json(indent=2))

# Initialize code to None
code = None

# Check if data and nested structures exist and are not empty
if data['data'] and data['data'][0]['content'] and data['data'][0]['content'][0]['text']['annotations']:
    # Now it's safe to access the first element
    code = data['data'][0]['content'][0]['text']['annotations'][0]['file_path']['file_id']

# Proceed only if code is not None
if code:
    content = client.files.content(code)
    refined_file_path = os.path.join(download_directory, file_name)  # Reuse file_name from the loop
    code_file = content.write_to_file(refined_file_path)
else:
    print("No code found or annotations list is empty.")

'''print(messages.model_dump_json(indent=2))

#Extract the content of the latest question only
data = json.loads(messages.model_dump_json(indent=2))
code = data['data'][0]['content'][0]['text']['annotations'][0]['file_path']['file_id']
print(code)

content = client.files.content(code)
refined_file_path = os.path.join(download_directory, file_name)  # Reuse file_name from the loop
code_file = content.write_to_file(refined_file_path) '''

# Check if all Python and Java files have been refined
source_files = {f for f in os.listdir(source_directory) if f.endswith('.py') or f.endswith('.java')}
refined_files = {f for f in os.listdir(download_directory) if f.endswith('.py') or f.endswith('.java')}

if source_files.issubset(refined_files):
    print('Script-Has-Uploaded-All-Files')
else:
    print('Script-Has-Remain-Some-Files-To-Uploaded')
