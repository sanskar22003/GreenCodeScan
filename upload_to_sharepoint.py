from shareplum import Site
from shareplum import Office365
from shareplum.site import Version

# Authenticate to Office365
authcookie = Office365('https://sbupune.sharepoint.com', username='SANSKAR.MCA22003@SBUP.EDU.IN', password='Sk@6353910033').GetCookies()

# Initialize the Site
site = Site('https://sbupune.sharepoint.com/sites/TechMahindraGreenCodePipeline2', authcookie=authcookie)

# Get the folder
folder = site.Folder('Shared Documents/Pipeline CSVs')

# Upload the files
with open('C:\\ProgramData\\Jenkins\\.jenkins\\workspace\\GreenCodeScanPipeline\\emissions_data.csv', 'rb') as file:
    folder.upload_file(file, 'emissions_data.csv')

with open('C:\\ProgramData\\Jenkins\\.jenkins\\workspace\\GreenCodeScanPipeline\\server_data.xlsx', 'rb') as file:
    folder.upload_file(file, 'server_data.xlsx')

