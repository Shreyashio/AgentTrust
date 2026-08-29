# Implementation Plan - AgentTrust Backend

AgentTrust is a backend governance and execution system for AI agent-managed ecommerce and ads. It intercepts AI agent actions, validates them against governance policies, processes Razorpay payments, classifies orders as human or agent, and computes segmented ROAS analytics.

## User Review Required

> [!IMPORTANT]
> - **API Keys**: Razorpay Test Keys (`RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`) and Anthropic API Key (`ANTHROPIC_API_KEY`) will be read from a `.env` file. We will provide a fallback / mock mode when keys are not provided so you can still test all endpoints and governance logic immediately.
> - **Step-by-Step Execution**: We will implement the project in structured steps, providing short terminal commands and expected output after each step.

## Architecture & System Design

```
                     ┌───────────────────────────┐
                     │   User / Merchant / API   │
                     └─────────────┬─────────────┘
                                   │
              ┌────────────────────┴────────────────────┐
              ▼                                         ▼
┌──────────────────────────┐               ┌──────────────────────────┐
│ Claude AI Agent Service  │               │   Direct Orders / Web    │
│ (Tool Calling Interface) │               └────────────┬─────────────┘
└─────────────┬────────────┘                            │
              ▼                                         ▼
┌──────────────────────────┐               ┌──────────────────────────┐
│    Governance Engine     │               │  Order Classification    │
│ (Rule Validation & Audit)│               │    (Human vs Agent)      │
└─────────────┬────────────┘               └────────────┬─────────────┘
              ▼                                         ▼
┌──────────────────────────┐               ┌──────────────────────────┐
│ Action Execution Layer   │               │ Razorpay Payment Gateway │
│ (Campaigns, Pricing, Ads)│               │       (Test Mode)        │
└─────────────┬────────────┘               └────────────┬─────────────┘
              │                                         │
              └────────────────────┬────────────────────┘
                                   ▼
              ┌─────────────────────────────────────────┐
              │          SQLite Database Layer          │
              │  (Campaigns, Orders, Rules, Audit Logs) │
              └────────────────────┬────────────────────┘
                                   ▼
              ┌─────────────────────────────────────────┐
              │         ROAS & Analytics Engine         │
              │   (ROAS split by Human vs Agent Orders) │
              └─────────────────────────────────────────┘
```

## Step-by-Step Implementation Roadmap

### Step 1: Environment & Project Setup
- Setup virtual environment, `requirements.txt` (`fastapi`, `uvicorn`, `sqlalchemy`, `pydantic`, `razorpay`, `anthropic`, `python-dotenv`, `httpx`).
- Setup `.env` configuration loader with sensible defaults.
- Create initial `main.py` healthcheck endpoint.

### Step 2: Database Schema & Models (SQLite)
- SQLite database (`agenttrust.db`) with SQLAlchemy models:
  - `Campaign`: name, budget, daily_limit, current_spend, status.
  - `Product`: name, base_price, current_price, inventory.
  - `Order`: razorpay_order_id, amount, status, source (`human` or `agent`), metadata.
  - `GovernanceRule`: rule_type, condition, threshold_value, active, description.
  - `AuditLog`: actor, action_type, payload, status (`APPROVED`, `BLOCKED`, `PENDING_REVIEW`), reason.
- Database initialization and seed script with sample products, campaigns, and governance rules.

### Step 3: Governance Policy Engine
- Core rules enforcement:
  - Max budget increase cap (e.g., max 20% or max $500 per change).
  - Max discount cap (e.g., maximum 30% discount allowed).
  - Minimum product price floor.
  - Daily ad spend velocity limiter.
- Audit logging for every agent action attempt (allowed / rejected with detailed reason).
- REST endpoints: `GET /governance/rules`, `POST /governance/rules`, `POST /governance/evaluate`.

### Step 4: Razorpay Payments & Order Classification
- Order creation endpoint `POST /orders/create`:
  - Interacts with Razorpay Test Mode API to create a payment order.
  - Classifies source as `agent` or `human` via headers (`X-Agent-ID`, `X-Source-Type`), user-agent heuristics, or payload metadata.
- Payment verification endpoint `POST /orders/verify`:
  - Verifies Razorpay signature / test capture.
  - Updates order status to `PAID` and records attributed revenue.

### Step 5: Campaigns & ROAS Analytics Engine
- Campaign and Ad Spend management endpoints:
  - `POST /campaigns/spend`: Record ad expenditure.
  - `GET /campaigns`: List campaigns and their budget/spend.
- ROAS Calculation endpoint `GET /analytics/roas`:
  - Total Ad Spend.
  - Total Revenue, Human-attributed Revenue, Agent-attributed Revenue.
  - Human ROAS (`Human Revenue / Ad Spend`), Agent ROAS (`Agent Revenue / Ad Spend`), and Overall ROAS (`Total Revenue / Ad Spend`).

### Step 6: Claude AI Agent with Tool Calling & Governance Enforcement
- Anthropic Claude tool calling service:
  - Tools defined: `update_campaign_budget`, `adjust_product_price`, `record_ad_spend`, `create_promotional_discount`.
  - Every tool call is routed through the **Governance Engine** before modifying the database.
  - If a rule is violated, Claude is informed that the action was blocked and explains the rejection reason back to the user.
- Endpoint `POST /agent/chat`: Send natural language prompt to the AI agent and receive the execution result with governance validation report.

### Step 7: End-to-End Verification & Test Runner
- Automated Python test script (`test_all.py`) validating the entire flow:
  1. Healthcheck
  2. Rule creation & enforcement
  3. Ad spend recording
  4. Human and Agent order placement & Razorpay verification
  5. ROAS analytics breakdown
  6. Agent tool execution with both valid actions and blocked governance violations

## Proposed Files

- `requirements.txt`: Project dependencies
- `.env.example`: Configuration template
- `config.py`: Settings & environment variable loader
- `database.py`: SQLite engine and session factory
- `models.py`: SQLAlchemy database models
- `schemas.py`: Pydantic request/response validation models
- `governance.py`: Governance rule validation logic and audit logger
- `razorpay_service.py`: Razorpay client wrapper (with graceful fallback for test mode without keys)
- `agent_service.py`: Claude tool definition, prompt runner, and tool executor
- `routers/`
  - `governance_router.py`: Governance API endpoints
  - `orders_router.py`: Order creation, classification & verification
  - `campaigns_router.py`: Campaign management & ROAS analytics
  - `agent_router.py`: Agent execution endpoints
- `main.py`: FastAPI entrypoint
- `test_flow.py`: Complete step-by-step verification script

## Verification Plan

### Automated Tests
- Running `python test_flow.py` for comprehensive integration testing.
- Individual curl / Postman commands for each step.

### Manual Verification
- Testing each endpoint with clean, concise curl/PowerShell commands.
