import os
import json
import dotenv
import uuid
import time
from dotenv import load_dotenv
from openai import AzureOpenAI

# Load environment variables
load_dotenv(dotenv_path=".env", verbose=True, override=True)

# Define directories using environment variables
source_directory = os.getenv('SOURCE_DIRECTORY')
green_refined_directory = os.getenv('GREEN_REFINED_DIRECTORY')
temp_directory = os.path.join(green_refined_directory, 'temp')

# Initialize AzureOpenAI client using environment variables
client = AzureOpenAI(
    api_key=os.getenv('AZURE_API_KEY'),
    api_version=os.getenv('AZURE_API_VERSION'),
    azure_endpoint=os.getenv('AZURE_ENDPOINT')
)

unique_name = f"GreenCodeRefiner {uuid.uuid4()}"
# Create an assistant
assistant = client.beta.assistants.create(
    name=unique_name,
    instructions=("You are a helpful AI assistant who re-factors the code from an uploaded file to make it more efficient. "
                  "You have access to a sandboxed environment for writing and testing code. "
                  "1. Re-write the code in the same language as the original code. "
                  "2. Test the re-written code and ensure it functions correctly and same as the original code. "
                  "3. Run the code to confirm that it runs successfully. "
                  "4. If the code runs successfully, share the code as a file that can be downloaded. "
                  "5. If the code is unsuccessful, display the error message and try to revise the code and rerun."),
    model="code",
    tools=[{"type": "code_interpreter"}]
)

# Create a thread
thread = client.beta.threads.create()
print(thread)

# Function to ensure directory structure in download_directory mirrors source_directory
def ensure_directory_structure(path):
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Folder '{path}' created.")

# Function to recursively find files with specific extensions
def find_files(directory, extensions):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(tuple(extensions)):
                yield os.path.join(root, file)

# Check if the download directory exists, if not, create it
ensure_directory_structure(green_refined_directory)
ensure_directory_structure(temp_directory)

# Log file creation
log_file_path = os.path.join(green_refined_directory, "upload_log.txt")
if not os.path.exists(log_file_path):
    with open(log_file_path, 'w') as log_file:
        log_file.write("")

# Step 1: Read the log file into a set
uploaded_files = set()
if os.path.exists(log_file_path):
    with open(log_file_path, 'r') as log_file:
        uploaded_files = {line.strip() for line in log_file}

# Define the prompts
prompts = [
    "Make the code more energy efficient",
    "Eliminate any redundant or dead code",
    "Simplify complex algorithms to reduce computational load"
]

# Function to process a file with the given prompt
def process_file_with_prompt(file_id, prompt, refined_file_path):
    print(f"Applying prompt: {prompt}")
    # Create a thread with the prompt
    thread = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
                "file_ids": [file_id]
            }
        ]
    )

    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id
    )

    # Retrieve the status of the run
    start_time = time.time()
    while True:
        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        ).status
        print(f"Current status: {run_status}")

        if run_status == 'completed':
            break
        elif time.time() - start_time > 1200:  # Timeout after 10 minutes
            print("Processing timed out.")
            return False
        else:
            time.sleep(5)

    messages = client.beta.threads.messages.list(
        thread_id=thread.id
    )

    data = json.loads(messages.model_dump_json(indent=2))

    code = None
    if data['data'] and data['data'][0]['content'] and data['data'][0]['content'][0]['text']['annotations']:
        code = data['data'][0]['content'][0]['text']['annotations'][0]['file_path']['file_id']

    if code:
        content = client.files.content(code)
        content.write_to_file(refined_file_path)
        print(f"File refined with prompt: {prompt}")
        return True
    else:
        print("No code found or annotations list is empty.")
        return False

# List of files to exclude from processing
excluded_files = {
    'GreenCodeRefiner.py',
    'compare_emissions.py',
    'server_emissions.py',
    'track_emissions.py'
}

# Upload and refine files
file_processed = False
for file_path in find_files(source_directory, ['.py', '.java', '.xml', '.php', '.cpp']):
    relative_path = os.path.relpath(file_path, source_directory)
    file_name = os.path.basename(file_path)

    # Skip excluded files and the green_refined_folder and its subdirectories
    if file_name in excluded_files or relative_path.startswith(os.path.relpath(green_refined_directory, source_directory)):
        print(f"Skipping excluded file or directory: {relative_path}")
        continue
    
    if relative_path in uploaded_files:
        print(f"{relative_path} has already been uploaded. Skipping.")
        continue

    with open(file_path, "rb") as file:
        uploaded_file = client.files.create(
            file=file,
            purpose='assistants'
        )

    refined_temp_file_path = os.path.join(temp_directory, file_name)
    ensure_directory_structure(os.path.dirname(refined_temp_file_path))

    refined_success = False
    for prompt in prompts:
        refined_success = process_file_with_prompt(uploaded_file.id, prompt, refined_temp_file_path)
        if not refined_success:
            break

    if refined_success:
        final_refined_directory = os.path.join(green_refined_directory, os.path.dirname(relative_path))
        ensure_directory_structure(final_refined_directory)

        final_refined_file_path = os.path.join(final_refined_directory, file_name)
        os.rename(refined_temp_file_path, final_refined_file_path)
        print(f"File moved to final location: {final_refined_file_path}")

        with open(log_file_path, 'a') as log_file:
            log_file.write(f"{relative_path}\n")
        uploaded_files.add(relative_path)
        file_processed = True
    else:
        print(f"Failed to refine the file: {file_path}")

    break

if not file_processed:
    print("No new files were processed.")

# Ensure temp directory is empty
if not os.listdir(temp_directory):
    print("Temp directory is empty.")
else:
    print("Temp directory is not empty.")

# Check messages in the thread
thread_messages = client.beta.threads.messages.list(thread.id)
print(thread_messages.model_dump_json(indent=2))

# Check if all relevant files have been refined
source_files = {os.path.relpath(os.path.join(root, file), source_directory) for root, _, files in os.walk(source_directory) for file in files if file.endswith(('.py', '.java', '.xml', '.php', '.cpp'))}
refined_files = {os.path.relpath(os.path.join(root, file), green_refined_directory) for root, _, files in os.walk(green_refined_directory) for file in files if file.endswith(('.py', '.java', '.xml', '.php', '.cpp'))}

# Exclude specific files and the Green_Refined_Files directory from comparison
excluded_from_comparison = excluded_files.union(
    {os.path.relpath(file, source_directory) for file in [
        os.path.join(source_directory, 'Green_Refined_Files')
    ]}
)

source_files -= excluded_from_comparison
refined_files -= excluded_from_comparison

if source_files.issubset(refined_files):
    print('Script-Has-Uploaded-All-Files')
else:
    print('Script-Has-Remain-Some-Files-To-Uploaded')
