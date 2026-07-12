# Solar Monitoring Dashboard

A self-hosted, multi-plant solar monitoring platform. Track generation, consumption, battery health, grid usage, billing, and maintenance for one or many solar installations — with your own PostgreSQL database, not a third-party cloud.

## Features

- **Live dashboard** — generation, consumption, grid import/export, battery charge, estimated monthly bill and savings
- **Multi-plant support** — each customer's own plant is tracked independently once they fill in their plant details
- **Swappable data source** — ships with a simulator; a Modbus TCP driver is included for real inverters
- **Authentication** — signup/login with hashed passwords, JWT sessions, and optional TOTP-based 2FA
- **Admin panel** — user management, plant & device management, energy reports (daily/weekly/monthly/yearly) with bar/pie charts, maintenance records, activity & error logs, site settings, and database backup/restore
- **Public marketing site** — landing page, company/solutions/portfolio pages, live rates pulled from admin settings
- **Alerts** — automatic detection of inverter faults, low battery, and zero generation during peak sunlight

## Tech stack

- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL + SQLAlchemy
- **Scheduler:** APScheduler (background sensor ticks)
- **Frontend:** Server-rendered Jinja2 templates + Chart.js
- **Auth:** bcrypt, PyJWT, PyOTP (2FA)

## Getting started

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create a PostgreSQL database

```sql
CREATE DATABASE solar_monitor;
```

### 3. Configure environment

Copy `.env.example` to `.env` and fill in your own values:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `TARIFF_RATE` / `FEED_IN_RATE` | Default grid tariff and export rate (₹/kWh) |
| `BATTERY_CAPACITY_KWH` | Default battery size |
| `SIM_INTERVAL_SECONDS` | How often the simulator generates a reading |
| `JWT_SECRET` | Generate with `python -c "import secrets; print(secrets.token_hex(32))"` |

### 4. Run

```bash
python run.py
```

The app starts on `http://localhost:8020` (configurable in `run.py`). The first account you register automatically becomes the super admin.

## Project structure

```
app/
├── main.py                 # FastAPI app, scheduler, page routes
├── config.py                # Settings loaded from .env
├── database.py               # SQLAlchemy engine/session
├── models.py                  # ORM models
├── auth.py                     # JWT auth helpers
├── routers/                     # API endpoints
├── services/                     # Business logic
│   └── drivers/                   # Pluggable data sources (simulator, Modbus)
├── templates/                      # Server-rendered pages
└── static/                          # CSS
```

## Notes

- Backup/restore uses `pg_dump`/`psql` and assumes a local PostgreSQL install (path configured in `app/routers/backup.py`).
- Email/SMS/push notifications are not wired up — they require your own SMTP/Twilio/Firebase credentials.
