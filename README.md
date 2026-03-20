# 🚀 Amazon Seller Autopilot

**AI-Powered Multi-Tenant Amazon Seller Automation Platform**

> Most of the heavy lifting is done by AI agents. Humans only take crucial decisions.

---

## Vision

A unified, AI-native SaaS platform where specialized AI agents automate the entire Amazon Seller Central experience — product listings, A+ content, inventory management, PPC advertising, competitor analysis, keyword research, dynamic pricing, promotions, compliance, and more.

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│              Seller Tenants (OAuth)              │
├─────────────────────────────────────────────────┤
│          React Dashboard + Approval UI          │
├─────────────────────────────────────────────────┤
│       API Gateway + Control Plane (FastAPI)     │
├─────────────────────────────────────────────────┤
│            Orchestrator Agent (Director)         │
├────────┬────────┬────────┬────────┬─────────────┤
│Listing │Inventory│  Ads  │Pricing │  Analytics  │
│ Agent  │ Agent   │ Agent │ Agent  │   Agent     │
├────────┴────────┴────────┴────────┴─────────────┤
│         Event Bus (SQS + EventBridge)           │
├─────────────┬──────────────┬────────────────────┤
│ Amazon      │ Amazon Ads   │ Data Kiosk         │
│ SP-API      │ MCP Server   │ API                │
├─────────────┴──────────────┴────────────────────┤
│  PostgreSQL (RLS) + Redis + pgvector + S3       │
├─────────────────────────────────────────────────┤
│       Claude API + Amazon Bedrock (LLM)         │
└─────────────────────────────────────────────────┘
```

## Key Differentiators

- **Unified Agent Orchestration** — Single AI brain coordinating across all seller functions (unlike point solutions like Helium 10, Jungle Scout, Perpetua)
- **Amazon Ads MCP Server Integration** — Native natural-language campaign management via Model Context Protocol
- **Human-in-the-Loop** — AI agents propose; humans approve. Every critical action requires seller confirmation
- **Cross-Domain Intelligence** — When inventory runs low, ads reduce spend AND pricing adjusts simultaneously
- **Multi-Tenant by Design** — Per-tenant data isolation (RLS), encryption, rate limiting, and configurable agents

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | Python (FastAPI) + Node.js |
| Frontend | React + Next.js + Tailwind CSS |
| AI / LLM | Claude API (Anthropic) + Amazon Bedrock |
| Agent Framework | LangGraph + Custom Orchestrator |
| Database | PostgreSQL (RLS) + Redis + pgvector |
| Event Bus | Amazon SQS + EventBridge |
| Containers | Amazon EKS (Kubernetes) |
| Data Warehouse | Amazon Redshift + S3 Data Lake |
| MCP Integration | Amazon Ads MCP Server + Custom MCP Servers |
| Auth | Amazon Cognito + OAuth 2.0 (LWA) |
| Monitoring | CloudWatch + Datadog + LangSmith |

## Automation Domains (14 Agents)

### Tier 1: Core (Highest Impact)
1. Product Listing Management & Optimization
2. A+ Content & Brand Store Management
3. Inventory Management & Demand Forecasting
4. PPC Advertising (SP + SB via MCP)
5. Dynamic Pricing & Buy Box Optimization
6. Competitor Analysis & Market Intelligence
7. Keyword Research & SEO Optimization

### Tier 2: High-Value
8. Promotions & Deals Management
9. Order Management & Customer Service
10. Financial Analytics & Profitability Tracking
11. Compliance & Account Health Monitoring

### Tier 3: Advanced Differentiation
12. Multi-Marketplace Expansion
13. Sponsored Display & DSP Campaign Management
14. Product Launch Orchestration

## Roadmap

| Phase | Timeline | Focus |
|-------|----------|-------|
| **Phase 1: Foundation** | Months 1–4 | Multi-tenant infra, OAuth, Listing Agent, Pricing Agent |
| **Phase 2: Core Agents** | Months 5–8 | Advertising Agent (MCP), Inventory Agent, Analytics, Orchestrator |
| **Phase 3: Advanced** | Months 9–12 | A+ Content, Compliance, Promotions, Multi-marketplace |
| **Phase 4: Scale** | Months 13–18 | DSP, Enterprise features, Mobile app, ML models |

## Amazon API Integration

- **SP-API**: Listings, Catalog, Pricing, Inventory, Orders, Finances, Notifications, Data Kiosk, A+ Content, Feeds, Reports
- **Amazon Ads API**: Campaign Management v3, Unified Reporting, AMC, Marketing Stream
- **Amazon Ads MCP Server**: Natural-language campaign management (open beta Feb 2026)
- **Brand Stores API**: Programmatic storefront management (GA Feb 2026)

## Project Structure

```
amazon-seller-autopilot/
├── docs/
│   ├── architecture/          # System design documents
│   ├── api-integration/       # Amazon API integration guides
│   ├── user-stories/          # Epic & user story specs
│   └── roadmap/               # Implementation roadmap
├── src/
│   ├── backend/               # FastAPI + Agent services
│   ├── frontend/              # React + Next.js dashboard
│   ├── agents/                # AI agent implementations
│   ├── integrations/          # SP-API, Ads API, MCP connectors
│   └── shared/                # Common utilities, types
├── infra/                     # Terraform / CDK IaC
├── tests/                     # Test suites
└── .github/                   # CI/CD workflows, issue templates
```

## Compliance

This platform is designed for full compliance with:
- **Amazon Agent Policy** (effective March 4, 2026)
- **Amazon SP-API Developer Agreement**
- **Amazon Ads API Terms of Service**
- SOC2, GDPR data handling requirements

## License

Proprietary — All rights reserved.

---

*Built with ❤️ by the Adaptative team*
