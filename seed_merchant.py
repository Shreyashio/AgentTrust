"""
Seed script for a specific merchant tenant.

Adds the sample SKUs plus a couple of campaigns for the given merchant_id
(Cliff's Clerk user ID). It is idempotent: it only creates products/campaigns
for that merchant if they do not already exist, so it never clobbers a real
merchant's live data.

Usage:
    python seed_merchant.py                      # seeds the "demo" tenant
    python seed_merchant.py <merchant_id>        # seeds a specific Clerk user
"""
import sys
from datetime import datetime, timedelta, timezone
from database import SessionLocal
from models import Product, Campaign

SAMPLE_PRODUCTS = [
    {"name": "Wireless Noise-Cancelling Headphones", "stock_count": 45, "price": 2999.00, "margin": 0.35, "age_hours": 2},
    {"name": "Mechanical Gaming Keyboard RGB", "stock_count": 20, "price": 4499.00, "margin": 0.40, "age_hours": 5},
    {"name": "Ultra-Wide Gaming Monitor 27-inch", "stock_count": 12, "price": 18999.00, "margin": 0.25, "age_minutes": 15},
    {"name": "Ergonomic Aluminium Laptop Stand", "stock_count": 85, "price": 1299.00, "margin": 0.50, "age_hours": 18},
    {"name": "Vintage USB-C Mechanical Numpad", "stock_count": 5, "price": 1799.00, "margin": 0.30, "age_days": 5},
    {"name": "Legacy USB 2.0 Hub 4-Port", "stock_count": 0, "price": 499.00, "margin": 0.20, "age_days": 45},
]


def seed_merchant(merchant_id: str = "demo"):
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        existing_products = {
            p.name: p for p in db.query(Product).filter(Product.merchant_id == merchant_id).all()
        }
        existing_campaigns = {
            c.name: c for c in db.query(Campaign).filter(Campaign.merchant_id == merchant_id).all()
        }

        created_products = 0
        for spec in SAMPLE_PRODUCTS:
            if spec["name"] in existing_products:
                continue
            last_updated = now - timedelta(
                days=spec.get("age_days", 0),
                hours=spec.get("age_hours", 0),
                minutes=spec.get("age_minutes", 0),
            )
            db.add(Product(
                name=spec["name"],
                stock_count=spec["stock_count"],
                price=spec["price"],
                margin=spec["margin"],
                last_updated=last_updated,
                merchant_id=merchant_id,
            ))
            created_products += 1
        db.commit()

        # Re-query after commit to link campaigns to freshly created products.
        product_rows = db.query(Product).filter(Product.merchant_id == merchant_id).all()
        created_campaigns = 0
        for i, prod in enumerate(product_rows):
            camp_name = f"{prod.name} Campaign"
            if camp_name in existing_campaigns:
                continue
            db.add(Campaign(
                name=camp_name,
                product_id=prod.id,
                budget=1500.0 + i * 500,
                ad_spend=250.0 + i * 100,
                status="active",
                merchant_id=merchant_id,
            ))
            created_campaigns += 1
        db.commit()

        print(f"Merchant '{merchant_id}': created {created_products} product(s), {created_campaigns} campaign(s). "
              f"Total products: {len(product_rows)}.")
    finally:
        db.close()


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "demo"
    seed_merchant(target)
