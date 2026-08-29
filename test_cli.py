"""
Simple CLI test utility for AgentTrust.
Allows running all test scenarios from terminal without PowerShell quote-escaping problems.
"""
import sys
import json
import httpx

BASE_URL = "http://127.0.0.1:8000"

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_cli.py [products|gov-check|agent-fresh|agent-high|agent-stale|pay-human|pay-agent|webhook-capture|orders|roas|audit]")
        return

    cmd = sys.argv[1].lower()
    
    with httpx.Client(base_url=BASE_URL, timeout=15.0) as client:
        try:
            if cmd == "products":
                res = client.get("/products")
            elif cmd == "gov-check":
                res = client.post("/governance/check", json={
                    "action": "adjust_ad_budget",
                    "details": {"current_budget": 1000, "new_budget": 1080}
                })
            elif cmd == "agent-fresh":
                res = client.post("/agent/act", json={
                    "instruction": "Create an ad for Mechanical Gaming Keyboard RGB with a 500 budget"
                })
            elif cmd == "agent-high":
                res = client.post("/agent/act", json={
                    "instruction": "Create an ad for Mechanical Gaming Keyboard RGB with a 2500 budget"
                })
            elif cmd == "agent-stale":
                res = client.post("/agent/act", json={
                    "instruction": "Create an ad for Vintage USB-C Mechanical Numpad with a 500 budget"
                })
            elif cmd in ("pay-human", "pay-link-human"):
                res = client.post("/payments/create-link", json={
                    "product_id": 1,
                    "product_name": "Wireless Noise-Cancelling Headphones",
                    "amount": 2999.0,
                    "source": "human"
                })
            elif cmd in ("pay-agent", "pay-link-agent"):
                res = client.post("/payments/create-link", json={
                    "product_id": 2,
                    "product_name": "Mechanical Gaming Keyboard RGB",
                    "amount": 4499.0,
                    "source": "agent"
                })
            elif cmd == "webhook-capture":
                res = client.post("/payments/webhooks/razorpay", json={
                    "event": "payment.captured",
                    "payload": {
                        "payment": {
                            "entity": {
                                "id": "pay_test_998877",
                                "amount": 449900,
                                "currency": "INR",
                                "status": "captured",
                                "notes": {
                                    "source": "agent",
                                    "product_name": "Mechanical Gaming Keyboard RGB",
                                    "product_id": "2"
                                }
                            }
                        }
                    }
                })
            elif cmd == "orders":
                res = client.get("/payments/orders")
            elif cmd == "roas":
                res = client.get("/analytics/roas")
            elif cmd in ("audit", "audit-log"):
                res = client.get("/audit-log")
            else:
                print(f"Unknown command '{cmd}'")
                return

            print(f"HTTP {res.status_code}")
            print(json.dumps(res.json(), indent=2))
        except Exception as e:
            print(f"Error connecting to {BASE_URL}: {e}")
            print("Make sure server is running with: python -m uvicorn main:app --reload")

if __name__ == "__main__":
    main()
