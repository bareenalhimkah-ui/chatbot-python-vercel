from http.server import BaseHTTPRequestHandler
import os, json, re
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# 🌍 ENV laden
env_path = os.path.join(os.path.dirname(__file__), "../.env.local")
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)

# 🔑 OpenAI initialisieren
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
MODEL = os.environ.get("FINETUNED_MODEL", "ft:gpt-4o-mini-2024-07-18:bareen::CW6GdbsO")

# ⚙️ Config laden
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

PRAXEN = CONFIG["praxen"]

# 💬 Systemrolle
SYSTEM_PROMPT = (
    "Du bist die freundliche Assistentin von Liquid Aesthetik. "
    "Sprich in Du-Form, antworte warm, ruhig und kompetent. "
    "Wenn Preise, Öffnungszeiten oder Kontaktdaten bekannt sind, verwende sie aus den Praxisdaten. "
    "Wenn eine Stadt genannt wird (z. B. Wiesbaden, Mannheim oder Dortmund), nutze die passenden Daten dieser Praxis. "
    "Wenn etwas nicht in den Daten steht, sag höflich, dass du dazu leider keine Information hast."
)

# 📬 API-Handler
class handler(BaseHTTPRequestHandler):
    def _send(self, status=200, body=None):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if body:
            self.wfile.write(json.dumps(body, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self._send(200, "")

    def do_GET(self):
        self._send(200, {"status": "ok", "time": datetime.now().isoformat()})

    def do_POST(self):
        try:
            length = int(self.headers.get("content-length", "0"))
            raw = self.rfile.read(length)
            data = json.loads(raw.decode("utf-8"))
            user_message = data.get("message", "").strip().lower()

            if not user_message:
                self._send(400, {"error": "Keine Nachricht erhalten."})
                return

            # 🏙 Standort erkennen
            selected_praxis = None
            for key, praxis in PRAXEN.items():
                if key in user_message or praxis["name"].lower() in user_message:
                    selected_praxis = praxis
                    break

            # Wenn keine Stadt genannt wurde → generelle Antwort
            if not selected_praxis:
                selected_praxis = {
                    "name": "Liquid Aesthetik",
                    "adresse": "Standorte: Wiesbaden, Mannheim und Dortmund",
                    "telefon": "0157 – 880 588 48",
                    "email": "info@liquid-aesthetik.de",
                    "oeffnungszeiten": "Termine nach Vereinbarung",
                    "beschreibung": "Liquid Aesthetik ist eine Praxisgruppe für ästhetische Medizin mit mehreren Standorten in Deutschland.",
                }

            # 🧠 Nachrichten an Modell senden
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
                {"role": "system", "content": f"Praxisdaten: {json.dumps(selected_praxis, ensure_ascii=False)}"},
                {"role": "system", "content": f"Weitere Praxen: {', '.join(PRAXEN.keys())}"},
            ]

            completion = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.3
            )

            reply = completion.choices[0].message.content.strip()
            self._send(200, {"reply": reply})

        except Exception as e:
            print("❌ Fehler:", e)
            self._send(500, {"error": str(e)})
