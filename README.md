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
   - Classifies every order as `"human"` or `"agent"` using real technical fingerprint signals (`User-Agent`, `Click-Delay`) with a manual tag fallback.
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
python -m playwright install chromium
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
python -m uvicorn main:app --reload
```
The server will run on `http://127.0.0.1:8000`. 
- 🛒 **Test Storefront**: `http://127.0.0.1:8000/store`
- 📖 **OpenAPI Docs**: `http://127.0.0.1:8000/docs`

---

## 🧪 Testing

### Automated End-to-End Suite
Run the complete verification test with one command:
```bash
python test_all.py
```

### Run Automated Playwright Bot Purchase
```bash
python robot_purchaser.py
```

### Interactive CLI Helper
You can quickly test any specific component:
```bash
python test_cli.py products        # List products & staleness
python test_cli.py gov-check       # Test governance policy rules
python test_cli.py agent-fresh     # Test agent with fresh product (Approved)
python test_cli.py agent-stale     # Test agent with stale inventory (Blocked)
python test_cli.py pay-human       # Create human payment link
python test_cli.py pay-agent       # Create agent payment link
python test_cli.py webhook-capture # Simulate Razorpay payment webhook
python test_cli.py orders          # List all orders & technical signals
python test_cli.py compare         # Compare recent Human vs Robot order signals
python test_cli.py roas            # View ROAS report split by Human vs Agent
python test_cli.py audit           # View full audit trail timeline
```

---

## 🔬 How We Tested Real Agent vs Human Detection

To prove that **Human vs Agent purchase classification** isn't just an arbitrary manual tag, we built an end-to-end live testing environment on localhost:

1. **Tiny Local Storefront (`http://127.0.0.1:8000/store`)**:
   - Built a lightweight HTML/JS storefront that displays live products from SQLite.
   - Measures browser interaction metrics, specifically recording the **click delay gap** (seconds between page load and clicking "Buy Now").

2. **Automated Playwright Robot (`robot_purchaser.py`)**:
   - Built a Python Playwright script that simulates an automated AI bot completing a checkout.
   - The bot runs with automated browser signatures (`HeadlessChrome` User-Agent) and completes the click flow with sub-second timing ($< 1.2$ seconds).

3. **Human Manual Purchase**:
   - Completed a real human purchase via standard desktop browser (Chrome/Edge), recording realistic human reading/aiming delays ($> 3.5$ seconds) and a standard browser `User-Agent`.

4. **Captured Fingerprint Signals**:
   - **User-Agent Header**: Detects headless automation signatures (`HeadlessChrome`, `PlaywrightBot`, `python-urllib`, `httpx`, `Selenium`).
   - **Click Timing Gap**: Evaluates whether the purchase click occurred at super-human speed ($< 1.5$ seconds threshold).
   - **Referer & IP Metadata**: Captures request routing signals.

5. **Dual-Layer Classification Engine**:
   - **Primary**: Uses real captured technical signals (`"real_signal_based"`).
   - **Fallback**: Uses explicit source parameter tags (`"manual_tag_fallback"`) when headers/timing are inconclusive.
   - Every order explicitly logs `classification_method` so the attribution reasoning is completely transparent.

6. **Side-by-Side Signal Analytics (`/compare-orders`)**:
   - `GET /analytics/compare-orders` contrasts recent orders side-by-side to visually demonstrate how automated scripts differ from human buyers.

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Server health check and API keys status |
| `GET` | `/store` | Interactive HTML Test Storefront |
| `GET` | `/products` | List all SKU inventory items with staleness status (`fresh`/`stale`) |
| `POST` | `/governance/check` | Test an action against policy rules and log attempt |
| `GET` | `/governance/logs` | View all logged governance decisions |
| `POST` | `/agent/act` | Send natural language instruction to AI agent with governance intercept |
| `POST` | `/payments/create-link` | Generate Razorpay payment link with captured signals |
| `POST` | `/payments/webhooks/razorpay` | Razorpay webhook listener for `payment.captured` & `payment.failed` |
| `GET` | `/payments/orders` | List all orders with payment status, signals, and buyer classification |
| `GET` | `/analytics/roas` | Return overall and per-campaign ROAS split by human and agent orders |
| `GET` | `/analytics/compare-orders` | Side-by-side technical signal comparison of recent human vs robot orders |
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
├── .gitignore            # Git ignore rules for secrets, DB, planning files
├── README.md             # Project documentation and API guide
├── requirements.txt      # Python dependencies
├── config.py             # Configuration loader
├── database.py           # SQLite connection & session maker
├── models.py             # SQLAlchemy ORM models (Product, Campaign, Order, ActionLog, WebhookLog)
├── schemas.py            # Pydantic validation schemas
├── governance.py         # Policy enforcement logic
├── policies.json         # Configurable governance rules
├── razorpay_service.py   # Razorpay API client & real-signal purchase source classifier
├── agent_service.py      # Claude tool definitions, executor, and agent fallback
├── robot_purchaser.py    # Playwright automated robot purchase script
├── seed.py               # Database seeder with sample fresh and stale SKUs
├── test_all.py           # Automated end-to-end test suite
├── test_cli.py           # Fast terminal CLI tester
├── main.py               # FastAPI application entrypoint
└── storefront/
    └── index.html        # HTML/JS test storefront
└── routers/
    ├── products.py       # Inventory & staleness routes
    ├── governance.py     # Governance checking & log routes
    ├── agent.py          # /agent/act route
    ├── payments.py       # Razorpay payment links & webhook handler
    ├── analytics.py      # ROAS breakdown & /compare-orders routes
    └── audit.py          # /audit-log timeline route
```

---

## ▶️ Running the Project — Complete Step-by-Step Guide

Follow these steps in order to get the full AgentTrust system running locally.

---

### Step 1 — Clone & Install Dependencies

```bash
# Clone the repository
git clone https://github.com/your-username/Razorpay-AgentTrust.git
cd Razorpay-AgentTrust

# Create and activate virtual environment
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS / Linux
source venv/bin/activate

# Install all Python dependencies
pip install -r requirements.txt

# Install Playwright browser (needed for robot_purchaser.py)
python -m playwright install chromium
```

---

### Step 2 — Configure Environment Variables

```bash
# Copy the example env file
cp .env.example .env   # macOS/Linux
copy .env.example .env  # Windows
```

Open `.env` and fill in your keys. All keys are **optional** — the app runs in mock/fallback mode without them:

```ini
APP_NAME=AgentTrust
HOST=0.0.0.0
PORT=8000
DEBUG=True
DATABASE_URL=sqlite:///./agenttrust.db

# Optional — Razorpay Test Mode Keys
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxx
RAZORPAY_KEY_SECRET=your_secret_here
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret

# Optional — Anthropic API Key for Claude Agent
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx
```

> **No keys?** The server still runs fully. Payment links use mock responses, and the agent uses a deterministic keyword fallback instead of Claude.

---

### Step 3 — Seed the Database

Populate SQLite with sample products, campaigns, and governance rules:

```bash
python seed.py
```

Expected output:
```
✅ Database seeded: 3 products, 2 campaigns, 5 governance rules.
```

---

### Step 4 — Start the Server

```bash
python -m uvicorn main:app --reload --port 8000
```

Or use the built-in runner:

```bash
python main.py
```

The server is now live at:

| URL | Description |
|---|---|
| `http://127.0.0.1:8000` | API root |
| `http://127.0.0.1:8000/store` | 🛒 HTML Test Storefront |
| `http://127.0.0.1:8000/docs` | 📖 Interactive OpenAPI Docs |
| `http://127.0.0.1:8000/health` | ❤️ Health check |

---

### Step 5 — Run the Automated Test Suite

Verify the entire system end-to-end with one command:

```bash
python test_all.py
```

All 8 steps should pass (✅). This tests: health check, governance rules, ad spend, payment links, webhook capture, ROAS analytics, and agent tool-calling.

---

### Step 6 — Live Human vs Robot Purchase Test

This is the core demo — running a real human purchase side-by-side with an automated robot.

#### 6a. Human Purchase (Manual)

1. Open your browser and go to: **`http://127.0.0.1:8000/store`**
2. Browse the products and click **"Buy Now"** on any product
3. Complete the purchase on the Razorpay test page using the test card:
   - **Card Number**: `4111 1111 1111 1111`
   - **Expiry**: `12/30`
   - **CVV**: `123`
4. On the OTP screen, click **"Success"**

#### 6b. Robot Purchase (Automated)

In a **new terminal** (with the server still running), run:

```bash
python robot_purchaser.py
```

Watch the Playwright browser window open, automatically navigate to the storefront, click "Buy Now", and complete the Razorpay checkout — all without human input.

---

### Step 7 — Compare the Results

After both purchases, run the comparison report:

```bash
# Via CLI
python test_cli.py compare

# Or via HTTP
curl http://127.0.0.1:8000/analytics/compare-orders
```

This shows the captured technical signals (User-Agent, click timing) side-by-side, proving the classifier correctly separated the human from the bot.

---

### Step 8 — View ROAS Analytics

```bash
# Via CLI
python test_cli.py roas

# Or via HTTP
curl http://127.0.0.1:8000/analytics/roas
```

Returns Human ROAS, Agent ROAS, and Blended ROAS per campaign.

---

### Step 9 — Test the AI Agent

Send a natural language instruction to the Claude agent (governance enforced):

```bash
# Approved action — within policy limits
curl -X POST http://127.0.0.1:8000/agent/act \
  -H "Content-Type: application/json" \
  -d "{\"instruction\": \"Check inventory and generate an ad for fresh products\"}"

# Blocked action — exceeds budget policy
curl -X POST http://127.0.0.1:8000/agent/act \
  -H "Content-Type: application/json" \
  -d "{\"instruction\": \"Increase campaign budget by 50%\"}"
```

Or use the interactive CLI:

```bash
python test_cli.py agent-fresh   # Should be APPROVED
python test_cli.py agent-stale   # Should be BLOCKED
```

---

### Step 10 — View the Audit Trail

See a chronological timeline of every action, governance decision, and webhook event:

```bash
python test_cli.py audit

# Or via HTTP
curl http://127.0.0.1:8000/audit-log
```

---

### 🔧 Quick CLI Reference

All CLI commands in one place:

```bash
python test_cli.py products        # List products & staleness
python test_cli.py gov-check       # Test governance policy rules
python test_cli.py agent-fresh     # Agent with fresh product (Approved)
python test_cli.py agent-stale     # Agent with stale inventory (Blocked)
python test_cli.py pay-human       # Create human payment link
python test_cli.py pay-agent       # Create agent payment link
python test_cli.py webhook-capture # Simulate Razorpay payment webhook
python test_cli.py orders          # List all orders & signals
python test_cli.py compare         # Side-by-side Human vs Robot signals
python test_cli.py roas            # ROAS split by Human vs Agent
python test_cli.py audit           # Full audit trail timeline
```

---

### 🛑 Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` inside your venv |
| `agenttrust.db` not found | Run `python seed.py` first |
| Payment links return mock URLs | Add `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` to `.env` |
| Agent uses fallback, not Claude | Add `ANTHROPIC_API_KEY` to `.env` |
| Playwright browser not found | Run `python -m playwright install chromium` |
| Port 8000 already in use | Run `uvicorn main:app --port 8001` and update `STOREFRONT_URL` in `robot_purchaser.py` |
