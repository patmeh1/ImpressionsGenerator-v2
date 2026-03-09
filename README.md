# Impressions Generator v2 — Multi-Agent Report Generation

A healthcare radiology/oncology AI application that generates clinical report
sections (findings, impressions, recommendations) in each doctor's unique
writing style, powered by a **multi-agent pipeline** built on
**Microsoft Agent Framework (MAF)** with **Azure AI Foundry SDK 2.x**.

## Architecture

```
User → FastAPI → MAF Supervisor Agent
                    ├── Style Analyst Agent  ──► Cosmos DB
                    ├── Clinical RAG Agent   ──► Azure AI Search
                    ├── Report Writer Agent  ──► Azure OpenAI (GPT-5.2)
                    ├── Grounding Agent      ──► Azure OpenAI (validation)
                    └── Clinical Reviewer    ──► Azure OpenAI (peer review)
                    
                    ──► OpenTelemetry (audit, monitoring)
```

### Agents

| Agent | Role | Pattern |
|---|---|---|
| Style Analyst | Extracts & maintains doctor writing style profiles | Tool Agent |
| Clinical RAG | Searches Azure AI Search for relevant historical notes | Tool Agent |
| Report Writer | Generates findings/impressions/recommendations | Core LLM Agent |
| Grounding Validator | AI-powered grounding check with confidence scores | Peer Review |
| Clinical Reviewer | Reviews for medical accuracy & style adherence | Peer Review |
| Supervisor | Orchestrates pipeline, decides accept/revise | Supervisor |

## Tech Stack

- **Backend:** Python 3.11, FastAPI, Microsoft Agent Framework, Azure AI Foundry SDK 2.x
- **Frontend:** Next.js 14, React 18, TailwindCSS
- **AI:** Azure OpenAI GPT-5.2 (swedencentral)
- **Data:** Azure Cosmos DB, Azure AI Search, Azure Blob Storage
- **Infra:** Bicep IaC, Azure Container Apps, Azure Static Web Apps
- **Observability:** OpenTelemetry, Azure Monitor, Application Insights
- **Auth:** Microsoft Entra ID (Azure AD)
- **CI/CD:** GitHub Actions

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- Azure CLI
- Azure subscription with OpenAI access

### Backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # Configure Azure credentials
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Deploy
```bash
# Step-by-step deployment with progress checks
./infrastructure/scripts/deploy.ps1 -Environment dev
```

## Deployment Guide

See [DEPLOYMENT.md](DEPLOYMENT.md) for the complete step-by-step deployment
guide with progress checks for each component, roles & permissions setup,
and troubleshooting.

## Testing

```bash
# Backend tests
cd backend && pytest tests/ --cov=app

# Frontend tests
cd frontend && npm test

# E2E tests
cd tests && npx playwright test

# Integration tests
cd tests/integration && pytest
```

## License

MIT
