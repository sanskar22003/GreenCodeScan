import os
import sys
import json
import time
import dotenv
from dotenv import load_dotenv
from openai import AzureOpenAI
import logging

# Setup logging
logging.basicConfig(filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

try:
    # Load environment variables
    load_dotenv(dotenv_path=".env", verbose=True, override=True)
    logging.info("Environment variables loaded successfully.")

    # Azure OpenAI client setup
    client = AzureOpenAI(
        api_key="eadf76dd169e4172a463e7375946835f",
        api_version="2024-02-15-preview",
        azure_endpoint="https://green-code-uks.openai.azure.com"
    )
    logging.info("Azure OpenAI client setup completed.")

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
    logging.info("Assistant created successfully.")

    # Create a thread
    thread = client.beta.threads.create()
    logging.info(f"Thread created: {thread}")

    source_directory = 'C:\\ProgramData\\Jenkins\\.jenkins\\workspace\\GreenCodeScanPipeline'
    download_directory = "D:\\Documents\\TechM\\Green_Software_Development\\Third Task\\Projects & Docs\\Assistant api\\Container"

    
    # Modify the part of the code for dynamic file upload
    for filename in os.listdir(source_directory):
        if (filename.endswith(".py") or filename.endswith(".java")) and filename not in processed_files:
            file_path = os.path.join(source_directory, filename)
            with open(file_path, "rb") as file:
                uploaded_file = client.files.create(
                    file=file,
                    purpose='assistants'
                )
                logging.info(f"File uploaded successfully: {filename}")

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
                logging.info(f"Message passed to thread for file: {filename}")

                # Mark file as processed
                with open(processed_files_log, 'a') as f:
                    f.write(filename + '\n')
                logging.info(f"File marked as processed: {filename}")

    # Check messages in the thread
    thread_messages = client.beta.threads.messages.list(thread.id)
    logging.info("Thread messages checked.")

    # Optional code execution
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id
    )
    logging.info("Code execution initiated.")

    # Wait for the run to complete
    while True:
        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )
        if run_status.status == 'completed':
            logging.info("Code execution completed.")
            break
        time.sleep(5)  # Wait for 5 seconds before checking again

    # Print messages in the thread post run
    messages = client.beta.threads.messages.list(
        thread_id=thread.id
    )
    logging.info("Messages post run checked.")

    # Extract the content of the latest question only
    data = json.loads(messages.model_dump_json(indent=2))
    code = data['data'][0]['content'][0]['text']['annotations'][0]['file_path']['file_id']
    logging.info(f"Code extracted: {code}")

    # Assuming `client.files.content(code)` retrieves the file content
    content = client.files.content(code)

    # Use the original filename and download directory to construct the file path
    file_path = os.path.join(download_directory, filename)

    # Use the content object's method to write to the specified file path
    content.write_to_file(file_path)
    logging.info(f"File written to path: {file_path}")

    # Check if all files have been refined
    source_files = {file for file in os.listdir(source_directory) if file.endswith(('.py', '.java'))}
    refined_files = {file for file in os.listdir(download_directory) if file.endswith(('.py', '.java'))}

    if source_files.issubset(refined_files):
        print('done')
        sys.exit(0)  # Success
    else:
        print('pending')
        sys.exit(1)  # Failure
except Exception as e:
    logging.error(f"An error occurred: {str(e)}")
    sys.exit(1)  # Exit with error
