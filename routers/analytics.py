"""
API endpoints for ROAS (Return On Ad Spend) Ledger and Attribution Analytics.
Splits revenue and ROAS metrics by Human-tagged orders vs Agent-tagged orders.
"""
from typing import List, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Campaign, Product, Order
from schemas import ROASReportResponse, ROASSummary, CampaignROASBreakdown

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
