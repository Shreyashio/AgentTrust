"""
API endpoints for Razorpay Test Payments, Webhooks, and Human vs Agent Order Classification.
Captures HTTP headers (User-Agent, Referer), timing signals, and IP addresses.
"""
import json
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request, Header, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Order, WebhookLog, Product, Campaign
from schemas import CreatePaymentLinkRequest, PaymentLinkResponse, OrderResponse, WebhookResponse, SimulatePaymentRequest
from razorpay_service import create_payment_link, verify_webhook_signature, classify_purchase_source, fetch_payment_link_status
from auth import get_optional_merchant_id, get_current_merchant_id
router = APIRouter(prefix="/payments", tags=["Payments & Orders"])


def _resolve_merchant(payload: CreatePaymentLinkRequest, merchant_id) -> str:
    """
    For the no-login public storefront, allow a caller to explicitly supply a
    merchant_id via the request body (used only for testing/demo purposes). For
    authenticated calls, the Clerk-verified merchant always wins.
    """
    if merchant_id:
        return merchant_id
    if payload.merchant_id:
        return payload.merchant_id
    return get_demo_merchant_id()


@router.post("/create-link", response_model=PaymentLinkResponse)
def create_test_payment_link(
    payload: CreatePaymentLinkRequest,
    request: Request,
    x_click_delay: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    merchant_id: Optional[str] = Depends(get_optional_merchant_id)
):
    """
    Generates a Razorpay Test Mode Payment Link for a product/amount.
    Captures request technical signals (User-Agent, Referer, Click Delay, IP) and classifies purchase.
    """
    merchant_id = _resolve_merchant(payload, merchant_id)
    prod_name = payload.product_name
    prod_id = payload.product_id
    camp_id = payload.campaign_id

    # 1. Extract technical fingerprint signals from request
    user_agent = request.headers.get("user-agent", "Unknown")
    referer = request.headers.get("referer") or request.headers.get("referrer", "")
    ip_address = request.client.host if request.client else None
    
    click_delay = payload.click_delay_seconds
    if click_delay is None and x_click_delay:
        try:
            click_delay = float(x_click_delay)
        except (ValueError, TypeError):
            click_delay = None

    # 2. Evaluate signals via updated Classifier Engine
    classified_source, classification_method, reason = classify_purchase_source(
        custom_source=payload.source,
        user_agent=user_agent,
        click_delay_seconds=click_delay
    )

    # If product_id is provided, fetch the merchant's own product details
    if prod_id:
        prod = db.query(Product).filter(
            Product.id == prod_id,
            Product.merchant_id == merchant_id
        ).first()
        if prod:
            prod_name = prod.name
            if payload.amount <= 0:
                payload.amount = prod.price
                
    # If campaign_id not specified, look for the merchant's active campaign promoting this product
    if not camp_id and prod_id:
        active_camp = db.query(Campaign).filter(
            Campaign.product_id == prod_id,
            Campaign.merchant_id == merchant_id
        ).order_by(Campaign.id.desc()).first()
        if active_camp:
            camp_id = active_camp.id

    # Generate link via Razorpay service
    link_data = create_payment_link(
        amount=payload.amount,
        product_name=prod_name,
        product_id=prod_id,
        source=classified_source,
        customer_email=payload.customer_email,
        customer_contact=payload.customer_contact
    )
    
    # Embed signals and classification method in metadata notes
    link_data["notes"]["user_agent"] = user_agent
    link_data["notes"]["referer"] = referer
    link_data["notes"]["classification_method"] = classification_method
    if click_delay is not None:
        link_data["notes"]["click_delay_seconds"] = str(click_delay)
    if camp_id:
        link_data["notes"]["campaign_id"] = str(camp_id)

    # Record order with technical fingerprint signals in SQLite database
    order = Order(
        payment_link_id=link_data["id"],
        payment_id=None,
        campaign_id=camp_id,
        product_id=prod_id,
        product_name=prod_name,
        amount=payload.amount,
        currency="INR",
        status="created",
        source=classified_source,
        user_agent=user_agent,
        referer=referer,
        click_delay_seconds=click_delay,
        ip_address=ip_address,
        classification_method=classification_method,
        notes=json.dumps(link_data["notes"]),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        merchant_id=merchant_id
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    
    return PaymentLinkResponse(
        payment_link_id=link_data["id"],
        short_url=link_data["short_url"],
        amount=link_data["amount"],
        product_name=prod_name,
        campaign_id=camp_id,
        source=classified_source,
        status=link_data["status"],
        mode=link_data.get("mode")
    )

def process_payment_event(db: Session, data: dict) -> WebhookResponse:
    """
    Applies a Razorpay payment event (payment.captured / payment.failed / payment_link.paid)
    to the database: logs the webhook, classifies human vs agent from real signals,
    and updates (or creates) the matching Order. Shared by the real webhook receiver
    and the local simulated-payment test endpoint.
    """
    event = data.get("event", "unknown")
    payload = data.get("payload", {})

    # Extract payment / payment_link entity details
    payment_entity = payload.get("payment", {}).get("entity", {})
    payment_link_entity = payload.get("payment_link", {}).get("entity", {})

    payment_id = payment_entity.get("id")
    payment_link_id = payment_link_entity.get("id") or payment_entity.get("invoice_id") or payment_entity.get("order_id")

    # Extract notes/metadata
    notes = payment_entity.get("notes") or payment_link_entity.get("notes") or data.get("notes") or {}

    # Log incoming webhook to SQLite
    webhook_log = WebhookLog(
        event=event,
        payment_id=payment_id,
        payment_link_id=payment_link_id,
        payload=json.dumps(data),
        status="processed",
        received_at=datetime.now(timezone.utc)
    )
    db.add(webhook_log)

    # 2. Classify Purchase Source using real signals + manual fallback
    classified_source, classification_method, reason = classify_purchase_source(
        notes=notes,
        user_agent=notes.get("user_agent"),
        click_delay_seconds=float(notes.get("click_delay_seconds")) if str(notes.get("click_delay_seconds", "")).replace('.', '', 1).isdigit() else None
    )

    # 3. Locate and update or create Order record in DB
    order = None
    if payment_link_id:
        order = db.query(Order).filter(Order.payment_link_id == payment_link_id).first()

    if not order and payment_id:
        order = db.query(Order).filter(Order.payment_id == payment_id).first()

    if order:
        order.payment_id = payment_id or order.payment_id
        order.source = classified_source
        order.classification_method = classification_method
        order.updated_at = datetime.now(timezone.utc)

        if event in ("payment.captured", "payment_link.paid", "order.paid"):
            order.status = "captured"
        elif event in ("payment.failed",):
            order.status = "failed"

        db.commit()
        db.refresh(order)
        order_id = order.id

        # Keep tenant copies of the order (adopted demo-storefront duplicate) in sync
        # so the merchant's own Orders / ROAS reflect captures from the real webhook.
        if payment_link_id:
            copies = db.query(Order).filter(
                Order.payment_link_id == f"{payment_link_id}_adopted",
                Order.id != order.id
            ).all()
            for copy in copies:
                copy.payment_id = order.payment_id or copy.payment_id
                copy.status = order.status
                copy.source = order.source
                copy.classification_method = order.classification_method
                copy.updated_at = datetime.now(timezone.utc)
            if copies:
                db.commit()
    else:
        amount_paise = payment_entity.get("amount") or payment_link_entity.get("amount") or 0
        amount_val = float(amount_paise) / 100.0 if amount_paise else 0.0
        prod_name = notes.get("product_name", "Webhook Order Item")
        camp_id = int(notes.get("campaign_id")) if str(notes.get("campaign_id", "")).isdigit() else None

        status_val = "captured" if event in ("payment.captured", "payment_link.paid", "order.paid") else "failed"

        new_order = Order(
            payment_link_id=payment_link_id or f"plink_ext_{payment_id}",
            payment_id=payment_id,
            campaign_id=camp_id,
            product_id=int(notes.get("product_id")) if str(notes.get("product_id", "")).isdigit() else None,
            product_name=prod_name,
            amount=amount_val,
            currency="INR",
            status=status_val,
            source=classified_source,
            user_agent=notes.get("user_agent"),
            referer=notes.get("referer"),
            click_delay_seconds=float(notes.get("click_delay_seconds")) if str(notes.get("click_delay_seconds", "")).replace('.', '', 1).isdigit() else None,
            classification_method=classification_method,
            notes=json.dumps(notes),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(new_order)
        db.commit()
        db.refresh(new_order)
        order_id = new_order.id

    return WebhookResponse(
        status="success",
        event=event,
        message=f"Event '{event}' processed. Order #{order_id} tagged as '{classified_source}' ({classification_method}).",
        order_id=order_id,
        source=classified_source
    )


@router.post("/webhooks/razorpay", response_model=WebhookResponse)
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Webhook receiver for Razorpay events (payment.captured, payment.failed, payment_link.paid).
    Validates webhook signature, then applies the event to the database.
    """
    body_bytes = await request.body()

    # 1. Verify webhook signature if secret configured
    if not verify_webhook_signature(body_bytes, x_razorpay_signature):
        # Log the rejected event so the audit timeline shows whether webhooks are
        # arriving but failing signature check (usually a dashboard/.env secret mismatch).
        raw_event = ""
        raw_body = body_bytes.decode("utf-8", errors="replace")[:4000]
        try:
            raw_event = json.loads(raw_body).get("event", "")
        except Exception:
            pass
        db.add(WebhookLog(
            event=raw_event or "(rejected)",
            payment_id=None,
            payment_link_id=None,
            payload=raw_body,
            status="invalid_signature",
            received_at=datetime.now(timezone.utc)
        ))
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid Razorpay webhook signature")

    try:
        data = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON webhook payload")

    return process_payment_event(db=db, data=data)


@router.post("/simulate-payment", response_model=WebhookResponse)
def simulate_payment_capture(
    payload: SimulatePaymentRequest,
    db: Session = Depends(get_db),
    merchant_id: str = Depends(get_current_merchant_id)
):
    """
    Local test helper: simulates a Razorpay 'payment.captured' webhook for one of the
    logged-in merchant's own orders (by order_id or payment_link_id), so "created" orders
    move to "captured" without the Razorpay dashboard. Uses the exact same processing
    (classification + repr) as the real webhook endpoint.
    """
    order = None
    if payload.order_id:
        order = db.query(Order).filter(
            Order.id == payload.order_id,
            Order.merchant_id == merchant_id
        ).first()
    elif payload.payment_link_id:
        order = db.query(Order).filter(
            Order.payment_link_id == payload.payment_link_id,
            Order.merchant_id == merchant_id
        ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found for this merchant")

    try:
        notes = json.loads(order.notes) if order.notes else {}
    except Exception:
        notes = {}
    if not notes.get("source"):
        notes["source"] = order.source

    data = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": order.payment_id or f"pay_sim_{order.id}",
                    "amount": int(round(order.amount * 100)),
                    "invoice_id": order.payment_link_id,
                    "notes": notes,
                }
            }
        }
    }
    return process_payment_event(db=db, data=data)

def _looks_like_real_link(link_id: str) -> bool:
    """True for real Razorpay payment-link ids (plink_...) vs generated mock ids."""
    if not link_id:
        return False
    if link_id.startswith("plink_test_") or link_id.startswith("plink_mock_"):
        return False
    return link_id.startswith("plink_") and len(link_id) >= 14


def reconcile_pending_payments(db: Session) -> int:
    """
    Pulls the live Razorpay status of every order that is still 'created' with a
    real payment link, and if Razorpay reports it 'paid', applies the exact same
    capture/classification logic as a real payment.captured webhook. This makes
    revenue flow into ROAS without depending on the webhook tunnel arriving.
    Returns the number of orders newly captured.
    """
    pending = db.query(Order).filter(Order.status == "created").all()
    captured = 0
    for o in pending:
        if not _looks_like_real_link(o.payment_link_id):
            continue
        status = fetch_payment_link_status(o.payment_link_id)
        if status != "paid":
            continue
        try:
            notes = json.loads(o.notes) if o.notes else {}
        except Exception:
            notes = {}
        data = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": None,
                        "amount": int(round(o.amount * 100)),
                        "invoice_id": o.payment_link_id,
                        "notes": notes,
                    }
                }
            }
        }
        before = o.status
        process_payment_event(db=db, data=data)
        if before != "captured":
            captured += 1
    return captured


@router.get("/orders", response_model=List[OrderResponse])
def list_orders(
    db: Session = Depends(get_db),
    merchant_id: str = Depends(get_current_merchant_id)
):
    """List the logged-in merchant's orders with classification ('human' vs 'agent') and payment status.

    Purchases made via the no-login demo storefront land in the shared 'demo'
    tenant; auto-adopt them into this merchant so they show up immediately.
    """
    from seed_merchant import adopt_demo_orders
    adopt_demo_orders(merchant_id)
    reconcile_pending_payments(db)
    orders = db.query(Order).filter(Order.merchant_id == merchant_id).order_by(Order.id.desc()).all()
    return orders


@router.post("/orders/adopt-demo", response_model=dict)
def adopt_demo_orders_for_merchant(
    db: Session = Depends(get_db),
    merchant_id: str = Depends(get_current_merchant_id)
):
    """
    Pulls orders created via the no-login demo storefront (e.g. robot_purchaser)
    into the logged-in merchant's tenant so they appear in Orders / ROAS / Audit.
    Idempotent: already-imported orders are skipped.
    """
    from seed_merchant import adopt_demo_orders
    imported = adopt_demo_orders(merchant_id)
    total = db.query(Order).filter(Order.merchant_id == merchant_id).count()
    return {"imported": imported, "orders": total}
