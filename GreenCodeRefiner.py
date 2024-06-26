import os
import json
import dotenv
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv(dotenv_path=".env", verbose=True, override=True)


client = AzureOpenAI(
    api_key="eadf76dd169e4172a463e7375946835f",  
    api_version="2024-02-15-preview",
    azure_endpoint = "https://green-code-uks.openai.azure.com"
    )

# Create an assistant
assistant = client.beta.assistants.create(
  name = 'Green IT Code Writer 2',
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

#Create a thread
thread = client.beta.threads.create()
print(thread)

# Upload a reference file
file = client.files.create(
  file=open("refine_code.py", "rb"),
  purpose='assistants'
)

#pass a message to thread
thread = client.beta.threads.create(
  messages=[
    {
      "role": "user",
      "content": "Make the code energy efficient",
      "file_ids": [file.id]
    }
  ]
)

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

print(messages.model_dump_json(indent=2))

#Extract the content of the latest question only
data = json.loads(messages.model_dump_json(indent=2))
code = data['data'][0]['content'][0]['text']['annotations'][0]['file_path']['file_id']
print(code)

#Download the code file
content = client.files.content(code)

code_file= content.write_to_file("refactored_refine_code.py")
