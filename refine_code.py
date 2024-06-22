import os
import json
import dotenv
from dotenv import load_dotenv
from openai import AzureOpenAI
import time

# Load environment variables
load_dotenv(dotenv_path=".env", verbose=True, override=True)

# Initialize the AzureOpenAI client
client = AzureOpenAI(
    api_key="eadf76dd169e4172a463e7375946835f",  
    api_version="2024-02-15-preview",
    azure_endpoint = "https://green-code-uks.openai.azure.com"
    )

# Create an assistant
assistant = client.beta.assistants.create(
  name='Green IT Code Writer 4',
  instructions=("You are a helpful AI assistant who re-factors the code from an uploaded file to make it more efficient "
                "You have access to a sandboxed environment for writing and testing code. "
                "1. Re-write the code in the same language as the original code. "
                "2. Test the re-written code and ensure it functions correctly and same as the original code. "
                "3. Run the code to confirm that it runs successfully "
                "4. If the code runs successfully, share the code as a file that can be downloaded "
                "5. If the code is unsuccessful display the error message and try to revise the code and rerun going through the steps from above again."),
  model="code",
  tools=[{"type": "code_interpreter"}]
)

directory = 'C:\\ProgramData\\Jenkins\\.jenkins\\workspace\\GreenCodeScanPipeline'
download_directory = "D:\\Documents\\TechM\\Green_Software_Development\\Third Task\\Projects & Docs\\Assistant api\\Refined Files"
prompts = ["Make the code energy efficient", "Provide a version of this function that is optimized for energy efficiency", "Optimize this code to use less CPU resources"]

for filename in os.listdir(directory):
    if filename.endswith('.py') or filename.endswith('.java'):
        file_path = os.path.join(directory, filename)
        with open(file_path, "rb") as f:
            # Upload the file
            uploaded_file = client.files.create(
                file=f,
                purpose='assistants'
            )
        print(f"Uploaded file: {file_path}")

        for prompt in prompts:
            # Create a thread for processing
            thread = client.beta.threads.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                        "file_ids": [uploaded_file.id]
                    }
                ]
            )

            # Start processing
            run = client.beta.threads.runs.create(
              thread_id=thread.id,
              assistant_id=assistant.id
            )

            # Wait for the run to complete
            while True:
                run = client.beta.threads.runs.retrieve(
                  thread_id=thread.id,
                  run_id=run.id
                )
                if run.status == 'completed':
                    break
                time.sleep(5)  # wait for 5 seconds before checking the status again

            # Retrieve the messages
            messages = client.beta.threads.messages.list(
              thread_id=thread.id
            )

            # Assuming the refined code is in the last message
            refined_code = messages[-1]['content']  # This line needs to be adjusted based on the actual structure of the response

            # Initialize a variable to hold the last message
            last_message_content = None

# Iterate over the messages to find the last one
            for message in messages:
    # Assuming 'message' is a dictionary and has a key 'content' that holds the code
    # Adjust the key access based on the actual structure of the message object
                last_message_content = message.content  # Adjust this line based on the actual structure

# Check if we have the last message's content
            if last_message_content is not None:
    # Save the refined code to a file
                original_filename = os.path.basename(file_path)
                new_filename = "refined_" + original_filename
                with open(os.path.join(download_directory, new_filename), 'w') as code_file:
                    code_file.write(last_message_content)
                print(f"Downloaded refined file: {new_filename}")
            else:
                print("No refined code found.")
