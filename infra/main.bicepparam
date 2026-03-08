using 'main.bicep'

param baseName = 'websummariser'

// Option A: Deploy a new Foundry resource (set deployFoundry to true)
param deployFoundry = false
// param foundryModelName = 'gpt-4o'
// param foundryModelVersion = '2024-11-20'
// param foundryModelCapacity = 10

// Option B: Use an existing Foundry resource (set deployFoundry to false)
param existingFoundryResourceId = '/subscriptions/2b973351-38a5-4b95-9d56-d0d04a54e54f/resourceGroups/foundry-rg/providers/Microsoft.CognitiveServices/accounts/lab-foundry-fdry'
param existingFoundryEndpoint = 'https://lab-foundry-fdry.cognitiveservices.azure.com/'

param foundryDeployment = 'gpt-5-chat'
