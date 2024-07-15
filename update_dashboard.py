from office365.runtime.auth.authentication_context import AuthenticationContext
from office365.sharepoint.client_context import ClientContext
from office365.sharepoint.files.file import FileCreationInformation
import os

site_url = "https://sbupune.sharepoint.com/sites/TechMahindraGreenCodePipeline2"
list_name = "Pipeline CSVs"
username = "SANSKAR.MCA22003@SBUP.EDU.IN"
password = "Sk@6353910033"

file_paths = [
    "C:\\ProgramData\\Jenkins\\.jenkins\\workspace\\GreenCodeScanPipeline\\emissions_data.csv",
    "C:\\ProgramData\\Jenkins\\.jenkins\\workspace\\GreenCodeScanPipeline\\server_data.xlsx"
]

ctx_auth = AuthenticationContext(site_url)
if ctx_auth.acquire_token_for_user(username, password):
    ctx = ClientContext(site_url, ctx_auth)
    web = ctx.web
    ctx.load(web)
    ctx.execute_query()
    for file_path in file_paths:
        with open(file_path, 'rb') as content_file:
            file_content = content_file.read()
        list_obj = ctx.web.lists.get_by_title(list_name)
        info = FileCreationInformation()
        info.content = file_content
        info.url = os.path.basename(file_path)
        info.overwrite = True
        upload_file = list_obj.root_folder.files.add(info)
        ctx.execute_query()
        print(f"File uploaded successfully: {os.path.basename(file_path)}")
else:
    print("Authentication failed")
