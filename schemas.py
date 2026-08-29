"""
Pydantic schemas for request validation and response serialization.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ConfigDict

# --- Product Schemas ---
class ProductBase(BaseModel):
    name: str
    stock_count: int
    price: float
    margin: float

class ProductResponse(ProductBase):
    id: int
    last_updated: datetime
    staleness_status: str  # "fresh" or "stale"
    hours_since_update: float

    model_config = ConfigDict(from_attributes=True)

# --- Governance & Action Log Schemas ---
class PolicyCheckRequest(BaseModel):
    action: str  # e.g., "adjust_ad_budget" or "launch_campaign"
    details: Dict[str, Any]

class PolicyCheckResponse(BaseModel):
    action: str
    result: str  # "approved", "needs_approval", "blocked"
    reason: str
    log_id: int
    timestamp: datetime

class ActionLogResponse(BaseModel):
    id: int
    action: str
    details: str
    result: str
    reason: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Agent Schemas ---
class AgentActRequest(BaseModel):
    instruction: str

class ToolExecutionStep(BaseModel):
    tool: str
    input: Dict[str, Any]
    governance_result: Optional[str] = None
    governance_reason: Optional[str] = None
    output: Dict[str, Any]

class AgentActResponse(BaseModel):
    instruction: str
    status: str
    steps: List[ToolExecutionStep]
    final_summary: str

# --- Payment & Order Schemas ---
class CreatePaymentLinkRequest(BaseModel):
    amount: float
    product_name: Optional[str] = "Product Item"
    product_id: Optional[int] = None
    campaign_id: Optional[int] = None
    source: Optional[str] = "human"  # "human" or "agent"
    customer_email: Optional[str] = "buyer@example.com"
    customer_contact: Optional[str] = "+919876543210"

class PaymentLinkResponse(BaseModel):
    payment_link_id: str
    short_url: str
    amount: float
    product_name: str
    campaign_id: Optional[int] = None
    source: str
    status: str
    mode: Optional[str] = None

class OrderResponse(BaseModel):
    id: int
    payment_link_id: str
    payment_id: Optional[str] = None
    campaign_id: Optional[int] = None
    product_name: str
    amount: float
    currency: str
    status: str
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class WebhookResponse(BaseModel):
    status: str
    event: str
    message: str
    order_id: Optional[int] = None
    source: Optional[str] = None

# --- ROAS Analytics Schemas ---
class ROASSummary(BaseModel):
    total_cost: float
    total_revenue: float
    human_revenue: float
    agent_revenue: float
    human_roas: float
    agent_roas: float
    total_roas: float
    orders_count: Dict[str, int]

class CampaignROASBreakdown(BaseModel):
    campaign_id: int
    campaign_name: str
    product_id: Optional[int]
    product_name: Optional[str]
    cost: float
    human_revenue: float
    agent_revenue: float
    total_revenue: float
    human_roas: float
    agent_roas: float
    total_roas: float
    orders_count: Dict[str, int]

class ROASReportResponse(BaseModel):
    summary: ROASSummary
    campaigns: List[CampaignROASBreakdown]

# --- Audit Log Timeline Schemas ---
class TimelineEvent(BaseModel):
    timestamp: datetime
    category: str  # "governance", "order", "campaign", "webhook"
    event_type: str
    title: str
    result: Optional[str] = None
    reason: Optional[str] = None
    details: Dict[str, Any]

class AuditLogResponse(BaseModel):
    total_events: int
    timeline: List[TimelineEvent]
