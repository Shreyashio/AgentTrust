"""
Complete End-to-End Verification Suite for AgentTrust.
Tests all 8 steps:
  1. Base Setup & Health
  2. Inventory & Staleness Tracking
  3. Governance Policy Engine
  4. Claude AI Agent Tool-Calling (/agent/act)
  5. Razorpay Test Payments & Links
  6. Human vs Agent Purchase Classifier & Webhooks
  7. ROAS Ledger & Attribution Breakdown
  8. Unified Audit Trail Timeline (/audit-log)
"""
import json
from fastapi.testclient import TestClient
import main
from seed import seed_database

def run_full_suite():
    print("=========================================================")
    print("           AGENTTRUST END-TO-END TEST SUITE              ")
    print("=========================================================")
    
    # 1. Reset and seed SQLite database
    print("\n[Step 1 & 2] Seeding database and verifying products & staleness...")
    seed_database(reset_all_tables=True)
    client = TestClient(main.app)
    
    res = client.get("/products")
    assert res.status_code == 200
    products = res.json()
    print(f"-> Verified {len(products)} products loaded.")
    fresh_count = sum(1 for p in products if p['staleness_status'] == 'fresh')
    stale_count = sum(1 for p in products if p['staleness_status'] == 'stale')
    print(f"-> Fresh items: {fresh_count}, Stale items: {stale_count}")

    # 2. Test Governance Policy Engine
    print("\n[Step 3] Testing Governance Policy Rules...")
    # Check 8% budget increase (Approved)
    g1 = client.post("/governance/check", json={"action": "adjust_ad_budget", "details": {"current_budget": 1000, "new_budget": 1080}})
    assert g1.json()["result"] == "approved"
    print(f"-> 8% budget change: {g1.json()['result']} ({g1.json()['reason']})")
    
    # Check 25% budget increase (Needs Approval)
    g2 = client.post("/governance/check", json={"action": "adjust_ad_budget", "details": {"current_budget": 1000, "new_budget": 1250}})
    assert g2.json()["result"] == "needs_approval"
    print(f"-> 25% budget change: {g2.json()['result']} ({g2.json()['reason']})")

    # 3. Test AI Agent Tool Calling
    print("\n[Step 4] Testing AI Agent (/agent/act) with Governance intercept...")
    # Fresh product + INR 500 budget -> Approved
    a1 = client.post("/agent/act", json={"instruction": "Create an ad for Mechanical Gaming Keyboard RGB with a 500 budget"})
    assert a1.json()["status"] == "approved_and_executed"
    print(f"-> Agent instruction (Fresh + INR 500): {a1.json()['status']}")
    
    # Stale product -> Blocked due to stale data
    a2 = client.post("/agent/act", json={"instruction": "Create an ad for Vintage USB-C Mechanical Numpad with a 500 budget"})
    assert a2.json()["status"] == "blocked_due_to_stale_data"
    print(f"-> Agent instruction (Stale item): {a2.json()['status']}")

    # 4. Test Razorpay Payment Links & Order Classification
    print("\n[Step 5 & 6] Testing Razorpay Payment Links & Webhooks...")
    # Create Agent order link
    l1 = client.post("/payments/create-link", json={"product_id": 2, "amount": 4499.0, "source": "agent"})
    agent_link_id = l1.json()["payment_link_id"]
    print(f"-> Generated Agent Payment Link: {agent_link_id} (Source: {l1.json()['source']})")
    
    # Create Human order link
    l2 = client.post("/payments/create-link", json={"product_id": 1, "amount": 2999.0, "source": "human"})
    human_link_id = l2.json()["payment_link_id"]
    print(f"-> Generated Human Payment Link: {human_link_id} (Source: {l2.json()['source']})")
    
    # Simulate captured webhooks
    w1 = client.post("/payments/webhooks/razorpay", json={
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_agent_captured_01",
                    "amount": 449900,
                    "currency": "INR",
                    "invoice_id": agent_link_id,
                    "notes": {"source": "agent", "product_id": "2", "product_name": "Mechanical Gaming Keyboard RGB"}
                }
            }
        }
    })
    assert w1.json()["source"] == "agent"
    
    w2 = client.post("/payments/webhooks/razorpay", json={
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_human_captured_01",
                    "amount": 299900,
                    "currency": "INR",
                    "invoice_id": human_link_id,
                    "notes": {"source": "human", "product_id": "1", "product_name": "Wireless Noise-Cancelling Headphones"}
                }
            }
        }
    })
    assert w2.json()["source"] == "human"
    print("-> Successfully captured both Agent and Human payments via Webhooks.")

    # 5. Test ROAS Ledger & Analytics
    print("\n[Step 7] Testing ROAS Ledger split by Human vs Agent purchases...")
    roas_res = client.get("/analytics/roas")
    assert roas_res.status_code == 200
    report = roas_res.json()
    summary = report["summary"]
    
    print("================ ROAS LEDGER REPORT ================")
    print(f" Total Ad Spend (Cost) : INR {summary['total_cost']:.2f}")
    print(f" Total Revenue Incurred : INR {summary['total_revenue']:.2f}")
    print(f"   * Human Revenue      : INR {summary['human_revenue']:.2f}")
    print(f"   * Agent Revenue      : INR {summary['agent_revenue']:.2f}")
    print("----------------------------------------------------")
    print(f" Human Purchase ROAS    : {summary['human_roas']}x")
    print(f" Agent Purchase ROAS    : {summary['agent_roas']}x")
    print(f" Overall Blended ROAS   : {summary['total_roas']}x")
    print("====================================================")

    # 6. Test Audit Log Timeline
    print("\n[Step 8] Testing Complete Audit Trail Timeline (/audit-log)...")
    audit_res = client.get("/audit-log")
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    print(f"-> Total chronological timeline events recorded: {audit_data['total_events']}")
    for idx, ev in enumerate(audit_data["timeline"][:5], 1):
        print(f"   {idx}. [{ev['category'].upper()}] {ev['title']} -> {ev.get('result', '')} ({ev.get('reason', '')})")
    
    print("\n====================================================")
    print("      ALL 8 STEPS TESTED AND PASSED FLAWLESSLY!     ")
    print("====================================================")

if __name__ == "__main__":
    run_full_suite()
