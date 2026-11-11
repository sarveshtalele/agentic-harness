# ==============================================================================
# 1-TIME AZURE INFRASTRUCTURE SETUP SCRIPT (POWERSHELL) FOR AGENTIC QE PLATFORM
# Region: eastus2 | Tier: Basic B1 | OS: Linux
# ==============================================================================
[CmdletBinding()]
param(
    [string]$ResourceGroup = "rg-agentic-harness-eastus2",
    [string]$Location = "eastus2",
    [string]$AppPlan = "asp-agentic-harness-b1",
    [string]$BackendApp = "agentic-backend",
    [string]$FrontendApp = "agentic-frontend",
    [string]$Sku = "B1"
)

$ErrorActionPreference = "Stop"
$KeyVault = "kv-agentic-harness"  # holds atlas-admin-password, atlas-secret-key, atlas-database-url

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host " 1-Time Azure Infrastructure Setup" -ForegroundColor Cyan
Write-Host " Resource Group: $ResourceGroup"
Write-Host " Location:       $Location"
Write-Host " Plan:           $AppPlan (Linux $Sku)"
Write-Host " Backend App:    $BackendApp (Python 3.12)"
Write-Host " Frontend App:   $FrontendApp (Node.js 20)"
Write-Host "==================================================================" -ForegroundColor Cyan

# 1. Create Resource Group
Write-Host "`n[1/6] Creating Resource Group..." -ForegroundColor Yellow
az group create --name $ResourceGroup --location $Location

# 2. Create Shared Linux App Service Plan
Write-Host "`n[2/6] Creating App Service Plan ($Sku Linux)..." -ForegroundColor Yellow
az appservice plan create `
  --name $AppPlan `
  --resource-group $ResourceGroup `
  --location $Location `
  --is-linux `
  --sku $Sku

# 3. Create Backend WebApp (Python 3.12)
Write-Host "`n[3/6] Creating Backend WebApp..." -ForegroundColor Yellow
az webapp create `
  --name $BackendApp `
  --resource-group $ResourceGroup `
  --plan $AppPlan `
  --runtime "PYTHON:3.12" `
  --startup-file "/home/site/wwwroot/startup.sh"

# 4. Configure Backend Settings & Persistent Storage
Write-Host "`n[4/6] Configuring Backend Environment & Persistent Storage..." -ForegroundColor Yellow
az webapp config appsettings set `
  --name $BackendApp `
  --resource-group $ResourceGroup `
  --settings `
    WEBSITES_PORT="8000" `
    PORT="8000" `
    WEBSITES_ENABLE_APP_SERVICE_STORAGE="true" `
    ATLAS_HOME="/home/atlas" `
    ATLAS_DATA_DIR="/home/atlas/data" `
    ATLAS_KEY_VAULT_URL="https://$KeyVault.vault.azure.net" `
    ATLAS_ALLOWED_HOSTS="$BackendApp.azurewebsites.net" `
    ATLAS_ALLOWED_ORIGINS="https://$FrontendApp.azurewebsites.net" `
    SCM_DO_BUILD_DURING_DEPLOYMENT="true" `
    ENABLE_ORYX_BUILD="true"

# Sign-in: the admin account lives in App Settings (the package never ships .env). The password is sent from a
# private temp file, never on a command line.
$AdminUser = Read-Host "Platform admin username"
$AdminPass = [System.Net.NetworkCredential]::new("", (Read-Host "Platform admin password" -AsSecureString)).Password
$SettingsFile = New-TemporaryFile
@(@{ name = "ATLAS_ADMIN_USERNAME"; value = $AdminUser; slotSetting = $false }, @{ name = "ATLAS_ADMIN_PASSWORD"; value = $AdminPass; slotSetting = $false }) | ConvertTo-Json | Set-Content -Path $SettingsFile -Encoding utf8
az webapp config appsettings set --name $BackendApp --resource-group $ResourceGroup --settings "@$SettingsFile" | Out-Null
Remove-Item $SettingsFile; Remove-Variable AdminPass

# 5. Create Frontend WebApp (Node 20)
Write-Host "`n[5/6] Creating Frontend WebApp..." -ForegroundColor Yellow
az webapp create `
  --name $FrontendApp `
  --resource-group $ResourceGroup `
  --plan $AppPlan `
  --runtime "NODE:20-lts" `
  --startup-file "/home/site/wwwroot/startup.sh"

# 6. Configure Frontend Settings & Backend Proxy Binding
Write-Host "`n[6/6] Binding Frontend to Backend URL..." -ForegroundColor Yellow
az webapp config appsettings set `
  --name $FrontendApp `
  --resource-group $ResourceGroup `
  --settings `
    WEBSITES_PORT="3000" `
    PORT="3000" `
    WEBSITES_ENABLE_APP_SERVICE_STORAGE="true" `
    ATLAS_BACKEND_URL="https://$BackendApp.azurewebsites.net" `
    NEXT_TELEMETRY_DISABLED="1" `
    SCM_DO_BUILD_DURING_DEPLOYMENT="true"

# Enable CORS on Backend for Frontend Origin
az webapp cors add `
  --name $BackendApp `
  --resource-group $ResourceGroup `
  --allowed-origins "https://$FrontendApp.azurewebsites.net"

Write-Host "`n==================================================================" -ForegroundColor Green
Write-Host " 1-Time Azure Setup Complete!" -ForegroundColor Green
Write-Host " Backend URL:  https://$BackendApp.azurewebsites.net"
Write-Host " Frontend URL: https://$FrontendApp.azurewebsites.net"
Write-Host " Next Step: Run python scripts/azure_convert_and_deploy.py --convert"
Write-Host "==================================================================" -ForegroundColor Green
