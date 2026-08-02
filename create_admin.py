"""Create a SteelConnect administrator without exposing a password in source code."""

from getpass import getpass

from werkzeug.security import generate_password_hash

from database import get_connection, init_db


def prompt(label):
    value = input(f"{label}: ").strip()
    if not value:
        raise SystemExit(f"{label} is required.")
    return value


if __name__ == "__main__":
    init_db()
    fullname = prompt("Full name")
    email = prompt("Email").lower()
    phone = prompt("Phone")
    password = getpass("Password (at least 8 characters): ")
    if len(password) < 8:
        raise SystemExit("Password must contain at least 8 characters.")
    with get_connection() as connection:
        existing = connection.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            connection.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (existing["id"],))
        else:
            connection.execute(
                "INSERT INTO users (fullname, email, phone, password, is_admin) VALUES (?, ?, ?, ?, 1)",
                (fullname, email, phone, generate_password_hash(password)),
            )
    print(f"Administrator account ready for {email}.")
