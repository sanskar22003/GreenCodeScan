import os
import json
import dotenv
import uuid
import time
import shutil
from dotenv import load_dotenv
from openai import AzureOpenAI

# Load environment variables
env_path = os.path.abspath(".env")
load_dotenv(dotenv_path=env_path, verbose=True, override=True)

# Define directories
source_directory = os.path.dirname(env_path)
green_code_directory = os.path.join(source_directory, 'GreenCode')
temp_directory = os.path.join(green_code_directory, 'temp')
test_file_directory = os.path.join(source_directory, 'test_file')

# Store file extensions in a variable
file_extensions = ['.py', '.java', '.xml', '.php', '.cpp','.html','.css','.ts','.rb']

# Initialize AzureOpenAI client using environment variables
client = AzureOpenAI(
    api_key=os.getenv('AZURE_API_KEY'),
    api_version=os.getenv('AZURE_API_VERSION'),
    azure_endpoint=os.getenv('AZURE_ENDPOINT')
)

# Function to delete a directory and its contents
def remove_directory(directory):
    if os.path.exists(directory):
        shutil.rmtree(directory)
        print(f"Directory '{directory}' deleted successfully!")

# Directory creation logic: Delete existing 'GreenCode' directory if it exists, then create a fresh one
remove_directory(green_code_directory)
os.makedirs(green_code_directory)
print(f"Directory '{green_code_directory}' created successfully!")

# Ensure temp and test_file directories exist
def ensure_directory_structure(path):
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Folder '{path}' created.")

ensure_directory_structure(temp_directory)
ensure_directory_structure(test_file_directory)

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
    model="GPT4o",
    tools=[{"type": "code_interpreter"}]
)

# List of files to exclude from processing
excluded_files = {
    'GreenCodeRefiner.py',
    'compare_emissions.py',
    'server_emissions.py',
    'track_emissions.py'
}

# Function to find files in the source directory
def find_files(directory, extensions, excluded_files):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file in excluded_files:
                continue
            if file.endswith(tuple(extensions)):
                yield os.path.join(root, file)

# Function to create unit test files for source files without a test file
def create_unit_test_files(file_list):
    for file_path in file_list:
        file_name = os.path.basename(file_path)
        base_name, ext = os.path.splitext(file_name)
        
        # Check if the file is a test file
        if 'test' in base_name.lower():
            print(f"Skipping test file: {file_path}")
            continue

        # Check if a corresponding test file exists
        test_file_name = f"{base_name}Test{ext}"
        test_file_path = os.path.join(test_file_directory, test_file_name)
        
        if os.path.exists(test_file_path):
            print(f"Test file already exists: {test_file_path}")
            continue

        # Create a unit test file
        prompt = f"Create a unit test case for the following {ext} file: {file_name}"
        with open(file_path, "rb") as file:
            uploaded_file = client.files.create(
                file=file,
                purpose='assistants'
            )
        print(f"Creating unit test file for: {file_name}")
        
        thread = client.beta.threads.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "file_ids": [uploaded_file.id]
                }
            ]
        )
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id
        )
        
        start_time = time.time()
        while True:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            ).status
            if run_status == 'completed':
                break
            elif time.time() - start_time > 1200:  # Timeout after 20 minutes
                print("Unit test creation timed out.")
                return
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
            content.write_to_file(test_file_path)
            print(f"Unit test file created: {test_file_path}")
        else:
            print(f"Failed to create unit test for file: {file_path}")

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
        elif time.time() - start_time > 1200:  # Timeout after 20 minutes
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

# Define the list to store files
file_list = list(find_files(source_directory, file_extensions, excluded_files))

# Step 1: Create unit test files for all source files without test files
create_unit_test_files(file_list)

# Re-scan the source directory to include newly created test files
file_list = list(find_files(source_directory, file_extensions, excluded_files))

# Define the prompts for refining the code
prompts = [
    "Make the code more energy efficient",
    "Eliminate any redundant or dead code",
    "Simplify complex algorithms to reduce computational load",
    "Enhance the readability of the code",
    "Optimize memory usage in the code",
    "Reduce the number of dependencies",
    "Ensure the code adheres to the latest coding standards",
    "Improve the maintainability of the code",
    "Refactor the code to reduce complexity",
    "Test the code for edge cases"
]

# Upload and refine files
while file_list:
    file_path = file_list.pop(0)
    relative_path = os.path.relpath(file_path, source_directory)
    file_name = os.path.basename(file_path)
    
    # Skip excluded files and the green_code_directory and its subdirectories
    if file_name in excluded_files or relative_path.startswith(os.path.relpath(green_code_directory, source_directory)):
        print(f"Skipping excluded file or directory: {relative_path}")
        continue
    
    # Check if the file is empty
    if os.path.getsize(file_path) == 0:
        print(f"Skipping empty file: {file_path}")
        continue
    
    with open(file_path, "rb") as file:
        uploaded_file = client.files.create(
            file=file,
            purpose='assistants'
        )
    
    refined_temp_file_path = os.path.join(temp_directory, file_name)
    ensure_directory_structure(os.path.dirname(refined_temp_file_path))
    
    refined_success = False
    
    # Apply all prompts sequentially
    for prompt in prompts:
        refined_success = process_file_with_prompt(uploaded_file.id, prompt, refined_temp_file_path)
        
        # If the file is refined successfully with the current prompt, continue with the next prompt
        if refined_success:
            print(f"Successfully applied prompt: '{prompt}' to {file_name}")
        else:
            print(f"Failed to apply prompt: '{prompt}' to {file_name}")
    
    # Move the refined file after all prompts have been applied
    if refined_success:
        final_file_path = os.path.join(green_code_directory, relative_path)
        ensure_directory_structure(os.path.dirname(final_file_path))
        os.rename(refined_temp_file_path, final_file_path)
        print(f"File refined and moved: {final_file_path}")
    else:
        print(f"Failed to refine file: {file_path}")
