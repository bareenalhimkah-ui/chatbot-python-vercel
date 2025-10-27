from http.server import BaseHTTPRequestHandler
import os
import json
import re
import time
import difflib
from datetime import datetime
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM_PROMPT = (
    "Du bist eine freundliche, professionelle Assistentin einer ästhetischen Praxis. "
    "Sprich in Du-Form, antworte klar und sympathisch. "
    "Gib Preisangaben exakt wie in der Preisliste an. "
    "Wenn etwas fehlt, sag: 'Dazu liegt mir aktuell kein Preis vor.'"
)

CACHE_FILE = "website_data.txt"
SCRAPER_SCRIPT = "scrape_site.py"
MAX_CACHE_AGE_HOURS = 24

def ensure_website_data():
    needs_update = True
    if os.path.exists(CACHE_FILE):
        age_hours = (time.time() - os.path.getmtime(CACHE_FILE)) / 3600
        needs_update = age_hours > MAX_CACHE_AGE_HOURS
    if needs_update:
        os.system(f"python {SCRAPER_SCRIPT}")

ensure_website_data()

try:
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        WEBSITE_TEXT = f.read()[:15000]
except:
    WEBSITE_TEXT = ""

try:
    with open("preise.json", "r", encoding="utf-8") as f:
        PREISE = json.load(f)
except:
    PREISE = {}

SYNONYMS = {
    "hyaluronspritze": "hyaluron",
    "hyaluronbehandlung": "hyaluron",
    "faltenunterspritzung": "hyaluron",
    "lippen aufspritzen": "Lippen 1 ml",
    "lippenunterspritzung": "Lippen 1 ml",
    "lippenbehandlung": "Lippen 1 ml",
    "fettwegspritze": "Lipolyse/Fettwegspritze",
    "fettweg spritze": "Lipolyse/Fettwegspritze",
    "kinnfettbehandlung": "Lipolyse/Fettwegspritze",
    "nasenkorrektur": "Nasen­korrektur ohne OP",
    "botoxbehandlung": "B. Botox",
    "botox": "B. Botox"
}

def normalize(text):
    return re.sub(r"[^a-z0-9äöüß]+", " ", text.lower()).strip()

class handler(BaseHTTPRequestHandler):
    def _send(self, status=200, body=None, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
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
            length = int(self.headers.get("content-length", 0))
            data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            user_message = (data.get("message") or "").strip()

            if not user_message:
                self._send(400, {"error": "Feld 'message' ist leer."})
                return

            # Text normalisieren und Token generieren
            normalized = normalize(user_message)
            tokens = set(normalized.split())

            # Direkter Preis-Treffer inkl. Wortstamm
            for key, value in PREISE.items():
                key_norm = normalize(key)

                if (
                    key_norm in tokens
                    or key_norm in normalized
                    or any(key_norm in token for token in tokens)
                ):
                    reply = f"Die Preise für {key} beginnen {value}."
                    self._send(200, {"reply": reply})
                    return

            # Synonym-Treffer
            for syn, target in SYNONYMS.items():
                if normalize(syn) in normalized and target in PREISE:
                    reply = f"Die Preise für {target} beginnen {PREISE[target]}."
                    self._send(200, {"reply": reply})
                    return

            # Tippfehler-Erkennung
            possible_terms = list(PREISE.keys()) + list(SYNONYMS.keys())
            matches = difflib.get_close_matches(
                user_message.lower(), possible_terms, n=1, cutoff=0.45
            )

            if matches:
                m = matches[0]
                term = SYNONYMS.get(m, m)
                if term in PREISE:
                    reply = f"Die Preise für {term} beginnen {PREISE[term]}."
                    self._send(200, {"reply": reply})
                    return

            # GPT-Fallback
            prompt = (
                "Beantworte die Nutzerfrage anhand des folgenden Website-Textes. "
                "Wenn Preise genannt werden, nutze ausschließlich die Preisliste. "
                "Website:\n---\n" + WEBSITE_TEXT + "\n---\n"
                "Frage: " + user_message
            )

            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3
            )

            answer = completion.choices[0].message.content.strip()
            self._send(200, {"reply": answer})

        except Exception as e:
            self._send(500, {"error": str(e)})
