import smtplib, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email_config import EMAIL_FROM, EMAIL_PASSWORD
from alaska_sea import load_full_results, build_email_html

BASE_URL = os.environ.get('BASE_URL', 'https://awards.rorotech.com')


def send_welcome_email(to_email, unsubscribe_token, lang='en'):
    unsubscribe_url = f"{BASE_URL}/unsubscribe/{unsubscribe_token}"

    flights, booking_links = load_full_results()
    flights_html = ""
    if flights:
        if lang == 'zh':
            flights_html = '<h3 style="color:#003366;margin-top:28px">当前可用航班</h3>'
        else:
            flights_html = '<h3 style="color:#003366;margin-top:28px">Currently Available Flights</h3>'
        flights_html += build_email_html(flights, [], booking_links, unsubscribe_url='', lang=lang)
        # strip the footer/unsubscribe from the embedded table (we have our own below)
        cut = flights_html.find('<hr style="border:none;border-top:1px solid #eee;margin:20px 0">')
        if cut != -1:
            flights_html = flights_html[:cut]

    if lang == 'zh':
        subject = "Alaska Award Alerts：订阅成功 ✈️"
        html = f"""
    <html><body style="font-family:Arial,sans-serif;color:#333;max-width:680px;margin:0 auto;padding:20px">
      <h2 style="color:#003366">✈️ 订阅成功！</h2>
      <p>当亚洲 ↔ 西雅图 (SEA) 之间出现新的商务舱里程票时，你将第一时间收到邮件通知。</p>
      <ul>
        <li><strong>航线：</strong>NRT、ICN、HKG、SIN、BKK、MNL ↔ SEA</li>
        <li><strong>舱位：</strong>商务舱 (J舱)</li>
        <li><strong>里程上限：</strong>≤ 10万阿拉斯加里程</li>
        <li><strong>频率：</strong>每20分钟检查一次，仅在出现新座位时发送，不骚扰</li>
      </ul>
      <p>祝你早日抢到心仪的航班！</p>
      {flights_html}
      <hr style="border:none;border-top:1px solid #eee;margin:24px 0">
      <p style="color:#999;font-size:12px">
        ☕ 如果提醒帮助到你，<a href="https://ko-fi.com/rorocofi" style="color:#f5a623;font-weight:600">请我喝杯咖啡</a> 让服务器继续运行。
        &nbsp;·&nbsp;
        <a href="{unsubscribe_url}" style="color:#999">退订</a>
      </p>
    </body></html>"""
    else:
        subject = "Alaska Award Alerts: You're subscribed ✈️"
        html = f"""
    <html><body style="font-family:Arial,sans-serif;color:#333;max-width:680px;margin:0 auto;padding:20px">
      <h2 style="color:#003366">✈️ You're subscribed to Alaska Award Alerts</h2>
      <p>You'll receive an email whenever new business class award seats appear between Asia and Seattle (SEA) using Alaska Mileage Plan miles.</p>
      <ul>
        <li><strong>Routes:</strong> NRT, ICN, HKG, SIN, BKK, MNL ↔ SEA</li>
        <li><strong>Class:</strong> Business (J cabin)</li>
        <li><strong>Cap:</strong> ≤ 100,000 Alaska miles</li>
        <li><strong>Frequency:</strong> Only when new seats appear (checked every 20 min)</li>
      </ul>
      <p>Alerts go out only when new availability appears — no spam.</p>
      {flights_html}
      <hr style="border:none;border-top:1px solid #eee;margin:24px 0">
      <p style="color:#999;font-size:12px">
        ☕ Enjoying the alerts? <a href="https://ko-fi.com/rorocofi" style="color:#f5a623;font-weight:600">Buy me a coffee</a> to keep the server running.
        &nbsp;·&nbsp;
        <a href="{unsubscribe_url}" style="color:#999">Unsubscribe</a>
      </p>
    </body></html>"""

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f"Alaska Award Alerts <{EMAIL_FROM}>"
    msg['To'] = to_email
    msg['List-Unsubscribe'] = f"<{unsubscribe_url}>"
    msg.attach(MIMEText(html, 'html'))

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
        s.login(EMAIL_FROM, EMAIL_PASSWORD)
        s.sendmail(EMAIL_FROM, [to_email], msg.as_string())
