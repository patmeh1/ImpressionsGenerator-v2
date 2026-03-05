// ============================================================================
// Azure OpenAI Module — GPT-5.2 deployment in swedencentral
// Multi-agent pipeline for clinical report generation
// ============================================================================

@description('Azure region for all resources')
param location string

@allowed(['dev', 'staging', 'prod'])
@description('Environment name')
param environmentName string

@description('Project name used for resource naming')
param projectName string

// 30K TPM for dev/staging, 120K TPM for prod
var modelCapacity = environmentName == 'prod' ? 120 : 30

// --- Azure OpenAI Account ---
resource openaiAccount 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' = {
  name: '${projectName}-openai-${environmentName}'
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: '${projectName}-openai-${environmentName}'
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
  }
}

// --- GPT-5.2 Model Deployment ---
resource gpt52Deployment 'Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview' = {
  parent: openaiAccount
  name: 'gpt-52'
  sku: {
    name: 'Standard'
    capacity: modelCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-5.2'
      version: '2026-01-01'
    }
    raiPolicyName: 'Microsoft.DefaultV2'
  }
}

// --- Outputs ---
output openaiEndpoint string = openaiAccount.properties.endpoint
output openaiAccountId string = openaiAccount.id
output openaiDeploymentName string = gpt52Deployment.name
output openaiPrincipalId string = openaiAccount.identity.principalId
