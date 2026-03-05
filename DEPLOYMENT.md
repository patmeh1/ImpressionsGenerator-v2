# Deployment Guide — Impressions Generator v2

## Prerequisites

### Required Tools
- **Azure CLI** ≥ 2.60 with Bicep extension
- **Docker** ≥ 24.0
- **Node.js** ≥ 20 LTS
- **Python** ≥ 3.11
- **Git**

### Required Azure Access
| Role | Scope | Purpose |
|------|-------|---------|
| Contributor | Subscription | Deploy resources |
| User Access Administrator | Subscription | Assign RBAC roles |
| Cognitive Services Contributor | Resource Group | Deploy OpenAI models |

### Required GitHub Secrets
| Secret | Description |
|--------|-------------|
| `AZURE_SUBSCRIPTION_ID` | Target Azure subscription |
| `AZURE_TENANT_ID` | Microsoft Entra tenant |
| `AZURE_CLIENT_ID` | Service principal / app registration |
| `ACR_NAME` | Azure Container Registry name |
| `SWA_DEPLOYMENT_TOKEN` | Static Web App token |
| `BACKEND_URL` | Deployed backend URL |

---

## Step-by-Step Deployment

### Step 1: Clone & Configure

```bash
git clone https://github.com/patmeh1/ImpressionsGenerator-v2.git
cd ImpressionsGenerator-v2

# Copy and edit environment config
cp backend/.env.example backend/.env
# Edit backend/.env with your Azure credentials
```

**Progress check:** `cat backend/.env` — verify all values are set.

---

### Step 2: Validate Bicep Templates

```bash
az bicep install
az bicep build --file infrastructure/main.bicep --stdout > /dev/null
echo "✓ Bicep templates valid"
```

**Progress check:** Command exits with code 0.

---

### Step 3: Deploy Azure Infrastructure

```bash
az login
az account set --subscription YOUR_SUBSCRIPTION_ID

az deployment sub create \
  --location swedencentral \
  --template-file infrastructure/main.bicep \
  --parameters environmentName=dev location=swedencentral projectName=impgen2 \
  --name "manual-deploy-$(date +%Y%m%d)"
```

**Progress check:**
```bash
az resource list -g impgen2-rg-dev --query "[].{Name:name, Type:type}" -o table
```
Expected: 8+ resources (Cosmos, OpenAI, Search, Storage, etc.)

---

### Step 4: Verify GPT-5.2 Deployment

```bash
az cognitiveservices account deployment show \
  --name impgen2-openai-dev \
  -g impgen2-rg-dev \
  --deployment-name gpt-52 \
  --query "{model:properties.model.name, version:properties.model.version}" -o table
```

**Progress check:** Model = `gpt-5.2`, deployed in swedencentral.

---

### Step 5: Verify RBAC Role Assignments

```bash
PRINCIPAL_ID=$(az containerapp show \
  --name impgen2-api-dev -g impgen2-rg-dev \
  --query "identity.principalId" -o tsv)

az role assignment list --assignee $PRINCIPAL_ID \
  -g impgen2-rg-dev --query "[].roleDefinitionName" -o table
```

**Progress check:** Should show:
- Storage Blob Data Contributor
- Cognitive Services OpenAI User
- Search Index Data Contributor

---

### Step 6: Build & Deploy Backend

```bash
# Login to ACR
az acr login --name impgen2acrdev

# Build and push
cd backend
docker build -t impgen2acrdev.azurecr.io/impressions-backend:latest .
docker push impgen2acrdev.azurecr.io/impressions-backend:latest

# Update Container App
az containerapp update \
  --name impgen2-api-dev \
  -g impgen2-rg-dev \
  --image impgen2acrdev.azurecr.io/impressions-backend:latest
```

**Progress check:**
```bash
curl https://impgen2-api-dev.azurecontainerapps.io/health
# Expected: {"status":"healthy","version":"2.0.0","pipeline":"multi-agent"}
```

---

### Step 7: Verify Multi-Agent Pipeline

```bash
curl https://impgen2-api-dev.azurecontainerapps.io/api/generate/pipeline-info | jq .
```

**Progress check:** Should return 6 agents: style_analyst, clinical_rag, report_writer, grounding_validator, clinical_reviewer, supervisor.

---

### Step 8: Build & Deploy Frontend

```bash
cd frontend
npm ci
NEXT_PUBLIC_API_URL=https://impgen2-api-dev.azurecontainerapps.io npm run build
# Deploy via SWA CLI or GitHub Actions
```

**Progress check:** Frontend accessible at Static Web App URL.

---

### Step 9: End-to-End Verification

```bash
# Test the full pipeline
curl -X POST https://impgen2-api-dev.azurecontainerapps.io/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "dictated_text": "CT chest without contrast. Lungs clear bilaterally. No pleural effusion.",
    "doctor_id": "test-doctor",
    "report_type": "CT",
    "body_region": "Chest"
  }'
```

**Progress check:** Response includes:
- `findings`, `impressions`, `recommendations`
- `grounding.is_grounded` = true
- `review.overall_quality` ≥ 0.75
- `decision` = "accepted"
- `pipeline_trace` with all 5 agents

---

## Automated Deployment

Use the provided deployment script:

```powershell
# PowerShell
.\infrastructure\scripts\deploy.ps1 -Environment dev -SubscriptionId YOUR_SUB_ID
```

```bash
# Bash
./infrastructure/scripts/deploy.sh dev YOUR_SUB_ID
```

Both scripts include step-by-step progress checks and will report PASSED/FAILED for each step.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| GPT-5.2 not available | Verify swedencentral supports the model in your subscription |
| RBAC errors | Wait 5 minutes for propagation, then retry |
| Container App unhealthy | Check `az containerapp logs show` for startup errors |
| Search index missing | The app auto-creates the index on first startup |
| CORS errors | Verify `ALLOWED_ORIGINS` includes your frontend URL |
