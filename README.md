# Alaska Award Alerts

A personal tool that monitors [seats.aero](https://seats.aero) for **business class** award availability between major Asian cities and Seattle (SEA) using Alaska Mileage Plan miles, and sends email alerts when new seats appear.

Live at: **[awards.rorotech.com](https://awards.rorotech.com)**

---

## What It Does

- Monitors 6 Asian airports ↔ SEA: **NRT, ICN, HKG, SIN, BKK, MNL**
- Filters to business class (`J` cabin) · Alaska Mileage Plan · ≤ 100,000 miles
- Checks every **20 minutes** via cron
- Sends email alerts only when **new** availability appears (no noise)
- Each subscriber gets a personalized unsubscribe link
- Bilingual alerts: English or Chinese based on subscriber's language preference
- Welcome email includes currently available flights

---

## Project Structure

```
alaska_sea.py          # Core search + email alert script (run via cron)
email_config.py        # Gmail credentials (git-ignored)
web/
  app.py               # Flask web app (subscription signup + unsubscribe)
  db.py                # SQLite subscriber management
  send_welcome.py      # Welcome email with current flights
  templates/
    index.html         # Bilingual landing page (EN / 中文)
```

---

## Requirements

- Python 3.12+
- [seats.aero Partner API key](https://seats.aero/partner-api) — set as `SEATS_AERO_API_KEY`
- [`seats-aero-cli`](https://pypi.org/project/seats-aero-cli/) Python package
- Gmail account with App Password for sending emails

```bash
pip install seats-aero-cli flask
```

---

## Setup

### 1. Email config

Create `email_config.py` (git-ignored):

```python
EMAIL_FROM     = "your@gmail.com"
EMAIL_PASSWORD = "your-app-password"
```

### 2. Run the search script manually

```bash
SEATS_AERO_API_KEY=your_key python alaska_sea.py
```

### 3. Set up cron (every 20 minutes)

```
*/20 * * * * SEATS_AERO_API_KEY=your_key /usr/bin/python3 /path/to/alaska_sea.py >> /path/to/alaska_sea.log 2>&1
```

### 4. Run the web app

```bash
cd web && python app.py
```

Serves on port 5055. Put nginx in front with SSL for production.

---

## Web App Features

- Email subscription form with success/error feedback
- One-click unsubscribe via token link in every email
- Re-subscribe support after unsubscribing
- Language preference stored per subscriber (EN / ZH)
- Feature request form (sends to owner's email)
- Donation links (Ko-fi + Stripe)

---

## Configuration

Edit `alaska_sea.py` to customize:

```python
ORIGINS = ["NRT", "ICN", "HKG", "SIN", "BKK", "MNL"]  # Airport codes to monitor
SOURCES = "alaska"   # seats.aero mileage program
```

Miles cap (default 100,000):

```python
int(r.get('JMileageCost') or 999999) <= 100000
```

---

## Data Source

Availability data sourced from [seats.aero](https://seats.aero) via their Partner API.
This is an independent personal project — not affiliated with Alaska Airlines or seats.aero.
