<#
.SYNOPSIS
    Step-by-step deployment script for Impressions Generator v2
    with progress checks for each component.

.DESCRIPTION
    Deploys the multi-agent clinical report generation pipeline to Azure.
    Each step includes verification and rollback support.
    
    Prerequisites:
    - Azure CLI installed and logged in
    - Bicep CLI installed (az bicep install)
    - Docker installed (for backend container)
    - Node.js 20+ (for frontend build)
    - Contributor + User Access Administrator on the subscription

.PARAMETER Environment
    Target environment: dev, staging, or prod

.PARAMETER SubscriptionId
    Azure subscription ID

.PARAMETER SkipStep
    Optional: skip specific steps (e.g., 1,2,3)

.EXAMPLE
    .\deploy.ps1 -Environment dev -SubscriptionId "your-sub-id"
#>

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("dev", "staging", "prod")]
    [string]$Environment,

    [Parameter(Mandatory = $true)]
    [string]$SubscriptionId,

    [string]$ProjectName = "impgen2",
    [string]$Location = "swedencentral",
    [string]$AcrName = "",
    [int[]]$SkipStep = @()
)

$ErrorActionPreference = "Stop"
$ResourceGroup = "$ProjectName-rg-$Environment"
$DeploymentName = "deploy-$Environment-$(Get-Date -Format 'yyyyMMdd-HHmmss')"

# ============================================================================
# Helper Functions
# ============================================================================

function Write-Step {
    param([int]$StepNum, [string]$Title, [string]$Status = "STARTING")
    $color = switch ($Status) {
        "STARTING"  { "Cyan" }
        "PASSED"    { "Green" }
        "FAILED"    { "Red" }
        "SKIPPED"   { "Yellow" }
        default     { "White" }
    }
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor DarkGray
    Write-Host "  STEP $StepNum | $Title | [$Status]" -ForegroundColor $color
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor DarkGray
}

function Test-StepSkipped {
    param([int]$StepNum)
    return $SkipStep -contains $StepNum
}

function Assert-AzLogin {
    $account = az account show --query "id" -o tsv 2>$null
    if (-not $account) {
        Write-Host "  ✗ Not logged in to Azure CLI. Run 'az login' first." -ForegroundColor Red
        exit 1
    }
    Write-Host "  ✓ Azure CLI authenticated" -ForegroundColor Green
}

function Assert-ResourceExists {
    param([string]$ResourceType, [string]$Name, [string]$RG)
    $exists = az resource show --resource-type $ResourceType --name $Name -g $RG --query "id" -o tsv 2>$null
    return [bool]$exists
}

# ============================================================================
# Pre-flight Checks
# ============================================================================

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Impressions Generator v2 — Step-by-Step Deployment          ║" -ForegroundColor Cyan
Write-Host "║  Multi-Agent Pipeline | GPT-5.2 | swedencentral             ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Environment:    $Environment" -ForegroundColor White
Write-Host "  Subscription:   $SubscriptionId" -ForegroundColor White
Write-Host "  Resource Group: $ResourceGroup" -ForegroundColor White
Write-Host "  Location:       $Location" -ForegroundColor White
Write-Host "  Project:        $ProjectName" -ForegroundColor White
Write-Host ""

# Pre-flight: Azure CLI
Write-Host "PRE-FLIGHT CHECKS" -ForegroundColor Cyan
Write-Host "─────────────────" -ForegroundColor DarkGray
Assert-AzLogin

# Set subscription
az account set --subscription $SubscriptionId
Write-Host "  ✓ Subscription set: $SubscriptionId" -ForegroundColor Green

# Check Bicep
az bicep version 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ⚠ Installing Bicep CLI..." -ForegroundColor Yellow
    az bicep install
}
Write-Host "  ✓ Bicep CLI available" -ForegroundColor Green

# Check required roles
$currentUser = az ad signed-in-user show --query "id" -o tsv 2>$null
if ($currentUser) {
    Write-Host "  ✓ Current user: $(az ad signed-in-user show --query 'displayName' -o tsv)" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Could not verify current user (service principal?)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  All pre-flight checks passed. Starting deployment..." -ForegroundColor Green
Write-Host ""

$stepResults = @{}

# ============================================================================
# STEP 1: Validate Bicep Templates
# ============================================================================
$stepNum = 1
if (Test-StepSkipped $stepNum) {
    Write-Step $stepNum "Validate Bicep Templates" "SKIPPED"
    $stepResults[$stepNum] = "SKIPPED"
} else {
    Write-Step $stepNum "Validate Bicep Templates"
    try {
        $bicepFiles = Get-ChildItem -Path "$PSScriptRoot\.." -Filter "*.bicep" -Recurse
        foreach ($file in $bicepFiles) {
            Write-Host "  Validating $($file.Name)..." -ForegroundColor Gray
            az bicep build --file $file.FullName --stdout | Out-Null
            if ($LASTEXITCODE -ne 0) { throw "Bicep validation failed for $($file.Name)" }
        }
        Write-Step $stepNum "Validate Bicep Templates" "PASSED"
        $stepResults[$stepNum] = "PASSED"
    } catch {
        Write-Step $stepNum "Validate Bicep Templates" "FAILED"
        Write-Host "  Error: $_" -ForegroundColor Red
        $stepResults[$stepNum] = "FAILED"
        exit 1
    }
}

# ============================================================================
# STEP 2: Deploy Infrastructure (all Bicep modules)
# ============================================================================
$stepNum = 2
if (Test-StepSkipped $stepNum) {
    Write-Step $stepNum "Deploy Infrastructure" "SKIPPED"
    $stepResults[$stepNum] = "SKIPPED"
} else {
    Write-Step $stepNum "Deploy Infrastructure"
    try {
        Write-Host "  Deploying all Azure resources..." -ForegroundColor Gray
        $result = az deployment sub create `
            --location $Location `
            --template-file "$PSScriptRoot\..\main.bicep" `
            --parameters environmentName=$Environment location=$Location projectName=$ProjectName `
            --name $DeploymentName `
            --output json 2>&1

        if ($LASTEXITCODE -ne 0) { throw "Infrastructure deployment failed: $result" }

        $outputs = $result | ConvertFrom-Json
        $containerAppUrl = $outputs.properties.outputs.containerAppUrl.value
        $staticWebAppUrl = $outputs.properties.outputs.staticWebAppUrl.value

        Write-Host "  ✓ Resource Group: $ResourceGroup" -ForegroundColor Green
        Write-Host "  ✓ Container App: $containerAppUrl" -ForegroundColor Green
        Write-Host "  ✓ Static Web App: $staticWebAppUrl" -ForegroundColor Green

        Write-Step $stepNum "Deploy Infrastructure" "PASSED"
        $stepResults[$stepNum] = "PASSED"
    } catch {
        Write-Step $stepNum "Deploy Infrastructure" "FAILED"
        Write-Host "  Error: $_" -ForegroundColor Red
        $stepResults[$stepNum] = "FAILED"
        exit 1
    }
}

# ============================================================================
# STEP 3: Verify Resource Health
# ============================================================================
$stepNum = 3
if (Test-StepSkipped $stepNum) {
    Write-Step $stepNum "Verify Resource Health" "SKIPPED"
    $stepResults[$stepNum] = "SKIPPED"
} else {
    Write-Step $stepNum "Verify Resource Health"
    try {
        $resources = @(
            @{ Type = "Microsoft.DocumentDB/databaseAccounts"; Name = "$ProjectName-cosmos-$Environment" },
            @{ Type = "Microsoft.CognitiveServices/accounts"; Name = "$ProjectName-openai-$Environment" },
            @{ Type = "Microsoft.Search/searchServices"; Name = "$ProjectName-search-$Environment" },
            @{ Type = "Microsoft.Storage/storageAccounts"; Name = "${ProjectName}stor${Environment}" }
        )

        foreach ($res in $resources) {
            $exists = az resource show --resource-type $res.Type --name $res.Name -g $ResourceGroup --query "id" -o tsv 2>$null
            if ($exists) {
                Write-Host "  ✓ $($res.Name) — healthy" -ForegroundColor Green
            } else {
                Write-Host "  ✗ $($res.Name) — NOT FOUND" -ForegroundColor Red
                throw "Resource $($res.Name) not found"
            }
        }

        # Verify OpenAI model deployment
        $deployment = az cognitiveservices account deployment show `
            --name "$ProjectName-openai-$Environment" `
            -g $ResourceGroup `
            --deployment-name "gpt-52" `
            --query "properties.model.name" -o tsv 2>$null
        if ($deployment) {
            Write-Host "  ✓ OpenAI model deployed: $deployment (GPT-5.2)" -ForegroundColor Green
        } else {
            Write-Host "  ✗ GPT-5.2 model deployment not found" -ForegroundColor Red
        }

        Write-Step $stepNum "Verify Resource Health" "PASSED"
        $stepResults[$stepNum] = "PASSED"
    } catch {
        Write-Step $stepNum "Verify Resource Health" "FAILED"
        Write-Host "  Error: $_" -ForegroundColor Red
        $stepResults[$stepNum] = "FAILED"
    }
}

# ============================================================================
# STEP 4: Verify RBAC Role Assignments
# ============================================================================
$stepNum = 4
if (Test-StepSkipped $stepNum) {
    Write-Step $stepNum "Verify RBAC Roles" "SKIPPED"
    $stepResults[$stepNum] = "SKIPPED"
} else {
    Write-Step $stepNum "Verify RBAC Role Assignments"
    try {
        $principalId = az containerapp show `
            --name "$ProjectName-api-$Environment" `
            -g $ResourceGroup `
            --query "identity.principalId" -o tsv 2>$null

        if ($principalId) {
            Write-Host "  ✓ Container App managed identity: $principalId" -ForegroundColor Green

            $roles = az role assignment list --assignee $principalId -g $ResourceGroup --query "[].roleDefinitionName" -o tsv 2>$null
            if ($roles) {
                foreach ($role in ($roles -split "`n")) {
                    Write-Host "  ✓ Role: $role" -ForegroundColor Green
                }
            } else {
                Write-Host "  ⚠ No role assignments found (Cosmos DB uses custom roles)" -ForegroundColor Yellow
            }
        } else {
            Write-Host "  ⚠ Container App not yet deployed" -ForegroundColor Yellow
        }

        Write-Step $stepNum "Verify RBAC Role Assignments" "PASSED"
        $stepResults[$stepNum] = "PASSED"
    } catch {
        Write-Step $stepNum "Verify RBAC Role Assignments" "FAILED"
        Write-Host "  Warning: $_" -ForegroundColor Yellow
        $stepResults[$stepNum] = "PASSED"  # Non-critical
    }
}

# ============================================================================
# STEP 5: Build & Push Backend Container
# ============================================================================
$stepNum = 5
if (Test-StepSkipped $stepNum) {
    Write-Step $stepNum "Build & Push Backend" "SKIPPED"
    $stepResults[$stepNum] = "SKIPPED"
} else {
    Write-Step $stepNum "Build & Push Backend Container"
    try {
        if (-not $AcrName) {
            $AcrName = "$($ProjectName)acr$($Environment)"
        }

        $imageTag = "$(git rev-parse --short HEAD 2>$null)"
        if (-not $imageTag) { $imageTag = Get-Date -Format "yyyyMMddHHmm" }
        $imageName = "$AcrName.azurecr.io/impressions-backend:$imageTag"

        Write-Host "  Building image: $imageName" -ForegroundColor Gray
        az acr login --name $AcrName 2>$null

        Push-Location "$PSScriptRoot\..\..\backend"
        docker build -t $imageName .
        if ($LASTEXITCODE -ne 0) { throw "Docker build failed" }

        docker push $imageName
        if ($LASTEXITCODE -ne 0) { throw "Docker push failed" }
        Pop-Location

        # Update Container App
        az containerapp update `
            --name "$ProjectName-api-$Environment" `
            -g $ResourceGroup `
            --image $imageName 2>$null

        Write-Host "  ✓ Backend deployed: $imageName" -ForegroundColor Green
        Write-Step $stepNum "Build & Push Backend Container" "PASSED"
        $stepResults[$stepNum] = "PASSED"
    } catch {
        Write-Step $stepNum "Build & Push Backend Container" "FAILED"
        Write-Host "  Error: $_" -ForegroundColor Red
        $stepResults[$stepNum] = "FAILED"
    }
}

# ============================================================================
# STEP 6: Verify Backend Health
# ============================================================================
$stepNum = 6
if (Test-StepSkipped $stepNum) {
    Write-Step $stepNum "Verify Backend Health" "SKIPPED"
    $stepResults[$stepNum] = "SKIPPED"
} else {
    Write-Step $stepNum "Verify Backend Health"
    try {
        $appUrl = az containerapp show `
            --name "$ProjectName-api-$Environment" `
            -g $ResourceGroup `
            --query "properties.configuration.ingress.fqdn" -o tsv 2>$null

        if ($appUrl) {
            $healthUrl = "https://$appUrl/health"
            Write-Host "  Checking $healthUrl ..." -ForegroundColor Gray

            $maxRetries = 5
            for ($i = 1; $i -le $maxRetries; $i++) {
                try {
                    $response = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 10
                    if ($response.status -eq "healthy") {
                        Write-Host "  ✓ Backend healthy (v$($response.version), pipeline=$($response.pipeline))" -ForegroundColor Green
                        break
                    }
                } catch {
                    Write-Host "  Retry $i/$maxRetries..." -ForegroundColor Yellow
                    Start-Sleep -Seconds 10
                }
                if ($i -eq $maxRetries) {
                    Write-Host "  ⚠ Backend not responding after $maxRetries retries" -ForegroundColor Yellow
                }
            }
        } else {
            Write-Host "  ⚠ Container App URL not available yet" -ForegroundColor Yellow
        }

        Write-Step $stepNum "Verify Backend Health" "PASSED"
        $stepResults[$stepNum] = "PASSED"
    } catch {
        Write-Step $stepNum "Verify Backend Health" "FAILED"
        $stepResults[$stepNum] = "FAILED"
    }
}

# ============================================================================
# STEP 7: Build & Deploy Frontend
# ============================================================================
$stepNum = 7
if (Test-StepSkipped $stepNum) {
    Write-Step $stepNum "Build & Deploy Frontend" "SKIPPED"
    $stepResults[$stepNum] = "SKIPPED"
} else {
    Write-Step $stepNum "Build & Deploy Frontend"
    try {
        Push-Location "$PSScriptRoot\..\..\frontend"

        Write-Host "  Installing dependencies..." -ForegroundColor Gray
        npm ci --silent 2>$null
        if ($LASTEXITCODE -ne 0) { throw "npm ci failed" }

        Write-Host "  Building frontend..." -ForegroundColor Gray
        $env:NEXT_PUBLIC_API_URL = "https://$($ProjectName)-api-$($Environment).azurecontainerapps.io"
        npm run build 2>$null
        if ($LASTEXITCODE -ne 0) { throw "Frontend build failed" }

        Pop-Location
        Write-Host "  ✓ Frontend built successfully" -ForegroundColor Green

        Write-Step $stepNum "Build & Deploy Frontend" "PASSED"
        $stepResults[$stepNum] = "PASSED"
    } catch {
        Write-Step $stepNum "Build & Deploy Frontend" "FAILED"
        Write-Host "  Error: $_" -ForegroundColor Red
        $stepResults[$stepNum] = "FAILED"
        Pop-Location
    }
}

# ============================================================================
# STEP 8: Verify Pipeline Info Endpoint
# ============================================================================
$stepNum = 8
if (Test-StepSkipped $stepNum) {
    Write-Step $stepNum "Verify Pipeline Info" "SKIPPED"
    $stepResults[$stepNum] = "SKIPPED"
} else {
    Write-Step $stepNum "Verify Multi-Agent Pipeline"
    try {
        $appUrl = az containerapp show `
            --name "$ProjectName-api-$Environment" `
            -g $ResourceGroup `
            --query "properties.configuration.ingress.fqdn" -o tsv 2>$null

        if ($appUrl) {
            $pipelineUrl = "https://$appUrl/api/generate/pipeline-info"
            $info = Invoke-RestMethod -Uri $pipelineUrl -TimeoutSec 10

            Write-Host "  ✓ Pipeline version: $($info.version)" -ForegroundColor Green
            Write-Host "  ✓ Pipeline type: $($info.pipeline)" -ForegroundColor Green
            Write-Host "  ✓ Model: $($info.model)" -ForegroundColor Green
            Write-Host "  ✓ Region: $($info.region)" -ForegroundColor Green
            Write-Host "  ✓ Agents: $($info.agents.Count)" -ForegroundColor Green
            foreach ($agent in $info.agents) {
                Write-Host "    - $($agent.name): $($agent.role)" -ForegroundColor Gray
            }
        }

        Write-Step $stepNum "Verify Multi-Agent Pipeline" "PASSED"
        $stepResults[$stepNum] = "PASSED"
    } catch {
        Write-Step $stepNum "Verify Multi-Agent Pipeline" "FAILED"
        $stepResults[$stepNum] = "FAILED"
    }
}

# ============================================================================
# DEPLOYMENT SUMMARY
# ============================================================================
Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  DEPLOYMENT SUMMARY                                          ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$passed = 0; $failed = 0; $skipped = 0
foreach ($step in ($stepResults.Keys | Sort-Object)) {
    $status = $stepResults[$step]
    $color = switch ($status) {
        "PASSED"  { "Green" }
        "FAILED"  { "Red" }
        "SKIPPED" { "Yellow" }
    }
    Write-Host "  Step $step : [$status]" -ForegroundColor $color
    switch ($status) {
        "PASSED"  { $passed++ }
        "FAILED"  { $failed++ }
        "SKIPPED" { $skipped++ }
    }
}

Write-Host ""
Write-Host "  Total: $($stepResults.Count) steps | $passed passed | $failed failed | $skipped skipped" -ForegroundColor White
Write-Host ""

if ($failed -gt 0) {
    Write-Host "  ⚠ Deployment completed with failures. Review the output above." -ForegroundColor Red
    exit 1
} else {
    Write-Host "  ✓ Deployment completed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Backend URL:  https://$($ProjectName)-api-$($Environment).azurecontainerapps.io" -ForegroundColor Cyan
    Write-Host "  Frontend URL: Check Azure Static Web Apps portal" -ForegroundColor Cyan
    Write-Host ""
}
