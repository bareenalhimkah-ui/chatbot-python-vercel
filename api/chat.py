from http.server import BaseHTTPRequestHandler
import os, json
from openai import OpenAI

# Der API Key kommt sicher aus der Umgebungsvariable (Vercel: Project Settings -> Environment Variables)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM_PROMPT = "Du bist ein hilfsbereiter deutschsprachiger Assistent."

class handler(BaseHTTPRequestHandler):
    def _send(self, status=200, body=None, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        # CORS - sinnvoll falls du lokal von anderem Port testest. Auf Vercel (gleiche Domain) unkritisch.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.end_headers()
        if body is not None:
            if isinstance(body, (dict, list)):
                body = json.dumps(body, ensure_ascii=False)
            self.wfile.write(body.encode("utf-8"))

    def do_OPTIONS(self):
        self._send(200, "")

    def do_POST(self):
        try:
            length = int(self.headers.get("content-length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            data = json.loads(raw.decode("utf-8") or "{}")
            user_message = (data.get("message") or "").strip()
            if not user_message:
                self._send(400, {"error": "Feld 'message' ist leer."})
                return

            # OpenAI Chat Completion
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.3,
            )
            reply = completion.choices[0].message.content
            self._send(200, {"reply": reply})
        except Exception as e:
            # Schreibe Fehlertext zurück (nur für Debug; in Produktion eher nicht den genauen Fehler leaken)
            self._send(500, {"error": str(e)})
