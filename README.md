# AI Bookstore Demo (Flask)

## Overview
A full-stack online bookstore built with Flask, SQLAlchemy, server-rendered templates, and REST APIs.

## Tech Stack
- Backend: Flask, Flask-SQLAlchemy, Flask-Login
- Security: Flask-WTF CSRF, password hashing (Werkzeug)
- i18n: Flask-Babel (English/French)
- Database: SQLite (dev), configurable for PostgreSQL/MySQL via `DATABASE_URL`
- Testing: pytest

## Project Structure
- `/app` Flask app factory, models, services, web + API blueprints
- `/app/templates` server-rendered UI
- `/app/static` CSS
- `/tests` unit/integration-style API tests
- `config.py` app settings
- `.env.example` environment variable template

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
flask --app run.py seed
python run.py
```

## Firebase 2FA Configuration
Set these environment variables:
- `FIREBASE_PROJECT_ID`
- `FIREBASE_WEB_API_KEY`

2FA can be enabled per-user through `PUT /api/users/profile` using:
```json
{
  "two_factor_enabled": true,
  "two_factor_method": "app"
}
```
When enabled, `POST /api/users/login` requires `otp_code`.

## Language Switching (EN/FR)
- UI toggle uses `?lang=en` / `?lang=fr`
- Preference can be persisted via `PUT /api/users/profile` with `language_preference`
- Flask-Babel catalogs are in `/translations`

## Seeding Data
`flask --app run.py seed` creates:
- 10 categories
- 100 placeholder books
- admin user: `admin@bookstore.local` / `Admin123!`

## Run Tests
```bash
pytest tests -q
```

## Developer Notes
- Add categories/books using admin API endpoints.
- Payment processing is abstracted in `app/services/payment.py` for easy provider replacement.
- Extend i18n by updating `translations/*/LC_MESSAGES/messages.po` and compiling catalogs.
- Full endpoint list: see `API.md`.
