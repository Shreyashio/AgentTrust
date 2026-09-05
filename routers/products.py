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
from auth import get_current_merchant_id, get_demo_merchant_id

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
def list_products(
    db: Session = Depends(get_db),
    merchant_id: str = Depends(get_current_merchant_id)
):
    """List the logged-in merchant's products with stock, price, margin, and staleness status."""
    products = db.query(Product).filter(Product.merchant_id == merchant_id).all()
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

@router.get("/demo", response_model=List[ProductResponse])
def list_demo_products(db: Session = Depends(get_db)):
    """List the demo tenant's products (used by the no-login storefront)."""
    return _serialize_products(
        db.query(Product).filter(Product.merchant_id == get_demo_merchant_id()).all()
    )


@router.post("/seed-demo", response_model=dict)
def seed_demo_for_merchant(
    db: Session = Depends(get_db),
    merchant_id: str = Depends(get_current_merchant_id)
):
    """Seeds sample products + campaigns for the logged-in merchant (idempotent)."""
    from seed_merchant import seed_merchant
    seed_merchant(merchant_id)
    count = db.query(Product).filter(Product.merchant_id == merchant_id).count()
    return {"merchant_id": merchant_id, "products": count}


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    merchant_id: str = Depends(get_current_merchant_id)
):
    """Get a single product by ID (must belong to the logged-in merchant)."""
    p = db.query(Product).filter(
        Product.id == product_id,
        Product.merchant_id == merchant_id
    ).first()
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


def _serialize_products(products):
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
