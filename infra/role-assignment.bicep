// Role assignment scoped to a Cognitive Services account.
// Deployed as a cross-resource-group module from main.bicep.

param foundryAccountName string
param principalId string
param roleDefinitionId string

resource foundryResource 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: foundryAccountName
}

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundryResource.id, principalId, roleDefinitionId)
  scope: foundryResource
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitionId)
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}
