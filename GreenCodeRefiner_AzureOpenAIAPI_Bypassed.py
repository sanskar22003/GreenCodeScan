import os
import json
import dotenv
import uuid
import time
import shutil
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.abspath(".env")
load_dotenv(dotenv_path=env_path, verbose=True, override=True)

# Define directories
source_directory = os.path.dirname(env_path)
green_code_directory = os.path.join(source_directory, 'GreenCode')
temp_directory = os.path.join(green_code_directory, 'temp')
test_file_directory = os.path.join(source_directory, 'TestCases')  # Rename

# Store file extensions in a variable
file_extensions = ['.py', '.java', '.xml', '.php', '.cpp', '.html', '.css', '.ts', '.rb']

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

# Mocking unique name creation
unique_name = f"GreenCodeRefiner {uuid.uuid4()}"

# List of files to exclude from processing
excluded_files = {
    'GreenCodeRefiner.py',
    'compare_emissions.py',
    'server_emissions.py',
    'track_emissions.py'
}

# Function to find files in the source directory
def Identify_SourceFiles(directory, extensions, excluded_files):
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

        # Simulate test file creation
        test_file_name = ext
        test_file_path = os.path.join(test_file_directory, test_file_name)

        if os.path.exists(test_file_path):
            print(f"Test file already exists: {test_file_path}")
            continue

        print(f"Creating mock unit test file for: {file_name}")
        with open(test_file_path, 'w') as test_file:
            test_file.write(f"# This is a mock test file for {file_name}")
        print(f"Unit test file created: {test_file_path}")

# Mock function to simulate applying prompts to files
def Apply_GreenPrompts(file_id, prompt, refined_file_path):
    print(f"Mock applying prompt: {prompt} to {file_id}")
    time.sleep(1)  # Simulate time taken to process the file
    with open(refined_file_path, 'w') as refined_file:
        refined_file.write(f"# Mock refined code for file_id: {file_id} with prompt: {prompt}")
    return True

# Define the list to store files
file_list = list(Identify_SourceFiles(source_directory, file_extensions, excluded_files))

# Step 1: Create unit test files for all source files without test files
create_unit_test_files(file_list)

# Re-scan the source directory to include newly created test files
file_list = list(Identify_SourceFiles(source_directory, file_extensions, excluded_files))

# Define the prompts for refining the code
prompts = [
    "Make the code more energy efficient",
    "Eliminate any redundant or dead code", 
    "Simplify complex algorithms to reduce computational load",
    "Optimize memory usage in the code",
    "Reduce the number of dependencies",
    "Refactor the code to reduce complexity",
    "Test the code for edge cases"
]

# Function to get user confirmation
def get_user_confirmation(message):
    while True:
        user_input = input(message + " (yes/no): ").lower().strip()
        if user_input == 'yes':
            return True
        elif user_input == 'no':
            return False
        else:
            print("Invalid input. Please enter 'yes' or 'no'.")

# Upload and refine files with user interaction (Mocked)
while file_list:
    file_path = file_list.pop(0)
    relative_path = os.path.relpath(file_path, source_directory)
    file_name = os.path.basename(file_path)

    # Ask user permission to process the current file
    if not get_user_confirmation(f"Do you want to process the file: {file_name}?"):
        print(f"Skipping file: {file_name}")
        continue

    # Skip excluded files and the green_code_directory and its subdirectories
    if file_name in excluded_files or relative_path.startswith(os.path.relpath(green_code_directory, source_directory)):
        print(f"Skipping excluded file or directory: {relative_path}")
        continue

    # Check if the file is empty
    if os.path.getsize(file_path) == 0:
        print(f"Skipping empty file: {file_path}")
        continue

    # Mock the upload file part (simulate file processing)
    uploaded_file_id = f"mock_{uuid.uuid4()}"
    refined_temp_file_path = os.path.join(temp_directory, file_name)
    ensure_directory_structure(os.path.dirname(refined_temp_file_path))

    refined_success = False

    # Apply prompts with user interaction
    for prompt in prompts:
        if get_user_confirmation(f"Do you want to apply the prompt: '{prompt}' to the file: {file_name}?"):
            refined_success = Apply_GreenPrompts(uploaded_file_id, prompt, refined_temp_file_path)

            # If the file is refined successfully with the current prompt, continue with the next prompt
            if refined_success:
                print(f"Successfully applied prompt: '{prompt}' to {file_name}")
            else:
                print(f"Failed to apply prompt: '{prompt}' to {file_name}")
        else:
            print(f"Skipping prompt: '{prompt}' for file: {file_name}")

    # Move the refined file after all prompts have been applied
    if refined_success:
        final_file_path = os.path.join(green_code_directory, relative_path)
        ensure_directory_structure(os.path.dirname(final_file_path))
        os.rename(refined_temp_file_path, final_file_path)
        print(f"File refined and moved: {final_file_path}")
    else:
        print(f"Failed to refine file: {file_path}")
