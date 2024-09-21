import os
import json
import dotenv
import uuid
import time
import shutil
import logging
import requests 
from dotenv import load_dotenv
from openai import AzureOpenAI

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
env_path = os.path.abspath(".env")
load_dotenv(dotenv_path=env_path, verbose=True, override=True)

# Function to get environment variable and log error if missing
def get_env_variable(var_name, is_required=True):
    value = os.getenv(var_name)
    if not value and is_required:
        logging.error(f"Environment variable '{var_name}' is missing or not defined!")
        raise EnvironmentError(f"Missing required environment variable: {var_name}")
    return value

def check_azure_subscription(api_key, azure_endpoint, api_version):
    logging.info("Checking Azure subscription availability...")

    try:
        # Use a valid OpenAI API endpoint to verify the subscription
        url = f"{azure_endpoint}/openai/models?api-version={api_version}"
        headers = {
            'api-key': api_key,
            'Content-Type': 'application/json'
        }

        response = requests.get(url, headers=headers)

        # Check if the subscription check was successful
        if response.status_code == 200:
            logging.info("Azure subscription is active and available.")
            return True
        else:
            logging.error(f"Failed to verify Azure subscription: {response.status_code} - {response.reason}")
            return False

    except requests.RequestException as e:
        logging.error(f"An error occurred while checking Azure subscription: {e}")
        return False

# Initialize AzureOpenAI client using environment variables
try:
    api_key = get_env_variable('AZURE_API_KEY')
    api_version = get_env_variable('AZURE_API_VERSION')
    azure_endpoint = get_env_variable('AZURE_ENDPOINT')

    # Check Azure subscription availability using the values from the .env file
    if not check_azure_subscription(api_key, azure_endpoint, api_version):
        raise EnvironmentError("Azure subscription is unavailable. Please verify your subscription status.")
    
    client = AzureOpenAI(
        api_key=api_key,
        api_version=api_version,
        azure_endpoint=azure_endpoint
    )
    logging.info("AzureOpenAI client initialized successfully.")
except EnvironmentError as e:
    logging.critical(f"Failed to initialize AzureOpenAI client: {e}")
    raise

# Define directories
source_directory = os.path.dirname(env_path)
green_code_directory = os.path.join(source_directory, 'GreenCode')
temp_directory = os.path.join(green_code_directory, 'temp')
test_file_directory = os.path.join(source_directory, 'TestCases')

# Store file extensions in a variable
file_extensions = ['.py', '.java', '.xml', '.php', '.cpp', '.html', '.css', '.ts', '.rb']

# Function to delete a directory and its contents
def remove_directory(directory):
    if os.path.exists(directory):
        shutil.rmtree(directory)
        logging.info(f"Directory '{directory}' deleted successfully!")

# Directory creation logic: Delete existing 'GreenCode' directory if it exists, then create a fresh one
remove_directory(green_code_directory)
os.makedirs(green_code_directory)
logging.info(f"Directory '{green_code_directory}' created successfully!")

# Ensure temp and test_file directories exist
def ensure_directory_structure(path):
    if not os.path.exists(path):
        os.makedirs(path)
        logging.info(f"Folder '{path}' created.")
ensure_directory_structure(temp_directory)
ensure_directory_structure(test_file_directory)

unique_name = f"GreenCodeRefiner {uuid.uuid4()}"

# Create an assistant
try:
    assistant = client.beta.assistants.create(
        name=unique_name,
        instructions=(
            "You are a helpful AI assistant who refactors the code from an uploaded file to make it more efficient. "
            "1. Re-write the code in the same language as the original code. "
            "2. Test the re-written code and ensure it functions correctly and the same as the original code. "
            "3. Run the code to confirm that it runs successfully. "
            "4. If the code runs successfully, share the code as a file that can be downloaded. "
            "5. If the code is unsuccessful, display the error message and try to revise the code and rerun."
        ),
        model="gpt-4o-mini",
        tools=[{"type": "code_interpreter"}]
    )
    logging.info(f"Assistant '{unique_name}' created successfully.")
except Exception as e:
    logging.critical(f"Failed to create Azure OpenAI assistant: {e}")
    raise

# List of files to exclude from processing
excluded_files = {
    'GreenCodeRefiner.py',
    'compare_emissions.py',
    'server_emissions.py',
    'track_emissions.py'
}

# Function to find files in the source directory
def identify_source_files(directory, extensions, excluded_files):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file in excluded_files:
                continue
            if file.endswith(tuple(extensions)):
                yield os.path.join(root, file)

# Function to load prompts from the .env file
def load_prompts_from_env():
    prompts = []
    for key in os.environ:
        if key.startswith("PROMPT_"):
            # Split the prompt and its flag
            prompt_data = os.getenv(key).split(", ")
            if len(prompt_data) == 2 and prompt_data[1].lower() == "y":
                prompts.append(prompt_data[0])
            else:
                logging.warning(f"Skipping prompt '{key}' due to missing or incorrect flag.")
    return prompts

# Function to create unit test files for source files without a test file
def create_unit_test_files(file_list):
    prompt_testcase = get_env_variable('PROMPT_GENERATE_TESTCASES', is_required=False)
    if prompt_testcase:
        prompt, toggle = prompt_testcase.rsplit(',', 1)
        toggle = toggle.strip().lower()
    else:
        logging.warning("Unit test case prompt not found in .env.")
        return
    if toggle != 'y':
        logging.info("Skipping unit test generation as per .env configuration.")
        return
    for file_path in file_list:
        file_name = os.path.basename(file_path)
        base_name, ext = os.path.splitext(file_name)
        if 'test' in base_name.lower():
            logging.info(f"Skipping test file: {file_path}")
            continue
        test_file_name = f"{base_name}Test{ext}"
        test_file_path = os.path.join(test_file_directory, test_file_name)
        if os.path.exists(test_file_path):
            logging.info(f"Test file already exists: {test_file_path}")
            continue
        prompt = prompt_testcase.format(file_extension=ext, file_name=file_name)
        with open(file_path, "rb") as file:
            try:
                uploaded_file = client.files.create(file=file, purpose='assistants')
                logging.info(f"File uploaded for unit test creation: {file_name}")
            except Exception as e:
                logging.error(f"Error uploading file {file_name} for unit test: {e}")
                continue

        logging.info(f"Creating unit test file for: {file_name}")
        thread = client.beta.threads.create(
            messages=[{"role": "user", "content": prompt, "file_ids": [uploaded_file.id]}]
        )
        run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant.id)
        
        start_time = time.time()
        while True:
            run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id).status
            logging.info(f"Unit test creation status for {file_name}: {run_status}")
            if run_status == 'completed':
                break
            elif time.time() - start_time > 1200:
                logging.warning(f"Unit test creation timed out for file: {file_name}")
                return
            else:
                time.sleep(5)

        # Handle the retrieved data for the test case creation...
        logging.info(f"Unit test file created successfully for {file_name}")


        messages = client.beta.threads.messages.list(thread_id=thread.id)
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


def apply_green_prompts(file_id, prompt, refined_file_path):
    logging.info(f"Applying prompt: {prompt} to file {file_id}")
    try:
        thread = client.beta.threads.create(
            messages=[{"role": "user", "content": prompt, "file_ids": [file_id]}]
        )
        run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant.id)

        start_time = time.time()
        while True:
            run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id).status
            logging.info(f"Processing status for file {file_id}: {run_status}")
            if run_status == 'completed':
                break
            elif time.time() - start_time > 1200:
                logging.warning(f"Processing timed out for file: {file_id}")
                return False
            else:
                time.sleep(5)

        messages = client.beta.threads.messages.list(thread_id=thread.id)
        data = json.loads(messages.model_dump_json(indent=2))

        # Log the entire API response for debugging
        logging.info(f"API response for file {file_id}: {json.dumps(data, indent=2)}")

        code = None
        if data['data'] and data['data'][0]['content'] and data['data'][0]['content'][0]['text']['annotations']:
            code = data['data'][0]['content'][0]['text']['annotations'][0]['file_path']['file_id']

        if code:
            try:
                content = client.files.content(code)
                content.write_to_file(refined_file_path)
                logging.info(f"File refined successfully with prompt: {prompt}")
                return True
            except Exception as e:
                logging.error(f"Error writing refined file for prompt {prompt}: {e}")
                return False
        else:
            logging.error(f"No code found or annotations list is empty for prompt: {prompt} and file {file_id}. Possible file-specific issue or API response problem.")
            return False

    except Exception as e:
        logging.error(f"Exception occurred while applying prompt '{prompt}' to file {file_id}: {e}")
        return False

# # Applying green prompts
# def apply_green_prompts(file_id, prompt, refined_file_path):
#     logging.info(f"Applying prompt: {prompt} to file {file_id}")
#     thread = client.beta.threads.create(
#         messages=[{"role": "user", "content": prompt, "file_ids": [file_id]}]
#     )
#     run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant.id)

#     start_time = time.time()
#     while True:
#         run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id).status
#         logging.info(f"Processing status for file {file_id}: {run_status}")
#         if run_status == 'completed':
#             break
#         elif time.time() - start_time > 1200:
#             logging.warning(f"Processing timed out for file: {file_id}")
#             return False
#         else:
#             time.sleep(5)

#     messages = client.beta.threads.messages.list(thread_id=thread.id)
#     data = json.loads(messages.model_dump_json(indent=2))
#     code = None
#     if data['data'] and data['data'][0]['content'] and data['data'][0]['content'][0]['text']['annotations']:
#         code = data['data'][0]['content'][0]['text']['annotations'][0]['file_path']['file_id']
    
#     if code:
#         try:
#             content = client.files.content(code)
#             content.write_to_file(refined_file_path)
#             logging.info(f"File refined successfully with prompt: {prompt}")
#             return True
#         except Exception as e:
#             logging.error(f"Error writing refined file for prompt {prompt}: {e}")
#             return False
#     else:
#         logging.warning(f"No code found or annotations list is empty for prompt: {prompt}")
#         return False
    
# Function to load prompts from the .env file
def load_prompts_from_env():
    prompts = []
    for key in os.environ:
        if key.startswith("PROMPT_"):
            # Split the prompt and its flag
            prompt_data = os.getenv(key).split(", ")
            if len(prompt_data) == 2 and prompt_data[1].lower() == "y":
                prompts.append(prompt_data[0])
    return prompts

# Load prompts with "Yes" authentication
prompts = load_prompts_from_env()

# Define the list to store files
file_list = list(identify_source_files(source_directory, file_extensions, excluded_files))

# Step 1: Create unit test files for all source files without test files
create_unit_test_files(file_list)

# Re-scan the source directory to include newly created test files
file_list = list(identify_source_files(source_directory, file_extensions, excluded_files))

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
        uploaded_file = client.files.create(file=file, purpose='assistants')
    refined_temp_file_path = os.path.join(temp_directory, file_name)
    ensure_directory_structure(os.path.dirname(refined_temp_file_path))
    refined_success = False

    # Apply only the prompts marked as "Yes"
    for prompt in prompts:
        refined_success = apply_green_prompts(uploaded_file.id, prompt, refined_temp_file_path)

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
