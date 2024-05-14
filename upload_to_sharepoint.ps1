# Import the SharePoint client libraries
Add-Type -Path "C:\Program Files\SharePoint Online Management Shell\Microsoft.Online.SharePoint.PowerShell\Microsoft.SharePoint.Client.dll"
Add-Type -Path "C:\Program Files\SharePoint Online Management Shell\Microsoft.Online.SharePoint.PowerShell\Microsoft.SharePoint.Client.Runtime.dll"

# Set the variables
$siteUrl = "https://sbupune.sharepoint.com/sites/TechMahindraGreenCodePipeline2"
$listName = "Shared Documents"
$folderName = "Pipeline CSVs"
$username = "SANSKAR.MCA22003@SBUP.EDU.IN"
$password = ConvertTo-SecureString "Sk@6353910033" -AsPlainText -Force

# Create a credential object
$credential = New-Object Microsoft.SharePoint.Client.SharePointOnlineCredentials($username, $password)

# Connect to the SharePoint site
$context = New-Object Microsoft.SharePoint.Client.ClientContext($siteUrl)
$context.Credentials = $credential

# Get the list and folder
$list = $context.Web.Lists.GetByTitle($listName)
$folder = $list.RootFolder.Folders.GetByUrl($folderName)
$context.Load($list)
$context.Load($folder)
$context.ExecuteQuery()

# Upload the files
$files = @("C:\ProgramData\Jenkins\.jenkins\workspace\GreenCodeScanPipeline\emissions_data.csv", "C:\ProgramData\Jenkins\.jenkins\workspace\GreenCodeScanPipeline\server_data.xlsx")
foreach ($filePath in $files) {
    $fileContent = [System.IO.File]::ReadAllBytes($filePath)
    $fileInfo = New-Object Microsoft.SharePoint.Client.FileCreationInformation
    $fileInfo.Content = $fileContent
    $fileInfo.Url = [System.IO.Path]::GetFileName($filePath)
    $fileInfo.Overwrite = $true
    $file = $folder.Files.Add($fileInfo)
    $context.Load($file)
    $context.ExecuteQuery()

    Write-Host "File uploaded successfully: $filePath"
}
