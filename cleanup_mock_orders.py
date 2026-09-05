"""
Cleanup helper for stale MOCK fallback orders.

Removes orders whose payment_link_id is a generated fallback link
(plink_test_... / plink_mock_...) plus their related webhook logs.

By default it only deletes 'created' (never-paid) mock orders and keeps any
that reached 'captured'/'failed', so your simulated test revenue isn't wiped
out. Pass --purge-all to also remove captured/failed mock orders.
Dry-run (preview only) unless --yes is passed.
"""
import argparse
import sys

from database import SessionLocal
from models import Order, WebhookLog

MOCK_PREFIXES = ("plink_test_", "plink_mock_")


def find_mock_orders(db, purge_all: bool):
    rows = db.query(Order).filter(
        Order.payment_link_id.like("plink_test_%") | Order.payment_link_id.like("plink_mock_%")
    ).order_by(Order.id).all()

    if purge_all:
        return rows

    keep = []
    delete = []
    for o in rows:
        if o.status in ("captured", "failed"):
            keep.append(o)
        else:
            delete.append(o)
    return delete


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", action="store_true", help="actually delete (no preview)")
    parser.add_argument("--purge-all", action="store_true",
                        help="also delete captured/failed mock orders")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        targets = find_mock_orders(db, args.purge_all)
        if not targets:
            print("No removable mock orders found.")
            return 0

        print(f"Mock orders to remove: {len(targets)}")
        for o in targets:
            print(f"  #{o.id}  link={o.payment_link_id!r}  source={o.source}  "
                  f"status={o.status}  amount={o.amount:.2f}  merchant={o.merchant_id}")

        links = {o.payment_link_id for o in targets}

        if not args.yes:
            print("\nDry run — nothing deleted. Re-run with --yes to apply.")
            return 0

        # Delete webhook logs referencing removed orders first.
        for link_chunk in list(links):
            db.query(WebhookLog).filter(WebhookLog.payment_link_id == link_chunk).delete(
                synchronize_session=False
            )
        db.query(Order).filter(Order.payment_link_id.in_(links)).delete(synchronize_session=False)
        db.commit()
        print(f"\nDeleted {len(targets)} mock order(s) and their webhook logs.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())