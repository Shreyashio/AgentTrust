# AgentTrust 🛡️🤖

**AgentTrust** is a backend governance and execution system for autonomous AI agents managing merchant ads, inventory, and sales. It intercepts agent actions against real-time governance rules before execution, classifies incoming purchases as **Human** or **Agent**, integrates with **Razorpay Test Mode**, and calculates return on ad spend (**ROAS**) segmented by purchase type.

---

## 🏗️ System Architecture

```
                     ┌───────────────────────────┐
                     │   Merchant / Client API   │
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

---

## ✨ Key Features

1. **SKU & Inventory Staleness Tracking**:
   - Manages stock, base prices, profit margins, and timestamps.
   - Dynamically flags inventory as `"fresh"` ($\le 24$ hours) or `"stale"` ($> 24$ hours).
2. **Governance & Policy Engine**:
   - Validates agent actions against configurable limits defined in `policies.json`.
   - Autonomous budget change cap: maximum $10\%$ adjustment without human approval.
   - Autonomous campaign budget limit: strictly under $₹1000$.
   - Blocks ad creation on stale inventory to prevent wasted ad spend.
   - Logs every action attempt and policy decision to SQLite (`action_logs` table).
3. **Claude AI Agent Tool-Calling**:
   - Interprets natural language instructions via Claude 3.5 Sonnet tool-calling (with automatic deterministic fallback for offline testing).
   - Tools: `check_inventory`, `generate_ad`, `launch_campaign`, `adjust_budget`.
4. **Razorpay Test Payments & Webhook Pipeline**:
   - Generates test mode Payment Links with embedded source metadata.
   - Webhook receiver (`POST /webhooks/razorpay`) processes `payment.captured` and `payment.failed` events.
5. **Human vs Agent Purchase Classifier**:
   - Classifies every order as `"human"` or `"agent"` based on payment link metadata and purchase headers.
6. **ROAS Ledger & Attribution Breakdown**:
   - Computes return on ad spend split into:
     - **Human ROAS** ($\text{Human Revenue} / \text{Ad Spend}$)
     - **Agent ROAS** ($\text{Agent Revenue} / \text{Ad Spend}$)
     - **Total Blended ROAS** ($\text{Total Revenue} / \text{Ad Spend}$)
7. **Unified Audit Trail Timeline**:
   - `GET /audit-log`: Full chronological timeline of every agent action, policy evaluation, order transaction, and webhook event.

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- pip

### 2. Installation
Clone the repository and install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Configuration
Copy `.env.example` to `.env` and add your API keys (optional — offline mock fallback is included for seamless local development):
```bash
cp .env.example .env
```

`.env` variables:
```ini
APP_NAME=AgentTrust
HOST=0.0.0.0
PORT=8000
DEBUG=True
DATABASE_URL=sqlite:///./agenttrust.db

# Razorpay Test Mode Keys (Optional)
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret

# Anthropic API Key (Optional)
ANTHROPIC_API_KEY=your_anthropic_api_key
ANTHROPIC_WORKSPACE_ID=
```

### 4. Seed Database
Initialize SQLite tables and populate sample fresh/stale products:
```bash
python seed.py
```

### 5. Start the Server
```bash
uvicorn main:app --reload
```
The server will run on `http://127.0.0.1:8000`. Interactive OpenAPI documentation is available at `http://127.0.0.1:8000/docs`.

---

## 🧪 Testing

### Automated End-to-End Suite
Run the complete 8-step verification test with one command:
```bash
python test_all.py
```

### Interactive CLI Helper
You can quickly test any specific component without escaping JSON quotes:
```bash
# List products & staleness
python test_cli.py products

# Test governance policy check
python test_cli.py gov-check

# Test agent with fresh product (Approved)
python test_cli.py agent-fresh

# Test agent with high budget (Held for approval)
python test_cli.py agent-high

# Test agent with stale inventory (Blocked)
python test_cli.py agent-stale

# Create human payment link
python test_cli.py pay-human

# Create agent payment link
python test_cli.py pay-agent

# Simulate Razorpay captured payment webhook
python test_cli.py webhook-capture

# List all orders & classifications
python test_cli.py orders

# Get ROAS report (split by Human vs Agent)
python test_cli.py roas

# View full audit trail timeline
python test_cli.py audit
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Server health check and API keys status |
| `GET` | `/products` | List all SKU inventory items with staleness status (`fresh`/`stale`) |
| `POST` | `/governance/check` | Test an action against policy rules and log attempt |
| `GET` | `/governance/logs` | View all logged governance decisions |
| `POST` | `/agent/act` | Send natural language instruction to AI agent with governance intercept |
| `POST` | `/payments/create-link` | Generate Razorpay payment link tagged as `human` or `agent` |
| `POST` | `/webhooks/razorpay` | Razorpay webhook listener for `payment.captured` & `payment.failed` |
| `GET` | `/payments/orders` | List all orders with payment status and classified buyer type |
| `GET` | `/analytics/roas` | Return overall and per-campaign ROAS split by human and agent orders |
| `GET` | `/audit-log` | Chronological unified timeline of all system actions and decisions |

---

## 📜 Governance Rules (`policies.json`)

```json
{
  "max_budget_adjustment_percent": 10.0,
  "max_campaign_launch_budget_inr": 1000.0,
  "rules": {
    "adjust_ad_budget": {
      "max_autonomous_percent": 10.0,
      "description": "Agent can adjust ad budget autonomously up to 10%"
    },
    "launch_campaign": {
      "max_autonomous_budget": 1000.0,
      "currency": "INR",
      "description": "Agent can launch a campaign only if budget is under INR 1000"
    }
  }
}
```

---

## 📁 Repository Structure

```
├── .env.example          # Environment variable template
├── .gitignore            # Git ignore rules for secrets and DB
├── README.md             # Project documentation and API guide
├── requirements.txt      # Python dependencies
├── config.py             # Configuration loader
├── database.py           # SQLite connection & session maker
├── models.py             # SQLAlchemy ORM models (Product, Campaign, Order, ActionLog, WebhookLog)
├── schemas.py            # Pydantic validation schemas
├── governance.py         # Policy enforcement logic
├── policies.json         # Configurable governance rules
├── razorpay_service.py   # Razorpay API client & purchase source classifier
├── agent_service.py      # Claude tool definitions, executor, and agent fallback
├── seed.py               # Database seeder with sample fresh and stale SKUs
├── test_all.py           # Automated end-to-end test suite
├── test_cli.py           # Fast terminal CLI tester
├── main.py               # FastAPI application entrypoint
└── routers/
    ├── products.py       # Inventory & staleness routes
    ├── governance.py     # Governance checking & log routes
    ├── agent.py          # /agent/act route
    ├── payments.py       # Razorpay payment links & webhook handler
    ├── analytics.py      # ROAS breakdown & ledger routes
    └── audit.py          # /audit-log timeline route
```
