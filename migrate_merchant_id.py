"""
One-time migration: adds a merchant_id column to every merchant-owned table.

Existing rows are tagged with the default "demo" merchant so nothing breaks.

Safe to run more than once (it only adds columns that are missing):
    python migrate_merchant_id.py
"""
from sqlalchemy import create_engine, inspect, text
import config

engine = create_engine(config.DATABASE_URL)

# (table name -> SQL column definition to add)
TABLES = {
    "products": "merchant_id VARCHAR NOT NULL DEFAULT 'demo'",
    "campaigns": "merchant_id VARCHAR NOT NULL DEFAULT 'demo'",
    "orders": "merchant_id VARCHAR NOT NULL DEFAULT 'demo'",
    "action_logs": "merchant_id VARCHAR NOT NULL DEFAULT 'demo'",
}


def migrate():
    inspector = inspect(engine)

    with engine.begin() as conn:
        for table, column_ddl in TABLES.items():
            if table not in inspector.get_table_names():
                print(f"Skipped {table}: table does not exist yet.")
                continue

            column_names = [c["name"] for c in inspector.get_columns(table)]
            if "merchant_id" in column_names:
                print(f"OK {table}: merchant_id already present.")
            else:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_ddl}"))
                print(f"Added merchant_id to {table}.")

    inspector.clear_cache()
    print("Migration finished. Existing rows are tagged as merchant 'demo'.")


if __name__ == "__main__":
    migrate()