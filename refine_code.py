import os
import time
import dotenv
from dotenv import load_dotenv

# Assuming you have a way to interact with Azure OpenAI
from azure_openai_client import AzureOpenAI  # Placeholder for actual import

# Load environment variables
load_dotenv(dotenv_path=".env", verbose=True, override=True)

# Initialize Azure OpenAI client
client = AzureOpenAI(
    api_key="eadf76dd169e4172a463e7375946835f",  
    api_version="2024-02-15-preview",
    azure_endpoint = "https://green-code-uks.openai.azure.com"
)


# Directory where the files are stored and where to download the optimized code
source_directory = 'C:\\ProgramData\\Jenkins\\.jenkins\\workspace\\GreenCodeScanPipeline'
download_directory = "D:\\Documents\\TechM\\Green_Software_Development\\Third Task\\Projects & Docs\\Assistant api\\Refined Files"

def upload_and_optimize_file(file_path):
    # Upload the file
    with open(file_path, "rb") as f:
        uploaded_file_object = client.files.create(file=f, purpose='assistants')
    print(f"Uploaded file: {file_path}")

    # Create a thread with a prompt to optimize the code
    prompt = "Make the code energy efficient"
    thread = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
                "file_ids": [uploaded_file_object.id]
            }
        ]
    )

    # Wait for the thread to complete processing
    print(f"Processing thread: {thread.id}")
    thread_status = "in_progress"
    while thread_status != "completed":
        # This is a placeholder for how you might check the thread's status
        # You'll need to replace this with the actual method to check the thread's status
        thread_status = check_thread_status(thread.id)
        if thread_status != "completed":
            time.sleep(5)  # Wait for 5 seconds before checking again
    print("Processing completed.")

    # Download the optimized code
    # This assumes there's a way to get the optimized file ID from the thread
    optimized_file_id = get_optimized_file_id(thread.id)  # Placeholder for actual method
    optimized_content = client.files.content(optimized_file_id)
    optimized_file_path = os.path.join(download_directory, os.path.basename(file_path))
    with open(optimized_file_path, "wb") as f:
        f.write(optimized_content)
    print(f"Downloaded optimized file to: {optimized_file_path}")

def process_files(directory):
    for filename in os.listdir(directory):
        if filename.endswith('.py') or filename.endswith('.java'):
            file_path = os.path.join(directory, filename)
            upload_and_optimize_file(file_path)
            break  # Process only one file for simplicity

process_files(source_directory)
