"""Legacy compatibility command: use the central schema setup instead."""

from database import init_db


if __name__ == "__main__":
    init_db()
    print("Orders table is ready. No sample orders were added.")
