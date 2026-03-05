// ============================================================================
// RBAC Module — Role assignments for managed identity access
// Grants the Container App's managed identity access to all Azure services
// ============================================================================

@description('Container App managed identity principal ID')
param containerAppPrincipalId string

@description('Cosmos DB account name')
param cosmosAccountName string

@description('Storage account name')
param storageAccountName string

@description('Azure OpenAI account resource ID')
param openaiAccountId string

@description('AI Search service name')
param searchServiceName string

// Role definition IDs
var cosmosDbDataContributor = '00000000-0000-0000-0000-000000000002' // Cosmos DB Built-in Data Contributor
var storageBlobContributor = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
var cognitiveServicesUser = 'a97b65f3-24c7-4388-baec-2e87135dc908'
var searchIndexDataContributor = '8ebe5a00-799e-43f5-93ac-243d3dce84a7'

// --- Cosmos DB Data Contributor ---
resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-02-15-preview' existing = {
  name: cosmosAccountName
}

resource cosmosRoleAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-02-15-preview' = {
  parent: cosmosAccount
  name: guid(cosmosAccount.id, containerAppPrincipalId, cosmosDbDataContributor)
  properties: {
    roleDefinitionId: '${cosmosAccount.id}/sqlRoleDefinitions/${cosmosDbDataContributor}'
    principalId: containerAppPrincipalId
    scope: cosmosAccount.id
  }
}

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

// --- Cognitive Services OpenAI User ---
resource openaiRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openaiAccountId, containerAppPrincipalId, cognitiveServicesUser)
  scope: resourceGroup
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
