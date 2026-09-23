"""SteelConnect web application."""

import os
import re
import secrets
from datetime import datetime
from functools import wraps
from urllib.parse import urljoin, urlparse

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_connection, init_db


app = Flask(__name__)
# Local development has a harmless fallback, but production must supply a secret.
secret_key = os.environ.get("SECRET_KEY")
if os.environ.get("FLASK_ENV") == "production" and not secret_key:
    raise RuntimeError("Set SECRET_KEY before running SteelConnect in production.")
app.config["SECRET_KEY"] = secret_key or "local-development-only-change-me"

PRODUCT_IMAGE_FILENAMES = {
    "tmt bars": "images/tmt-bars.png",
    "steel coils": "images/steel-coils.png",
    "ms sheets": "images/ms-sheets.png",
    "steel pipes": "images/steel-pipes.png",
    "angle steel": "images/angle-steel.png",
    "channel steel": "images/channel-steel.png",
    "i beam": "images/i-beam.png",
    "square bars": "images/square-bars.png",
}

init_db()


def csrf_token():
    """Create one CSRF token per browser session for form protection."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


@app.context_processor
def inject_template_values():
    return {
        "csrf_token": csrf_token,
        "product_image": lambda product: url_for(
            "static",
            filename=(product["image_filename"] if hasattr(product, "keys") and product["image_filename"] else PRODUCT_IMAGE_FILENAMES.get(str(product).lower(), "images/steel-mill-hero.png")),
        ),
    }


def require_csrf():
    if not secrets.compare_digest(request.form.get("csrf_token", ""), session.get("csrf_token", "")):
        abort(400, "Your form expired. Please refresh the page and try again.")


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Administrator access is required for that page.", "danger")
            return redirect(url_for("home"))
        return view(*args, **kwargs)
    return wrapped_view


def parse_positive_integer(value, field_name):
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a whole number.")
    if number <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")
    return number


def make_order_id():
    return f"ORD-{datetime.now():%Y%m%d}-{secrets.token_hex(3).upper()}"


def make_ticket_id():
    return f"TKT-{datetime.now():%Y%m%d}-{secrets.token_hex(3).upper()}"


def is_safe_redirect_url(target):
    """Allow redirects only to pages inside this application."""
    if not target:
        return False
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return redirect_url.scheme in {"http", "https"} and redirect_url.netloc == host_url.netloc


def parse_nonnegative_integer(value, field_name):
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a whole number.")
    if number < 0:
        raise ValueError(f"{field_name} cannot be negative.")
    return number


@app.route("/")
def home():
    with get_connection() as connection:
        products = connection.execute("SELECT * FROM products ORDER BY id LIMIT 4").fetchall()
        inventory_snapshot = connection.execute(
            "SELECT * FROM products ORDER BY stock DESC, name LIMIT 6"
        ).fetchall()
        metrics = connection.execute(
            """SELECT
                (SELECT COUNT(*) FROM products) AS product_count,
                (SELECT COALESCE(SUM(stock), 0) FROM products) AS total_stock,
                (SELECT COUNT(*) FROM orders) AS order_count
            """
        ).fetchone()
    return render_template("index.html", products=products, inventory_snapshot=inventory_snapshot, metrics=metrics)


@app.route("/products")
def products_catalog():
    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    availability = request.args.get("availability", "").strip()
    sort = request.args.get("sort", "featured")
    sort_options = {
        "featured": "id ASC",
        "price-low": "price ASC",
        "price-high": "price DESC",
        "stock-high": "stock DESC",
        "name": "name COLLATE NOCASE ASC",
    }
    clauses, values = [], []
    if search:
        clauses.append("(name LIKE ? OR category LIKE ? OR description LIKE ?)")
        values.extend([f"%{search}%"] * 3)
    if category:
        clauses.append("category = ?")
        values.append(category)
    if availability == "in-stock":
        clauses.append("stock > 0")
    elif availability == "low-stock":
        clauses.append("stock > 0 AND stock <= 50")
    elif availability == "out-of-stock":
        clauses.append("stock <= 0")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_connection() as connection:
        products = connection.execute(
            f"SELECT * FROM products {where} ORDER BY {sort_options.get(sort, sort_options['featured'])}", values
        ).fetchall()
        categories = connection.execute("SELECT DISTINCT category FROM products ORDER BY category").fetchall()
    return render_template("products_catalog.html", products=products, categories=categories, search=search,
                           selected_category=category, availability=availability, selected_sort=sort)


@app.route("/products/<int:product_id>")
def product_detail(product_id):
    with get_connection() as connection:
        product = connection.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        abort(404)
    return render_template("product_detail.html", product=product)


@app.route("/admin")
@login_required
@admin_required
def admin():
    with get_connection() as connection:
        products = connection.execute("SELECT * FROM products ORDER BY name").fetchall()
        stats = connection.execute(
            """SELECT
                (SELECT COUNT(*) FROM products) AS product_count,
                (SELECT COALESCE(SUM(stock), 0) FROM products) AS total_stock,
                (SELECT COUNT(*) FROM orders WHERE status != 'Delivered') AS active_orders
            """
        ).fetchone()
    return render_template("admin.html", products=products, stats=stats)


@app.route("/admin/customers")
@login_required
@admin_required
def admin_customers():
    with get_connection() as connection:
        customers = connection.execute(
            """SELECT u.id, u.fullname, u.email, u.phone, COUNT(o.id) AS order_count
               FROM users u LEFT JOIN orders o ON o.user_email = u.email
               WHERE u.is_admin = 0 GROUP BY u.id ORDER BY u.fullname COLLATE NOCASE"""
        ).fetchall()
    return render_template("admin_customers.html", customers=customers)


@app.route("/admin/reports")
@login_required
@admin_required
def admin_reports():
    with get_connection() as connection:
        summary = connection.execute(
            """SELECT
                (SELECT COUNT(*) FROM products) AS product_count,
                (SELECT COALESCE(SUM(stock), 0) FROM products) AS stock_total,
                (SELECT COUNT(*) FROM orders) AS order_count,
                (SELECT COALESCE(SUM(quantity), 0) FROM orders) AS tons_ordered,
                (SELECT COUNT(*) FROM users WHERE is_admin = 0) AS customer_count"""
        ).fetchone()
        statuses = connection.execute(
            "SELECT status, COUNT(*) AS total FROM orders GROUP BY status ORDER BY total DESC"
        ).fetchall()
        low_stock = connection.execute(
            "SELECT * FROM products WHERE stock <= 50 ORDER BY stock ASC, name ASC"
        ).fetchall()
    return render_template("admin_reports.html", summary=summary, statuses=statuses, low_stock=low_stock)


@app.route("/products/new", methods=["GET", "POST"])
@login_required
@admin_required
def add_product():
    if request.method == "POST":
        require_csrf()
        name = request.form.get("product", "").strip()
        category = request.form.get("category", "Other").strip() or "Other"
        description = request.form.get("description", "").strip()
        try:
            stock = parse_nonnegative_integer(request.form.get("stock"), "Stock")
            price = parse_positive_integer(request.form.get("price"), "Price")
        except ValueError as error:
            flash(str(error), "danger")
            return render_template("add_product.html")
        if not name:
            flash("Product name is required.", "danger")
            return render_template("add_product.html")
        with get_connection() as connection:
            duplicate = connection.execute("SELECT 1 FROM products WHERE lower(name) = lower(?)", (name,)).fetchone()
            if duplicate:
                flash("A product with that name already exists.", "danger")
                return render_template("add_product.html")
            connection.execute(
                "INSERT INTO products (name, stock, price, category, description) VALUES (?, ?, ?, ?, ?)",
                (name, stock, price, category, description),
            )
        flash(f"{name} was added to inventory.", "success")
        return redirect(url_for("admin"))
    return render_template("add_product.html")


@app.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_product(product_id):
    with get_connection() as connection:
        product = connection.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if product is None:
            abort(404)
        if request.method == "POST":
            require_csrf()
            name = request.form.get("product", "").strip()
            category = request.form.get("category", "Other").strip() or "Other"
            description = request.form.get("description", "").strip()
            try:
                stock = parse_nonnegative_integer(request.form.get("stock"), "Stock")
                price = parse_positive_integer(request.form.get("price"), "Price")
            except ValueError as error:
                flash(str(error), "danger")
                return render_template("edit_product.html", product=product)
            duplicate = connection.execute("SELECT 1 FROM products WHERE lower(name) = lower(?) AND id != ?", (name, product_id)).fetchone()
            if not name or duplicate:
                flash("Enter a unique product name.", "danger")
                return render_template("edit_product.html", product=product)
            connection.execute(
                "UPDATE products SET name = ?, stock = ?, price = ?, category = ?, description = ? WHERE id = ?",
                (name, stock, price, category, description, product_id),
            )
    if request.method == "POST":
        flash("Inventory item updated.", "success")
        return redirect(url_for("admin"))
    return render_template("edit_product.html", product=product)


@app.post("/products/<int:product_id>/delete")
@login_required
@admin_required
def delete_product(product_id):
    require_csrf()
    with get_connection() as connection:
        product = connection.execute("SELECT name FROM products WHERE id = ?", (product_id,)).fetchone()
        if product is None:
            abort(404)
        connection.execute("DELETE FROM products WHERE id = ?", (product_id,))
    flash(f"{product['name']} was removed from inventory.", "success")
    return redirect(url_for("admin"))


@app.route("/orders")
@login_required
@admin_required
def orders():
    with get_connection() as connection:
        all_orders = connection.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    return render_template("orders.html", orders=all_orders)


@app.post("/orders/<int:order_id>/status")
@login_required
@admin_required
def update_order_status(order_id):
    require_csrf()
    next_status = {"Processing": "Approved", "Approved": "Dispatched", "Dispatched": "Delivered"}
    with get_connection() as connection:
        order = connection.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if order is None:
            abort(404)
        expected_status = next_status.get(order["status"])
        if expected_status is None or request.form.get("status") != expected_status:
            flash("That status change is not allowed.", "danger")
        else:
            connection.execute("UPDATE orders SET status = ? WHERE id = ?", (expected_status, order_id))
            flash(f"{order['order_id']} is now {expected_status}.", "success")
    return redirect(url_for("orders"))


@app.route("/track-order", methods=["GET", "POST"])
def track_order():
    order = None
    if request.method == "POST":
        require_csrf()
        order_id = request.form.get("order_id", "").strip().upper()
        with get_connection() as connection:
            order = connection.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        if order is None:
            flash("We could not find that order ID. Please check it and try again.", "warning")
    return render_template("track_order.html", order=order)


@app.route("/place-order", methods=["GET", "POST"])
@login_required
def place_order():
    with get_connection() as connection:
        products = connection.execute("SELECT * FROM products WHERE stock > 0 ORDER BY name").fetchall()
    if request.method == "POST":
        require_csrf()
        customer = request.form.get("customer", "").strip()
        phone = request.form.get("phone", "").strip()
        product_id = request.form.get("product_id")
        try:
            quantity = parse_positive_integer(request.form.get("quantity"), "Quantity")
        except ValueError as error:
            flash(str(error), "danger")
            return render_template("place_order.html", products=products)
        if not customer or not phone:
            flash("Please provide your name and phone number.", "danger")
            return render_template("place_order.html", products=products)
        with get_connection() as connection:
            product = connection.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
            if product is None:
                flash("Please choose an available product.", "danger")
                return render_template("place_order.html", products=products)
            order_id = make_order_id()
            updated_product = connection.execute(
                "UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?",
                (quantity, product["id"], quantity),
            )
            if updated_product.rowcount != 1:
                flash(f"Only {product['stock']} tons of {product['name']} are currently available.", "danger")
                return render_template("place_order.html", products=products)
            connection.execute(
                """INSERT INTO orders (order_id, customer_name, phone, user_email, product, quantity, status)
                   VALUES (?, ?, ?, ?, ?, ?, 'Processing')""",
                (order_id, customer, phone, session["user_email"], product["name"], quantity),
            )
        return render_template("order_success.html", order_id=order_id)
    return render_template("place_order.html", products=products, selected_product_id=request.args.get("product_id", type=int))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        require_csrf()
        fullname = request.form.get("fullname", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        if not fullname or not phone or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            flash("Enter a valid name, email address, and phone number.", "danger")
        elif len(password) < 8:
            flash("Password must contain at least 8 characters.", "danger")
        elif password != confirm_password:
            flash("Passwords do not match.", "danger")
        else:
            with get_connection() as connection:
                duplicate = connection.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
                if duplicate:
                    flash("An account already exists for that email address.", "danger")
                else:
                    connection.execute(
                        "INSERT INTO users (fullname, email, phone, password, is_admin) VALUES (?, ?, ?, ?, ?)",
                        (fullname, email, phone, generate_password_hash(password), 0),
                    )
                    flash("Account created. You can log in now.", "success")
                    return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        require_csrf()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with get_connection() as connection:
            user = connection.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            valid_password = user and (check_password_hash(user["password"], password) if user["password"].startswith(("pbkdf2:", "scrypt:")) else secrets.compare_digest(user["password"], password))
            if valid_password and not user["password"].startswith(("pbkdf2:", "scrypt:")):
                connection.execute("UPDATE users SET password = ? WHERE id = ?", (generate_password_hash(password), user["id"]))
        if not valid_password:
            flash("Invalid email address or password.", "danger")
        else:
            session.clear()
            session.update(user_id=user["id"], user_name=user["fullname"], user_email=user["email"], user_phone=user["phone"], is_admin=bool(user["is_admin"]))
            flash(f"Welcome back, {user['fullname']}!", "success")
            next_url = request.args.get("next")
            return redirect(next_url if is_safe_redirect_url(next_url) else url_for("home"))
    return render_template("login.html")


@app.post("/logout")
def logout():
    require_csrf()
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


@app.route("/my-orders")
@login_required
def my_orders():
    with get_connection() as connection:
        customer_orders = connection.execute(
            "SELECT * FROM orders WHERE user_email = ? ORDER BY id DESC", (session["user_email"],)
        ).fetchall()
    return render_template("my_orders.html", orders=customer_orders)


@app.route("/complaints", methods=["GET", "POST"])
@login_required
def complaints():
    if request.method == "POST":
        require_csrf()
        subject = request.form.get("subject", "").strip()
        description = request.form.get("description", "").strip()
        if len(subject) < 5 or len(description) < 15:
            flash("Please enter a subject and at least 15 characters describing the issue.", "danger")
        else:
            ticket_id = make_ticket_id()
            with get_connection() as connection:
                connection.execute(
                    "INSERT INTO complaints (ticket_id, user_email, subject, description) VALUES (?, ?, ?, ?)",
                    (ticket_id, session["user_email"], subject, description),
                )
            flash(f"Complaint submitted. Your ticket ID is {ticket_id}.", "success")
            return redirect(url_for("complaints"))
    with get_connection() as connection:
        tickets = connection.execute(
            "SELECT * FROM complaints WHERE user_email = ? ORDER BY id DESC", (session["user_email"],)
        ).fetchall()
    return render_template("complaints.html", tickets=tickets)


@app.route("/admin/complaints", methods=["GET", "POST"])
@login_required
@admin_required
def manage_complaints():
    if request.method == "POST":
        require_csrf()
        ticket_id = request.form.get("ticket_id", type=int)
        status = request.form.get("status")
        if status not in {"Open", "In Progress", "Resolved"}:
            flash("That complaint status is not valid.", "danger")
        else:
            with get_connection() as connection:
                result = connection.execute("UPDATE complaints SET status = ? WHERE id = ?", (status, ticket_id))
            flash("Complaint status updated." if result.rowcount else "Complaint ticket not found.", "success" if result.rowcount else "warning")
        return redirect(url_for("manage_complaints"))
    with get_connection() as connection:
        tickets = connection.execute("SELECT * FROM complaints ORDER BY id DESC").fetchall()
    return render_template("manage_complaints.html", tickets=tickets)


@app.post("/chat")
def chat():
    message = request.form.get("message", "").strip()
    if not message:
        return jsonify(reply="Please type a message so I can help."), 400
    normalized = message.lower()
    with get_connection() as connection:
        order_match = re.search(r"ord[-\s]?\d{4,8}[-\s]?[a-f0-9]{0,6}", normalized, re.IGNORECASE)
        if order_match:
            order_id = order_match.group().upper().replace(" ", "-")
            order = connection.execute("SELECT order_id, status FROM orders WHERE order_id = ?", (order_id,)).fetchone()
            if order:
                return jsonify(reply=f"Order {order['order_id']} is currently {order['status']}.")
        products = connection.execute("SELECT name, stock, price FROM products ORDER BY name").fetchall()
    if any(word in normalized for word in ("price", "cost", "rate")):
        reply = "Current prices: " + "; ".join(f"{p['name']} — ₹{p['price']:,}/ton" for p in products)
    elif any(word in normalized for word in ("product", "inventory", "stock")):
        reply = "Available inventory: " + "; ".join(f"{p['name']} — {p['stock']} tons" for p in products)
    elif "order" in normalized:
        reply = "Enter your order ID on the Track Order page, or type it here for a quick status check."
    elif "complaint" in normalized or "support" in normalized:
        reply = "For support, please contact support@steelconnect.com. A complaint form is the next feature we can add."
    elif any(word in normalized for word in ("hello", "hi", "hey")):
        reply = "Hello! I can help with products, inventory, prices, and order tracking."
    else:
        reply = "I can help with products, inventory, prices, and order tracking. Try asking about stock or prices."
    return jsonify(reply=reply)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
