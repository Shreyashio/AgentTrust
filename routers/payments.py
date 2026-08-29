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
from schemas import CreatePaymentLinkRequest, PaymentLinkResponse, OrderResponse, WebhookResponse
from razorpay_service import create_payment_link, verify_webhook_signature, classify_purchase_source

router = APIRouter(prefix="/payments", tags=["Payments & Orders"])

@router.post("/create-link", response_model=PaymentLinkResponse)
def create_test_payment_link(
    payload: CreatePaymentLinkRequest,
    request: Request,
    x_click_delay: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Generates a Razorpay Test Mode Payment Link for a product/amount.
    Captures request technical signals (User-Agent, Referer, Click Delay, IP) and classifies purchase.
    """
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

    # If product_id is provided, fetch product details
    if prod_id:
        prod = db.query(Product).filter(Product.id == prod_id).first()
        if prod:
            prod_name = prod.name
            if payload.amount <= 0:
                payload.amount = prod.price
                
    # If campaign_id not specified, look for active campaign promoting this product
    if not camp_id and prod_id:
        active_camp = db.query(Campaign).filter(Campaign.product_id == prod_id).order_by(Campaign.id.desc()).first()
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
        updated_at=datetime.now(timezone.utc)
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

@router.post("/webhooks/razorpay", response_model=WebhookResponse)
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Webhook receiver for Razorpay events (payment.captured, payment.failed, payment_link.paid).
    Validates webhook, extracts metadata, classifies order, and updates SQLite database.
    """
    body_bytes = await request.body()
    
    # 1. Verify webhook signature if secret configured
    if not verify_webhook_signature(body_bytes, x_razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid Razorpay webhook signature")
    
    try:
        data = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON webhook payload")

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

@router.get("/orders", response_model=List[OrderResponse])
def list_orders(db: Session = Depends(get_db)):
    """List all orders with their classification ('human' vs 'agent') and payment status."""
    orders = db.query(Order).order_by(Order.id.desc()).all()
    return orders
