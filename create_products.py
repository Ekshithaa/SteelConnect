"""Legacy compatibility command: safely prepare product storage."""

from database import init_db


if __name__ == "__main__":
    init_db()
    print("Products table is ready. Existing inventory was not changed.")
