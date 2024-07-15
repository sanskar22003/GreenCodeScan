# Load environment variables from .env file
$envPath = "C:\ProgramData\Jenkins\.jenkins\workspace\GreenCodeScanPipeline\.env"
if (Test-Path $envPath) {
    $env = Get-Content $envPath | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim().Trim('"')
            Set-Item -Path "ENV:\$key" -Value $value
        }
    }
} else {
    Write-Host "The .env file could not be found at the specified path: $envPath"
    exit 1
}

# Validate SharePoint client libraries path
$sharepointLibPath = $env:SHAREPOINT_CLIENT_LIB_PATH
$clientDll = Join-Path -Path $sharepointLibPath -ChildPath "Microsoft.SharePoint.Client.dll"
$runtimeDll = Join-Path -Path $sharepointLibPath -ChildPath "Microsoft.SharePoint.Client.Runtime.dll"

if (-Not (Test-Path $clientDll) -or -Not (Test-Path $runtimeDll)) {
    Write-Host "The SharePoint client libraries could not be found at the specified path: $sharepointLibPath"
    exit 1
}

# Import the SharePoint client libraries
Add-Type -Path $clientDll
Add-Type -Path $runtimeDll

# Set the variables
$siteUrl = $env:SITE_URL
$listName = $env:LIST_NAME
$username = $env:USERNAME
$password = ConvertTo-SecureString $env:PASSWORD -AsPlainText -Force

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
$filesToUpload = ConvertFrom-Json $env:FILES_TO_UPLOAD
foreach ($filePath in $filesToUpload) {
    if (Test-Path $filePath) {
        $fileContent = [System.IO.File]::ReadAllBytes($filePath)
        $fileInfo = New-Object Microsoft.SharePoint.Client.FileCreationInformation
        $fileInfo.Content = $fileContent
        $fileInfo.Url = [System.IO.Path]::GetFileName($filePath)
        $fileInfo.Overwrite = $true
        $file = $folder.Files.Add($fileInfo)
        $context.Load($file)
        $context.ExecuteQuery()

        Write-Host "File uploaded successfully: $filePath"
    } else {
        Write-Host "File not found: $filePath"
    }
}
