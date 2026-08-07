# 🚘 AutoShop Pro — Workshop Management System

AutoShop Pro is a full-stack Auto Repair & Workshop Management System built with **Python (Django)**, **Bootstrap**, and **REST APIs** for mobile integration. It simplifies daily automotive workshop operations including job tracking, inventory management, customer vehicle history, and billing.

---

## 🌟 Key Features

* 📊 **Interactive Dashboard**: View active jobs, revenue metrics, inventory alerts, and quick actions.
* 🚗 **Customer & Vehicle Management**: Vehicle history linked to owners by license plate and phone number.
* 🛠️ **Job Cards & Workflows**: Real-time status tracking (`Pending`, `In Progress`, `Completed`), labor items, and parts usage.
* 📦 **Parts & Inventory Tracking**: Support for part categories (*Genuine, OEM, Aftermarket*), profit margin calculations, and low-stock alerts.
* 🧾 **Invoicing & PDF Receipts**: Automatic total calculation, partial/full payment status, thermal printing layout, and PDF generation.
* 📱 **Mobile REST APIs**: Integrated JSON endpoints (`/api/`) for mobile app integration.

---

## 🚀 Local Setup & Installation Guide

Follow these step-by-step instructions to run the project on your local machine:

### Prerequisites
* **Python 3.10+** installed
* **Git** installed

---

### Step 1: Clone the Repository
```bash
git clone https://github.com/Irtiza-coder/Auto-Workshop-Management.git
cd Auto-Workshop-Management
```

---

### Step 2: Create & Activate Virtual Environment

* **Windows (PowerShell / Command Prompt)**:
  ```bash
  python -m venv venv
  .\venv\Scripts\activate
  ```

* **macOS / Linux**:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

---

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

---

### Step 4: Run Database Migrations
```bash
python manage.py migrate
```

---

### Step 5: Create Admin Account (Superuser)
```bash
python manage.py createsuperuser
```
Follow the prompts to enter your admin **Username**, **Email**, and **Password**.

---

### Step 6: Start the Development Server
```bash
python manage.py runserver
```
It gives you Link Of the browser where project run.

---

## 📁 Project Structure

```
├── core/                   # Django App (Models, Views, Forms, APIs)
│   ├── models.py           # Customer, Vehicle, Part, JobCard, Invoice models
│   ├── views.py            # Web application views
│   └── views_api.py        # REST API endpoints for mobile app
├── templates/              # HTML Templates (Bootstrap UI)
├── static/                 # Static CSS, JS, Images, Icons
├── workshop_system/        # Project Settings & Routing
├── build.sh                # Deployment build script for Render
├── render.yaml             # Render Blueprint infrastructure definition
├── requirements.txt        # Python dependencies
└── manage.py               # Django CLI utility
```
