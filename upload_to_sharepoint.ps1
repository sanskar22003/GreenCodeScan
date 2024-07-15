# Load environment variables from .env file
$envPath = ".\path\to\your\.env"
if (Test-Path $envPath) {
    $env = Get-Content $envPath | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim().Trim('"')
            [System.Collections.DictionaryEntry]::new($key, $value)
        }
    } | ConvertTo-Dictionary
}

# Import the SharePoint client libraries
Add-Type -Path "$($env['SHAREPOINT_CLIENT_LIB_PATH'])\Microsoft.Online.SharePoint.PowerShell\Microsoft.SharePoint.Client.dll"
Add-Type -Path "$($env['SHAREPOINT_CLIENT_LIB_PATH'])\Microsoft.Online.SharePoint.PowerShell\Microsoft.SharePoint.Client.Runtime.dll"

# Set the variables
$siteUrl = $env['SITE_URL']
$listName = $env['LIST_NAME']
$username = $env['USERNAME']
$password = ConvertTo-SecureString $env['PASSWORD'] -AsPlainText -Force

# Create a credential object
$credential = New-Object Microsoft.SharePoint.Client.SharePointOnlineCredentials($username, $password)

# Connect to the SharePoint site
$context = New-Object Microsoft.SharePoint.Client.ClientContext($siteUrl)
$context.Credentials = $credential

# Get the list and folder
$list = $context.Web.Lists.GetByTitle($listName)
$folder = $list.RootFolder
$context.Load($list)
$context.Load($folder)
$context.ExecuteQuery()

# Upload the files
$filesToUpload = ConvertFrom-Json $env['FILES_TO_UPLOAD']
foreach ($filePath in $filesToUpload) {
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
