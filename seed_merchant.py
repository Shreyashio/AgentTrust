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
from sqlalchemy.exc import IntegrityError
from database import SessionLocal
from models import Product, Campaign, Order

DEMO_MERCHANT_ID = "demo"

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


def adopt_demo_orders(merchant_id: str) -> int:
    """
    Copies the shared 'demo' storefront's orders into the given merchant's tenant.

    This is how purchases made via the no-login demo storefront (e.g. the
    robot_purchaser) can be pulled into a merchant's own dashboard. Idempotent:
    orders whose payment_link_id already exist for this merchant are skipped.
    """
    db = SessionLocal()
    added = 0
    try:
        demo_orders = db.query(Order).filter(Order.merchant_id == DEMO_MERCHANT_ID).all()
        if not demo_orders:
            return added

        merchant_products = {p.name: p for p in db.query(Product).filter(Product.merchant_id == merchant_id).all()}
        existing_links = {o.payment_link_id for o in db.query(Order).filter(Order.merchant_id == merchant_id).all()}

        for o in demo_orders:
            adopted_link = f"{o.payment_link_id}_adopted"

            # Idempotent re-run: skip if we already own the raw link or a copy.
            if o.payment_link_id in existing_links:
                continue
            if adopted_link in existing_links:
                copy = db.query(Order).filter(Order.payment_link_id == adopted_link).first()
                if copy:
                    # Never downgrade a copy that already advanced (captured/failed).
                    if copy.status == "created" and o.status not in ("created", None):
                        copy.status = o.status
                    copy.payment_id = o.payment_id or copy.payment_id
                    copy.source = o.source or copy.source
                    copy.classification_method = o.classification_method or copy.classification_method
                    copy.updated_at = o.updated_at or copy.updated_at
                    db.commit()
                continue

            prod = merchant_products.get(o.product_name) if o.product_name else None
            camp = None
            if o.campaign_id and prod:
                camp = db.query(Campaign).filter(
                    Campaign.product_id == prod.id,
                    Campaign.merchant_id == merchant_id
                ).first()

            try:
                db.add(Order(
                    payment_link_id=adopted_link,
                    payment_id=o.payment_id,
                    campaign_id=camp.id if camp else None,
                    product_id=prod.id if prod else None,
                    product_name=o.product_name,
                    amount=o.amount,
                    currency=o.currency,
                    status=o.status,
                    source=o.source,
                    user_agent=o.user_agent,
                    referer=o.referer,
                    click_delay_seconds=o.click_delay_seconds,
                    ip_address=o.ip_address,
                    classification_method=o.classification_method,
                    notes=o.notes or "",
                    created_at=o.created_at,
                    updated_at=o.updated_at,
                    merchant_id=merchant_id,
                ))
                db.commit()
                existing_links.add(adopted_link)
                added += 1
            except IntegrityError:
                db.rollback()
    finally:
        db.close()
    return added


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "demo"
    seed_merchant(target)
