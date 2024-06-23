import os
import json
import dotenv
from dotenv import load_dotenv
from openai import AzureOpenAI
import time

# Load environment variables
load_dotenv(dotenv_path=".env", verbose=True, override=True)

# Initialize AzureOpenAI client
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
                  "You should follow these steps:"
                  "1. Re-write the code in the same language as the original code."
                  "2. Test the re-written code and ensure it functions correctly and same as the original code."
                  "3. Run the code to confirm that it runs successfully"
                  "4. If the code runs successfully, share the code as a file that can be downloaded"
                  "5. If the code is unsuccessful display the error message and try to revise the code and rerun going through the steps from above again."),
    model="code",
    tools=[{"type": "code_interpreter"}]
)

# Directory where the files are stored
directory = 'C:\\ProgramData\\Jenkins\\.jenkins\\workspace\\GreenCodeScanPipeline'
download_directory = "D:\\Documents\\TechM\\Green_Software_Development\\Third Task\\Projects & Docs\\Assistant api\\Refined Files"

# List to keep track of the uploaded files
uploaded_files = []
uploaded_file_objects = []

# Iterate over each file in the directory
for filename in os.listdir(directory):
    if filename.endswith('.py') or filename.endswith('.java'):
        file_path = os.path.join(directory, filename)
        if file_path not in uploaded_files:
            with open(file_path, "rb") as f:
                uploaded_file_object = client.files.create(file=f, purpose='assistants')
            uploaded_files.append(file_path)
            uploaded_file_objects.append(uploaded_file_object)
            print(f"Uploaded file: {file_path}")

            # Apply prompts to the uploaded file
            prompts = ["I want you to convert this code that is more energy efficient"]
            for prompt in prompts:
                thread = client.beta.threads.create(messages=[{"role": "user", "content": prompt, "file_ids": [uploaded_file_object.id]}])
                run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant.id)
                
                # Wait for the run to complete
                status = ""
                while status != "completed":
                    time.sleep(5)  # Wait for 5 seconds before checking the status again
                    run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
                    status = run.status
                
                messages = client.beta.threads.messages.list(thread_id=thread.id)
                data = json.loads(messages.model_dump_json(indent=2))
                code_file_id = data['data'][0]['content'][0]['text']['annotations'][0]['file_path']['file_id']
                
                # Download the refined file
                content = client.files.content(code_file_id)
                refined_file_path = os.path.join(download_directory, filename)  # Use the same file name for the refined file
                content.write_to_file(refined_file_path)
                print(f"Refined file downloaded: {refined_file_path}")
