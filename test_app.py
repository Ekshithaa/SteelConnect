"""End-to-end checks for the main SteelConnect workflow."""

import re
import tempfile
import unittest
from pathlib import Path

import database
from app import app
from werkzeug.security import generate_password_hash


class SteelConnectWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_database_path = database.DATABASE_PATH
        database.DATABASE_PATH = Path(self.temp_directory.name) / "test.db"
        database.init_db()
        app.config["TESTING"] = True
        self.client = app.test_client()

    def tearDown(self):
        database.DATABASE_PATH = self.original_database_path
        self.temp_directory.cleanup()

    def csrf_token(self, response):
        match = re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True))
        self.assertIsNotNone(match, "Expected form CSRF token was not found")
        return match.group(1)

    def create_and_login_admin(self):
        with database.get_connection() as connection:
            connection.execute(
                "INSERT INTO users (fullname, email, phone, password, is_admin) VALUES (?, ?, ?, ?, 1)",
                ("Test Admin", "admin@example.com", "9999999999", generate_password_hash("safe-password")),
            )

        token = self.csrf_token(self.client.get("/login"))
        response = self.client.post("/login", data={
            "csrf_token": token,
            "email": "admin@example.com",
            "password": "safe-password",
        })
        self.assertEqual(response.status_code, 302)

    def test_public_pages_load(self):
        for path in ("/", "/products", "/products?category=Long+Products&sort=price-low", "/login", "/register", "/track-order"):
            self.assertEqual(self.client.get(path).status_code, 200)
        self.assertEqual(self.client.get("/place-order").status_code, 302)
        self.assertEqual(self.client.get("/complaints").status_code, 302)

    def test_admin_workspace_pages_load(self):
        self.create_and_login_admin()
        for path in ("/admin", "/orders", "/admin/customers", "/admin/reports", "/admin/complaints", "/products/new"):
            self.assertEqual(self.client.get(path).status_code, 200)

    def test_order_reduces_stock_and_can_be_tracked(self):
        self.create_and_login_admin()
        order_page = self.client.get("/place-order")
        token = self.csrf_token(order_page)
        product_id = re.search(r'<option value="(\d+)">TMT Bars', order_page.get_data(as_text=True)).group(1)

        response = self.client.post("/place-order", data={
            "csrf_token": token,
            "customer": "Test Steel Ltd",
            "phone": "8888888888",
            "product_id": product_id,
            "quantity": "5",
        })
        self.assertEqual(response.status_code, 200)
        order_id = re.search(r'<div class="order-id">([^<]+)</div>', response.get_data(as_text=True)).group(1)

        with database.get_connection() as connection:
            stock = connection.execute("SELECT stock FROM products WHERE id = ?", (product_id,)).fetchone()["stock"]
        self.assertEqual(stock, 240)

        token = self.csrf_token(self.client.get("/track-order"))
        response = self.client.post("/track-order", data={"csrf_token": token, "order_id": order_id})
        self.assertIn(b"Processing", response.data)

        self.assertIn(order_id.encode(), self.client.get("/my-orders").data)

    def test_registered_customer_can_create_support_ticket(self):
        token = self.csrf_token(self.client.get("/register"))
        self.client.post("/register", data={
            "csrf_token": token,
            "fullname": "Customer User",
            "email": "customer@example.com",
            "phone": "8888888888",
            "password": "safe-password",
            "confirm_password": "safe-password",
        })
        token = self.csrf_token(self.client.get("/login"))
        self.client.post("/login", data={"csrf_token": token, "email": "customer@example.com", "password": "safe-password"})
        token = self.csrf_token(self.client.get("/complaints"))
        response = self.client.post("/complaints", data={
            "csrf_token": token,
            "subject": "Delivery status query",
            "description": "Please share an update for my steel order delivery schedule.",
        }, follow_redirects=True)
        self.assertIn(b"Complaint submitted", response.data)
        self.assertIn(b"Delivery status query", response.data)


if __name__ == "__main__":
    unittest.main()
