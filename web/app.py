import sys, os, smtplib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from flask import Flask, request, render_template, redirect, url_for, jsonify
from email.mime.text import MIMEText
from db import init_db, add_subscriber, unsubscribe
from send_welcome import send_welcome_email
from email_config import EMAIL_FROM, EMAIL_PASSWORD

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def index():
    message = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        lang  = request.form.get('lang', 'en')
        if lang not in ('en', 'zh'):
            lang = 'en'
        if not email or '@' not in email or '.' not in email.split('@')[-1]:
            message = ('error', 'Please enter a valid email address.')
        else:
            success, token = add_subscriber(email, lang)
            if success:
                try:
                    send_welcome_email(email, token, lang)
                except Exception as e:
                    print(f"[WARN] Welcome email failed for {email}: {e}")
                message = ('success', "You're subscribed! Check your inbox for a confirmation email.")
            else:
                message = ('info', 'This email is already subscribed.')
    return render_template('index.html', message=message)


@app.route('/request', methods=['POST'])
def feature_request():
    req_type = request.form.get('req_type', '').strip()
    message  = request.form.get('message', '').strip()
    email    = request.form.get('email', '').strip()

    if not message:
        return jsonify(ok=False), 400

    body = f"Type: {req_type}\nFrom: {email or '(not provided)'}\n\n{message}"
    msg = MIMEText(body)
    msg['Subject'] = f"[Alaska Awards] Feature Request: {req_type}"
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_FROM
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
            s.login(EMAIL_FROM, EMAIL_PASSWORD)
            s.sendmail(EMAIL_FROM, [EMAIL_FROM], msg.as_string())
    except Exception as e:
        print(f"[WARN] Feature request email failed: {e}")
    return jsonify(ok=True)


@app.route('/unsubscribe/<token>')
def unsubscribe_route(token):
    unsubscribe(token)
    return '''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Unsubscribed</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
</head><body>
<div class="container py-5 text-center" style="max-width:500px">
  <h4>You've been unsubscribed</h4>
  <p class="text-muted">You won't receive any more flight alerts.</p>
  <a href="/" class="btn btn-outline-primary btn-sm">Re-subscribe</a>
</div>
</body></html>'''


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5055)
