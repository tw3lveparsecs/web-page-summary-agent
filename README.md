# Web Page Summary Agent

A Python CLI tool that extracts content from any web page, including JavaScript rendered SPAs and dynamically loaded content, and generates structured summaries using Microsoft Foundry.

## Features

- **Dynamic content support** Uses a headless Chromium browser (Playwright) to render JavaScript heavy pages before extracting content
- **Batch processing** Pass a text file with multiple URLs or list them as arguments
- **AI powered summaries** Uses a Microsoft Foundry model deployment to produce structured summaries
- **Customisable prompts** Edit `prompt.txt` or pass a custom prompt file with `-p`
- **Markdown output** Results can be saved to a `.md` file or printed to the console

## Prerequisites

- Python 3.11+
- A Microsoft Foundry resource with a deployed model (e.g. `gpt-4o`)
- **Authentication** (one of the following):
  - **API key** Your Foundry resource API key, or
  - **Entra ID** An Azure identity with the *Cognitive Services OpenAI User* role on the Foundry resource

### Entra ID authentication

`DefaultAzureCredential` is used when `FOUNDRY_AUTH=entra`. It tries credential sources in the following order:

| Source | When it applies |
|---|---|
| Azure CLI (`az login`) | Local development, already logged in |
| Azure PowerShell (`Connect-AzAccount`) | Local development via PowerShell |
| Environment variables | Service principal: set `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET` |
| Managed identity (system assigned) | Azure hosted resources (VMs, App Service, etc.). No extra configuration needed |
| Managed identity (user assigned) | Set `AZURE_CLIENT_ID` to the identity's client ID |

For local development, `az login` is the simplest option. No service principal or additional configuration is required.

To assign the required role:

```bash
az role assignment create \
  --assignee <your-user-or-sp-object-id> \
  --role "Cognitive Services OpenAI User" \
  --scope /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<resource>
```

## Setup

1. **Clone the repo and install dependencies:**

   ```bash
   cd web-page-summary-agent
   pip install -r requirements.txt
   python -m playwright install chromium
   ```

2. **Configure environment variables:**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and fill in your Microsoft Foundry values:

   | Variable | Description |
   |---|---|
   | `FOUNDRY_AUTH` | Authentication method: `key` (default) or `entra` |
   | `FOUNDRY_ENDPOINT` | Your Microsoft Foundry resource endpoint |
   | `FOUNDRY_API_KEY` | Your API key (required when `FOUNDRY_AUTH=key`) |
   | `FOUNDRY_DEPLOYMENT` | Model deployment name (default: `gpt-4o`) |
   | `FOUNDRY_API_VERSION` | API version (default: `2024-12-01-preview`) |

   **Entra ID authentication:** Set `FOUNDRY_AUTH=entra` to authenticate using your Azure identity instead of an API key. This uses `DefaultAzureCredential`, which automatically picks up credentials from the Azure CLI, environment variables, managed identity, and other sources. Ensure your identity has the *Cognitive Services OpenAI User* role on the Foundry resource.

## Usage

### Summarise URLs from a file

Add URLs to `urls.txt` (one per line), then run:

```bash
python main.py urls.txt
```

### Save output to a markdown file

```bash
python main.py urls.txt -o summaries.md
```

### Pass URLs directly as arguments

```bash
python main.py https://example.com/page-one https://example.com/page-two
```

### Use a custom system prompt

```bash
python main.py urls.txt -p my-prompt.txt
```

## Project Structure

```
web-page-summary-agent/
├── .github/workflows/
│   ├── deploy-infra.yml      # Bicep infrastructure deployment
│   └── deploy-apps.yml       # Backend + frontend deployment with CORS config
├── frontend/                  # GitHub Spark app (your frontend files go here)
│   └── README.md
├── infra/
│   ├── main.bicep             # Azure infrastructure (App Service, Foundry, roles)
│   └── main.bicepparam        # Parameter values
├── api.py                     # FastAPI HTTP wrapper (used by Azure deployment)
├── main.py                    # CLI entry point and pipeline orchestration
├── extractor.py               # Headless browser extraction for JS rendered pages
├── summariser.py              # Microsoft Foundry integration and summarisation
├── prompt.txt                 # Default system prompt (customisable)
├── startup.sh                 # Azure App Service startup script
├── urls.txt                   # Sample input file with URLs
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variable template
└── .gitignore
```

## Azure Deployment

The project includes Bicep infrastructure and GitHub Actions workflows to deploy everything to Azure.

### What gets deployed

| Resource | Name | Purpose |
|---|---|---|
| App Service Plan | `<baseName>-plan` | Shared Linux plan (B1) |
| Web App (Python) | `<baseName>-api` | Backend FastAPI summarisation API |
| Web App (Node) | `<baseName>-web` | Frontend GitHub Spark app |
| AI Services *(optional)* | `<baseName>-foundry` | Microsoft Foundry model deployment |
| Role Assignment | — | Grants the backend *Cognitive Services OpenAI User* on Foundry |

### Prerequisites

1. **Azure subscription** with a resource group created
2. **Entra ID app registration** with a federated credential for GitHub Actions OIDC:

   ```bash
   # Create the app registration
   az ad app create --display-name "web-summary-deploy"

   # Add a federated credential for your repo
   az ad app federated-credential create \
     --id <app-object-id> \
     --parameters '{
       "name": "github-main",
       "issuer": "https://token.actions.githubusercontent.com",
       "subject": "repo:<owner>/<repo>:ref:refs/heads/main",
       "audiences": ["api://AzureADTokenExchange"]
     }'

   # Create a service principal and assign Contributor + RBAC Admin on the resource group
   az ad sp create --id <app-id>
   az role assignment create --assignee <app-id> --role Contributor \
     --scope /subscriptions/<sub>/resourceGroups/<rg>
   az role assignment create --assignee <app-id> --role "Role Based Access Control Administrator" \
     --scope /subscriptions/<sub>/resourceGroups/<rg> \
     --condition "((!(ActionMatches{'Microsoft.Authorization/roleAssignments/write'})) OR (@Request[Microsoft.Authorization/roleAssignments:RoleDefinitionId] ForAnyOfAnyValues:GuidEquals {5e0bd9bd-7b93-4f28-af87-19fc36ad61bd}))" \
     --condition-version "2.0"
   ```

3. **GitHub repository secrets** and **workflow env vars:**

   **Secrets** (set in GitHub repo settings):

   | Name | Value |
   |---|---|
   | `AZURE_CLIENT_ID` | App registration client ID |
   | `AZURE_TENANT_ID` | Entra ID tenant ID |
   | `AZURE_SUBSCRIPTION_ID` | Target subscription ID |

   **Env vars** (edit the `env:` block at the top of each workflow file):

   | Name | Value |
   |---|---|
   | `AZURE_RG` | Resource group name |
   | `BASE_NAME` | Base name for resources (e.g. `websummary`) |

### Deploy step by step

1. **Deploy infrastructure** — run the *Deploy Infrastructure* workflow from the Actions tab. Choose whether to deploy a new Foundry resource or supply your existing one.

2. **Deploy apps** — place your GitHub Spark app files in the `frontend/` directory, then run the *Deploy Apps* workflow. It deploys the backend and frontend in parallel, then automatically configures `ALLOWED_ORIGINS` on the backend to the frontend URL.

## Output Format

Each summary includes a concise bullet point overview with a link back to the source page. Customise the output format by editing `prompt.txt` or providing your own prompt file.