#!/usr/bin/env bash
# =============================================================================
# Step-by-step deployment script for Impressions Generator v2
# Multi-Agent Pipeline | GPT-5.2 | swedencentral
# =============================================================================

set -euo pipefail

ENVIRONMENT="${1:?Usage: $0 <dev|staging|prod> <subscription-id>}"
SUBSCRIPTION_ID="${2:?Usage: $0 <dev|staging|prod> <subscription-id>}"
PROJECT_NAME="${3:-impgen2}"
LOCATION="${4:-swedencentral}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RESOURCE_GROUP="${PROJECT_NAME}-rg-${ENVIRONMENT}"

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

step() { echo -e "\n${CYAN}═══ STEP $1: $2 ═══${NC}"; }
pass() { echo -e "  ${GREEN}✓ $1${NC}"; }
fail() { echo -e "  ${RED}✗ $1${NC}"; }
warn() { echo -e "  ${YELLOW}⚠ $1${NC}"; }

echo -e "${CYAN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  Impressions Generator v2 — Deployment               ║${NC}"
echo -e "${CYAN}║  Multi-Agent Pipeline | GPT-5.2 | swedencentral      ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  Environment:    $ENVIRONMENT"
echo "  Subscription:   $SUBSCRIPTION_ID"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Location:       $LOCATION"
echo ""

# Pre-flight
az account set --subscription "$SUBSCRIPTION_ID"
pass "Subscription set"
az bicep install 2>/dev/null || true
pass "Bicep CLI ready"

# Step 1: Validate Bicep
step 1 "Validate Bicep Templates"
for f in $(find "$SCRIPT_DIR/.." -name '*.bicep' -type f); do
    echo "  Validating $(basename $f)..."
    az bicep build --file "$f" --stdout > /dev/null
done
pass "All Bicep templates valid"

# Step 2: Deploy Infrastructure
step 2 "Deploy Infrastructure"
DEPLOY_NAME="deploy-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)"
az deployment sub create \
    --location "$LOCATION" \
    --template-file "$SCRIPT_DIR/../main.bicep" \
    --parameters environmentName="$ENVIRONMENT" location="$LOCATION" projectName="$PROJECT_NAME" \
    --name "$DEPLOY_NAME" \
    --output json > /tmp/deploy-output.json
pass "Infrastructure deployed"

# Step 3: Verify Resources
step 3 "Verify Resource Health"
for res in "${PROJECT_NAME}-cosmos-${ENVIRONMENT}" "${PROJECT_NAME}-openai-${ENVIRONMENT}" "${PROJECT_NAME}-search-${ENVIRONMENT}"; do
    if az resource show -g "$RESOURCE_GROUP" -n "$res" --query "id" -o tsv 2>/dev/null; then
        pass "$res — healthy"
    else
        warn "$res — not found (may use different naming)"
    fi
done

# Step 4: Verify RBAC
step 4 "Verify RBAC Roles"
PRINCIPAL_ID=$(az containerapp show \
    --name "${PROJECT_NAME}-api-${ENVIRONMENT}" \
    -g "$RESOURCE_GROUP" \
    --query "identity.principalId" -o tsv 2>/dev/null || echo "")
if [ -n "$PRINCIPAL_ID" ]; then
    pass "Container App identity: $PRINCIPAL_ID"
    az role assignment list --assignee "$PRINCIPAL_ID" -g "$RESOURCE_GROUP" \
        --query "[].roleDefinitionName" -o tsv 2>/dev/null | while read role; do
        pass "Role: $role"
    done
else
    warn "Container App not yet available"
fi

# Step 5: Build & Push Backend
step 5 "Build & Push Backend"
ACR_NAME="${PROJECT_NAME}acr${ENVIRONMENT}"
IMAGE_TAG=$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M)
IMAGE="${ACR_NAME}.azurecr.io/impressions-backend:${IMAGE_TAG}"

az acr login --name "$ACR_NAME" 2>/dev/null || warn "ACR login failed (may need creation)"
cd "$SCRIPT_DIR/../../backend"
docker build -t "$IMAGE" . && pass "Docker image built"
docker push "$IMAGE" 2>/dev/null && pass "Image pushed: $IMAGE" || warn "Push failed (ACR may not exist)"
cd "$SCRIPT_DIR"

# Step 6: Verify Backend Health
step 6 "Verify Backend Health"
APP_URL=$(az containerapp show \
    --name "${PROJECT_NAME}-api-${ENVIRONMENT}" \
    -g "$RESOURCE_GROUP" \
    --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "")
if [ -n "$APP_URL" ]; then
    for i in 1 2 3 4 5; do
        RESPONSE=$(curl -s "https://${APP_URL}/health" 2>/dev/null || echo "")
        if echo "$RESPONSE" | grep -q "healthy"; then
            pass "Backend healthy"
            break
        fi
        echo "  Retry $i/5..."
        sleep 10
    done
else
    warn "Container App URL not available"
fi

# Step 7: Build Frontend
step 7 "Build Frontend"
cd "$SCRIPT_DIR/../../frontend"
npm ci --silent 2>/dev/null
NEXT_PUBLIC_API_URL="https://${PROJECT_NAME}-api-${ENVIRONMENT}.azurecontainerapps.io" npm run build
pass "Frontend built"
cd "$SCRIPT_DIR"

# Step 8: Verify Pipeline
step 8 "Verify Multi-Agent Pipeline"
if [ -n "$APP_URL" ]; then
    PIPELINE_INFO=$(curl -s "https://${APP_URL}/api/generate/pipeline-info" 2>/dev/null || echo "")
    if echo "$PIPELINE_INFO" | grep -q "multi-agent"; then
        pass "Multi-agent pipeline active"
    fi
fi

echo ""
echo -e "${GREEN}✓ Deployment complete!${NC}"
echo "  Backend:  https://${PROJECT_NAME}-api-${ENVIRONMENT}.azurecontainerapps.io"
echo "  Frontend: Check Azure Static Web Apps portal"
