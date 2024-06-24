import os
import json
import dotenv
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

# Directory where the files are stored and to download the refined files
source_directory = 'C:\\ProgramData\\Jenkins\\.jenkins\\workspace\\GreenCodeScanPipeline'
download_directory = "D:\\Documents\\TechM\\Green_Software_Development\\Third Task\\Projects & Docs\\Assistant api\\Refined Files"

# Track processed files
processed_files = []

# Function to process a single file
def process_file():
    for filename in os.listdir(source_directory):
        if filename.endswith('.py') or filename.endswith('.java'):
            file_path = os.path.join(source_directory, filename)
            if file_path not in processed_files:
                with open(file_path, "rb") as f:
                    uploaded_file_object = client.files.create(file=f, purpose='assistants')
                print(f"Uploaded file: {file_path}")
                
                # Create a thread for the uploaded file
                thread = client.beta.threads.create()
                print(thread)
                
                # Apply prompts to the uploaded file
                prompts = ["Make the code energy efficient", "Provide a version of this function that is optimized for energy efficiency", "Optimize this code to use less CPU resources"]
                for prompt in prompts:
                    thread = client.beta.threads.create(
                        messages=[
                            {
                                "role": "user",
                                "content": prompt,
                                "file_ids": [uploaded_file_object.id]
                            }
                        ]
                    )
                
                # Wait for the process to complete and retrieve the status
                run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant.id)
                status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id).status
                print(status)
                
                # Extract the content and write to a new file
                messages = client.beta.threads.messages.list(thread_id=thread.id)
                data = json.loads(messages.model_dump_json(indent=2))
                code_file_id = data['data'][0]['content'][0]['text']['annotations'][0]['file_path']['file_id']
                content = client.files.content(code_file_id)
                content.write_to_file(os.path.join(download_directory, filename))
                
                processed_files.append(file_path)
                break  # Process one file at a time
    else:
        print("All files have been refined or no suitable files found.")

process_file()

# Check if there are more files to process
remaining_files = [f for f in os.listdir(source_directory) if f.endswith('.py') or f.endswith('.java')]
if set(remaining_files).issubset(set(processed_files)):
    print("All files are refined.")
else:
    print("Files are pending.")
