# SteelConnect

SteelConnect is a Flask web application for managing steel inventory, placing customer orders, tracking their status, and administering products and fulfillment.

## What works

- Professional responsive homepage and SteelBot assistant
- Account registration and secure password hashing
- Login, logout, and protected administrator pages
- Product add, edit, and delete tools for administrators
- Inventory-aware ordering that prevents overselling and reduces stock
- Public order tracking without exposing customer contact details
- Order fulfillment workflow: Processing → Approved → Dispatched → Delivered
- Personal order history and support-ticket workflow

## Run the project

1. Open a terminal in this project folder.
2. Create a virtual environment: `python3 -m venv .venv`
3. Activate it: `source .venv/bin/activate`
4. Install Flask: `pip install -r requirements.txt`
5. Start the site: `python3 app.py`
6. Open `http://127.0.0.1:5000` in your browser.

The database is created and upgraded automatically when the app starts. If there are no products, starter steel products are added automatically.

## Test the workflow

Run `python3 -m unittest test_app.py` to check public pages, registration, login, stock reduction, and order tracking using a temporary test database.

## Create the administrator account

Customer registration never grants administrator access. Create the first administrator securely from the project folder:

`python3 create_admin.py`

The command asks for the administrator details and password without storing them in source code or terminal history.

## Before deployment

Set a strong `SECRET_KEY` environment variable, use a production WSGI server, and move from SQLite to a managed database as the project grows. The app refuses to start with `FLASK_ENV=production` unless `SECRET_KEY` is set. See `.env.example` for the required values.

## Database setup and upgrades

Run `python3 database.py` to create or safely upgrade the database. The old `create_orders.py`, `create_products.py`, and `restore_products.py` commands now use the same safe setup process and no longer delete or insert conflicting data.
