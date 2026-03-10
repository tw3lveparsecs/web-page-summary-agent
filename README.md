# Web Page Summary Agent

A Python tool that summarises content from any web page, including JavaScript-rendered SPAs and dynamically loaded content. It generates structured summaries using Microsoft Foundry. Run it locally as a CLI tool or deploy to Azure with a web UI.

## Demo

https://github.com/user-attachments/assets/REPLACE_WITH_UPLOADED_VIDEO_URL.mp4

## Features

- **Dynamic content support** — Uses a headless Chromium browser (Playwright) to render JavaScript-heavy pages before extracting content
- **Bot-detection handling** — Automatically retries with a realistic browser fingerprint when bot-challenge pages are detected
- **Batch processing** — Pass a text file with multiple URLs or list them as arguments
- **AI-powered summaries** — Uses a Microsoft Foundry model deployment to produce structured summaries
- **Customisable prompts** — Edit `prompt.txt` or pass a custom prompt file with `-p`
- **Two modes** — Local CLI for quick one-off runs, or deploy the FastAPI backend + React frontend to Azure
- **SSE streaming** — The web UI streams real-time status updates and results via Server-Sent Events
- **Secure by default** — VNet integration with service endpoints secures traffic between the App Service and Foundry

> **Note:** This project has been developed with a balance of cost-effectiveness and security for Azure. The infrastructure uses a B1 App Service Plan, a single VNet with service endpoints, and system-assigned managed identity. For enterprise deployments, modifications will be required — for example, private endpoints, WAF/Application Gateway, dedicated App Service Environments, enhanced logging and monitoring, and stricter network segmentation.

---

## Table of Contents

- [Local Development (CLI)](#local-development-cli)
- [Local Development (Web UI)](#local-development-web-ui)
- [Azure Deployment](#azure-deployment)
  - [What Gets Deployed](#what-gets-deployed)
  - [Option A: GitHub Actions (CI/CD)](#option-a-github-actions-cicd)
  - [Option B: Manual Deployment via Azure Portal + CLI](#option-b-manual-deployment-via-azure-portal--cli)
- [Authentication](#authentication)
- [Project Structure](#project-structure)

---

## Local Development (CLI)

The CLI tool summarises web pages directly from the terminal — no Azure deployment needed.

### Prerequisites

- Python 3.11+
- A Microsoft Foundry resource with a deployed model (e.g. `gpt-4o`)
- An API key **or** an Azure identity with the *Cognitive Services OpenAI User* role

### Setup

```bash
# Clone the repo
git clone https://github.com/<owner>/url-summary-agent.git
cd url-summary-agent

# Create a virtual environment and install dependencies
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS / Linux

pip install -r requirements.txt
python -m playwright install chromium
```

### Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

| Variable | Description |
|---|---|
| `FOUNDRY_AUTH` | `key` (default) or `entra` |
| `FOUNDRY_ENDPOINT` | Your Foundry resource endpoint URL |
| `FOUNDRY_API_KEY` | API key (required when `FOUNDRY_AUTH=key`) |
| `FOUNDRY_DEPLOYMENT` | Model deployment name (default: `gpt-4o`) |
| `FOUNDRY_API_VERSION` | API version (default: `2024-12-01-preview`) |
| `AZURE_TENANT_ID` | Entra tenant ID (service principal auth only) |
| `AZURE_CLIENT_ID` | App/managed-identity client ID (service principal or user-assigned MI) |
| `AZURE_CLIENT_SECRET` | Client secret (service principal auth only) |

For Entra ID authentication set `FOUNDRY_AUTH=entra`. The credential is resolved as follows:

- **Service principal** — set `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, and `AZURE_CLIENT_SECRET`
- **User-assigned managed identity** — set only `AZURE_CLIENT_ID` (no secret)
- **System-assigned managed identity / Azure CLI** — leave all three blank and `DefaultAzureCredential` will pick up the ambient identity (e.g. `az login` locally, system MI on App Service)

### Usage

```bash
# Summarise URLs from a file (one URL per line, # comments supported)
python main.py urls.txt

# Save output to a markdown file
python main.py urls.txt -o summaries.md

# Pass URLs directly
python main.py https://example.com/page-one https://example.com/page-two

# Use a custom system prompt
python main.py urls.txt -p my-prompt.txt
```

---

## Local Development (Web UI)

Run the FastAPI backend and React frontend locally for development.

### Start the backend

```bash
# From the repo root (with .venv activated)
uvicorn api:app --reload --port 8000
```

### Start the frontend

```bash
cd frontend
npm install
VITE_API_URL=http://localhost:8000 npm run dev
```

Open the URL printed by Vite (usually `http://localhost:5173`). The UI lets you enter URLs, choose an auth method (API key, service principal, or managed identity), and view streamed results.

---

## Azure Deployment

Deploy the full stack to Azure — the Python API backend, React frontend, and supporting infrastructure.

### What Gets Deployed

| Resource | Name | Purpose |
|---|---|---|
| Virtual Network | `<baseName>-vnet` | VNet with integration subnet and Cognitive Services service endpoint |
| App Service Plan | `<baseName>-plan` | Shared Linux plan (B1 SKU) |
| Web App (Python 3.13) | `<baseName>-api` | FastAPI backend with Playwright, VNet-integrated |
| Web App (Node 22) | `<baseName>-web` | React frontend served by `server.mjs` |
| AI Services *(optional)* | `<baseName>-foundry` | Microsoft Foundry model deployment |
| Role Assignment | — | Grants the backend managed identity *Cognitive Services OpenAI User* on the Foundry resource |

### Option A: GitHub Actions (CI/CD)

Automated deployment using two GitHub Actions workflows.

#### 1. Create an Entra ID app registration with OIDC federation

```bash
# Create the app registration
az ad app create --display-name "web-summary-deploy"

# Note the appId and id (object ID) from the output, then:
az ad app federated-credential create \
  --id <app-object-id> \
  --parameters '{
    "name": "github-main",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:<owner>/<repo>:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# Create a service principal
az ad sp create --id <app-id>
```

#### 2. Assign roles

The service principal needs different roles depending on scope:

**On the target resource group** (where infrastructure is deployed):

```bash
az role assignment create --assignee <app-id> --role Contributor \
  --scope /subscriptions/<sub>/resourceGroups/<rg>

az role assignment create --assignee <app-id> \
  --role "Role Based Access Control Administrator" \
  --scope /subscriptions/<sub>/resourceGroups/<rg> \
  --condition "((!(ActionMatches{'Microsoft.Authorization/roleAssignments/write'})) OR (@Request[Microsoft.Authorization/roleAssignments:RoleDefinitionId] ForAnyOfAnyValues:GuidEquals {5e0bd9bd-7b93-4f28-af87-19fc36ad61bd}))" \
  --condition-version "2.0"
```

**On the Foundry account** (may be in a different resource group):

```bash
az role assignment create --assignee <app-id> \
  --role "Cognitive Services Contributor" \
  --scope /subscriptions/<sub>/resourceGroups/<foundry-rg>/providers/Microsoft.CognitiveServices/accounts/<foundry-account>

az role assignment create --assignee <app-id> \
  --role "Network Contributor" \
  --scope /subscriptions/<sub>/resourceGroups/<foundry-rg>/providers/Microsoft.CognitiveServices/accounts/<foundry-account>
```

> **Note:** The service principal needs **Cognitive Services Contributor** to manage the Foundry resource and **Network Contributor** on the Foundry account to add VNet network rules. The integration subnet is in the same resource group where the SP already has Contributor access, so no additional role is needed there.

#### 3. Configure GitHub secrets

In your repo go to **Settings → Secrets and variables → Actions** and add:

| Secret | Value |
|---|---|
| `AZURE_CLIENT_ID` | App registration client ID |
| `AZURE_TENANT_ID` | Entra ID tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Target Azure subscription ID |

#### 4. Edit workflow env vars

In both `.github/workflows/deploy-infra.yml` and `deploy-apps.yml`, update the `env:` block at the top:

| Variable | Description |
|---|---|
| `AZURE_RG` | Resource group name (e.g. `web-summariser-rg`) |
| `BASE_NAME` | Base name for resources (e.g. `websummariser`) |

#### 5. Edit Bicep parameters

Open `infra/main.bicepparam` and set:

- `baseName` — same value as `BASE_NAME` in the workflows
- `deployFoundry` — `true` to create a new Foundry resource, or `false` to use an existing one
- `existingFoundryResourceId` / `existingFoundryEndpoint` — required when `deployFoundry = false`
- `foundryDeployment` — the model deployment name to use

#### 6. Run the workflows

1. Go to the **Actions** tab in GitHub
2. Run **Deploy Infrastructure** — this creates the VNet, App Service Plan, web apps, and role assignments
3. Run **Deploy Apps** — this builds and deploys the backend and frontend, then configures CORS

After both workflows complete, open `https://<baseName>-web.azurewebsites.net` in your browser.

---

### Option B: Manual Deployment via Azure Portal + CLI

If you prefer not to use GitHub Actions, you can deploy manually.

#### 1. Create a resource group

```bash
az group create --name web-summariser-rg --location australiaeast
```

#### 2. Deploy infrastructure with Bicep

```bash
az deployment group create \
  --resource-group web-summariser-rg \
  --template-file infra/main.bicep \
  --parameters infra/main.bicepparam
```

#### 3. Add the Foundry network rule

```bash
# Get outputs from the deployment
FOUNDRY_NAME=$(az deployment group show -g web-summariser-rg -n main --query properties.outputs.foundryAccountName.value -o tsv)
FOUNDRY_RG=$(az deployment group show -g web-summariser-rg -n main --query properties.outputs.foundryResourceGroupName.value -o tsv)
SUBNET_ID=$(az deployment group show -g web-summariser-rg -n main --query properties.outputs.integrationSubnetId.value -o tsv)

az cognitiveservices account network-rule add \
  --name "$FOUNDRY_NAME" \
  --resource-group "$FOUNDRY_RG" \
  --subnet "$SUBNET_ID"
```

#### 4. Deploy the backend

```bash
# From the repo root
zip -r backend.zip api.py extractor.py summariser.py main.py prompt.txt requirements.txt

az webapp deploy \
  --name websummariser-api \
  --resource-group web-summariser-rg \
  --src-path backend.zip \
  --type zip
```

#### 5. Build and deploy the frontend

```bash
cd frontend
npm install
VITE_API_URL=https://websummariser-api.azurewebsites.net npm run build

cp server.mjs dist/
cd dist && zip -r ../../frontend.zip .
cd ../..

az webapp deploy \
  --name websummariser-web \
  --resource-group web-summariser-rg \
  --src-path frontend.zip \
  --type zip
```

#### 6. Configure CORS

```bash
az webapp config appsettings set \
  --name websummariser-api \
  --resource-group web-summariser-rg \
  --settings ALLOWED_ORIGINS="https://websummariser-web.azurewebsites.net"

az webapp cors add \
  --name websummariser-api \
  --resource-group web-summariser-rg \
  --allowed-origins "https://websummariser-web.azurewebsites.net"
```

Open `https://websummariser-web.azurewebsites.net` — the app is ready to use.

---

## Authentication

The backend supports three authentication methods when calling Microsoft Foundry:

| Method | When to use | Configuration |
|---|---|---|
| **API key** | Quick local testing | Set `FOUNDRY_AUTH=key` and `FOUNDRY_API_KEY` in `.env`, or pass via the UI |
| **Entra ID (managed identity)** | Azure-hosted backend | Select *Managed Identity* in the UI — the backend uses `DefaultAzureCredential` with the system-assigned identity |
| **Entra ID (service principal)** | Cross-tenant or explicit SP | Provide tenant ID, client ID, and client secret in the UI |

### Entra ID with DefaultAzureCredential (CLI)

When `FOUNDRY_AUTH=entra` is set, `DefaultAzureCredential` tries sources in this order:

| Source | When it applies |
|---|---|
| Azure CLI (`az login`) | Local development |
| Azure PowerShell (`Connect-AzAccount`) | Local development via PowerShell |
| Environment variables | Service principal (`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET`) |
| System-assigned managed identity | Azure App Service, VMs — no extra configuration |
| User-assigned managed identity | Set `AZURE_CLIENT_ID` to the identity's client ID |

To assign the required role:

```bash
az role assignment create \
  --assignee <your-user-or-sp-object-id> \
  --role "Cognitive Services OpenAI User" \
  --scope /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<resource>
```

---

## Project Structure

```
url-summary-agent/
├── .github/workflows/
│   ├── deploy-infra.yml        # Bicep infrastructure deployment
│   └── deploy-apps.yml         # Backend + frontend deployment with CORS config
├── frontend/                    # React web UI (GitHub Spark + Vite + Tailwind)
│   ├── src/App.tsx              # Main application component
│   ├── server.mjs               # Lightweight Node.js static file server for Azure
│   ├── package.json
│   └── ...
├── infra/
│   ├── main.bicep               # All Azure infrastructure (VNet, App Services, Foundry, roles)
│   ├── main.bicepparam          # Parameter values
│   └── role-assignment.bicep    # Cross-resource-group role assignment module
├── api.py                       # FastAPI backend with SSE streaming
├── main.py                      # CLI entry point
├── extractor.py                 # Headless browser content extraction (sync + async)
├── summariser.py                # Microsoft Foundry integration and summarisation
├── prompt.txt                   # Default system prompt (customisable)
├── urls.txt                     # Sample input file with URLs
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variable template
└── .gitignore
```

## Output Format

Each summary will be printed to the console (or streamed to the frontend) in this format defined by the system prompt in `prompt.txt`. The prompt can be customised as needed.