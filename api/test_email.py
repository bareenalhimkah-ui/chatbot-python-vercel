import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
import os
from dotenv import load_dotenv

load_dotenv(".env.local")

SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

SENDER_NAME = "Liquid Aesthetik Test"
RECIPIENT = input("Empfänger E-Mail-Adresse eingeben: ")

subject = "Test – SMTP funktioniert!"
body = (
    "Hallo 👋\n\n"
    "Dies ist eine Test-Mail vom Liquid Aesthetik Server.\n"
    "Wenn du diese Nachricht siehst, ist alles korrekt eingerichtet."
)

msg = MIMEText(body, "plain", "utf-8")
msg["Subject"] = subject
msg["From"] = formataddr((SENDER_NAME, SMTP_USER))
msg["To"] = RECIPIENT

try:
    print(f"🔗 Verbinde mit {SMTP_SERVER}:{SMTP_PORT} ...")
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [RECIPIENT], msg.as_string())
    print("✅ E-Mail erfolgreich gesendet!")
except Exception as e:
    print("❌ Fehler beim Senden:", e)
