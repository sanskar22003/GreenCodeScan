import os
import json
import dotenv
import time
from dotenv import load_dotenv
from openai import AzureOpenAI

# Load environment variables
load_dotenv(dotenv_path=".env", verbose=True, override=True)

# Initialize the AzureOpenAI client
client = AzureOpenAI(
    api_key="eadf76dd169e4172a463e7375946835f",
    api_version="2024-02-15-preview",
    azure_endpoint="https://green-code-uks.openai.azure.com"
)

# Create an assistant
assistant = client.beta.assistants.create(
    name='Green IT Code Writer 6',
    instructions=("You are a helpful AI assistant who re-factors the code from an uploaded file to make it more efficient"
                  "You have access to a sandboxed environment for writing and testing code."
                  "1. Re-write the code in the same language as the original code."
                  "2. Test the re-written code and ensure it functions correctly and same as the original code."
                  "3. Run the code to confirm that it runs successfully"
                  "4. If the code runs successfully, share the code as a file that can be downloaded"
                  "5. If the code is unsuccessful display the error message and try to revise the code and rerun going through the steps from above again."),
    model="code",
    tools=[{"type": "code_interpreter"}]
)

# Create a thread
thread = client.beta.threads.create()
print(f"Thread created: {thread.id}")

# Directory where the files are stored
directory = 'C:\\ProgramData\\Jenkins\\.jenkins\\workspace\\GreenCodeScanPipeline'
download_directory = "D:\\Documents\\TechM\\Green_Software_Development\\Third Task\\Projects & Docs\\Assistant api\\Refined Files"

# List to keep track of the uploaded FileObjects
uploaded_file_objects = []

# Upload all .py and .java files
for filename in os.listdir(directory):
    if filename.endswith('.py') or filename.endswith('.java'):
        file_path = os.path.join(directory, filename)
        with open(file_path, "rb") as f:
            uploaded_file_object = client.files.create(file=f, purpose='assistants')
            uploaded_file_objects.append(uploaded_file_object)
            print(f"Uploaded file: {file_path}")

# Apply prompts to each uploaded file and download the refined file
prompts = ["Make the code energy efficient", "Provide a version of this function that is optimized for energy efficiency", "Optimize this code to use less CPU resources"]
for uploaded_file_object in uploaded_file_objects:
    for prompt in prompts:
        thread = client.beta.threads.create(messages=[{"role": "user", "content": prompt, "file_ids": [uploaded_file_object.id]}])
        run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant.id)
        status = 'pending'
        while status != 'completed':
            time.sleep(5)  # Wait for 5 seconds before checking the status again
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            status = run.status
        print(f"Run completed for file: {uploaded_file_object.filename}")

        # Assuming the refined code is available in the thread messages, download it
        # This part needs to be adjusted based on how the refined code is shared in the thread
        # For demonstration, using the original file content
        original_filename = os.path.basename(uploaded_file_object.filename)
        new_filename = "refined_" + original_filename
        with open(os.path.join(download_directory, new_filename), 'wb') as f:
            f.write(b"Refined code here")  # Replace with actual refined code content
        print(f"Downloaded refined file: {new_filename}")
