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

# Check if the download directory exists, if not, create it
if not os.path.exists(download_directory):
    os.makedirs(download_directory)
    print(f"Folder '{download_directory}' created.")
    
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

def process_and_upload_files(source_directory):
    for root, dirs, files in os.walk(source_directory):
        for file_name in files:
            if file_name.endswith('.py') or file_name.endswith('.java'):
                full_file_path = os.path.join(root, file_name)  # Full path to the file
                relative_file_path = os.path.relpath(full_file_path, start=source_directory)  # Relative path from the source directory

                if relative_file_path in uploaded_files:
                    print(f"{relative_file_path} has already been uploaded. Skipping.")
                    continue  # Skip this file and move to the next one

                with open(full_file_path, "rb") as file:
                    uploaded_file = client.files.create(
                        file=file,
                        purpose='assistants'
                    )
                # Write uploaded file name to log file and add to the set
                with open(log_file_path, 'a') as log_file:
                    log_file.write(f"{relative_file_path}\n")
                uploaded_files.add(relative_file_path)

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
                # No break here, continue processing other files

# Call the function to process and upload 
file_processed = process_and_upload_files(source_directory)

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
