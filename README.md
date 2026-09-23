
# 🏭 SteelConnect: Smart Inventory & Customer Assistance System

🌐 **Live Website:** https://steelconnect.onrender.com

📂 **GitHub Repository:** https://github.com/Ekshithaa/SteelConnect

## 📌 Project Overview

SteelConnect is a web-based Smart Inventory and Customer Assistance System developed to simplify steel product management, inventory tracking, customer ordering, and customer support.

The application provides an efficient platform for administrators to manage products and orders while allowing customers to browse products, place orders, track deliveries, and interact with the SteelBot assistant.

---

## 🎯 Objectives

- Digitize steel inventory management.
- Simplify customer product ordering.
- Prevent overselling through inventory-aware ordering.
- Provide public order tracking.
- Improve customer assistance using SteelBot.
- Secure administrator operations through authentication.

---

## ✨ Key Features

### 👤 User Features

- User registration and login.
- Secure password hashing.
- Browse available steel products.
- Inventory-aware product ordering.
- Personal order history.
- Track order status.
- Submit support tickets.
- SteelBot customer assistance.

### 🛠️ Admin Features

- Secure administrator login.
- Protected admin dashboard.
- Add new products.
- Edit product details.
- Delete products.
- Manage inventory.
- View and manage customer orders.
- Update order fulfillment status.
- Manage customer support tickets.

### 📦 Order Management

The order workflow includes:

**Processing → Approved → Dispatched → Delivered**

- Inventory validation before ordering.
- Automatic stock reduction after successful order placement.
- Public order tracking.
- Order history for customers.

### 🤖 SteelBot Assistant

SteelBot provides customer assistance through an integrated chatbot interface, helping users navigate the website and access relevant product or service information.

---

## 🏗️ System Architecture

The project follows a web-based client-server architecture.

```text
                    ┌───────────────────────┐
                    │       Customer        │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │    Frontend Layer     │
                    │ HTML | CSS | JavaScript│
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │    Flask Backend      │
                    │       Python          │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │    SQLite Database    │
                    │ Users | Products      │
                    │ Orders | Inventory    │
                    └───────────────────────┘
```

---

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| HTML5 | Website structure |
| CSS3 | Styling and responsive design |
| JavaScript | Frontend interactivity |
| Python | Backend programming |
| Flask | Web application framework |
| SQLite | Database management |
| Werkzeug | Password hashing and security |
| Gunicorn | Production WSGI server |
| Git & GitHub | Version control |
| Render | Cloud deployment |

---

## 📂 Project Structure

```text
SteelConnect/
│
├── app.py
├── database.py
├── requirements.txt
├── README.md
│
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── products.html
│   ├── admin.html
│   ├── orders.html
│   └── ...
│
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│
└── instance/
    └── database.db
```

*Note: Update the structure if your actual folder names differ.*

---

## ⚙️ Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Ekshithaa/SteelConnect.git
```

### 2. Navigate to the Project Directory

```bash
cd SteelConnect
```

### 3. Create a Virtual Environment

```bash
python3 -m venv venv
```

### 4. Activate the Virtual Environment

**macOS / Linux:**

```bash
source venv/bin/activate
```

**Windows:**

```bash
venv\Scripts\activate
```

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

### 6. Run the Application

```bash
python3 app.py
```

### 7. Open in Browser

```text
http://127.0.0.1:5000
```

*If your application uses another port, open the corresponding local URL.*

---

## 🔐 Security Features

- Password hashing using Werkzeug.
- Session-based authentication.
- Protected administrator routes.
- Authentication checks for admin operations.
- Inventory validation during order placement.

---

## ☁️ Deployment

SteelConnect is deployed using Render.

### Deployment Configuration

```text
Build Command:
pip install -r requirements.txt

Start Command:
gunicorn app:app
```

**Live Application:**

https://steelconnect.onrender.com

> ⚠️ Production Note: SQLite persistence and secret configuration should be reviewed before using the application for production data. Render's default filesystem is ephemeral.

---

## 🧪 Testing

The project includes testing support for application functionality.

To run tests, use the appropriate test command configured in your project.

Example:

```bash
python -m unittest discover
```

---

## 🔮 Future Enhancements

- Online payment integration.
- Email notifications for order updates.
- Advanced inventory analytics.
- Role-based access control.
- Improved AI-powered customer assistance.
- Persistent production database.
- Enhanced reporting dashboard.

---

## 👩‍💻 Developer

**Ekshithaa Valli Thelu**

B.Tech Computer Science and Engineering

Andhra University College of Engineering for Women, Visakhapatnam.

---

## 📜 License

This project is developed for educational and project demonstration purposes during my internship.

---

## What works

- Professional responsive homepage and SteelBot assistant
- Account registration and secure password hashing
- Login, logout, and protected administrator pages
- Product add, edit, and delete tools for administrators
- Inventory-aware ordering that prevents overselling and reduces stock
- Public order tracking without exposing customer contact details
- Order fulfillment workflow: Processing → Approved → Dispatched → Delivered
- Personal order history and support-ticket workflow
