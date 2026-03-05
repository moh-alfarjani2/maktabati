# 📚 maktabati-POS: Professional Library & Inventory Management System

A comprehensive **Library and Bookstore Management Platform** built with **Django**, **React**, and **PostgreSQL** — featuring a robust inventory engine, POS capabilities, financial reporting, and a premium administrative dashboard.

---

## 📸 Project Preview
![maktabati-POS Preview](main.png)

---

## 🚀 Project Overview

**maktabati-POS** is a production-ready application designed to streamline library and bookstore operations. From real-time inventory tracking and automated sales processing to advanced financial analytics, the platform provides a complete solution for modern book management.

The platform is divided into several specialized modules:

- **Inventory Engine**: Manage books, authors, and stock levels with precision.
- **POS & Sales**: interactive point-of-sale interface for processing transactions and generating invoices.
- **Reporting Suite**: Comprehensive financial and operational reports (Sales, Purchases, Damages).
- **Accounts & Security**: Role-based access control and secure user management.

The application is engineered with high standards for data integrity, ensuring accurate financial calculations and preventing stock inconsistencies.

---

## 📅 Development Plan (As Implemented)

| Phase | Focus Area | Outcome |
|-------|-----------|---------|
| 1 | Core Infrastructure | Modular Django architecture with specialized apps for Books, Sales, and Accounts |
| 2 | Inventory Management | Advanced metadata tracking (Author, ISBN, Pages) with automated stock adjustments |
| 3 | Sales & POS | Integrated sale processing with real-time total calculation and invoice history |
| 4 | Purchase Workflow | Comprehensive system for tracking incoming stock and supplier management |
| 5 | Financial Guardrails | Logic-shielded transaction processing to ensure financial precision |
| 6 | Reporting Engine | Dynamic generation of sales, damange, and stock reports for business insights |
| 7 | Global Search | High-performance search across the entire library and transaction history |
| 8 | UI/UX Refinement | Premium, responsive interface designed for high-efficiency workflows |

---

## 🗂️ Project Structure

```
maktabati-POS/
├── apps/                          # Specialized Django Applications
│   ├── accounts/                  # User Authentication & Profiles
│   ├── books/                     # Book Metadata & Catalog
│   ├── core/                      # Shared views and utilities
│   ├── inventory/                 # Stock movement & Tracking
│   ├── sales/                     # POS & Transaction logic
│   ├── purchases/                 # Supplier & Procurement management
│   ├── damages/                   # Damage tracking & Loss reporting
│   └── reports/                   # Financial & Operational Analytics
├── bookstore/                     # Project configuration & Settings
├── templates/                     # Centralized HTML templates
├── static/                        # CSS, JS, and Assets
├── manage.py                      # Django management script
├── .gitignore                     # Repository exclusions
└── README.md                      # (This file)
```

---

## 🛠️ Technologies & Tools

### Backend & Logic
- **Python 3.12+** — The core programming language
- **Django 5.x** — Robust web framework for the backend API and logic
- **PostgreSQL** — Production-grade relational database
- **Django Template Language** — Clean and efficient UI rendering

### Frontend & Styling
- **Modern CSS** — Custom, premium styling for a professional look
- **Vanilla JavaScript** — Dynamic UI interactions and POS logic
- **Lucide Icons** — Sleek iconography across the dashboard

---

## 🔍 Features (Detailed)

### 📊 Advanced Inventory Management
- **Rich Metadata**: Track Author, Language, Page Count, and Category.
- **Stock Automation**: Real-time updates on sales, purchases, and damage reports.
- **Availability Tracking**: Instant visibility into what's on the shelf vs. archived.

### 💰 Professional Sales & POS
- **Transaction History**: Searchable records of all past sales.
- **Invoice Generation**: Automated generation of purchase and sales invoices.
- **Discount Management**: Built-in support for transaction-level discounts.

### 🛡️ Hardened Business Logic
- **Atomic Transactions**: Ensuring database integrity during complex stock updates.
- **Role Enforcement**: Secure access control for staff vs. managers.
- **Error Boundaries**: Robust handling of invalid inputs in financial fields.

---

## ✅ How To Run (Local)

### Prerequisites
- **Python** 3.12 or later
- **PostgreSQL** (Optional, defaults to SQLite for dev)

### Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/moh-alfarjani/maktabati-POS.git
   cd maktabati-POS
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the database:**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

5. **Start development server:**
   ```bash
   python manage.py runserver
   ```

---

## 🏗️ Build for Production

```bash
python manage.py collectstatic
# Use gunicorn or uWSGI for production deployment
```

---

## 📄 License

This project is licensed under the **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**. 

- **Attribution**: You must give appropriate credit.
- **Non-Commercial**: You may **not** use the material for commercial purposes.
- **No Derivatives**: If you remix, transform, or build upon the material, you may not distribute the modified material.

For commercial licensing inquiries, please contact the developer.

---

## 🌐 Contact & Follow
- Project Link: [github.com/moh-alfarjani/maktabati-POS](https://github.com/moh-alfarjani/maktabati-POS)
- Developer: [Mohammad Alfarjani](https://github.com/moh-alfarjani)
- **Email**: [Your Email Here]
- **LinkedIn**: [Your LinkedIn Here]

---

💬 **Final Words**

**maktabati-POS** is more than just a bookstore script; it's a complete business operational system. Built with scalability and data integrity at its core, it provides the tools needed to manage a professional library or retail bookstore with confidence.

---
