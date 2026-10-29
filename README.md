# SmartRestrict: Indian Packaged-Food Nutrition, Allergen & Dietary-Restriction Analysis Platform

SmartRestrict is a full-stack food intelligence web application built with **Python FastAPI**, **Oracle Database Free 26ai**, and **Bootstrap 5**. It enables consumers to explore Indian packaged foods, screen items against health restrictions (such as Diabetes, High Cholesterol, Low Sodium, Gluten Intolerance) and allergens, evaluate rule-based nutritional tags, and discover healthier category alternatives.

---

## 1. Project Directory Structure

```
smartrestrict/
├── backend/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application entrypoint, CORS, static mounts
│   ├── config.py                # Environment configuration & DB connection settings
│   ├── database.py              # Oracle connection pooling, health checks, parameterized helpers
│   ├── models.py                # Pydantic schemas for requests, responses, and domain entities
│   ├── services/
│   │   ├── __init__.py
│   │   ├── product_service.py   # Catalogue search, pagination, deep details, metadata
│   │   ├── rule_engine.py       # Dynamic tag derivation & explainable suitability engine
│   │   ├── recommendation_service.py # Healthier alternative recommendation scoring
│   │   └── user_service.py      # User profile & restriction preferences in Oracle
│   └── routers/
│       ├── __init__.py
│       ├── products.py          # /api/products endpoints
│       ├── metadata.py          # /api/metadata endpoint (brands, categories, tags, rules)
│       ├── evaluate.py          # /api/evaluate suitability endpoint
│       ├── alternatives.py      # /api/products/{id}/alternatives endpoint
│       └── users.py             # /api/users profile persistence endpoints
├── frontend/
│   ├── index.html               # Responsive homepage with search, categories, and metrics
│   ├── catalogue.html           # Product catalogue with live search, filters, and pagination
│   ├── product-detail.html      # Deep product analysis: nutrition table, allergens, alternatives
│   ├── evaluate.html            # Dedicated interactive Dietary & Allergen Studio
│   ├── profile.html             # User profile & default restrictions management
│   ├── css/
│   │   └── style.css            # Custom design system, badges, contrast, and layout
│   └── js/
│       ├── api.js               # Centralized API fetch wrapper
│       ├── app.js               # Shared state, badges, navbar, and session helpers
│       ├── catalogue.js         # Catalogue filtering, search, and pagination controller
│       ├── detail.js            # Product details, nutrition breakdown, and alternatives controller
│       ├── evaluate.js          # Interactive evaluation studio controller
│       └── profile.js           # User profile controller
├── docs/
│   ├── schema_metadata.json     # Extracted Oracle schema metadata (19 tables)
│   └── api_examples.md          # Postman collection & API request/response examples
├── tests/
│   ├── __init__.py
│   ├── test_rules.py            # Unit tests for tag derivation & suitability engine
│   ├── test_recommendations.py  # Unit tests for alternative scoring model
│   └── test_api.py              # API contract & validation integration tests
├── scripts/
│   ├── inspect_schema.py        # Oracle metadata extraction script
│   ├── show_tables.py           # Table inspection utility
│   └── test_backend_services.py # End-to-end backend service test
├── packaged_foods_india.csv     # Source Indian packaged food dataset (852 items)
├── requirements.txt             # Backend Python dependencies
├── .env.example                 # Environment variable template with placeholders
├── .gitignore                   # Git ignore file (securing credentials & venv)
└── README.md                    # Setup and documentation
```

---

## 2. Oracle Database Schema Overview

The database runs on **Oracle Database Free 26ai** (Pluggable Database: `FREEPDB1`, User/Schema: `SMARTRESTRICT`). It comprises 19 normalized relational tables:

| Table | Description | Stored Rows |
| :--- | :--- | :--- |
| **`PRODUCTS`** | Indian packaged food items with brands, serving sizes, and label info | 852 |
| **`BRANDS`** | Verified packaged food manufacturers and brand names | 262 |
| **`CATEGORIES`** | Hierarchical categories (Biscuits, Chips, Noodles, Beverages, etc.) | 220 |
| **`NUTRIENTS`** | Master nutritional parameters (Calories, Sugar, Sodium, Saturated Fat, etc.) | 12 |
| **`PRODUCT_NUTRITION`** | M:N nutritional values per product per nutrient with measurement units | 10,118 |
| **`INGREDIENTS`** | Master identified ingredients (Maida, Sugar, Palm Oil, Cocoa, etc.) | 40 |
| **`PRODUCT_INGREDIENTS`** | M:N mapping of products to identified master ingredients | 5,250 |
| **`ALLERGENS`** | Tracked allergens (Milk, Soy, Wheat/Gluten, Egg, Peanut, Tree Nuts, Sesame, Mustard) | 8 |
| **`PRODUCT_ALLERGENS`** | M:N declared allergen mappings | 1,102 |
| **`DIETARY_TYPES`** | Classifications (Vegetarian, Eggetarian, Vegan-Friendly, Gluten-Free) | 4 |
| **`PRODUCT_DIETARY_TYPES`** | M:N dietary type tags | 1,798 |
| **`TAGS`** | Positive tags (Low Sugar, High Fibre, Clean Ingredients) & Concern tags (High Sodium, High Sugar, Trans Fat) | 12 |
| **`TAG_RULES`** | Statistical percentile thresholds automatically assigning tags | 11 |
| **`PRODUCT_TAGS`** | Derived product tag junction | 2,344 |
| **`RESTRICTIONS`** | Health profiles: Diabetes, High Cholesterol, Low Sodium, Weight Management, Gluten Intolerance | 5 |
| **`RESTRICTION_RULES`** | Rule mappings linking restrictions to positive/negative tags | 12 |
| **`PRODUCT_ALTERNATIVES`** | Schema support for computed healthier alternatives | Computed dynamically |
| **`USERS`** | Registered user profiles with email and creation timestamps | Stored in Oracle |
| **`USER_RESTRICTIONS`** | User-selected restriction preferences | Stored in Oracle |

---

## 3. Windows Setup & Launch Instructions

### Prerequisites
- Windows 10/11
- Python 3.10+ (tested on Python 3.14)
- Oracle Database Free 26ai running with listener on port 1522 (or 1521)
- Git and a modern web browser

### Step 1: Clone or Navigate to the Project Directory
Open **PowerShell** or **Command Prompt**:
```powershell
cd C:\Users\subiw\smartrestrict
```

### Step 2: Create and Activate the Virtual Environment
```powershell
# Create virtual environment
python -m venv .venv

# Activate in PowerShell
.\.venv\Scripts\Activate.ps1

# (Or in Command Prompt cmd.exe: .venv\Scripts\activate.bat)
```

> *Note: If PowerShell displays an execution policy warning, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and then run the activation script again.*

### Step 3: Install Required Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy `.env.example` to create your local `.env`:
```powershell
Copy-Item .env.example .env
```
Open `.env` in VS Code or Notepad and set your database connection details:
```ini
DB_USER=SMARTRESTRICT
DB_PASSWORD=your_actual_password_here
DB_HOST=localhost
DB_PORT=1522
DB_SERVICE_NAME=FREEPDB1
APP_ENV=development
APP_PORT=8000
```
*(The `.env` file is excluded from Git via `.gitignore` to protect credentials).*

### Step 5: Start the SmartRestrict Full-Stack Server
```powershell
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Step 6: Open the Application in Your Browser
- **Web Application**: [http://localhost:8000](http://localhost:8000)
- **Product Catalogue**: [http://localhost:8000/catalogue](http://localhost:8000/catalogue)
- **Dietary Restriction Checker**: [http://localhost:8000/evaluate](http://localhost:8000/evaluate)
- **User Health Profile**: [http://localhost:8000/profile](http://localhost:8000/profile)
- **Interactive Swagger API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc API Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 4. Multi-Laptop & Team Database Access Guide

If one laptop acts as the Oracle database host and a teammate wants to run the application or connect from another laptop, follow these steps:

### On the Host Laptop (Where Oracle Database Is Installed)
1. **Find Current Reachable IP**:
   Open PowerShell on the host laptop:
   ```powershell
   Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -like "*Wi-Fi*" }
   ```
   *Note: If both laptops are connected to a phone hotspot or Wi-Fi router, the host IP will be something like `172.20.10.2` or `192.168.1.x`. Because DHCP can reassign this IP when reconnecting, check this IP whenever switching networks.*
2. **Ensure Oracle Listener Is Running**:
   In PowerShell on the host laptop:
   ```powershell
   lsnrctl status
   ```
   Ensure the listener endpoint indicates port `1522` and service `FREEPDB1` is in `READY` status.
3. **Allow Windows Firewall Access on Port 1522**:
   If the teammate cannot connect, open port 1522 in Windows Defender Firewall:
   ```powershell
   New-NetFirewallRule -DisplayName "Oracle Listener 1522" -Direction Inbound -LocalPort 1522 -Protocol TCP -Action Allow
   ```

### On the Teammate's Laptop
1. In the teammate's `.env` file, set `DB_HOST` to the host laptop's current IP:
   ```ini
   DB_USER=SMARTRESTRICT
   DB_PASSWORD=your_database_password
   DB_HOST=172.20.10.2   # Set to the host laptop's current IP
   DB_PORT=1522
   DB_SERVICE_NAME=FREEPDB1
   ```
2. Test network connectivity before starting:
   ```powershell
   Test-NetConnection -ComputerName 172.20.10.2 -Port 1522
   ```
   When `TcpTestSucceeded : True` is returned, launch the application:
   ```powershell
   uvicorn backend.main:app --port 8000 --reload
   ```

---

## 5. Running Automated Tests

To run the automated test suite covering rule evaluations, recommendation calculations, and API contracts:
```powershell
pytest tests -v
```

---

## 6. Key Application Features

1. **Rule-Based Nutritional Tagging**:
   - Tags like `High Sugar`, `Low Sugar`, `High Sodium`, `High Saturated Fat`, `High Fibre`, and `Clean Ingredients` are derived directly using `TAG_RULES` statistical percentile thresholds.
   - Missing values are explicitly recorded and **never assumed to be zero**.
2. **Transparent Suitability Engine**:
   - Compares active restrictions (`Diabetes`, `High Cholesterol`, `Low Sodium`, `Weight Management`, `Gluten Intolerance`) with `RESTRICTION_RULES`.
   - Explains the exact reason behind every verdict (e.g. *"Contains 32.5g of Sugar, triggering High Sugar rule (>33.5g/100g)"*).
   - Distinguishes between recorded allergens and missing allergen data.
3. **Healthier Alternatives Recommender**:
   - Dynamically calculates healthier options from the same or related categories.
   - Scores alternatives (0–100%) and provides clear, human-readable trade-offs (e.g., *"61% less sugar, higher fibre, with trade-off: slightly higher sodium"*).
4. **User Profile & Preference Persistence**:
   - Manages user profiles in the Oracle `USERS` table and links default restrictions via `USER_RESTRICTIONS` without storing passwords in plaintext.
   - Profile preferences auto-screen products across the catalog.

