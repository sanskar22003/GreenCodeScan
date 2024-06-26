import os
import json
import dotenv
import time
from dotenv import load_dotenv
from openai import AzureOpenAI

# Paths
source_directory = 'C:\\ProgramData\\Jenkins\\.jenkins\\workspace\\GreenCodeScanPipeline'
download_directory = "D:\\Documents\\TechM\\Green_Software_Development\\Third Task\\Projects & Docs\\Assistant api\\Refined Files"
log_file_path = "processed_files.log"

# Load environment variables
load_dotenv(dotenv_path=".env", verbose=True, override=True)

# Initialize AzureOpenAI client
client = AzureOpenAI(
    api_key="eadf76dd169e4172a463e7375946835f",
    api_version="2024-02-15-preview",
    azure_endpoint="https://green-code-uks.openai.azure.com"
)

# Function to check if file is already processed
def is_file_processed(filename):
    if os.path.exists(log_file_path):
        with open(log_file_path, 'r') as log_file:
            processed_files = log_file.read().splitlines()
            return filename in processed_files
    return False

# Function to log processed file
def log_processed_file(filename):
    with open(log_file_path, 'a') as log_file:
        log_file.write(filename + '\n')

# Function to process file
def process_file(filepath):
    # Create an assistant
    assistant = client.beta.assistants.create(
        name='Green IT Code Writer 2',
        instructions="You are a helpful AI assistant who re-factors the code from an uploaded file to make it more efficient"
                     "You have access to a sandboxed environment for writing and testing code."
                     "You should follow these steps:"
                     "1. Re-write the code in the same language as the original code."
                     "2. Test the re-written code and ensure it functions correctly and same as the original code."
                     "3. Run the code to confirm that it runs successfully"
                     "4. If the code runs successfully, share the code as a file that can be downloaded"
                     "5. If the code is unsuccessful display the error message and try to revise the code and rerun going through the steps from above again.",
        model="code",
        tools=[{"type": "code_interpreter"}]
    )

    # Upload a reference file
    with open(filepath, "rb") as file:
        uploaded_file = client.files.create(
            file=file,
            purpose='assistants'
        )

    # Create a thread and pass a message
    thread = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": "Make the code energy efficient",
                "file_ids": [uploaded_file.id]
            }
        ]
    )

    # Wait for the run to complete
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id
    )

    while True:
        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        ).status
        if run_status == 'completed':
            break
        else:
            time.sleep(5)

    # Download the refined file
    messages = client.beta.threads.messages.list(
        thread_id=thread.id
    )
    data = json.loads(messages.model_dump_json(indent=2))
    code = data['data'][0]['content'][0]['text']['annotations'][0]['file_path']['file_id']
    content = client.files.content(code)
    download_path = os.path.join(download_directory, os.path.basename(filepath))
    content.write_to_file(download_path)

    # Log the processed file
    log_processed_file(os.path.basename(filepath))

# Main script
for filename in os.listdir(source_directory):
    filepath = os.path.join(source_directory, filename)
    if filename.endswith(('.py', '.java')) and not is_file_processed(filename):
        process_file(filepath)

# Check if all Python and Java files are refined
source_files = {f for f in os.listdir(source_directory) if f.endswith(('.py', '.java'))}
downloaded_files = {f for f in os.listdir(download_directory) if f.endswith(('.py', '.java'))}
if source_files.issubset(downloaded_files):
    print('done')
else:
    print('pending')
