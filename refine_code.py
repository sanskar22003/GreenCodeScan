import os
import json
import time
import dotenv
from dotenv import load_dotenv
from openai import AzureOpenAI

# Load environment variables
load_dotenv(dotenv_path=".env", verbose=True, override=True)

# Azure OpenAI client setup
client = AzureOpenAI(
    api_key="eadf76dd169e4172a463e7375946835f",
    api_version="2024-02-15-preview",
    azure_endpoint="https://green-code-uks.openai.azure.com"
)

# Create an assistant
assistant = client.beta.assistants.create(
    name='Green IT Code Writer 6',
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

# Create a thread
thread = client.beta.threads.create()
print(thread)

source_directory = 'C:\\ProgramData\\Jenkins\\.jenkins\\workspace\\GreenCodeScanPipeline'
download_directory = "D:\\Documents\\TechM\\Green_Software_Development\\Third Task\\Projects & Docs\\Assistant api\\Refined Files"

# Track processed files
processed_files_log = os.path.join(download_directory, "processed_files.log")
if not os.path.exists(processed_files_log):
    with open(processed_files_log, 'w') as f:
        pass  # Create an empty log file if it doesn't exist

# Read the list of already processed files
with open(processed_files_log, 'r') as f:
    processed_files = f.read().splitlines()

# Modify the part of the code for dynamic file upload
for filename in os.listdir(source_directory):
    if filename.endswith(".py") or filename.endswith(".java") and filename not in processed_files:  # Check if file is not processed
        file_path = os.path.join(source_directory, filename)
        with open(file_path, "rb") as file:
            uploaded_file = client.files.create(
                file=file,
                purpose='assistants'
            )

            # Pass a message to thread for each file
            thread = client.beta.threads.create(
                messages=[
                    {
                        "role": "user",
                        "content": "Make the code energy efficient",
                        "file_ids": [uploaded_file.id]
                    }
                ]
            )

            # Mark file as processed
            with open(processed_files_log, 'a') as f:
                f.write(filename + '\n')

# Check messages in the thread
thread_messages = client.beta.threads.messages.list(thread.id)
print(thread_messages.model_dump_json(indent=2))

# Optional code execution
run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id=assistant.id
)

# Wait for the run to complete
while True:
    run_status = client.beta.threads.runs.retrieve(
        thread_id=thread.id,
        run_id=run.id
    )
    if run_status.status == 'completed':
        break
    time.sleep(5)  # Wait for 5 seconds before checking again

# Print messages in the thread post run
messages = client.beta.threads.messages.list(
    thread_id=thread.id
)
print(messages.model_dump_json(indent=2))

# Cleanup
client.beta.assistants.delete(assistant.id)
client.beta.threads.delete(thread.id)

# Check if all files have been refined
source_files = {file for file in os.listdir(source_directory) if file.endswith(('.py', '.java'))}
refined_files = {file for file in os.listdir(download_directory) if file.endswith(('.py', '.java'))}

if source_files.issubset(refined_files):
    print('done')
else:
    print('pending')
