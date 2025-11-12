# booking/email_utils.py
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
import os

SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SENDER_NAME = "Liquid Aesthetik"


def send_email(to: str, subject: str, body: str):
    """E-Mail senden – mit Fallback in Entwicklungsmodus"""
    if not SMTP_USER or not SMTP_PASS:
        print("[email] SMTP nicht konfiguriert – würde senden an:", to, subject)
        return

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = formataddr((SENDER_NAME, SMTP_USER))
    msg["To"] = to

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [to], msg.as_string())
