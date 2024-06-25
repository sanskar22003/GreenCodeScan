import os
import json
import dotenv
from dotenv import load_dotenv
from openai import AzureOpenAI

# Load environment variables
load_dotenv(dotenv_path=".env", verbose=True, override=True)

# Initialize Azure OpenAI client
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

# Directory where the files are stored
directory = 'C:\\ProgramData\\Jenkins\\.jenkins\\workspace\\GreenCodeScanPipeline'

# Function to upload a single file
def upload_file(file_path):
    with open(file_path, "rb") as f:
        uploaded_file_object = client.files.create(
            file=f,
            purpose='assistants'
        )
    print(f"Uploaded file: {file_path}")
    return uploaded_file_object

# Function to apply prompts to the uploaded file
def apply_prompts(file_object):
    prompts = ["Make the code energy efficient", "Provide a version of this function that is optimized for energy efficiency", "Optimize this code to use less CPU resources"]
    for prompt in prompts:
        thread = client.beta.threads.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "file_ids": [file_object.id]
                }
            ]
        )

# Function to check and wait for run completion
def wait_for_completion(thread_id):
    run_status = "in_progress"
    while run_status != "completed":
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )
        run_status = run.status
        if run_status != "completed":
            time.sleep(5)  # Wait for 5 seconds before checking again

# Function to download the refined file
def download_refined_file(file_id, download_directory):
    content = client.files.content(file_id)
    file_path = os.path.join(download_directory, "refactored_fibonacci.py")
    content.write_to_file(file_path)
    print(f"Downloaded refined file to: {file_path}")

# Main function to process files
def process_files():
    for filename in os.listdir(directory):
        if filename.endswith('.py') or filename.endswith('.java'):
            file_path = os.path.join(directory, filename)
            uploaded_file_object = upload_file(file_path)
            apply_prompts(uploaded_file_object)
            wait_for_completion(thread.id)
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            data = json.loads(messages.model_dump_json(indent=2))
            code_file_id = data['data'][0]['content'][0]['text']['annotations'][0]['file_path']['file_id']
            download_directory = "D:\\Documents\\TechM\\Green_Software_Development\\Third Task\\Projects & Docs\\Assistant api\\Refined Files"
            download_refined_file(code_file_id, download_directory)
            break  # Process only one file per run

process_files()
