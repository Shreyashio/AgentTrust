"""
Seed script to initialize SQLite database and insert sample SKU / inventory data.
Includes both fresh products and products with older timestamps to simulate stale data.
"""
from datetime import datetime, timedelta, timezone
from database import engine, SessionLocal, Base
from models import Product, Campaign, Order, ActionLog, WebhookLog

def seed_database(reset_all_tables: bool = False):
    """
    Initializes or resets database tables and seeds sample inventory items.
    """
    if reset_all_tables:
        Base.metadata.drop_all(bind=engine)
        
    # Create all database tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Clear existing products to ensure clean seed
        db.query(Product).delete()
        
        now = datetime.now(timezone.utc)
        
        sample_products = [
            Product(
                name="Wireless Noise-Cancelling Headphones",
                stock_count=45,
                price=2999.00,
                margin=0.35,
                last_updated=now - timedelta(hours=2)  # Fresh (2 hours old)
            ),
            Product(
                name="Mechanical Gaming Keyboard RGB",
                stock_count=20,
                price=4499.00,
                margin=0.40,
                last_updated=now - timedelta(hours=5)  # Fresh (5 hours old)
            ),
            Product(
                name="Ultra-Wide Gaming Monitor 27-inch",
                stock_count=12,
                price=18999.00,
                margin=0.25,
                last_updated=now - timedelta(minutes=15)  # Fresh (15 minutes old)
            ),
            Product(
                name="Ergonomic Aluminium Laptop Stand",
                stock_count=85,
                price=1299.00,
                margin=0.50,
                last_updated=now - timedelta(hours=18)  # Fresh (18 hours old)
            ),
            Product(
                name="Vintage USB-C Mechanical Numpad",
                stock_count=5,
                price=1799.00,
                margin=0.30,
                last_updated=now - timedelta(days=5)  # Stale (5 days old)
            ),
            Product(
                name="Legacy USB 2.0 Hub 4-Port",
                stock_count=0,
                price=499.00,
                margin=0.20,
                last_updated=now - timedelta(days=45)  # Stale (45 days old)
            ),
        ]
        
        db.add_all(sample_products)
        db.commit()
        print(f"Successfully initialized and seeded {len(sample_products)} products into SQLite database.")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database(reset_all_tables=True)
