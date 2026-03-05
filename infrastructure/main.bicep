// ============================================================================
// Main Orchestrator — Impressions Generator v2 Infrastructure
// Multi-agent pipeline deployed to swedencentral with GPT-5.2
// Step-by-step deployment with dependency ordering
// ============================================================================

targetScope = 'subscription'

@allowed(['dev', 'staging', 'prod'])
@description('Deployment environment')
param environmentName string

@description('Azure region for all resources')
param location string = 'swedencentral'

@description('Project name used for resource naming')
param projectName string = 'impgen2'

// --- Resource Group ---
resource resourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: '${projectName}-rg-${environmentName}'
  location: location
  tags: {
    environment: environmentName
    project: projectName
    compliance: 'HIPAA'
    managedBy: 'bicep'
    version: '2.0.0'
    pipeline: 'multi-agent'
  }
}

// --- Step 1: Monitoring (Log Analytics + App Insights) ---
module monitoring 'modules/monitoring.bicep' = {
  name: 'step1-monitoring'
  scope: resourceGroup
  params: {
    location: location
    environmentName: environmentName
    projectName: projectName
  }
}

// --- Step 2: Storage Account ---
module storage 'modules/storage.bicep' = {
  name: 'step2-storage'
  scope: resourceGroup
  params: {
    location: location
    environmentName: environmentName
    projectName: projectName
  }
}

// --- Step 3: Cosmos DB ---
module cosmosdb 'modules/cosmosdb.bicep' = {
  name: 'step3-cosmosdb'
  scope: resourceGroup
  params: {
    location: location
    environmentName: environmentName
    projectName: projectName
  }
}

// --- Step 4: Azure OpenAI (GPT-5.2 in swedencentral) ---
module openai 'modules/openai.bicep' = {
  name: 'step4-openai'
  scope: resourceGroup
  params: {
    location: location
    environmentName: environmentName
    projectName: projectName
  }
}

// --- Step 5: AI Search ---
module aiSearch 'modules/ai-search.bicep' = {
  name: 'step5-ai-search'
  scope: resourceGroup
  params: {
    location: location
    environmentName: environmentName
    projectName: projectName
  }
}

// --- Step 6: Container Apps (depends on all above) ---
module containerApps 'modules/container-apps.bicep' = {
  name: 'step6-container-apps'
  scope: resourceGroup
  params: {
    location: location
    environmentName: environmentName
    projectName: projectName
    cosmosEndpoint: cosmosdb.outputs.cosmosEndpoint
    storageAccountName: storage.outputs.storageAccountName
    blobEndpoint: storage.outputs.blobEndpoint
    openaiEndpoint: openai.outputs.openaiEndpoint
    openaiDeploymentName: openai.outputs.openaiDeploymentName
    searchEndpoint: aiSearch.outputs.searchEndpoint
    searchServiceName: aiSearch.outputs.searchServiceName
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
  }
}

// --- Step 7: Key Vault (depends on container apps for principal ID) ---
module keyvault 'modules/keyvault.bicep' = {
  name: 'step7-keyvault'
  scope: resourceGroup
  params: {
    location: location
    environmentName: environmentName
    projectName: projectName
    containerAppPrincipalId: containerApps.outputs.containerAppPrincipalId
    cosmosEndpoint: cosmosdb.outputs.cosmosEndpoint
    storageAccountName: storage.outputs.storageAccountName
    openaiEndpoint: openai.outputs.openaiEndpoint
    searchEndpoint: aiSearch.outputs.searchEndpoint
  }
}

// --- Step 8: Static Web App (westeurope — SWA not available in swedencentral) ---
module staticWebApp 'modules/static-web-app.bicep' = {
  name: 'step8-static-web-app'
  scope: resourceGroup
  params: {
    location: 'westeurope'
    environmentName: environmentName
    projectName: projectName
  }
}

// --- Step 9: RBAC Role Assignments ---
module rbac 'modules/rbac.bicep' = {
  name: 'step9-rbac'
  scope: resourceGroup
  params: {
    containerAppPrincipalId: containerApps.outputs.containerAppPrincipalId
    storageAccountName: storage.outputs.storageAccountName
    openaiAccountId: openai.outputs.openaiAccountId
    searchServiceName: aiSearch.outputs.searchServiceName
  }
}

// --- Outputs ---
output resourceGroupName string = resourceGroup.name
output containerAppUrl string = containerApps.outputs.containerAppUrl
output staticWebAppUrl string = staticWebApp.outputs.staticWebAppUrl
output cosmosEndpoint string = cosmosdb.outputs.cosmosEndpoint
output openaiEndpoint string = openai.outputs.openaiEndpoint
output searchEndpoint string = aiSearch.outputs.searchEndpoint
output keyVaultUri string = keyvault.outputs.keyVaultUri
output appInsightsConnectionString string = monitoring.outputs.appInsightsConnectionString
output storageAccountName string = storage.outputs.storageAccountName
