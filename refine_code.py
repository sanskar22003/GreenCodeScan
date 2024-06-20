import os
import json
import dotenv
from dotenv import load_dotenv
from openai import AzureOpenAI
import time

load_dotenv(dotenv_path=".env", verbose=True, override=True)

client = AzureOpenAI(
    api_key="eadf76dd169e4172a463e7375946835f",  
    api_version="2024-02-15-preview",
    azure_endpoint = "https://green-code-uks.openai.azure.com"
)

assistant = client.beta.assistants.create(
  name = 'Green IT Code Writer 4',
  instructions=f"You are a helpful AI assistant who re-factors the code from an uploaded file to make it more efficient" 
    f"You have access to a sandboxed environment for writing and testing code."
    f"You should follow these steps:"
    f"1. Re-write the code in the same language as the origninal code."
    f"2. Test the re-written code and ensure it functions correctly and same as the original code."
    f"3. Run the code to confirm that it runs successfully"
    f"4. If the code runs successfully, share the code as a file that can be downloaded"
    f"5. If the code is unsuccessful display the error message and try to revise the code and rerun going through the steps from above again.",
  model="code",
  tools=[{"type": "code_interpreter"}]
)

directory = 'C:\\ProgramData\\Jenkins\\.jenkins\\workspace\\GreenCodeScanPipeline'
download_directory = "D:\\Documents\\TechM\\Green_Software_Development\\Third Task\\Projects & Docs\\Assistant api\\Refined Files"
prompts = ["Make the code energy efficient", "Provide a version of this function that is optimized for energy efficiency ", "Optimize this code to use less CPU resources"]

for filename in os.listdir(directory):
    if filename == 'contact.py':
        continue
    if filename.endswith('.py') or filename.endswith('.java'):
        file_path = os.path.join(directory, filename)
        with open(file_path, "rb") as f:
            uploaded_file = client.files.create(
                file=f,
                purpose='assistants'
            )
        print(f"Uploaded file: {file_path}")

        for prompt in prompts:
            thread = client.beta.threads.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                        "file_ids": [uploaded_file.id]
                    }
                ]
            )

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

            messages = client.beta.threads.messages.list(
              thread_id=thread.id
            )

            data = json.loads(messages.model_dump_json(indent=2))
            code = data['data'][0]['content'][0]['text']['annotations'][0]['file_path']['file_id']

            content = client.files.content(uploaded_file.id)
            original_filename = os.path.basename(uploaded_file.file_path)
            new_filename = "refined_" + original_filename
            code_file = content.write_to_file(os.path.join(download_directory, new_filename))
            print(f"Downloaded refined file: {new_filename}")
