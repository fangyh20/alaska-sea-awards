# Bilt transfer partners: Asia <-> Seattle (SEA), business class, <= 100k miles
# Usage: python alaska_sea.py
import subprocess, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

ORIGINS = [
    "NRT",        # Japan Tokyo（数据最多）
    "ICN",        # Korea Seoul（数据最多）
    "HKG",        # Hong Kong
    "SIN",        # Singapore
    "BKK",        # Bangkok
    "MNL",        # Manila
]

SOURCES = "alaska"

PROGRAM_NAMES = {
    "alaska":         "Alaska",
    "united":         "United",
    "aeroplan":       "Aeroplan",
    "flyingblue":     "Flying Blue",
    "emirates":       "Emirates",
    "qatar":          "Qatar",
    "etihad":         "Etihad",
    "american":       "American",
    "virginatlantic": "Virgin Atlantic",
}

def alaska_booking_url(origin, dest, date):
    """直接从 origin/dest/date 构造 Alaska 里程兑换搜索链接，无需额外 API 调用。"""
    return (f"https://www.alaskaair.com/search/results?"
            f"O={origin}&D={dest}&OD={date}&A=1&C=0&L=0&RT=false&ShoppingMethod=onlineaward")


def hyperlink(url, text):
    """ANSI OSC 8 终端超链接（Windows Terminal / iTerm2 等支持直接点击）。"""
    ESC = "\x1b"
    return f"{ESC}]8;;{url}{ESC}\\{text}{ESC}]8;;{ESC}\\"


def fetch_pair(origin, dest):
    all_results, cursor, skip = [], None, 0
    for _ in range(10):
        cmd = [
            r"C:\Python312\python.exe", "-m", "seats_aero_cli.cli",
            "search",
            "--origin-airport", origin,
            "--destination-airport", dest,
            "--cabins", "business",
            "--sources", SOURCES,
            "--take", "1000", "--json",
        ]
        if cursor:
            cmd += ["--cursor", str(cursor), "--skip", str(skip)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if not r.stdout.strip():
            break
        data = json.loads(r.stdout)
        batch = data.get('data', [])
        all_results.extend(batch)
        if not data.get('hasMore'):
            break
        cursor, skip = data.get('cursor'), skip + len(batch)
    direction = "->SEA" if dest == "SEA" else "SEA->"
    print(f"  {origin}->{dest}  {direction}  ({len(all_results)} records)")
    return all_results, dest == "SEA"

pairs = [(o, "SEA") for o in ORIGINS] + [("SEA", o) for o in ORIGINS]

print(f"Searching {len(ORIGINS)} Asian cities <-> SEA, business class, all Bilt programs...")
print(f"({len(pairs)} route pairs, running in parallel)\n")

all_inbound, all_outbound = [], []
with ThreadPoolExecutor(max_workers=len(pairs)) as ex:
    futures = {ex.submit(fetch_pair, o, d): (o, d) for o, d in pairs}
    for f in as_completed(futures):
        results, is_inbound = f.result()
        if is_inbound:
            all_inbound.extend(results)
        else:
            all_outbound.extend(results)

def filter_results(results):
    return [
        r for r in results
        if r.get('JAvailable')
        and int(r.get('JMileageCost') or 999999) <= 100000
    ]

inbound  = sorted(filter_results(all_inbound),  key=lambda x: x.get('Date', ''))
outbound = sorted(filter_results(all_outbound), key=lambda x: x.get('Date', ''))

total_scanned = len(all_inbound) + len(all_outbound)
print(f"\nScanned {total_scanned} total | ->SEA: {len(inbound)} found | SEA->: {len(outbound)} found\n")

booking_links = {}
for r in inbound + outbound:
    route = r.get('Route', {})
    orig = route.get('OriginAirport', '')
    dest = route.get('DestinationAirport', '')
    date = r.get('Date', '')
    if orig and dest and date:
        booking_links[r['ID']] = alaska_booking_url(orig, dest, date)

now = datetime.now(timezone.utc)

def fmt_updated(updated_raw):
    try:
        dt = datetime.fromisoformat(updated_raw.replace('Z', '+00:00'))
        h = (now - dt).total_seconds() / 3600
        if h < 1:   return f"{int(h*60)}m ago"
        if h < 24:  return f"{int(h)}h ago"
        return f"{int(h/24)}d ago"
    except Exception:
        return updated_raw[:10] if updated_raw else '?'

def print_section(label, results, booking_links):
    if not results:
        print(f"  No results.")
        return
    print(f"{'Date':<12} {'Day':<4} {'Route':<10} {'Program':<16} {'Miles':>8}  {'Direct':<7} {'Seats':>5}  {'Updated':<14}  {'Airlines':<22}  Link")
    print("-" * 110)
    for r in results:
        route = r.get('Route', {})
        orig  = route.get('OriginAirport', '?')
        dest  = route.get('DestinationAirport', '?')
        src   = PROGRAM_NAMES.get(r.get('Source', ''), r.get('Source', ''))
        direct = "yes" if r.get('JDirect') else "no"
        seats  = r.get('JRemainingSeats') or 0
        updated = fmt_updated(r.get('UpdatedAt', ''))
        try:
            dow = datetime.strptime(r['Date'], '%Y-%m-%d').strftime('%a')
        except Exception:
            dow = '???'
        link_url = booking_links.get(r.get('ID', ''))
        link_cell = hyperlink(link_url, "[Book]") if link_url else ""
        print(f"{r['Date']} {dow:<4} {orig}->{dest:<6} {src:<16} {r.get('JMileageCost'):>8}  {direct:<7} {seats:>5}  {updated:<14}  {r.get('JAirlines',''):<22}  {link_cell}")

print("=== SEA -> Asia ===")
print_section("SEA->", outbound, booking_links)
print()
print("=== Asia -> SEA ===")
print_section("->SEA", inbound, booking_links)
