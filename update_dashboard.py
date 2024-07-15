# Import the SharePoint client libraries
from office365.sharepoint.client_context import ClientContext
from office365.sharepoint.files.file import File
from office365.runtime.auth.authentication_context import AuthenticationContext
from office365.sharepoint.files.file_creation_information import FileCreationInformation

# Set the variables
site_url = "https://sbupune.sharepoint.com/sites/TechMahindraGreenCodePipeline2"
list_name = "Pipeline CSVs"
folder_name = ""  # No subfolder
username = "SANSKAR.MCA22003@SBUP.EDU.IN"
password = "Sk@6353910033"

# Connect to the SharePoint site
context_auth = AuthenticationContext(site_url)
context_auth.acquire_token_for_user(username, password)
ctx = ClientContext(site_url, context_auth)

# Get the list and folder
list_obj = ctx.web.lists.get_by_title(list_name)
folder = list_obj.rootFolder  # No subfolder
ctx.load(list_obj)
ctx.load(folder)
ctx.execute_query()

# Upload the files
files = [
    "C:\\ProgramData\\Jenkins\\.jenkins\\workspace\\GreenCodeScanPipeline\\emissions_data.csv",
    "C:\\ProgramData\\Jenkins\\.jenkins\\workspace\\GreenCodeScanPipeline\\server_data.xlsx"
]
for file_path in files:
    with open(file_path, 'rb') as file_content:
        file_info = FileCreationInformation()
        file_info.content = file_content.read()
        file_info.url = file_path.split("\\")[-1]
        file_info.overwrite = True
        upload_file = folder.files.add(file_info)
        ctx.load(upload_file)
        ctx.execute_query()
        print(f"File uploaded successfully: {file_path}")
