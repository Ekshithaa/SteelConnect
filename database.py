"""Database helpers and safe schema setup for SteelConnect."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


# A local file is convenient while developing. Hosting providers can set
# DATABASE_PATH to a mounted persistent disk, for example /var/data/steelconnect.db.
DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", Path(__file__).with_name("steelconnect.db")))


@contextmanager
def get_connection():
    """Yield a transaction-safe SQLite connection and always close it."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _columns(connection, table_name):
    return {row["name"] for row in connection.execute(f"PRAGMA table_info({table_name})")}


def init_db():
    """Create the application's tables and safely upgrade the original schema."""
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fullname TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                phone TEXT NOT NULL,
                password TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
                price INTEGER NOT NULL DEFAULT 0 CHECK (price >= 0),
                category TEXT NOT NULL DEFAULT 'Other',
                description TEXT NOT NULL DEFAULT '',
                image_filename TEXT NOT NULL DEFAULT 'images/steel-mill-hero.png'
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL UNIQUE,
                customer_name TEXT NOT NULL,
                phone TEXT,
                user_email TEXT,
                product TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                status TEXT NOT NULL DEFAULT 'Processing'
                    CHECK (status IN ('Processing', 'Approved', 'Dispatched', 'Delivered')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT NOT NULL UNIQUE,
                user_email TEXT NOT NULL,
                subject TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open'
                    CHECK (status IN ('Open', 'In Progress', 'Resolved')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # These upgrades preserve data from the first version of the project.
        order_columns = _columns(connection, "orders")
        if "customer_name" not in order_columns:
            connection.execute("ALTER TABLE orders ADD COLUMN customer_name TEXT")
            if "customer" in order_columns:
                connection.execute("UPDATE orders SET customer_name = customer")
        if "phone" not in order_columns:
            connection.execute("ALTER TABLE orders ADD COLUMN phone TEXT")
        if "quantity" not in order_columns:
            connection.execute("ALTER TABLE orders ADD COLUMN quantity INTEGER")
        if "user_email" not in order_columns:
            connection.execute("ALTER TABLE orders ADD COLUMN user_email TEXT")
        if "created_at" not in order_columns:
            connection.execute("ALTER TABLE orders ADD COLUMN created_at TEXT")
            connection.execute("UPDATE orders SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")

        user_columns = _columns(connection, "users")
        if "is_admin" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")

        product_columns = _columns(connection, "products")
        if "category" not in product_columns:
            connection.execute("ALTER TABLE products ADD COLUMN category TEXT NOT NULL DEFAULT 'Other'")
        if "description" not in product_columns:
            connection.execute("ALTER TABLE products ADD COLUMN description TEXT NOT NULL DEFAULT ''")
        if "image_filename" not in product_columns:
            connection.execute("ALTER TABLE products ADD COLUMN image_filename TEXT NOT NULL DEFAULT 'images/steel-mill-hero.png'")

        product_count = connection.execute("SELECT COUNT(*) AS count FROM products").fetchone()["count"]
        if product_count == 0:
            connection.executemany(
                "INSERT INTO products (name, stock, price, category, description, image_filename) VALUES (?, ?, ?, ?, ?, ?)",
                [
                    ("TMT Bars", 245, 58500, "Long Products", "High-strength TMT bars for construction.", "images/tmt-bars.png"),
                    ("Steel Coils", 120, 72000, "Flat Products", "Premium quality steel coils for industry.", "images/steel-coils.png"),
                    ("MS Sheets", 300, 65000, "Flat Products", "Durable mild steel sheets for fabrication.", "images/ms-sheets.png"),
                    ("Steel Pipes", 150, 48000, "Pipes & Tubes", "Durable industrial steel pipes.", "images/steel-pipes.png"),
                ],
            )

        catalog_products = [
            ("TMT Bars", 245, 58500, "Long Products", "High-strength TMT bars for construction.", "images/tmt-bars.png"),
            ("Steel Coils", 120, 72000, "Flat Products", "Premium quality steel coils for industry.", "images/steel-coils.png"),
            ("MS Sheets", 300, 65000, "Flat Products", "Durable mild steel sheets for fabrication.", "images/ms-sheets.png"),
            ("Steel Pipes", 150, 48000, "Pipes & Tubes", "Durable industrial steel pipes.", "images/steel-pipes.png"),
            ("Angle Steel", 85, 56000, "Long Products", "Reliable angle steel for structural applications.", "images/angle-steel.png"),
            ("Channel Steel", 70, 59000, "Long Products", "Strong structural channel steel for construction.", "images/channel-steel.png"),
            ("I Beam", 60, 60000, "Structural Steel", "Heavy-duty I-beams for industrial structures.", "images/i-beam.png"),
            ("Square Bars", 95, 54000, "Long Products", "Mild steel square bars for fabrication work.", "images/square-bars.png"),
        ]
        for product in catalog_products:
            existing_product = connection.execute("SELECT id FROM products WHERE name = ?", (product[0],)).fetchone()
            if existing_product:
                connection.execute(
                    "UPDATE products SET category = ?, description = ?, image_filename = ? WHERE id = ?",
                    (product[3], product[4], product[5], existing_product["id"]),
                )
            else:
                connection.execute(
                    "INSERT INTO products (name, stock, price, category, description, image_filename) VALUES (?, ?, ?, ?, ?, ?)",
                    product,
                )

        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_order_id ON orders(order_id)"
        )


if __name__ == "__main__":
    init_db()
    print("Database is ready.")
