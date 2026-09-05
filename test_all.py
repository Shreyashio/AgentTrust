"""
Complete End-to-End Verification Suite for AgentTrust.

Runs all 8 README steps against the CURRENT system (Clerk auth + webhook
signature verification) WITHOUT wiping your database:

  1. Base Setup & Health
  2. Inventory & Staleness Tracking
  3. Governance Policy Engine
  4. AI Agent Tool-Calling (+ governance intercept)
  5. Razorpay Payment Links & signed Webhooks
  6. Human vs Agent Purchase Classification
  7. ROAS Ledger & Attribution Breakdown
  8. Unified Audit Trail Timeline

Design notes:
- All fixtures are created under a dedicated scoped test merchant
  (test_merchant_e2e_<random>) so nothing leaks into your real dashboard data.
- Auth-required logic is exercised through the router functions directly
  (same code paths as HTTP, minus the token middleware).
- The Razorpay webhook is sent over HTTP with a real HMAC-SHA256 signature
  computed from the configured webhook secret.
- Everything is cleaned up automatically at the end (pass --keep to retain).
"""
import hashlib
import hmac
import json
import sys
import uuid

from fastapi.testclient import TestClient

import config
import main
from database import SessionLocal
from models import Order, WebhookLog, ActionLog, Campaign, Product
from seed_merchant import seed_merchant
from governance import check_policy, log_action_attempt
from agent_service import fallback_heuristic_agent
from routers.analytics import get_roas_report, compare_recent_orders
from routers.audit import get_audit_trail

TEST_MERCHANT = f"test_merchant_e2e_{uuid.uuid4().hex[:6]}"


def banner(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def webhook_signature(body: bytes) -> str:
    """Compute the same HMAC-SHA256 signature Razorpay would send."""
    mac = hmac.new(
        config.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        body,
        digestmod=hashlib.sha256,
    )
    return mac.hexdigest()


def cleanup(db) -> None:
    """Remove every row created for the scoped test merchant."""
    links = [
        r[0] for r in db.query(Order.payment_link_id)
        .filter(Order.merchant_id == TEST_MERCHANT).all()
    ]
    if links:
        db.query(WebhookLog).filter(WebhookLog.payment_link_id.in_(links)).delete(synchronize_session=False)
    db.query(Order).filter(Order.merchant_id == TEST_MERCHANT).delete(synchronize_session=False)
    db.query(ActionLog).filter(ActionLog.merchant_id == TEST_MERCHANT).delete(synchronize_session=False)
    db.query(Campaign).filter(Campaign.merchant_id == TEST_MERCHANT).delete(synchronize_session=False)
    db.query(Product).filter(Product.merchant_id == TEST_MERCHANT).delete(synchronize_session=False)
    db.commit()


def run_full_suite(keep_fixtures: bool = False) -> int:
    failures = 0
    db = SessionLocal()
    try:
        print("=========================================================")
        print("           AGENTTRUST END-TO-END TEST SUITE              ")
        print("=========================================================")
        print(f"Scoped test merchant: {TEST_MERCHANT}")
        print("Your live database will NOT be wiped or modified.")

        client = TestClient(main.app)

        # ---- Step 1 & 2: Health, Inventory & Staleness (public routes) ----
        banner("Step 1 & 2 — Health + Inventory & Staleness")
        health = client.get("/health")
        assert health.status_code == 200, "health endpoint failed"
        print(f"-> health: {health.json()['status']}")

        products = client.get("/products/demo")
        assert products.status_code == 200
        prods = products.json()
        fresh_count = sum(1 for p in prods if p["staleness_status"] == "fresh")
        stale_count = sum(1 for p in prods if p["staleness_status"] == "stale")
        print(f"-> {len(prods)} demo products loaded (fresh: {fresh_count}, stale: {stale_count})")
        assert fresh_count > 0 and stale_count > 0, "expected both fresh and stale inventory"

        # ---- Step 3: Governance Policy Engine (direct, scoped) ----
        banner("Step 3 — Governance Policy Engine")
        g_ok = check_policy("adjust_ad_budget", {"current_budget": 1000, "new_budget": 1050})
        g_hold = check_policy("adjust_ad_budget", {"current_budget": 1000, "new_budget": 1250})
        print(f"-> 5% budget change: {g_ok['status']} ({g_ok['reason']})")
        print(f"-> 25% budget change: {g_hold['status']} ({g_hold['reason']})")
        assert g_ok["status"] == "approved"
        assert g_hold["status"] == "needs_approval"
        log_entry = log_action_attempt(
            db, "adjust_ad_budget",
            {"current_budget": 1000, "new_budget": 1050},
            g_ok["status"], g_ok["reason"], merchant_id=TEST_MERCHANT,
        )
        assert log_entry.id and log_entry.merchant_id == TEST_MERCHANT
        print(f"-> action logged to audit (log_id={log_entry.id})")

        # ---- Step 4: AI Agent tool chain + governance ----
        banner("Step 4 — AI Agent Tool-Calling (governance enforced)")
        seed_merchant(TEST_MERCHANT)  # sample products + campaigns for the test tenant
        a_fresh = fallback_heuristic_agent(
            "Create an ad for Mechanical Gaming Keyboard RGB with a 500 budget",
            db, TEST_MERCHANT,
        )
        a_stale = fallback_heuristic_agent(
            "Create an ad for Vintage USB-C Mechanical Numpad with a 500 budget",
            db, TEST_MERCHANT,
        )
        print(f"-> Fresh product: {a_fresh['status']}")
        print(f"-> Stale product : {a_stale['status']}")
        assert a_fresh["status"] == "approved_and_executed"
        assert a_stale["status"] == "blocked_due_to_stale_data"

        # ---- Step 5 & 6: Signed webhooks drive capture + classification ----
        banner("Step 5 & 6 — Razorpay Webhooks & Human vs Agent Classification")
        agent_order = Order(
            payment_link_id=f"plink_test_e2e_agent_{uuid.uuid4().hex[:8]}",
            payment_id=None,
            product_name="Mechanical Gaming Keyboard RGB",
            amount=4499.0,
            currency="INR",
            status="created",
            source="agent",
            user_agent="Mozilla/5.0 ... HeadlessChrome/128.0.0.0 (PlaywrightBot/1.0)",
            classification_method="real_signal_based",
            notes=json.dumps({"user_agent": "HeadlessChrome PlaywrightBot", "product_name": "Mechanical Gaming Keyboard RGB"}),
            merchant_id=TEST_MERCHANT,
        )
        human_order = Order(
            payment_link_id=f"plink_test_e2e_human_{uuid.uuid4().hex[:8]}",
            payment_id=None,
            product_name="Wireless Noise-Cancelling Headphones",
            amount=2999.0,
            currency="INR",
            status="created",
            source="human",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0 Safari/537.36",
            classification_method="manual_tag_fallback",
            notes=json.dumps({"user_agent": "regular Chrome browser"}),
            merchant_id=TEST_MERCHANT,
        )
        db.add_all([agent_order, human_order])
        db.commit()
        db.refresh(agent_order)
        db.refresh(human_order)

        def send_capture(order, source):
            body = json.dumps({
                "event": "payment.captured",
                "payload": {
                    "payment": {
                        "entity": {
                            "id": f"pay_e2e_{source}",
                            "amount": int(round(order.amount * 100)),
                            "currency": "INR",
                            "invoice_id": order.payment_link_id,
                            "notes": json.loads(order.notes or "{}"),
                        }
                    }
                },
            }).encode("utf-8")
            resp = client.post(
                "/payments/webhooks/razorpay",
                content=body,
                headers={"X-Razorpay-Signature": webhook_signature(body)},
            )
            assert resp.status_code == 200, resp.text
            return resp.json()

        w1 = send_capture(agent_order, "agent")
        w2 = send_capture(human_order, "human")
        print(f"-> agent webhook tagged: {w1['source']} (order #{w1['order_id']})")
        print(f"-> human webhook tagged: {w2['source']} (order #{w2['order_id']})")
        assert w1["source"] == "agent"
        assert w2["source"] == "human"

        # Bad-signature webhook must be rejected (400)
        bad_body = json.dumps({"event": "payment.captured", "payload": {}}).encode("utf-8")
        bad = client.post(
            "/payments/webhooks/razorpay",
            content=bad_body,
            headers={"X-Razorpay-Signature": "not-a-real-signature"},
        )
        print(f"-> forged signature rejected: {bad.status_code}")
        assert bad.status_code == 400

        # ---- Step 7: ROAS ledger ----
        banner("Step 7 — ROAS Ledger (Human vs Agent)")
        report = get_roas_report(db=db, merchant_id=TEST_MERCHANT)
        summary = report.summary
        print("================ ROAS LEDGER REPORT ================")
        print(f" Total Ad Spend (Cost) : INR {summary.total_cost:.2f}")
        print(f" Total Revenue Incurred : INR {summary.total_revenue:.2f}")
        print(f"   * Human Revenue      : INR {summary.human_revenue:.2f}")
        print(f"   * Agent Revenue      : INR {summary.agent_revenue:.2f}")
        print(f" Human Purchase ROAS    : {summary.human_roas}x")
        print(f" Agent Purchase ROAS    : {summary.agent_roas}x")
        print(f" Overall Blended ROAS   : {summary.total_roas}x")
        print("====================================================")
        assert summary.human_revenue == 2999.0, summary
        assert summary.agent_revenue == 4499.0, summary
        assert summary.total_cost > 0

        # ---- Step 7b: Compare orders (human vs agent signals) ----
        compare = compare_recent_orders(db=db, merchant_id=TEST_MERCHANT)
        print(f"-> compare: {compare.total_orders_compared} orders, "
              f"verdict: {compare.signal_differences.get('verdict', 'n/a')}")
        assert compare.total_orders_compared >= 2

        # ---- Step 8: Audit trail ----
        banner("Step 8 — Unified Audit Trail Timeline")
        audit = get_audit_trail(db=db, merchant_id=TEST_MERCHANT)
        print(f"-> total timeline events recorded: {audit.total_events}")
        categories = {ev.category for ev in audit.timeline}
        print(f"-> categories present: {sorted(categories)}")
        assert audit.total_events >= 1
        assert "webhook" in categories and "governance" in categories

        print("\n====================================================")
        print("      ALL 8 STEPS TESTED AND PASSED FLAWLESSLY!     ")
        print("====================================================")
    except AssertionError as e:
        failures += 1
        print(f"\n[FAIL] Assertion error: {e}")
    except Exception as e:  # noqa: BLE001
        failures += 1
        print(f"\n[FAIL] Unexpected exception: {type(e).__name__}: {e}")
    finally:
        if keep_fixtures:
            print(f"\n[KEEP] Retaining fixtures for merchant '{TEST_MERCHANT}'.")
        else:
            cleanup(db)
            print(f"\n[CLEAN] Removed all fixtures for 'test' merchant.")
        db.close()

    return failures


if __name__ == "__main__":
    keep = "--keep" in sys.argv
    code = run_full_suite(keep_fixtures=keep)
    sys.exit(code)