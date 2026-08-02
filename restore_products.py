"""Legacy compatibility command: safely prepare starter product storage."""

from database import init_db


if __name__ == "__main__":
    init_db()
    print("Inventory is ready. Starter products are only added to an empty database.")
