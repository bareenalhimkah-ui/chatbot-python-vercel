from http.server import BaseHTTPRequestHandler
import json
import os
import re
import time
import difflib
from pathlib import Path
import subprocess

from dotenv import load_dotenv
from openai import OpenAI


BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

load_dotenv(ROOT_DIR / ".env.local")


SYSTEM_PROMPT = (
    "Du bist eine freundliche, professionelle Assistentin einer ästhetischen Praxis. "
    "Sprich in Du-Form, antworte klar und sympathisch. "
    "Gib Preisangaben exakt wie in der Preisliste an. "
    "Wenn etwas fehlt, sag: 'Dazu liegt mir aktuell kein Preis vor.'"
)

BUNDLED_CACHE_FILE = ROOT_DIR / "website_data.txt"
CACHE_FILE = BASE_DIR / "website_data.txt"
SCRAPER_SCRIPT = BASE_DIR / "scrape_site.py"
MAX_CACHE_AGE_HOURS = 24


def build_openai_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Die Umgebungsvariable OPENAI_API_KEY ist nicht gesetzt. "
            "Lege sie in den Vercel-Einstellungen oder in einer .env.local Datei an."
        )
    return OpenAI(api_key=api_key)


client = None


def get_client() -> OpenAI:
    global client
    if client is None:
        client = build_openai_client()
    return client

def ensure_website_data() -> None:
    needs_update = True
    if CACHE_FILE.exists():
        age_hours = (time.time() - CACHE_FILE.stat().st_mtime) / 3600
        needs_update = age_hours > MAX_CACHE_AGE_HOURS

    if not needs_update:
        return

    try:
        subprocess.run(
            ["python", str(SCRAPER_SCRIPT)],
            cwd=str(BASE_DIR),
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as err:
        # Auf Vercel ist das Dateisystem schreibgeschützt. Wir protokollieren den Fehler,
        # damit die Anwendung nicht abstürzt, sondern mit dem Cache weiterarbeitet.
        print("Fehler beim Aktualisieren der Website-Daten:", err)


ensure_website_data()


def load_website_text() -> str:
    # Bevorzugt wird der aktualisierbare Cache im API-Verzeichnis. Sollte dieser
    # nicht verfügbar sein (z. B. beim ersten Deploy auf schreibgeschützten
    # Umgebungen), greifen wir auf die gebündelte Datei im Projektstamm zurück.
    candidates = [CACHE_FILE, BUNDLED_CACHE_FILE]
    for path in candidates:
        try:
            if path.exists():
                return path.read_text(encoding="utf-8")[:15000]
        except Exception as exc:
            print(f"Konnte Website-Daten aus {path} nicht laden:", exc)
    return "Keine Webdaten verfügbar."


WEBSITE_TEXT = load_website_text()


try:
    with (BASE_DIR / "preise.json").open("r", encoding="utf-8") as f:
        PREISE = json.load(f)
except Exception as exc:
    print("Konnte Preisliste nicht laden:", exc)
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
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.end_headers()
            if body is not None:
                if isinstance(body, (dict, list)):
                    body = json.dumps(body, ensure_ascii=False)
                if isinstance(body, str):
                    body = body.encode("utf-8")
                self.wfile.write(body)
        except Exception as exc:
            # Falls wir nicht schreiben können, loggen wir den Fehler, damit die
            # Function zumindest nicht unbemerkt abbricht.
            print("Fehler beim Senden der Antwort:", exc)

    def do_OPTIONS(self):
        self._send(200, "")

    def do_POST(self):
        try:
            try:
                length = int(self.headers.get("content-length", "0"))
            except ValueError:
                length = 0

            raw_body = self.rfile.read(length) if length > 0 else b""
            body_text = raw_body.decode("utf-8") if raw_body else ""
            try:
                data = json.loads(body_text) if body_text else {}
            except json.JSONDecodeError:
                self._send(400, {"error": "Ungültiges JSON im Request-Body."})
                return

            user_message = (data.get("message") or "").strip()

            if not user_message:
                self._send(400, {"error": "Feld 'message' ist leer."})
                return

            normalized = normalize(user_message)
            tokens = set(normalized.split())

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

            for syn, target in SYNONYMS.items():
                if normalize(syn) in normalized and target in PREISE:
                    reply = f"Die Preise für {target} beginnen {PREISE[target]}."
                    self._send(200, {"reply": reply})
                    return

            possible_terms = list(PREISE.keys()) + list(SYNONYMS.keys())
            normalized_map = {normalize(term): term for term in possible_terms}
            matches = difflib.get_close_matches(
                normalized,
                list(normalized_map.keys()),
                n=1,
                cutoff=0.65,
            )

            if matches:
                matched_norm = matches[0]
                original_term = normalized_map.get(matched_norm)
                if original_term:
                    lookup_term = SYNONYMS.get(original_term, original_term)
                    if lookup_term in PREISE:
                        reply = f"Die Preise für {lookup_term} beginnen {PREISE[lookup_term]}."
                        self._send(200, {"reply": reply})
                        return

            prompt = (
                "Beantworte die Nutzerfrage anhand des folgenden Website-Textes. "
                "Wenn Preise genannt werden, nutze ausschließlich die Preisliste. "
                "Website:\n---\n" + WEBSITE_TEXT + "\n---\n"
                "Frage: " + user_message
            )

            try:
                completion = get_client().chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    timeout=15,
                )
                answer = completion.choices[0].message.content.strip()
                self._send(200, {"reply": answer})
            except Exception as gpt_error:
                print("OpenAI-Fehler:", gpt_error)
                self._send(
                    500,
                    {
                        "error": "Die Antwort vom Sprachmodell konnte nicht abgerufen werden. "
                        "Bitte prüfe den API Key und versuche es erneut.",
                    },
                )

        except Exception as e:
            print("Allgemeiner Fehler im Handler:", e)
            self._send(500, {"error": "Interner Serverfehler."})
