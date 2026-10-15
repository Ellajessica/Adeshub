# AdesHub - African Food & Grocery E-Commerce Platform

AdesHub is a modern, high-performance African food and grocery e-commerce platform built to deliver a seamless shopping experience for customers and a comprehensive business management system for store owners and staff.

---

## Project Architecture

```
AdesHub/
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── asgi.py
│   └── apps/
│       ├── __init__.py
│       ├── accounts/           # Custom User model, auth API, permissions, admin
│       ├── cart/               # Shopping cart app, session/guest carts, line items, stock validation
│       │   ├── admin.py
│       │   ├── apps.py
│       │   ├── models.py
│       │   ├── serializers.py
│       │   ├── tests.py
│       │   ├── urls.py
│       │   └── views.py
│       ├── core/               # Baseline API, health checks, common utilities
│       └── products/           # Catalog, Categories, Variants, Images & Inventory
├── frontend/                   # React + TypeScript + Vite storefront
│   ├── src/
│   │   ├── components/
│   │   │   ├── catalog/        # ProductCard, CategoryCard, ProductGrid
│   │   │   ├── layout/         # Header, Footer, Layout
│   │   │   └── ui/             # Badge, Button, PriceDisplay, Toast, LoadingState
│   │   ├── context/            # CartContext state provider
│   │   ├── pages/              # HomePage, ShopPage, CategoryPage, ProductDetailPage, CartPage
│   │   ├── services/           # REST API client with session management
│   │   └── types/              # TypeScript interface definitions
├── .env.example                # Safe environment variables template
├── .env                        # Local environment settings (git-ignored)
├── .gitignore
└── README.md
```

---

## Technology Stack

- **Backend:** Python 3.10+, Django 4.2+, Django REST Framework (DRF) 3.14+
- **Frontend:** React 18, TypeScript, Vite, Lucide Icons, Vanilla CSS
- **Database Engine:** PostgreSQL (via `psycopg2-binary`) or SQLite for dev/test
- **Currency:** Centralized GBP (`£`) formatting

---

## Phase 4: Shopping Cart Architecture

### 1. Cart Data Model
- **`Cart`**: Stores active shopping cart session associated with a guest (`session_key` / `X-Cart-Session` header) or an authenticated user (`user`). Automatically merges guest carts upon customer sign-in.
- **`CartItem`**: Represents a specific line item in the cart (`cart`, `product`, `variant` [optional], `quantity`). Enforces non-duplicate lines per product/variant via unique constraints and positive quantity constraints.

### 2. Price Rule & Stock Validation Behavior
- **Backend as Source of Truth**: Frontend never determines prices or stock availability. Unit price, line totals, and subtotals are dynamically computed from active catalog data in the backend.
- **Strict Stock Enforcement**:
  - Quantity requested cannot exceed available stock (`stock_quantity` of variant or simple product).
  - Out-of-stock items (`stock_quantity <= 0`), inactive products, or inactive variants cannot be added to cart.
  - Adding the same product/variant twice automatically increments the quantity line instead of creating duplicate entries.
  - Quantity cannot be set to 0 or negative.

### 3. Guest & Authenticated Cart Behavior
- Customers can add products to cart without creating an account or logging in.
- Cart sessions persist across browser navigation and reloads using session cookies and `X-Cart-Session` headers stored in client `localStorage`.
- Ready for seamless merge when authenticated customer profiles are introduced in future phases.

---

## Available API Endpoints

| Method | Endpoint | Description | Auth / Session |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/` | API Root / System Health | Public |
| `GET` | `/api/health/` | System & DB Health Status | Public |
| `POST` | `/api/accounts/register/` | Register new customer account | Public |
| `POST` | `/api/accounts/login/` | User authentication (returns token) | Public |
| `POST` | `/api/accounts/logout/` | User logout (invalidates token) | Token |
| `GET` / `PUT` | `/api/accounts/me/` | Retrieve / Update user profile | Token |
| `GET` | `/api/categories/` | List active categories | Public |
| `GET` | `/api/products/` | List active products | Public |
| `GET` | `/api/products/<slug>/` | Product detail view | Public |
| **`GET`** | **`/api/cart/`** | **Get active cart details & items** | **Public / Guest Session** |
| **`POST`** | **`/api/cart/items/`** | **Add item to cart** | **Public / Guest Session** |
| **`PATCH`** | **`/api/cart/items/<id>/`** | **Update cart item quantity** | **Public / Guest Session** |
| **`DELETE`** | **`/api/cart/items/<id>/`** | **Remove item from cart** | **Public / Guest Session** |
| **`DELETE`** | **`/api/cart/`** | **Clear all items in cart** | **Public / Guest Session** |
| `GET` | `/admin/` | Django Administration Dashboard | Staff / Admin |

---

## How to Run Migrations

1. Navigate to the `backend` folder:
```bash
cd backend
```
2. Generate migration files (if model changes made):
```bash
python manage.py makemigrations
```
3. Apply migrations to database:
```bash
python manage.py migrate
```

---

## How to Test the Cart

### Backend Tests
Run the Django backend unit test suite (43+ automated tests including cart creation, stock validation, variant handling, duplicate handling, quantity updates, removal, and subtotals):

```bash
cd backend
python manage.py test
```

### Frontend Build & Test
Verify TypeScript compilation and Vite build:

```bash
cd frontend
npm run build
```

---

## Security & Inventory Integrity

- All currency amounts use GBP (`£`) formatting.
- All cart operations strictly validate stock quantities and product/variant availability on the server.
- Public APIs allow guest session carts; write/update operations validate stock against backend database before committing changes.

---

## Transactional Email Integration (Resend)

AdesHub uses the official [Resend](https://resend.com) Python SDK for high-deliverability transactional emails, integrated cleanly with Stripe checkout, order fulfillment, and secure password resets.

### Architecture Overview

- **Core Email Service (`apps.core.email_service.send_transactional_email`)**:
  - Reusable, modular interface powered by the official `resend` Python SDK.
  - Automatically loads `RESEND_API_KEY`, `EMAIL_FROM`, and `EMAIL_REPLY_TO` from environment variables.
  - PII-safe masking in logs (e.g., `c******r@example.com`). Never exposes API keys, user tokens, or customer secrets in application logs.
  - In production, returns explicit failure diagnostics rather than silently falling back to unverified local relays.
  - Supports automatic retries with backoff for transient network issues.
  - Safely falls back to Django's development backends during local development when `RESEND_API_KEY` is omitted.
  - Safe automated test execution: defaults to in-memory mail outbox during test runner runs so no external network requests or test spam occur.

- **Order Confirmation Emails (`apps.orders.email_service.send_order_confirmation_email`)**:
  - Triggered exclusively after Stripe verifies payment succeeded (`checkout.session.completed` or `payment_intent.succeeded`).
  - Includes order reference number, items, quantities, variant names, unit prices, line totals, delivery fee, and total paid in GBP (`£`).
  - Plain text and responsive HTML versions matching the AdesHub brand emerald palette.
  - Confirms order receipt and processing (never prematurely claims that an item has shipped).
  - Uses trusted customer email from verified order records.
  - Strict idempotency: uses atomic database locks and persistent state (`confirmation_email_sent=True`, `email_delivery_status='ACCEPTED'`) to prevent duplicate emails during Stripe webhook retries.
  - Resilient: email delivery failures never invalidate an otherwise successful customer payment.

- **Password Reset Emails (`apps.accounts.email_service.send_password_reset_email`)**:
  - Employs secure, expiring (24-hour), single-use Django cryptographic tokens (`default_token_generator`).
  - Tokens are never exposed in application logs.
  - Anti-enumeration protection: `/api/auth/password-reset/` returns a generic 200 response regardless of whether an account exists.
  - Reset links dynamically use `FRONTEND_URL` configured in `.env` (`https://adeshubafricanstore.com` in production).

---

### Environment Configuration

Add the following variables to your `.env` file:

```env
# 1. Resend API Key (Created with Sending Access at https://resend.com/api-keys)
RESEND_API_KEY=re_your_api_key_here

# 2. Sender Identity (Must match a verified domain in Resend)
#    - Production (after DNS verification of subdomain): AdesHub <orders@send.adeshubafricanstore.com>
#    - Sandbox Testing (prior to DNS verification): AdesHub <onboarding@resend.dev>
EMAIL_FROM=AdesHub <orders@send.adeshubafricanstore.com>

# 3. Reply-To and Support (Client's business email hosted on Zoho Mail)
EMAIL_REPLY_TO=Info@adeshub.co.uk
SUPPORT_EMAIL=Info@adeshub.co.uk
SUPPORT_PHONE=+44 (0) 20 1234 5678

# 4. Production Frontend URL for order and password-reset links
FRONTEND_URL=https://adeshubafricanstore.com
```

> **Security Note:** Never commit `.env` or real API keys to version control. The repository `.gitignore` automatically excludes `.env`.

---

### Outstanding DNS & Resend Domain Verification Steps

To send transactional emails to customers from `orders@send.adeshubafricanstore.com`:

1. **Log in to Resend Dashboard**: Navigate to [https://resend.com/domains](https://resend.com/domains).
2. **Add Domain**: Click **Add Domain** and enter the dedicated sending subdomain: `send.adeshubafricanstore.com`.
3. **Configure DNS Records** in your DNS provider (e.g., Namecheap, Cloudflare, GoDaddy):
   - **DKIM (TXT record)**: Provided by Resend (e.g. `resend._domainkey.send.adeshubafricanstore.com`).
   - **SPF (MX or TXT record)**: Provided by Resend for `send.adeshubafricanstore.com`.
   - **DMARC (TXT record)**: Recommended TXT `_dmarc.send.adeshubafricanstore.com` with `v=DMARC1; p=none;`.
   > **Important:** Do **not** modify or delete existing MX records for `adeshub.co.uk` (Zoho Mail). The client's Zoho mailbox for `Info@adeshub.co.uk` handles inbound customer replies and operates completely independently.
4. **Verify Domain**: Click **Verify DNS Records** in the Resend dashboard until status shows **Verified**.
5. **Update Environment**: Change `EMAIL_FROM` in production `.env` to:
   ```env
   EMAIL_FROM=AdesHub <orders@send.adeshubafricanstore.com>
   ```

---

### How to Run Automated Tests

The backend includes 134 automated unit and integration tests covering the Resend email service, Stripe webhooks, idempotency, order creation, and password reset flows:

```bash
cd backend
python manage.py test
```

All external Resend API requests are strictly mocked during automated testing to avoid sending real emails, incurring charges, or triggering rate limits.

---

### How to Test Email Delivery Manually

1. **Sandbox / Development Manual Test**:
   - In Resend sandbox mode (before custom domain DNS verification), Resend only allows sending to the email address registered with the Resend account (`emmanuellachinenye767@gmail.com`) using `onboarding@resend.dev`.
   - To send a test email via the Django shell:
   ```bash
   cd backend
   python manage.py shell
   ```
   ```python
   from apps.core.email_service import send_transactional_email
   result = send_transactional_email(
       to_email="emmanuellachinenye767@gmail.com",
       subject="AdesHub Resend Test Email",
       text_content="This is a test transactional email from AdesHub via Resend.",
       html_content="<h1>AdesHub Test</h1><p>Transactional email integration is working!</p>",
       reply_to="Info@adeshub.co.uk"
   )
   print(result)
   # Expected output: {'success': True, 'status': 'sent', 'message_id': '...', 'provider': 'resend', 'error': None}
   ```

2. **Production Manual Test (after DNS verification)**:
   - Perform a test checkout on the staging/production storefront.
   - Upon successful Stripe payment verification, check the customer inbox and the Resend Dashboard Logs (`https://resend.com/emails`) to confirm delivery.
   - Test password reset at `/forgot-password` and verify the link delivered to your inbox.

