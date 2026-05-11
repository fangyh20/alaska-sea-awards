# Bilt transfer partners: Asia <-> Seattle (SEA), business class, <= 100k miles
# Usage: python alaska_sea.py
import subprocess, json, os, smtplib, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email_config import EMAIL_FROM, EMAIL_PASSWORD

CACHE_FILE      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_results.json")
FULL_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_full_results.json")
STATS_FILE      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "route_stats.json")

# Learning thresholds
MIN_RUNS_BEFORE_LEARNING = 200  # wait for enough data before skipping
MIN_HIT_RATE = 0.05             # routes with <5% hit rate are "low priority"
PROBE_INTERVAL = 5              # probe a low-priority route every N skips

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

def load_stats():
    if not os.path.exists(STATS_FILE):
        return {}
    try:
        with open(STATS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_stats(stats):
    with open(STATS_FILE, 'w', encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

def should_skip_route(route_key, stats):
    s = stats.get(route_key, {})
    runs = s.get("runs", 0)
    hits = s.get("hits", 0)
    skips = s.get("skips", 0)
    if runs < MIN_RUNS_BEFORE_LEARNING:
        return False
    if hits / runs >= MIN_HIT_RATE:
        return False
    # Low hit rate: skip unless due for a probe
    return skips < PROBE_INTERVAL - 1

def update_route_stats(route_key, stats, result_count, was_skipped):
    s = stats.setdefault(route_key, {"runs": 0, "hits": 0, "skips": 0})
    if was_skipped:
        s["skips"] = s.get("skips", 0) + 1
    else:
        s["runs"] += 1
        s["skips"] = 0
        if result_count > 0:
            s["hits"] += 1

def print_stats_summary(stats):
    if not stats:
        return
    skipped_routes = [
        k for k, v in stats.items()
        if v.get("runs", 0) >= MIN_RUNS_BEFORE_LEARNING
        and v["hits"] / v["runs"] < MIN_HIT_RATE
    ]
    if skipped_routes:
        print(f"[LEARNING] Low-priority routes (hit rate <{int(MIN_HIT_RATE*100)}%): {', '.join(skipped_routes)}")

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
            sys.executable, "-m", "seats_aero_cli.cli",
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


all_pairs = [(o, "SEA") for o in ORIGINS] + [("SEA", o) for o in ORIGINS]

route_stats = load_stats()
print_stats_summary(route_stats)

active_pairs, skipped_pairs = [], []
for o, d in all_pairs:
    key = f"{o}->{d}"
    if should_skip_route(key, route_stats):
        skipped_pairs.append((o, d))
    else:
        active_pairs.append((o, d))

if skipped_pairs:
    skipped_keys = [f"{o}->{d}" for o, d in skipped_pairs]
    print(f"[LEARNING] Skipping {len(skipped_pairs)} low-priority route(s): {', '.join(skipped_keys)}")

print(f"Searching {len(active_pairs)}/{len(all_pairs)} route pairs, business class...")
print(f"(running in parallel)\n")

all_inbound, all_outbound = [], []
route_results = {}
with ThreadPoolExecutor(max_workers=max(len(active_pairs), 1)) as ex:
    futures = {ex.submit(fetch_pair, o, d): (o, d) for o, d in active_pairs}
    for f in as_completed(futures):
        o, d = futures[f]
        results, is_inbound = f.result()
        route_results[f"{o}->{d}"] = len(results)
        if is_inbound:
            all_inbound.extend(results)
        else:
            all_outbound.extend(results)

for o, d in active_pairs:
    key = f"{o}->{d}"
    # count filtered results per route
    count = sum(
        1 for r in (all_inbound if d == "SEA" else all_outbound)
        if r.get('Route', {}).get('OriginAirport') == o
        and r.get('Route', {}).get('DestinationAirport') == d
    )
    update_route_stats(key, route_stats, count, was_skipped=False)

for o, d in skipped_pairs:
    update_route_stats(f"{o}->{d}", route_stats, 0, was_skipped=True)

save_stats(route_stats)

def filter_results(results):
    return [
        r for r in results
        if r.get('JAvailable')
        and int(r.get('JMileageCost') or 999999) <= 100000
        and int(r.get('JTotalTaxes') or 0) < 40000  # exclude taxes >= $400 (stored in cents)
    ]


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


# ── 邮件通知 ────────────────────────────────────────────────────────────────

def load_last_results():
    """返回上次缓存的 (orig, dest, date) 集合；首次运行返回 None（不发邮件）。"""
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            return {tuple(x) for x in json.load(f)}
    except Exception:
        return None


def save_results(results):
    """把本次所有过滤结果的 (orig, dest, date) 写入缓存。"""
    keys = [
        [r.get('Route', {}).get('OriginAirport', ''),
         r.get('Route', {}).get('DestinationAirport', ''),
         r.get('Date', '')]
        for r in results
    ]
    with open(CACHE_FILE, 'w', encoding="utf-8") as f:
        json.dump(keys, f)


def save_full_results(results, booking_links):
    with open(FULL_CACHE_FILE, 'w', encoding="utf-8") as f:
        json.dump({"flights": results, "booking_links": booking_links}, f)


def load_full_results():
    try:
        with open(FULL_CACHE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("flights", []), data.get("booking_links", {})
    except Exception:
        return [], {}


def flight_key(r):
    route = r.get('Route', {})
    return (route.get('OriginAirport', ''), route.get('DestinationAirport', ''), r.get('Date', ''))


def build_email_html(all_flights, new_flights, booking_links, unsubscribe_url='#', lang='en'):
    new_keys = {flight_key(r) for r in new_flights}
    rows = ""
    for r in all_flights:
        route    = r.get('Route', {})
        orig     = route.get('OriginAirport', '?')
        dest     = route.get('DestinationAirport', '?')
        direct   = ("✅ 直飞" if r.get('JDirect') else "🔁 中转") if lang == 'zh' else ("✅ Direct" if r.get('JDirect') else "🔁 Stopover")
        seats    = r.get('JRemainingSeats') or 0
        miles    = r.get('JMileageCost', '?')
        airlines = r.get('JAirlines', '')
        link     = booking_links.get(r.get('ID', ''), '#')
        is_new   = flight_key(r) in new_keys
        row_bg   = "background:#fffbe6;font-weight:bold" if is_new else ""
        new_tag  = (' <span style="color:#cc6600;font-size:11px">[新]</span>' if lang == 'zh' else ' <span style="color:#cc6600;font-size:11px">[NEW]</span>') if is_new else ""
        try:
            dow = datetime.strptime(r['Date'], '%Y-%m-%d').strftime('%a')
        except Exception:
            dow = ''
        rows += f"""
        <tr style="{row_bg}">
          <td style="padding:6px 10px">{r['Date']} {dow}{new_tag}</td>
          <td style="padding:6px 10px">{orig} &rarr; {dest}</td>
          <td style="padding:6px 10px;text-align:right">{miles}</td>
          <td style="padding:6px 10px">{direct}</td>
          <td style="padding:6px 10px;text-align:center">{seats}</td>
          <td style="padding:6px 10px">{airlines}</td>
          <td style="padding:6px 10px"><a href="{link}" style="color:#0066cc;font-weight:bold">Book</a></td>
        </tr>"""

    if lang == 'zh':
        title    = "Alaska 里程计划 - 可用航班"
        subtitle = f"共 {len(all_flights)} 个可用航班 &mdash; <span style='background:#fffbe6;font-weight:bold;padding:2px 6px'>[新]</span> = 本次新出现"
        headers  = ["日期", "航线", "里程", "直飞", "剩余座位", "航空公司", "预订"]
        coffee   = f'☕ 如果提醒帮到你，<a href="https://ko-fi.com/rorocofi" style="color:#f5a623;font-weight:600">请我喝杯咖啡</a>'
        unsub    = f'<a href="{unsubscribe_url}" style="color:#999">退订</a>'
    else:
        title    = "Alaska Mileage Plan - Available Flights"
        subtitle = f"Showing all {len(all_flights)} available flights &mdash; <span style='background:#fffbe6;font-weight:bold;padding:2px 6px'>[NEW]</span> = newly appeared since last check"
        headers  = ["Date", "Route", "Miles", "Direct", "Seats Left", "Airlines", "Book"]
        coffee   = f'☕ If this alert helped, <a href="https://ko-fi.com/rorocofi" style="color:#f5a623;font-weight:600">buy me a coffee</a>'
        unsub    = f'<a href="{unsubscribe_url}" style="color:#999">Unsubscribe</a>'

    header_cells = "".join(f'<th style="padding:8px 10px">{h}</th>' for h in headers)

    return f"""
    <html><body style="font-family:Arial,sans-serif;color:#333">
      <h2 style="color:#003366">{title}</h2>
      <p style="color:#666">{subtitle}</p>
      <table border="0" cellpadding="0" cellspacing="0"
             style="border-collapse:collapse;border:1px solid #ddd;font-size:14px">
        <tr style="background:#003366;color:#fff">{header_cells}</tr>
        {rows}
      </table>
      <hr style="border:none;border-top:1px solid #eee;margin:20px 0">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td style="font-size:12px;color:#999">
            {coffee} &nbsp;·&nbsp; {unsub}
          </td>
        </tr>
      </table>
    </body></html>"""


def send_email(all_flights, new_flights, booking_links):
    """发送 HTML 邮件给每位订阅者（单独发送，互不可见对方地址）。"""
    if not new_flights:
        return

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from web.db import get_active_subscribers_with_tokens, init_db
    init_db()
    subscribers = get_active_subscribers_with_tokens()
    if not subscribers:
        print("[EMAIL] No active subscribers, skipping.")
        return

    n = len(new_flights)
    if n == 1:
        r0    = new_flights[0]
        orig0 = r0.get('Route', {}).get('OriginAirport', '')
        dest0 = r0.get('Route', {}).get('DestinationAirport', '')
        subject = f"Alaska Award Alerts: New {orig0}→{dest0} {r0.get('JMileageCost')}mi on {r0['Date']}"
    else:
        subject = f"Alaska Award Alerts: {n} new flights ({len(all_flights)} total available)"

    BASE_URL = 'https://awards.rorotech.com'
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
        s.login(EMAIL_FROM, EMAIL_PASSWORD)
        for recipient, token, lang in subscribers:
            unsubscribe_url = f"{BASE_URL}/unsubscribe/{token}"
            html = build_email_html(all_flights, new_flights, booking_links, unsubscribe_url, lang)
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From']    = f"Alaska Award Alerts <{EMAIL_FROM}>"
            msg['To']      = recipient
            msg['List-Unsubscribe'] = f"<{unsubscribe_url}>"
            msg.attach(MIMEText(html, 'html'))
            s.sendmail(EMAIL_FROM, [recipient], msg.as_string())
            print(f"[EMAIL SENT] -> {recipient}")
    print(f"[EMAIL] {subject}")


def main():
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

    print("=== SEA -> Asia ===")
    print_section("SEA->", outbound, booking_links)
    print()
    print("=== Asia -> SEA ===")
    print_section("->SEA", inbound, booking_links)

    all_filtered = inbound + outbound
    last_keys    = load_last_results()
    is_first_run = last_keys is None

    if not is_first_run:
        new_flights = [r for r in all_filtered if flight_key(r) not in last_keys]
        if new_flights:
            send_email(all_filtered, new_flights, booking_links)
        else:
            print("[OK] No new flights, no email sent.")
    else:
        print("[FIRST RUN] Baseline saved. Comparison starts next run.")

    save_results(all_filtered)
    save_full_results(all_filtered, booking_links)


if __name__ == '__main__':
    main()
