"""
API endpoints for Product SKU and Inventory management.
Includes staleness tracking (fresh if updated within 24 hours, stale otherwise).
"""
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Product
from schemas import ProductResponse

router = APIRouter(prefix="/products", tags=["Products"])

def calculate_staleness(last_updated: datetime):
    """
    Determines if a product's inventory data is fresh or stale.
    Fresh: updated within the last 24 hours.
    Stale: updated more than 24 hours ago.
    """
    now = datetime.now(timezone.utc)
    # Ensure last_updated has timezone info for comparison
    if last_updated.tzinfo is None:
        last_updated = last_updated.replace(tzinfo=timezone.utc)
    
    elapsed_seconds = (now - last_updated).total_seconds()
    hours_elapsed = round(max(0.0, elapsed_seconds / 3600.0), 2)
    staleness_status = "fresh" if hours_elapsed <= 24.0 else "stale"
    
    return staleness_status, hours_elapsed

@router.get("", response_model=List[ProductResponse])
def list_products(db: Session = Depends(get_db)):
    """List all products with their stock, price, margin, and staleness status."""
    products = db.query(Product).all()
    results = []
    
    for p in products:
        status, hours = calculate_staleness(p.last_updated)
        results.append(
            ProductResponse(
                id=p.id,
                name=p.name,
                stock_count=p.stock_count,
                price=p.price,
                margin=p.margin,
                last_updated=p.last_updated,
                staleness_status=status,
                hours_since_update=hours
            )
        )
    return results

@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get a single product by ID with staleness evaluation."""
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")
    
    status, hours = calculate_staleness(p.last_updated)
    return ProductResponse(
        id=p.id,
        name=p.name,
        stock_count=p.stock_count,
        price=p.price,
        margin=p.margin,
        last_updated=p.last_updated,
        staleness_status=status,
        hours_since_update=hours
    )
