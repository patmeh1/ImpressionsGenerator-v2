// ============================================================================
// RBAC Module — Role assignments for managed identity access
// Grants the Container App's managed identity access to all Azure services
// ============================================================================

@description('Container App managed identity principal ID')
param containerAppPrincipalId string

@description('Storage account name')
param storageAccountName string

@description('Azure OpenAI account resource ID')
param openaiAccountId string

@description('AI Search service name')
param searchServiceName string

// Role definition IDs
var storageBlobContributor = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
var cognitiveServicesUser = 'a97b65f3-24c7-4388-baec-2e87135dc908'
var searchIndexDataContributor = '8ebe5a00-799e-43f5-93ac-243d3dce84a7'

// --- Storage Blob Data Contributor ---
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

resource storageRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, containerAppPrincipalId, storageBlobContributor)
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobContributor)
    principalId: containerAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// --- Cognitive Services OpenAI User (scoped to the OpenAI account) ---
resource openaiAccount 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' existing = {
  name: split(openaiAccountId, '/')[8]
}

resource openaiRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openaiAccount.id, containerAppPrincipalId, cognitiveServicesUser)
  scope: openaiAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesUser)
    principalId: containerAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// --- Search Index Data Contributor ---
resource searchService 'Microsoft.Search/searchServices@2024-03-01-preview' existing = {
  name: searchServiceName
}

resource searchRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(searchService.id, containerAppPrincipalId, searchIndexDataContributor)
  scope: searchService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchIndexDataContributor)
    principalId: containerAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Note: Cosmos DB RBAC uses SQL role assignments which are handled
// within the Cosmos DB module or via az CLI post-deployment.
