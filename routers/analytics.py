"""
API endpoints for ROAS (Return On Ad Spend) Ledger and Order Technical Signal Comparison.
Splits revenue by Human vs Agent orders and provides side-by-side signal analytics.
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Campaign, Product, Order
from schemas import (
    ROASReportResponse, ROASSummary, CampaignROASBreakdown,
    CompareOrdersResponse, OrderSignalComparisonItem
)

router = APIRouter(prefix="/analytics", tags=["Analytics & ROAS"])

@router.get("/roas", response_model=ROASReportResponse)
def get_roas_report(db: Session = Depends(get_db)):
    """
    Computes overall ROAS and per-campaign ROAS breakdown split into:
    1. ROAS from Human-tagged purchases
    2. ROAS from Agent-tagged purchases
    """
    campaigns = db.query(Campaign).all()
    captured_orders = db.query(Order).filter(Order.status == "captured").all()

    # Calculate Global Totals
    total_cost = sum(c.ad_spend if c.ad_spend > 0 else c.budget for c in campaigns)
    
    human_orders = [o for o in captured_orders if o.source == "human"]
    agent_orders = [o for o in captured_orders if o.source == "agent"]
    
    human_revenue = sum(o.amount for o in human_orders)
    agent_revenue = sum(o.amount for o in agent_orders)
    total_revenue = human_revenue + agent_revenue
    
    human_roas = round(human_revenue / total_cost, 2) if total_cost > 0 else 0.0
    agent_roas = round(agent_revenue / total_cost, 2) if total_cost > 0 else 0.0
    total_roas = round(total_revenue / total_cost, 2) if total_cost > 0 else 0.0
    
    summary = ROASSummary(
        total_cost=round(total_cost, 2),
        total_revenue=round(total_revenue, 2),
        human_revenue=round(human_revenue, 2),
        agent_revenue=round(agent_revenue, 2),
        human_roas=human_roas,
        agent_roas=agent_roas,
        total_roas=total_roas,
        orders_count={
            "human": len(human_orders),
            "agent": len(agent_orders),
            "total": len(captured_orders)
        }
    )
    
    # Calculate Per-Campaign Breakdown
    campaign_breakdowns: List[CampaignROASBreakdown] = []
    for c in campaigns:
        prod = db.query(Product).filter(Product.id == c.product_id).first() if c.product_id else None
        
        # Link orders by direct campaign_id or fallback to product_id
        camp_orders = [
            o for o in captured_orders 
            if o.campaign_id == c.id or (o.campaign_id is None and c.product_id and o.product_id == c.product_id)
        ]
        
        c_human_orders = [o for o in camp_orders if o.source == "human"]
        c_agent_orders = [o for o in camp_orders if o.source == "agent"]
        
        c_human_rev = sum(o.amount for o in c_human_orders)
        c_agent_rev = sum(o.amount for o in c_agent_orders)
        c_total_rev = c_human_rev + c_agent_rev
        c_cost = c.ad_spend if c.ad_spend > 0 else c.budget
        
        c_human_roas = round(c_human_rev / c_cost, 2) if c_cost > 0 else 0.0
        c_agent_roas = round(c_agent_rev / c_cost, 2) if c_cost > 0 else 0.0
        c_total_roas = round(c_total_rev / c_cost, 2) if c_cost > 0 else 0.0
        
        campaign_breakdowns.append(
            CampaignROASBreakdown(
                campaign_id=c.id,
                campaign_name=c.name,
                product_id=c.product_id,
                product_name=prod.name if prod else None,
                cost=round(c_cost, 2),
                human_revenue=round(c_human_rev, 2),
                agent_revenue=round(c_agent_rev, 2),
                total_revenue=round(c_total_rev, 2),
                human_roas=c_human_roas,
                agent_roas=c_agent_roas,
                total_roas=c_total_roas,
                orders_count={
                    "human": len(c_human_orders),
                    "agent": len(c_agent_orders),
                    "total": len(camp_orders)
                }
            )
        )
        
    return ROASReportResponse(
        summary=summary,
        campaigns=campaign_breakdowns
    )

@router.get("/compare-orders", response_model=CompareOrdersResponse)
def compare_recent_orders(db: Session = Depends(get_db)):
    """
    Compares captured technical fingerprint signals (User-Agent, Referer, Click Delay)
    side-by-side for the two most recent orders to visually contrast Human vs Robot behavior.
    """
    recent_orders = db.query(Order).order_by(Order.id.desc()).limit(2).all()
    
    mapped_items = [OrderSignalComparisonItem.model_validate(o) for o in recent_orders]
    
    if len(recent_orders) < 2:
        return CompareOrdersResponse(
            total_orders_compared=len(recent_orders),
            recent_orders=mapped_items,
            signal_differences={
                "message": "At least 2 orders are required for side-by-side technical comparison. Perform 1 Human purchase and 1 Robot purchase first."
            }
        )
        
    o1, o2 = recent_orders[0], recent_orders[1]
    
    ua1, ua2 = (o1.user_agent or "").lower(), (o2.user_agent or "").lower()
    bot_keywords = ["headless", "playwright", "puppeteer", "selenium", "bot", "python-urllib", "httpx"]
    
    is_o1_bot_ua = any(kw in ua1 for kw in bot_keywords)
    is_o2_bot_ua = any(kw in ua2 for kw in bot_keywords)
    
    delay1 = o1.click_delay_seconds or 0.0
    delay2 = o2.click_delay_seconds or 0.0
    
    diff_summary = {
      "user_agent_signals": {
          f"order_id_{o1.id}": {
              "user_agent": o1.user_agent,
              "has_bot_signature": is_o1_bot_ua
          },
          f"order_id_{o2.id}": {
              "user_agent": o2.user_agent,
              "has_bot_signature": is_o2_bot_ua
          }
      },
      "click_timing_signals": {
          f"order_id_{o1.id}_delay": f"{delay1:.2f} seconds",
          f"order_id_{o2.id}_delay": f"{delay2:.2f} seconds",
          "timing_difference_seconds": round(abs(delay1 - delay2), 2),
          "faster_order_id": o1.id if delay1 < delay2 else o2.id
      },
      "verdict": (
          f"Order #{o1.id} ({o1.source}) vs Order #{o2.id} ({o2.source}). "
          f"User-Agents and click timing clearly distinguish automated robot scripts from human browser interaction."
      )
    }
    
    return CompareOrdersResponse(
        total_orders_compared=len(recent_orders),
        recent_orders=mapped_items,
        signal_differences=diff_summary
    )
