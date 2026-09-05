"""
Step 6 verification: multi-tenant merchant scoping.

Run from the project root with your project venv (requires fastapi, httpx,
sqlalchemy, anthropic, razorpay, clerk_backend_api):

    source /path/to/venv/bin/activate
    python test_step6.py

Uses a throwaway SQLite DB at %TEMP%/step6_test.db, so agenttrust.db is untouched.
No Clerk token is needed: the auth dependency is overridden to simulate two merchants.
"""
import os
import tempfile

TEST_DB = os.path.join(tempfile.gettempdir(), "step6_test.db")
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"

import main as main_module
from fastapi.testclient import TestClient
from auth import get_current_merchant_id
from database import SessionLocal
from models import Product, Campaign, Order, ActionLog, WebhookLog
from datetime import datetime, timezone

app = main_module.app
client = TestClient(app)
db = SessionLocal()

failures = []
passed = []

def check(condition, label):
    if condition:
        passed.append(label)
    else:
        failures.append(label)

def as_merchant(merchant_id):
    app.dependency_overrides[get_current_merchant_id] = lambda: merchant_id

def no_auth():
    app.dependency_overrides.pop(get_current_merchant_id, None)


b_product = Product(
    name="Merchant B Widget",
    stock_count=3,
    price=999.0,
    margin=0.2,
    last_updated=datetime.now(timezone.utc),
    merchant_id="merchant_b",
)
db.add(b_product)
db.flush()
b_campaign = Campaign(
    name="Merchant B Campaign",
    product_id=b_product.id,
    budget=200.0,
    ad_spend=50.0,
    status="active",
    merchant_id="merchant_b",
)
db.add(b_campaign)
db.flush()
db.add(Order(
    payment_link_id="pl_b_1",
    product_name=b_product.name,
    product_id=b_product.id,
    campaign_id=b_campaign.id,
    amount=2000.0,
    status="captured",
    source="agent",
    merchant_id="merchant_b",
    user_agent="Python urllib",
    click_delay_seconds=0.0,
))
db.add(ActionLog(
    action="launch_campaign",
    details="{}",
    result="blocked",
    reason="test",
    merchant_id="merchant_b",
))
db.commit()

check(os.environ["DATABASE_URL"].endswith("step6_test.db"), "uses throwaway DB")


no_auth()
for url in ["/products", "/governance/logs", "/analytics/roas", "/payments/orders", "/audit-log"]:
    r = client.get(url)
    check(r.status_code == 401, f"401 without token: GET {url} (got {r.status_code})")

demo_ids = sorted(p.id for p in db.query(Product).filter(Product.merchant_id == "demo").all())
b_ids = sorted(p.id for p in db.query(Product).filter(Product.merchant_id == "merchant_b").all())

as_merchant("demo")
r = client.get("/products")
check(r.status_code == 200 and len(r.json()) == len(demo_ids), "demo sees only its own products")
check({p["id"] for p in r.json()} == set(demo_ids), "demo product ids match")
r = client.get(f"/products/{b_ids[0]}")
check(r.status_code == 404, f"demo cannot read merchant_b product (expected 404, got {r.status_code})")
r = client.get(f"/products/{demo_ids[0]}")
check(r.status_code == 200, "demo can read its own product")

as_merchant("merchant_b")
r = client.get("/products")
check(r.status_code == 200 and len(r.json()) == len(b_ids), "merchant_b sees only its own products")
r = client.get(f"/products/{demo_ids[0]}")
check(r.status_code == 404, f"merchant_b cannot read demo product (expected 404, got {r.status_code})")


as_merchant("demo")
r = client.post("/governance/check", json={
    "action": "launch_campaign",
    "details": {"budget": 500, "campaign_name": "Demo Test", "product_id": demo_ids[0]},
})
check(r.status_code == 200, "demo can submit governance check")

as_merchant("merchant_b")
r = client.post("/governance/check", json={
    "action": "launch_campaign",
    "details": {"budget": 500, "campaign_name": "B Test", "product_id": b_ids[0]},
})
check(r.status_code == 200, "merchant_b can submit governance check")

as_merchant("demo")
demo_log_ids = {l["id"] for l in client.get("/governance/logs").json()}
as_merchant("merchant_b")
b_log_ids = {l["id"] for l in client.get("/governance/logs").json()}
check(demo_log_ids and b_log_ids and demo_log_ids.isdisjoint(b_log_ids),
      "governance/logs are tenant-scoped (no overlap)")
check(all(db.query(ActionLog).get(i).merchant_id == "demo" for i in demo_log_ids),
      "demo logs belong to merchant demo")
check(all(db.query(ActionLog).get(i).merchant_id == "merchant_b" for i in b_log_ids),
      "merchant_b logs belong to merchant_b")


as_merchant("demo")
demo_camps = {k for k in client.get("/analytics/roas").json()}
as_merchant("merchant_b")
b_camps = {k for k in client.get("/analytics/roas").json()}
check(demo_camps and b_camps and demo_camps.isdisjoint(b_camps),
      "analytics/roas is tenant-scoped (no campaign overlap)")


as_merchant("demo")
demo_orders = [o["id"] for o in client.get("/payments/orders").json()]
as_merchant("merchant_b")
b_orders = [o["id"] for o in client.get("/payments/orders").json()]
check(demo_orders and set(demo_orders).isdisjoint(b_orders),
      "payments/orders is tenant-scoped (no overlap)")


as_merchant("demo")
demo_audit = client.get("/audit-log").json()
as_merchant("merchant_b")
b_audit = client.get("/audit-log").json()
check(all(e["category"] in ("campaign", "order", "governance", "webhook") for e in demo_audit["timeline"]),
      "audit-log returns timeline")
check(demo_audit["total_events"] > 0 and b_audit["total_events"] > 0,
      "both merchants have audit events")


as_merchant("merchant_b")
r = client.post("/agent/act", json={"instruction": "adjust budget for campaign 1 to 500"})
check(r.status_code == 200, "agent/act works for merchant_b with scoped tenant")

db.close()
os.remove(TEST_DB)

print(f"\nPASSED: {len(passed)}")
for p in passed:
    print("  [PASS]", p)
if failures:
    print(f"FAILED: {len(failures)}")
    for f in failures:
        print("  [FAIL]", f)
    raise SystemExit(1)
print("STEP 6 VERIFICATION: ALL PASS")