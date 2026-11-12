"""The one-time Azure infrastructure setup script (bash) that azure_convert_and_deploy.py prints or writes."""
from __future__ import annotations


def generate_setup_script(
    resource_group: str = "rg-agentic-harness-eastus2",
    location: str = "eastus2",
    plan_name: str = "asp-agentic-harness-b1",
    backend_app: str = "agentic-harness-backend-prod",
    frontend_app: str = "agentic-harness-frontend-prod",
    sku: str = "B1",
) -> str:
    """Generates the authoritative Azure CLI bash script for 1-time setup."""
    return f"""#!/usr/bin/env bash
# ==============================================================================
# 1-TIME AZURE INFRASTRUCTURE SETUP SCRIPT FOR AGENTIC QE PLATFORM
# Region: {location} | Tier: Basic {sku} | OS: Linux
# ==============================================================================
set -euo pipefail

RESOURCE_GROUP="{resource_group}"
LOCATION="{location}"
APP_PLAN="{plan_name}"
BACKEND_APP="{backend_app}"
FRONTEND_APP="{frontend_app}"
SKU="{sku}"
KEY_VAULT="kv-agentic-harness"  # holds atlas-admin-password, atlas-secret-key, atlas-database-url

echo "=================================================================="
echo " 1-Time Azure Infrastructure Setup"
echo " Resource Group: $RESOURCE_GROUP"
echo " Location:       $LOCATION"
echo " Plan:           $APP_PLAN (Linux $SKU)"
echo " Backend App:    $BACKEND_APP (Python 3.12)"
echo " Frontend App:   $FRONTEND_APP (Node.js 20)"
echo "=================================================================="

# 1. Create Resource Group
echo "\\n[1/6] Creating Resource Group..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"

# 2. Create Shared Linux App Service Plan (Hosts both Backend & Frontend)
echo "\\n[2/6] Creating App Service Plan ($SKU Linux)..."
az appservice plan create \\
  --name "$APP_PLAN" \\
  --resource-group "$RESOURCE_GROUP" \\
  --location "$LOCATION" \\
  --is-linux \\
  --sku "$SKU"

# 3. Create Backend WebApp (Python 3.12)
echo "\\n[3/6] Creating Backend WebApp..."
az webapp create \\
  --name "$BACKEND_APP" \\
  --resource-group "$RESOURCE_GROUP" \\
  --plan "$APP_PLAN" \\
  --runtime "PYTHON:3.12" \\
  --startup-file "/home/site/wwwroot/startup.sh"

# 4. Configure Backend App Settings & Persistent Storage
echo "\\n[4/6] Configuring Backend Environment & Persistent Storage..."
az webapp config appsettings set \\
  --name "$BACKEND_APP" \\
  --resource-group "$RESOURCE_GROUP" \\
  --settings \\
    WEBSITES_PORT="8000" \\
    PORT="8000" \\
    WEBSITES_ENABLE_APP_SERVICE_STORAGE="true" \\
    ATLAS_HOME="/home/atlas" \\
    ATLAS_DATA_DIR="/home/atlas/data" \\
    ATLAS_KEY_VAULT_URL="https://$KEY_VAULT.vault.azure.net" \\
    ATLAS_ALLOWED_HOSTS="$BACKEND_APP.azurewebsites.net" \\
    ATLAS_ALLOWED_ORIGINS="https://$FRONTEND_APP.azurewebsites.net" \\
    SCM_DO_BUILD_DURING_DEPLOYMENT="false" \\
    ENABLE_ORYX_BUILD="false"

# Sign-in: the admin account lives in App Settings (the package never ships .env). Asked once, sent from a private
# temp file so the password is never on a command line.
read -r -p "Platform admin username: " ADMIN_USER
read -r -s -p "Platform admin password: " ADMIN_PASS; echo
SETTINGS_FILE="$(umask 077; mktemp)"
ADMIN_USER="$ADMIN_USER" ADMIN_PASS="$ADMIN_PASS" python3 -c 'import json, os, sys; json.dump([{{"name": "ATLAS_ADMIN_USERNAME", "value": os.environ["ADMIN_USER"], "slotSetting": False}}, {{"name": "ATLAS_ADMIN_PASSWORD", "value": os.environ["ADMIN_PASS"], "slotSetting": False}}], open(sys.argv[1], "w"))' "$SETTINGS_FILE"
az webapp config appsettings set --name "$BACKEND_APP" --resource-group "$RESOURCE_GROUP" --settings "@$SETTINGS_FILE" > /dev/null
rm -f "$SETTINGS_FILE"; unset ADMIN_PASS

# 5. Create Frontend WebApp (Node 20)
echo "\\n[5/6] Creating Frontend WebApp..."
az webapp create \\
  --name "$FRONTEND_APP" \\
  --resource-group "$RESOURCE_GROUP" \\
  --plan "$APP_PLAN" \\
  --runtime "NODE:20-lts" \\
  --startup-file "/home/site/wwwroot/startup.sh"

# 6. Configure Frontend App Settings & Backend Proxy Binding
echo "\\n[6/6] Binding Frontend to Backend URL..."
az webapp config appsettings set \\
  --name "$FRONTEND_APP" \\
  --resource-group "$RESOURCE_GROUP" \\
  --settings \\
    WEBSITES_PORT="3000" \\
    PORT="3000" \\
    WEBSITES_ENABLE_APP_SERVICE_STORAGE="true" \\
    ATLAS_BACKEND_URL="https://$BACKEND_APP.azurewebsites.net" \\
    NEXT_TELEMETRY_DISABLED="1" \\
    SCM_DO_BUILD_DURING_DEPLOYMENT="false"

# Enable CORS on Backend for Frontend Origin
az webapp cors add \\
  --name "$BACKEND_APP" \\
  --resource-group "$RESOURCE_GROUP" \\
  --allowed-origins "https://$FRONTEND_APP.azurewebsites.net"

echo "\\n=================================================================="
echo " 1-Time Azure Setup Complete!"
echo " Backend URL:  https://$BACKEND_APP.azurewebsites.net"
echo " Frontend URL: https://$FRONTEND_APP.azurewebsites.net"
echo " Next Step: Run python scripts/azure_convert_and_deploy.py --convert"
echo "=================================================================="
"""

