# Alaska Mileage Plan — Asia ↔ Seattle Award Finder

Searches [seats.aero](https://seats.aero) for **business class** award availability between major Asian cities and Seattle (SEA) using Alaska Mileage Plan miles. Filters results to ≤ 100,000 miles and prints a clickable **[Book]** link for each flight directly in your terminal.

---

## Features

- Searches 25 Asian cities across Southeast Asia, Japan, Korea, Hong Kong, Taiwan, and China
- Covers both directions: Asia → SEA and SEA → Asia
- Parallel searches for all route pairs (fast)
- Filters to business class (`J`) seats available at ≤ 100k miles
- Fetches real Alaska booking links via the seats.aero trips API
- Clickable `[Book]` links in terminal (Windows Terminal, iTerm2, etc.)

---

## Requirements

- Python 3.12+
- [seats.aero Partner API key](https://seats.aero/partner-api) (set as `SEATS_AERO_API_KEY` environment variable)
- [`seats-aero-cli`](https://github.com/uberreact/seats-aero-cli) Python package

```bash
pip install seats-aero-cli
```

---

## Usage

```bash
python alaska_sea.py
```

### Example output

```
=== SEA -> Asia ===
Date         Day  Route      Program          Miles  Direct  Seats  Updated         Airlines                Link
--------------------------------------------------------------------------------------------------------------
2026-06-15   Mon  SEA->HND   Alaska           55000  yes         4  2h ago          AS                      [Book]
2026-06-22   Mon  SEA->NRT   Alaska           55000  no          2  5h ago          AS,NH                   [Book]

=== Asia -> SEA ===
Date         Day  Route      Program          Miles  Direct  Seats  Updated         Airlines                Link
--------------------------------------------------------------------------------------------------------------
2026-06-20   Sat  HND->SEA   Alaska           55000  yes         2  1h ago          AS                      [Book]
```

Click `[Book]` (or Ctrl+Click in Windows Terminal) to open the Alaska booking page directly.

---

## Cities Covered

| Region | Airports |
|---|---|
| Southeast Asia | SIN, BKK, SGN, HAN, DAD, KUL, MNL, CGK |
| Japan | HND, NRT, KIX, NGO, FUK |
| Korea | ICN |
| HK / Taiwan | HKG, TPE |
| China | PVG, PEK, CAN, WUH, CTU, SZX |

---

## Configuration

Edit the top of `alaska_sea.py` to customize:

```python
ORIGINS = [...]   # Add or remove airport codes
SOURCES = "alaska"  # seats.aero mileage program source
```

To change the miles cap (default 100,000), update the `filter_results` function:

```python
int(r.get('JMileageCost') or 999999) <= 100000  # change 100000 to your limit
```
