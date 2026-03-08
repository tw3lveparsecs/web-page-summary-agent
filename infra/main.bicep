targetScope = 'resourceGroup'

// Parameters
@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Base name used to derive resource names.')
param baseName string

@description('Deploy a new Microsoft Foundry (AI Services) resource. Set to false if you already have one.')
param deployFoundry bool = false

@description('Resource ID of an existing Microsoft Foundry account. Required when deployFoundry is false.')
param existingFoundryResourceId string = ''

@description('Endpoint URL of an existing Microsoft Foundry account. Required when deployFoundry is false.')
param existingFoundryEndpoint string = ''

@description('Model name to deploy when creating a new Foundry resource.')
param foundryModelName string = 'gpt-4o'

@description('Model version to deploy when creating a new Foundry resource.')
param foundryModelVersion string = '2024-11-20'

@description('Token capacity for the model deployment.')
param foundryModelCapacity int = 10

@description('App Service Plan SKU.')
param appServicePlanSku string = 'B1'

@description('Python version for the backend web app.')
param pythonVersion string = '3.13'

@description('Node.js version for the frontend web app.')
param nodeVersion string = '20-lts'

@description('Microsoft Foundry model deployment name.')
param foundryDeployment string = 'gpt-4o'

@description('Microsoft Foundry API version.')
param foundryApiVersion string = '2024-12-01-preview'

@description('Allowed origins for CORS (comma separated). Set to the frontend URL after deployment.')
param allowedOrigins string = '*'

// Resolved values: use new Foundry outputs when deploying, otherwise use existing params
var foundryResourceId = foundryAccount.?outputs.?resourceId ?? existingFoundryResourceId
var foundryEndpoint = foundryAccount.?outputs.?endpoint ?? existingFoundryEndpoint

// App settings for the backend and frontend web apps
var backendAppSettings = {
  FOUNDRY_AUTH: 'entra'
  FOUNDRY_ENDPOINT: foundryEndpoint
  FOUNDRY_DEPLOYMENT: foundryDeployment
  FOUNDRY_API_VERSION: foundryApiVersion
  ALLOWED_ORIGINS: allowedOrigins
  SCM_DO_BUILD_DURING_DEPLOYMENT: 'true'
}
var frontendAppSettings = {
  API_BASE_URL: 'https://${baseName}-api.azurewebsites.net'
  SCM_DO_BUILD_DURING_DEPLOYMENT: 'true'
}

// Cognitive Services OpenAI User role definition ID
var cognitiveServicesOpenAIUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

// Optional: Microsoft Foundry (AI Services) resource with model deployment
module foundryAccount 'br/public:avm/res/cognitive-services/account:0.14.1' = if (deployFoundry) {
  name: 'foundryAccount'
  params: {
    name: '${baseName}-foundry'
    location: location
    kind: 'AIServices'
    customSubDomainName: '${baseName}-foundry'
    deployments: [
      {
        name: foundryDeployment
        model: {
          format: 'OpenAI'
          name: foundryModelName
          version: foundryModelVersion
        }
        sku: {
          name: 'Standard'
          capacity: foundryModelCapacity
        }
      }
    ]
  }
}

// App Service Plan (shared by frontend and backend)
module appServicePlan 'br/public:avm/res/web/serverfarm:0.7.0' = {
  name: 'appServicePlan'
  params: {
    name: '${baseName}-plan'
    location: location
    kind: 'Linux'
    reserved: true
    skuName: appServicePlanSku
    skuCapacity: 1
  }
}

// Backend Web App (Python agent API)
module backendApp 'br/public:avm/res/web/site:0.22.0' = {
  name: 'backendApp'
  params: {
    name: '${baseName}-api'
    location: location
    kind: 'app,linux'
    serverFarmResourceId: appServicePlan.outputs.resourceId
    managedIdentities: {
      systemAssigned: true
    }
    siteConfig: {
      linuxFxVersion: 'PYTHON|${pythonVersion}'
      appCommandLine: 'startup.sh'
      alwaysOn: true
    }
    configs: [
      {
        name: 'appsettings'
        properties: backendAppSettings
      }
    ]
  }
}

// Frontend Web App (GitHub Spark app)
module frontendApp 'br/public:avm/res/web/site:0.22.0' = {
  name: 'frontendApp'
  params: {
    name: '${baseName}-web'
    location: location
    kind: 'app,linux'
    serverFarmResourceId: appServicePlan.outputs.resourceId
    siteConfig: {
      linuxFxVersion: 'NODE|${nodeVersion}'
      alwaysOn: true
    }
    configs: [
      {
        name: 'appsettings'
        properties: frontendAppSettings
      }
    ]
  }
}

// Role assignment: grant the backend's system assigned identity
// "Cognitive Services OpenAI User" on the Foundry resource
module roleAssignment 'br/public:avm/ptn/authorization/resource-role-assignment:0.1.2' = {
  name: 'backendFoundryRole'
  params: {
    principalId: backendApp.outputs.?systemAssignedMIPrincipalId!
    roleDefinitionId: cognitiveServicesOpenAIUserRoleId
    resourceId: foundryResourceId
    principalType: 'ServicePrincipal'
  }
}

// Outputs
output backendUrl string = 'https://${baseName}-api.azurewebsites.net'
output frontendUrl string = 'https://${baseName}-web.azurewebsites.net'
output backendPrincipalId string = backendApp.outputs.?systemAssignedMIPrincipalId!
output foundryEndpointUrl string = foundryEndpoint
output foundryResourceIdOutput string = foundryResourceId
