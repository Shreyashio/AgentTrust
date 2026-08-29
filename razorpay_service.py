"""
Razorpay Payment Gateway integration (Test Mode) & Technical Signal Classifier.
Classifies purchases as 'agent' or 'human' using real fingerprint signals (User-Agent, Click Delay)
with a manual tag fallback.
"""
import hmac
import hashlib
import uuid
import json
from typing import Dict, Any, Optional, Tuple
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

def classify_purchase_source(
    notes: Optional[Dict[str, Any]] = None,
    custom_source: Optional[str] = None,
    user_agent: Optional[str] = None,
    click_delay_seconds: Optional[float] = None
) -> Tuple[str, str, str]:
    """
    Classifies a purchase as 'agent' or 'human'.
    
    Evaluates real technical fingerprint signals FIRST:
    1. User-Agent string (checks for headless browsers, Playwright, bot strings).
    2. Click Timing Gap (super-human click speed < 1.5s).
    3. Fallback: Manual declared source tag in notes / metadata.
    
    Returns tuple: (source: "human"|"agent", method: "real_signal_based"|"manual_tag_fallback", reason: str)
    """
    ua = (user_agent or "").lower()
    
    # Extract signals from notes if passed inside Razorpay payload metadata
    if notes and isinstance(notes, dict):
        if not ua and notes.get("user_agent"):
            ua = str(notes.get("user_agent")).lower()
        if click_delay_seconds is None and notes.get("click_delay_seconds"):
            try:
                click_delay_seconds = float(notes.get("click_delay_seconds"))
            except (ValueError, TypeError):
                pass

    # --- SIGNAL 1: User-Agent Bot Fingerprint Detection ---
    bot_keywords = ["headless", "playwright", "puppeteer", "selenium", "bot", "python-urllib", "httpx", "curl", "requests", "phantomjs"]
    for kw in bot_keywords:
        if kw in ua:
            return ("agent", "real_signal_based", f"Bot signature '{kw}' detected in User-Agent header.")

    # --- SIGNAL 2: Rapid Click Timing Detection ---
    if click_delay_seconds is not None and click_delay_seconds > 0:
        if click_delay_seconds < 1.5:  # Faster than human reading/aiming speed threshold
            return ("agent", "real_signal_based", f"Super-human click timing ({click_delay_seconds:.2f}s < 1.50s threshold).")

    # --- FALLBACK SIGNAL 3: Explicit Manual Tag in Request/Notes ---
    if custom_source:
        src = custom_source.strip().lower()
        if src in ("agent", "ai_agent", "bot", "autonomous"):
            return ("agent", "manual_tag_fallback", "Classified via explicit agent source tag parameter.")
        return ("human", "manual_tag_fallback", "Classified via explicit human source tag parameter.")

    if notes and isinstance(notes, dict):
        src = str(notes.get("source", "")).strip().lower()
        if src in ("agent", "ai_agent", "bot", "autonomous"):
            return ("agent", "manual_tag_fallback", "Classified via explicit agent tag in Razorpay notes.")
        if notes.get("agent_id") or notes.get("is_agent") is True:
            return ("agent", "manual_tag_fallback", "Classified via agent ID flag in Razorpay notes.")

    # Default fallback when no strong signal or tag exists
    return ("human", "manual_tag_fallback", "No bot signature detected; defaulted to human buyer.")

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
    resolved_source, method, reason = classify_purchase_source(custom_source=source)
    
    notes_payload = {
        "source": resolved_source,
        "classification_method": method,
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
                "classification_method": method,
                "notes": notes_payload,
                "mode": "live_test_api"
            }
        except Exception as e:
            mock_id = f"plink_mock_{uuid.uuid4().hex[:10]}"
            return {
                "id": mock_id,
                "short_url": f"https://rzp.io/i/{mock_id}",
                "amount": amount,
                "currency": "INR",
                "status": "created",
                "source": resolved_source,
                "classification_method": method,
                "notes": notes_payload,
                "mode": "simulated_fallback",
                "note": f"Live Razorpay API call failed ({str(e)}), generated test mock link"
            }
    else:
        mock_id = f"plink_test_{uuid.uuid4().hex[:10]}"
        return {
            "id": mock_id,
            "short_url": f"https://rzp.io/i/{mock_id}",
            "amount": amount,
            "currency": "INR",
            "status": "created",
            "source": resolved_source,
            "classification_method": method,
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
        return True
    if not signature:
        return False
    mac = hmac.new(
        config.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        body_bytes,
        digestmod=hashlib.sha256
    )
    return hmac.compare_digest(mac.hexdigest(), signature)
