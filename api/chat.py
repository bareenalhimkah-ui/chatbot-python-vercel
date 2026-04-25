from http.server import BaseHTTPRequestHandler
import os
import json
from datetime import datetime

from openai import OpenAI
from dotenv import load_dotenv

from core.client_loader import load_client_config, build_system_prompt


# 🌍 ENV laden
env_path = os.path.join(os.path.dirname(__file__), "../.env.local")
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)


MODEL = os.environ.get(
    "FINETUNED_MODEL",
    "ft:gpt-4o-mini-2024-07-18:bareen::CW6GdbsO"
)


def get_openai_client():
    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY fehlt.")

    return OpenAI(api_key=api_key)


def detect_location(user_message, client_data):
    text = user_message.lower()
    locations = client_data.get("locations", {})

    for location_key, location_data in locations.items():
        location_name = location_data.get("name", "").lower()

        if location_key.lower() in text or location_name in text:
            return location_key, location_data

    return None, None


class handler(BaseHTTPRequestHandler):
    def _send(self, status=200, body=None):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

        if body is not None:
            self.wfile.write(json.dumps(body, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self._send(200, {"status": "ok"})

    def do_GET(self):
        self._send(200, {"status": "ok", "time": datetime.now().isoformat()})

    def do_POST(self):
        try:
            length = int(self.headers.get("content-length", "0"))
            raw = self.rfile.read(length)
            data = json.loads(raw.decode("utf-8"))

            user_message = data.get("message", "").strip()
            client_id = data.get("client_id", "liquid_001").strip()
            channel = data.get("channel", "website").strip()

            if not user_message:
                self._send(400, {"error": "Keine Nachricht erhalten."})
                return

            client_data = load_client_config(client_id)
            system_prompt = build_system_prompt(client_data)

            location_key, location_data = detect_location(user_message, client_data)

            context = {
                "client_id": client_id,
                "channel": channel,
                "selected_location_key": location_key,
                "selected_location": location_data,
                "available_locations": list(client_data.get("locations", {}).keys())
            }

            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "system",
                    "content": f"Aktueller Kontext: {json.dumps(context, ensure_ascii=False)}"
                },
                {"role": "user", "content": user_message}
            ]

            client = get_openai_client()

            completion = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.3
            )

            reply = completion.choices[0].message.content.strip()

            self._send(200, {
                "reply": reply,
                "client_id": client_id,
                "location_detected": location_data is not None
            })

        except Exception as e:
            print("❌ Fehler:", str(e))
            self._send(500, {"error": str(e)})