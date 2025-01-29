import os
import json
import shutil
import logging
import time
import requests
from dotenv import load_dotenv

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

def handle_remove_error(func, path, exc_info):
    """Custom error handler for shutil.rmtree."""
    logging.error(f"Error removing {path}: {exc_info[1]}")

def remove_directory(directory):
    """Remove a directory and handle errors."""
    if os.path.exists(directory):
        try:
            shutil.rmtree(directory, onerror=handle_remove_error)
            logging.info(f"Directory '{directory}' deleted successfully!")
        except Exception as e:
            logging.error(f"An unexpected error occurred while removing directory '{directory}': {e}")
    else:
        logging.warning(f"Directory '{directory}' does not exist, skipping deletion.")

def _handle_remove_error(func, path, exc_info):
    """
    Custom error handler for shutil.rmtree.
    Logs the error and continues with the removal process.
    """
    if func in (os.unlink, os.remove):
        logging.warning(f"Failed to remove file '{path}': {exc_info[1]}")
    elif func in (os.rmdir, os.removedirs):
        logging.warning(f"Failed to remove directory '{path}': {exc_info[1]}")
    else:
        logging.error(f"Unexpected error while removing '{path}': {exc_info[1]}")

def ensure_directory_structure(path):
    """Ensure that the directory structure exists."""
    try:
        if os.path.exists(path):
            if os.path.isdir(path):
                logging.info(f"Directory '{path}' already exists. Skipping creation.")
            else:
                logging.warning(f"'{path}' exists but is not a directory. Attempting to remove and recreate.")
                os.remove(path)
                os.makedirs(path)
                logging.info(f"Directory '{path}' created successfully after removing the conflicting file.")
        else:
            os.makedirs(path)
            logging.info(f"Directory '{path}' created successfully.")
    except FileExistsError:
        logging.warning(f"Directory '{path}' already exists. This error was safely handled.")
    except Exception as e:
        logging.error(f"An unexpected error occurred while ensuring directory '{path}': {e}")


def identify_source_files(directory, extensions, excluded_files):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file in excluded_files:
                continue
            if file.endswith(tuple(extensions)):
                yield os.path.join(root, file)

def load_prompts_from_env():
    prompts = []
    for key in os.environ:
        if key.startswith("PROMPT_"):
            # Split the prompt and its flag
            prompt_data = os.getenv(key).split(", ")
            if len(prompt_data) == 2 and prompt_data[1].lower() == "y":
                prompts.append(prompt_data[0])
            else:
                logging.warning(f"Skipping prompt '{key}' as per .env configuration.")
    return prompts

# Define base directories
env_path = os.path.abspath(".env")
load_dotenv(dotenv_path=env_path, verbose=True, override=True)
BASE_DIR = os.path.dirname(env_path)
RESULT_DIR = os.path.join(BASE_DIR, 'Result')

def ensure_result_directory():
    """Ensure the Result directory exists."""
    if not os.path.exists(RESULT_DIR):
        try:
            os.makedirs(RESULT_DIR)
            logging.info(f"Created Result directory at: {RESULT_DIR}")
        except Exception as e:
            logging.error(f"Failed to create Result directory: {e}")
            raise

def ensure_csv_exists():
    """Ensure the CSV file exists and has the correct headers."""
    ensure_result_directory()  # Make sure the Result directory exists
    csv_path = os.path.join(RESULT_DIR, 'modification_overview.csv')
    
    if not os.path.exists(csv_path):
        try:
            with open(csv_path, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=['File Name', 'Modification Timestamp', 'Changes', 'Next Steps'])
                writer.writeheader()
            logging.info(f"Created modification_overview.csv at: {csv_path}")
        except Exception as e:
            logging.error(f"Failed to create CSV file: {e}")
            raise

def extract_section(content, start_marker, end_marker):
    """Extract content between specific markers."""
    try:
        start_idx = content.find(start_marker)
        if start_idx == -1:
            return None
        
        start_idx += len(start_marker)
        end_idx = content.find(end_marker, start_idx)
        
        if end_idx == -1:
            # If no end marker, take till the end
            section = content[start_idx:].strip()
        else:
            section = content[start_idx:end_idx].strip()
        
        # Extract the first meaningful line if multiple lines exist
        lines = [line.strip('- *•').strip() for line in section.split('\n') 
                 if line.strip('- *•').strip() and 
                 not any(marker in line.lower() for marker in ['here is', 'summary', 'changes made'])]
        
        return lines[0] if lines else None
    except Exception as e:
        logging.warning(f"Error extracting section: {e}")
        return None

def log_modifications(file_name, changes, next_steps):
    """Log modifications to the CSV file."""
    csv_path = os.path.join(RESULT_DIR, 'modification_overview.csv')
    ensure_csv_exists()
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        with open(csv_path, 'a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=['File Name', 'Modification Timestamp', 'Changes', 'Next Steps'])
            writer.writerow({
                'File Name': file_name,
                'Modification Timestamp': timestamp,
                'Changes': changes,
                'Next Steps': next_steps
            })
        logging.info(f"Logged modifications for file: {file_name}")
    except Exception as e:
        logging.error(f"Failed to log modifications: {e}")

def extract_changes_summary(data):
    """Extract changes summary from the assistant's response."""
    try:
        if not data['data'] or not data['data'][0]['content']:
            return None, None
            
        content = data['data'][0]['content'][0]['text']['value']
        
        # Extract changes
        changes = extract_section(content, 'CHANGES_START', 'CHANGES_END')
        
        # Extract next steps
        next_steps = extract_section(content, 'NEXT_STEPS_START', 'NEXT_STEPS_END')
        
        return (changes or "No specific changes provided", 
                next_steps or "No specific next steps identified")
        
    except Exception as e:
        logging.warning(f"Error extracting changes summary: {e}")
        return "Error extracting changes", "Error identifying next steps"

def create_unit_test_files(client, assistant, file_list, test_file_directory):
    prompt_testcase = get_env_variable('PROMPT_GENERATE_TESTCASES', is_required=False)
    if not prompt_testcase or ", " not in prompt_testcase:
        logging.warning("Unit test case prompt not found or incorrectly formatted in .env.")
        return
    
    prompt, toggle = prompt_testcase.rsplit(", ", 1)
    if toggle.strip().lower() != 'y':
        logging.info("Skipping unit test generation as per .env configuration.")
        return

    for file_path in file_list:
        file_name = os.path.basename(file_path)
        base_name, ext = os.path.splitext(file_name)
        
        if 'test' in base_name.lower():
            logging.info(f"Skipping test file: {file_path}")
            continue

            # -----------------modefied code-----------------

        # Get the relative path of the file from the source directory
        relative_path = os.path.relpath(file_path, BASE_DIR)       #added
            
        # test_file_name = f"{base_name}Test{ext}"
        # test_file_path = os.path.join(test_file_directory, test_file_name)

        # Construct the test file path preserving the directory structure
        test_file_name = f"{base_name}Test{ext}"    #replaced
        test_file_path = os.path.join(test_file_directory, os.path.dirname(relative_path), test_file_name) #replaced
        
        # Ensure the directory structure exists in the test directory
        ensure_directory_structure(os.path.dirname(test_file_path)) #added

            #-------------------------------------------------

        if os.path.exists(test_file_path):
            logging.info(f"Test file already exists: {test_file_path}")
            continue

        try:
            with open(file_path, "rb") as file:
                uploaded_file = client.files.create(file=file, purpose='assistants')
                logging.info(f"File uploaded for unit test creation: {file_name}")

            prompt_formatted = prompt.format(file_extension=ext, file_name=file_name)
            thread = client.beta.threads.create(
                messages=[{"role": "user", "content": prompt_formatted, "file_ids": [uploaded_file.id]}]
            )
            run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant.id)

            # Wait for completion
            start_time = time.time()
            while True:
                run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id).status
                if run_status == 'completed':
                    break
                elif time.time() - start_time > 1200:
                    logging.warning(f"Unit test creation timed out for file: {file_name}")
                    break
                time.sleep(5)

            messages = client.beta.threads.messages.list(thread_id=thread.id)
            data = json.loads(messages.model_dump_json(indent=2))
            
            # Extract code and changes summary
            code = None
            if data['data'] and data['data'][0]['content'] and data['data'][0]['content'][0]['text']['annotations']:
                code = data['data'][0]['content'][0]['text']['annotations'][0]['file_path']['file_id']

            if code:
                content = client.files.content(code)
                content.write_to_file(test_file_path)
                
                # Log modifications to the central CSV file
                changes_summary, next_steps = extract_changes_summary(data)
                log_modifications(test_file_name, changes_summary, next_steps)
                
                logging.info(f"Unit test file created: {test_file_path}")

            else:
                logging.error(f"Failed to create unit test for file: {file_path}")

        except Exception as e:
            logging.error(f"Error processing file {file_name} for unit test: {e}")

def apply_green_prompts(client, assistant, file_id, prompt, refined_file_path):
    logging.info(f"Applying prompt: {prompt} to file {file_id}")
    try:
        thread = client.beta.threads.create(
            messages=[{"role": "user", "content": prompt, "file_ids": [file_id]}]
        )
        run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant.id)

        start_time = time.time()
        while True:
            run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id).status
            if run_status == 'completed':
                break
            elif time.time() - start_time > 1200:
                logging.warning(f"Processing timed out for file: {file_id}")
                return False
            time.sleep(5)

        messages = client.beta.threads.messages.list(thread_id=thread.id)
        data = json.loads(messages.model_dump_json(indent=2))

        code = None
        if data['data'] and data['data'][0]['content'] and data['data'][0]['content'][0]['text']['annotations']:
            code = data['data'][0]['content'][0]['text']['annotations'][0]['file_path']['file_id']

        if code:
            try:
                content = client.files.content(code)
                content.write_to_file(refined_file_path)
                
                # Log modifications to the central CSV file
                changes_summary, next_steps = extract_changes_summary(data)
                log_modifications(os.path.basename(refined_file_path), changes_summary, next_steps)
                
                logging.info(f"File refined successfully with prompt: {prompt}")
                return True
            except Exception as e:
                logging.error(f"Error writing refined file for prompt {prompt}: {e}")
                return False
        else:
            logging.error(f"No code found in response for prompt: {prompt} and file {file_id}")
            return False

    except Exception as e:
        logging.error(f"Exception occurred while applying prompt '{prompt}' to file {file_id}: {e}")
        return False
