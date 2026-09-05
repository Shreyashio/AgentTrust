"""
SQLAlchemy ORM database models for AgentTrust.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Product(Base):
    """
    Product SKU / Inventory table.
    Tracks stock, price, profit margin, and timestamp for staleness checking.
    """
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    stock_count = Column(Integer, default=0, nullable=False)
    price = Column(Float, nullable=False)
    margin = Column(Float, default=0.0, nullable=False)  # e.g. 0.30 for 30% profit margin
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    merchant_id = Column(String, nullable=False, index=True, server_default="demo", default="demo")  # Clerk user ID

    # Relationships
    campaigns = relationship("Campaign", back_populates="product")
    orders = relationship("Order", back_populates="product")

class Campaign(Base):
    """
    Ad Campaign table.
    Tracks campaigns created or adjusted by the AI agent and their ad spend/cost.
    """
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    budget = Column(Float, nullable=False)
    ad_spend = Column(Float, default=0.0, nullable=False)  # Actual cost / ad expenditure
    ad_copy = Column(Text, nullable=True)
    status = Column(String, default="active", nullable=False)  # 'active', 'pending_approval', 'blocked'
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    merchant_id = Column(String, nullable=False, index=True, server_default="demo", default="demo")  # Clerk user ID

    # Relationships
    product = relationship("Product", back_populates="campaigns")
    orders = relationship("Order", back_populates="campaign")

class Order(Base):
    """
    Order table for transactions processed via Razorpay.
    Classifies purchases as 'human' or 'agent' and records technical fingerprint signals.
    """
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    payment_link_id = Column(String, unique=True, index=True, nullable=False)
    payment_id = Column(String, nullable=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    product_name = Column(String, nullable=False)
    amount = Column(Float, nullable=False)  # Revenue generated
    currency = Column(String, default="INR", nullable=False)
    status = Column(String, default="created", nullable=False)  # 'created', 'captured', 'failed'
    source = Column(String, default="human", nullable=False)  # 'human' or 'agent'
    
    # Technical Fingerprint Signals (Captured for Human vs Robot classification)
    user_agent = Column(Text, nullable=True)
    referer = Column(Text, nullable=True)
    click_delay_seconds = Column(Float, nullable=True)  # Time gap between page load and purchase click
    ip_address = Column(String, nullable=True)
    classification_method = Column(String, default="manual_tag_fallback", nullable=False)  # 'real_signal_based' or 'manual_tag_fallback'

    notes = Column(Text, nullable=True)  # JSON string of metadata/notes
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    merchant_id = Column(String, nullable=False, index=True, server_default="demo", default="demo")  # Clerk user ID

    # Relationships
    product = relationship("Product", back_populates="orders")
    campaign = relationship("Campaign", back_populates="orders")

class ActionLog(Base):
    """
    Audit log table recording every action attempt evaluated by the Governance Engine.
    """
    __tablename__ = "action_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, nullable=False, index=True)
    details = Column(Text, nullable=False)  # JSON-encoded payload details
    result = Column(String, nullable=False)  # 'approved', 'needs_approval', or 'blocked'
    reason = Column(String, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    merchant_id = Column(String, nullable=False, index=True, server_default="demo", default="demo")  # Clerk user ID

class WebhookLog(Base):
    """
    Logs all incoming Razorpay webhook events.
    """
    __tablename__ = "webhook_logs"

    id = Column(Integer, primary_key=True, index=True)
    event = Column(String, nullable=False, index=True)
    payment_id = Column(String, nullable=True)
    payment_link_id = Column(String, nullable=True)
    payload = Column(Text, nullable=False)
    status = Column(String, default="processed", nullable=False)
    received_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
