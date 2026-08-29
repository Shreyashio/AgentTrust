"""
Razorpay Payment Gateway integration (Test Mode) & Order Source Classifier.
Handles creating payment links, processing webhooks, and tagging purchases as human or agent.
"""
import hmac
import hashlib
import uuid
import json
from typing import Dict, Any, Optional
import config

def get_razorpay_client():
    """Initializes Razorpay Python client if keys are present."""
    if config.RAZORPAY_KEY_ID and config.RAZORPAY_KEY_SECRET:
        try:
            import razorpay
            return razorpay.Client(auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET))
        except Exception:
            return None
    return None

def classify_purchase_source(notes: Optional[Dict[str, Any]] = None, custom_source: Optional[str] = None) -> str:
    """
    Classifies a purchase as 'agent' or 'human'.
    Checks explicit source tags in notes / metadata, or defaults to 'human'.
    """
    if custom_source:
        src = custom_source.strip().lower()
        if src in ("agent", "ai_agent", "bot", "autonomous"):
            return "agent"
        return "human"

    if notes and isinstance(notes, dict):
        # Check explicit 'source' note
        src = str(notes.get("source", "")).strip().lower()
        if src in ("agent", "ai_agent", "bot", "autonomous"):
            return "agent"
        
        # Check for agent ID or AI buyer token
        if notes.get("agent_id") or notes.get("is_agent") is True:
            return "agent"

    return "human"

def create_payment_link(
    amount: float,
    product_name: str,
    product_id: Optional[int] = None,
    source: str = "human",
    customer_email: Optional[str] = None,
    customer_contact: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates a Razorpay test mode payment link.
    Embeds purchase classification metadata into the Razorpay 'notes' dictionary.
    """
    # Standardize source classification
    resolved_source = classify_purchase_source(custom_source=source)
    
    notes_payload = {
        "source": resolved_source,
        "product_id": str(product_id) if product_id is not None else "",
        "product_name": product_name
    }
    
    amount_in_paise = int(round(amount * 100))  # Razorpay expects amounts in paise
    client = get_razorpay_client()
    
    if client:
        try:
            payload = {
                "amount": amount_in_paise,
                "currency": "INR",
                "accept_partial": False,
                "description": f"Purchase for {product_name}",
                "notes": notes_payload,
                "customer": {
                    "email": customer_email or "customer@example.com",
                    "contact": customer_contact or "+919876543210"
                }
            }
            res = client.payment_link.create(payload)
            return {
                "id": res.get("id"),
                "short_url": res.get("short_url"),
                "amount": amount,
                "currency": "INR",
                "status": res.get("status", "created"),
                "source": resolved_source,
                "notes": notes_payload,
                "mode": "live_test_api"
            }
        except Exception as e:
            # Fallback to simulated link if Razorpay API errors (e.g. invalid test key)
            mock_id = f"plink_mock_{uuid.uuid4().hex[:10]}"
            return {
                "id": mock_id,
                "short_url": f"https://rzp.io/i/{mock_id}",
                "amount": amount,
                "currency": "INR",
                "status": "created",
                "source": resolved_source,
                "notes": notes_payload,
                "mode": "simulated_fallback",
                "note": f"Live Razorpay API call failed ({str(e)}), generated test mock link"
            }
    else:
        # No keys configured yet -> generate simulated test payment link
        mock_id = f"plink_test_{uuid.uuid4().hex[:10]}"
        return {
            "id": mock_id,
            "short_url": f"https://rzp.io/i/{mock_id}",
            "amount": amount,
            "currency": "INR",
            "status": "created",
            "source": resolved_source,
            "notes": notes_payload,
            "mode": "simulated_test"
        }

def verify_webhook_signature(body_bytes: bytes, signature: Optional[str]) -> bool:
    """
    Verifies Razorpay HMAC-SHA256 webhook signature.
    Returns True when no secret is set (allows open testing).
    Returns False when a secret is configured but the signature is missing or mismatched.
    """
    if not config.RAZORPAY_WEBHOOK_SECRET:
        # No secret configured — allow all webhook traffic (test/dev mode)
        return True
    if not signature:
        # Secret is configured but no signature header provided
        return False
    # Python 3 correct usage: hmac.new(key, msg, digestmod)
    mac = hmac.new(
        config.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        body_bytes,
        digestmod=hashlib.sha256
    )
    return hmac.compare_digest(mac.hexdigest(), signature)
