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
import ast
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Stream to stdout
    ]
)
# Define Base Directory
BASE_DIR = '/app/project'

# Load environment variables
env_path = '/app/.env'
load_dotenv(dotenv_path=env_path, verbose=True, override=True)

# Import functions from RefinerFunction.py
from RefinerFunction import (
    get_env_variable,
    check_azure_subscription,
    remove_directory,
    ensure_directory_structure,
    identify_source_files,
    load_prompts_from_env,
    create_unit_test_files,
    apply_green_prompts,
    MetricsTracker,
    finalize_processing
)

# Initialize AzureOpenAI client using environment variables
try:
    api_key = get_env_variable('AZURE_API_KEY')
    api_version = get_env_variable('AZURE_API_VERSION')
    azure_endpoint = get_env_variable('AZURE_ENDPOINT')
    
    # Check Azure subscription availability using the values from the .env file
    if not check_azure_subscription(api_key, azure_endpoint, api_version):
        raise EnvironmentError("Azure subscription is unavailable. Please verify your subscription status.")
    
    # Get the model from .env
    MODEL_NAME = os.getenv('AZURE_MODEL')
    # Parse EXCLUDED_FILES as a list, stripping any surrounding whitespace
    EXCLUDED_FILES = [file.strip() for file in os.getenv('EXCLUDED_FILES', '').split(',') if file.strip()]
    FILE_EXTENSIONS_ENV = os.getenv('FILE_EXTENSIONS')
    FILE_EXTENSIONS = ast.literal_eval(FILE_EXTENSIONS_ENV)
    
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
source_directory = BASE_DIR
green_code_directory = os.path.join(source_directory, 'GreenCode')
temp_directory = os.path.join(green_code_directory, 'temp')
test_file_directory = os.path.join(source_directory, 'SRC-TestSuite')
green_test_file_directory = os.path.join(green_code_directory, 'GreenCode-TestSuite')

# Create fresh directories
remove_directory(green_code_directory)
os.makedirs(green_code_directory, exist_ok=True)
logging.info(f"Directory '{green_code_directory}' created successfully!")

# Ensure all required directories exist
for directory in [temp_directory, test_file_directory, green_test_file_directory]:
    ensure_directory_structure(directory)

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
        model=MODEL_NAME,
        tools=[{"type": "code_interpreter"}]
    )
    logging.info(f"Assistant '{unique_name}' created successfully.")
except Exception as e:
    logging.critical(f"Failed to create Azure OpenAI assistant: {e}")
    raise

# Load prompts with "Yes" authentication
prompts = load_prompts_from_env()

metrics_tracker = MetricsTracker()
processing_start_time = time.time()

# # Limit the number of prompts to one by selecting the first 'y' prompt if available
# if not prompts:
#     logging.critical("No prompts marked as 'y' found in the environment variables. Exiting.")
#     raise EnvironmentError("No prompts marked as 'y' found in the environment variables.")

# selected_prompt = prompts[0]  # Select the first prompt
# logging.info(f"Selected prompt: '{selected_prompt}' to apply to all files.")

# Define the list to store files
file_list = list(identify_source_files(source_directory, FILE_EXTENSIONS, EXCLUDED_FILES))

# Limit the file list to only two files
file_list = file_list[:2]
logging.info(f"Processing {len(file_list)} files: {file_list}")

# Step 1: Create unit test files for the selected source files without test files
create_unit_test_files(client, assistant, file_list, test_file_directory)

# Re-scan the source directory to include newly created test files
file_list = list(identify_source_files(source_directory, FILE_EXTENSIONS, EXCLUDED_FILES))
file_list = file_list[:2]  # Ensure only two files are processed

# Upload and refine files
processed_files = 0  # Counter to track the number of processed files

for file_path in file_list:
    relative_path = os.path.relpath(file_path, source_directory)
    file_name = os.path.basename(file_path)
    
    # Skip excluded files and special directories
    if (file_name in EXCLUDED_FILES or 
        any(dir_name in relative_path for dir_name in ['GreenCode', 'SRC-TestSuite', 'GreenCode-TestSuite'])):
        logging.info(f"Skipping excluded file or directory: {relative_path}")
        continue
    
    # Check if the file is empty
    if os.path.getsize(file_path) == 0:
        logging.info(f"Skipping empty file: {file_path}")
        continue
    
    try:
        with open(file_path, "rb") as file:
            uploaded_file = client.files.create(file=file, purpose='assistants')
    except Exception as e:
        logging.error(f"Error uploading file {file_name}: {e}")
        continue
    
    refined_temp_file_path = os.path.join(temp_directory, file_name)
    ensure_directory_structure(os.path.dirname(refined_temp_file_path))
    
    # Apply the selected prompt
    refined_success = apply_green_prompts(client, assistant, uploaded_file.id, prompts, refined_temp_file_path)
    
    if refined_success:
        logging.info(f"Successfully applied prompt: '{prompts}' to {file_name}")
    else:
        shutil.copy2(file_path, refined_temp_file_path)
        logging.warning(f"Using original file as fallback for: {file_name}")
    
    # Move the file after prompt applied
    final_file_path = os.path.join(green_code_directory, relative_path)
    ensure_directory_structure(os.path.dirname(final_file_path))
    
    if os.path.exists(refined_temp_file_path):
        shutil.move(refined_temp_file_path, final_file_path)
        logging.info(f"File moved to final location: {final_file_path}")
    else:
        logging.error(f"Temp file not found: {refined_temp_file_path}")
        shutil.copy2(file_path, final_file_path)
        logging.warning(f"Copied original file as fallback to: {final_file_path}")
    
    processed_files += 1
    
    # If two files have been processed, break the loop
    if processed_files >= 4:
        break

# Generate final overview after all processing is complete
finalize_processing()

# Print the final message after processing
logging.info("Thank you for using the Green CodeRefiner Azure Marketplace Trial version. To expand the usage, subscribe to Azure Marketplace. You can check the output into the 'GreenCode' directory.")
