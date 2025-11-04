from http.server import BaseHTTPRequestHandler
import os, json
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

# 💬 Systemrolle
SYSTEM_PROMPT = (
    f"Du bist die freundliche Assistentin von {CONFIG['praxis']['name']}. "
    f"Sprich in Du-Form, antworte warm, ruhig und kompetent. "
    f"Wenn Preise oder Öffnungszeiten bekannt sind, verwende sie direkt aus den Praxisdaten. "
    f"Wenn etwas nicht in den Daten steht, sag höflich, dass du dazu leider keine Information hast."
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
            user_message = data.get("message", "").strip()

            if not user_message:
                self._send(400, {"error": "Keine Nachricht erhalten."})
                return

            # 🤖 Anfrage an Modell
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
                {"role": "system", "content": f"Praxisdaten: {json.dumps(CONFIG, ensure_ascii=False)}"}
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
