"""
API endpoint for the complete system Audit Trail and chronological Timeline.
Aggregates every agent action, policy decision, campaign lifecycle event, order transaction, and webhook.
"""
import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from models import ActionLog, Order, Campaign, WebhookLog
from schemas import AuditLogResponse, TimelineEvent
from auth import get_current_merchant_id

router = APIRouter(prefix="", tags=["Audit Trail"])

def safe_parse_json(text: Optional[str]) -> dict:
    """Helper to safely parse JSON strings or return empty dict."""
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        return {"raw": text}

@router.get("/audit-log", response_model=AuditLogResponse)
def get_audit_trail(
    order: str = Query("asc", description="Sort order: 'asc' for chronological narrative, 'desc' for latest first"),
    db: Session = Depends(get_db),
    merchant_id: str = Depends(get_current_merchant_id)
):
    """
    Returns a unified chronological audit trail of the logged-in merchant's system:
    - Every AI Agent action attempt
    - Every Governance policy decision (approved, held for approval, blocked)
    - Every Campaign created or updated
    - Every Order created, classified (human vs agent), and captured/failed
    - Every Razorpay webhook processed for this merchant's orders
    """
    events: List[TimelineEvent] = []

    # 1. Governance Policy Decisions & Agent Actions
    action_logs = db.query(ActionLog).filter(ActionLog.merchant_id == merchant_id).all()
    for log in action_logs:
        events.append(
            TimelineEvent(
                timestamp=log.timestamp,
                category="governance",
                event_type=f"action_{log.action}",
                title=f"Governance Check: {log.action}",
                result=log.result,
                reason=log.reason,
                details=safe_parse_json(log.details)
            )
        )

    # 2. Campaign Lifecycle Events
    campaigns = db.query(Campaign).filter(Campaign.merchant_id == merchant_id).all()
    for camp in campaigns:
        events.append(
            TimelineEvent(
                timestamp=camp.created_at,
                category="campaign",
                event_type="campaign_created",
                title=f"Campaign Proposed: '{camp.name}'",
                result=camp.status,
                reason=f"Campaign #{camp.id} created with budget INR {camp.budget:.2f} (Status: {camp.status})",
                details={
                    "campaign_id": camp.id,
                    "name": camp.name,
                    "product_id": camp.product_id,
                    "budget": camp.budget,
                    "ad_spend": camp.ad_spend,
                    "status": camp.status,
                    "ad_copy": camp.ad_copy
                }
            )
        )

    # 3. Orders Created & Captured
    orders = db.query(Order).filter(Order.merchant_id == merchant_id).all()
    for o in orders:
        # Order creation event
        events.append(
            TimelineEvent(
                timestamp=o.created_at,
                category="order",
                event_type="order_created",
                title=f"Order #{o.id} Created ({o.source.upper()} buyer)",
                result=o.status,
                reason=f"Payment link generated for '{o.product_name}' (INR {o.amount:.2f}) tagged as '{o.source}' purchase.",
                details={
                    "order_id": o.id,
                    "payment_link_id": o.payment_link_id,
                    "product_name": o.product_name,
                    "product_id": o.product_id,
                    "campaign_id": o.campaign_id,
                    "amount": o.amount,
                    "source": o.source,
                    "status": o.status
                }
            )
        )
        
        # Order status update event (e.g. captured or failed) if different from creation
        if o.updated_at and o.updated_at != o.created_at and o.status in ("captured", "failed"):
            events.append(
                TimelineEvent(
                    timestamp=o.updated_at,
                    category="order",
                    event_type=f"order_{o.status}",
                    title=f"Order #{o.id} Payment {o.status.capitalize()}",
                    result=o.status,
                    reason=f"Payment for Order #{o.id} ({o.product_name}) was {o.status}. Attributed to '{o.source}' revenue.",
                    details={
                        "order_id": o.id,
                        "payment_id": o.payment_id,
                        "amount": o.amount,
                        "source": o.source,
                        "status": o.status
                    }
                )
            )

    # 4. Razorpay Webhooks (only those tied to this merchant's orders via payment link / payment id)
    merchant_link_ids = {o.payment_link_id for o in orders if o.payment_link_id}
    merchant_payment_ids = {o.payment_id for o in orders if o.payment_id}
    webhook_logs = db.query(WebhookLog).all()
    for w in webhook_logs:
        belongs_to_merchant = (
            (w.payment_link_id and w.payment_link_id in merchant_link_ids) or
            (w.payment_id and w.payment_id in merchant_payment_ids)
        )
        if not belongs_to_merchant:
            continue
        events.append(
            TimelineEvent(
                timestamp=w.received_at,
                category="webhook",
                event_type=w.event,
                title=f"Webhook Received: {w.event}",
                result=w.status,
                reason=f"Razorpay webhook event '{w.event}' processed for payment '{w.payment_id or w.payment_link_id}'",
                details={
                    "webhook_id": w.id,
                    "event": w.event,
                    "payment_id": w.payment_id,
                    "payment_link_id": w.payment_link_id,
                    "status": w.status
                }
            )
        )

    # Sort timeline by timestamp
    reverse_sort = order.lower() == "desc"
    events.sort(key=lambda e: e.timestamp, reverse=reverse_sort)

    return AuditLogResponse(
        total_events=len(events),
        timeline=events
    )
