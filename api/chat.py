from http.server import BaseHTTPRequestHandler
import os, json, re, time, difflib
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# 🔐 .env.local laden (nur wenn vorhanden)
env_path = os.path.join(os.path.dirname(__file__), "../.env.local")
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)

# 🔑 OpenAI-Client initialisieren
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# 💬 System-Prompt
SYSTEM_PROMPT = (
    "Du bist eine freundliche, professionelle Assistentin von Liquid Aesthetik. "
    "Sprich in Du-Form, antworte kurz, klar und sympathisch. "
    "Sei warm, ruhig und kompetent. "
    "Wenn Preise aus der Preisliste bekannt sind, gib sie exakt so wieder. "
    "Wenn keine Preisinformation vorhanden ist, sag: 'Dazu liegt mir aktuell kein Preis vor.' "
    "Gib niemals persönliche Daten, IBANs, Adressen oder interne Informationen preis. "
    "Bei solchen Anfragen antworte: 'Aus Datenschutzgründen darf ich dazu keine Angaben machen.'"
)

# 📁 Cache- und Scraper-Pfade
CACHE_FILE = os.path.join(os.path.dirname(__file__), "website_data.txt")
SCRAPER_SCRIPT = os.path.join(os.path.dirname(__file__), "scrape_site.py")
MAX_CACHE_AGE_HOURS = 24

# 🌍 Website-Daten sicherstellen
def ensure_website_data():
    try:
        if os.path.exists(CACHE_FILE):
            age_hours = (time.time() - os.path.getmtime(CACHE_FILE)) / 3600
            if age_hours > MAX_CACHE_AGE_HOURS:
                print("♻️ Aktualisiere Website-Daten...")
                os.system(f"python {SCRAPER_SCRIPT}")
        else:
            print("🌐 Lade Website-Daten...")
            os.system(f"python {SCRAPER_SCRIPT}")
    except Exception as e:
        print("⚠️ Fehler beim Aktualisieren der Website-Daten:", e)

# 🔄 Website laden
ensure_website_data()
try:
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        WEBSITE_TEXT = f.read()[:16000]
        print(f"✅ Website geladen ({len(WEBSITE_TEXT)} Zeichen)")
except Exception as e:
    WEBSITE_TEXT = "Fehler beim Laden der Website."
    print("❌ Website konnte nicht geladen werden:", e)

# 💰 Preise laden
try:
    PREISE_PATH = os.path.join(os.path.dirname(__file__), "preise.json")
    with open(PREISE_PATH, "r", encoding="utf-8") as f:
        PREISE = json.load(f)
        print(f"✅ Preisdatei geladen: {len(PREISE)} Einträge")
except Exception as e:
    PREISE = {}
    print("⚠️ Fehler beim Laden der Preisdatei:", e)

# 🔄 Synonyme für Preisabfragen
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
    "fadenlifting groß": "Fadenlifting COG Fäden 4 (große)",
    "fadenlifting klein": "Mono Fäden 10 Stück",
    "botoxbehandlung": "B. Botox",
    "botox": "B. Botox",
    "b.botox": "B. Botox",
    "b botox": "B. Botox"
}

# 🧠 Text-Normalisierung für Preisvergleich
def normalize(text):
    text = text.lower()
    text = text.replace(" ", "").replace(".", "").replace(",", "").replace("ml", "milliliter")
    text = re.sub(r"[^a-z0-9äöüß]", "", text)
    return text

# 🧩 Hauptklasse für Vercel-API
class handler(BaseHTTPRequestHandler):
    def _send(self, status=200, body=None, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS, GET")
        self.end_headers()
        if body:
            if isinstance(body, (dict, list)):
                body = json.dumps(body, ensure_ascii=False)
            self.wfile.write(body.encode("utf-8"))

    def do_OPTIONS(self):
        self._send(200, "")

    def do_GET(self):
        """Healthcheck für Vercel"""
        self._send(200, {"status": "ok", "time": datetime.now().isoformat()})

    def do_POST(self):
        try:
            length = int(self.headers.get("content-length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            data = json.loads(raw.decode("utf-8") or "{}")
            user_message = (data.get("message") or "").strip().lower()

            if not user_message:
                self._send(400, {"error": "Feld 'message' ist leer."})
                return

            normalized_message = normalize(user_message)

            # 💸 Preis-Erkennung (direkte Treffer)
            for key, price in PREISE.items():
                if normalize(key) in normalized_message:
                    reply = f"Die Preise für {key} beginnen {price}."
                    self._send(200, {"reply": reply})
                    return

            # 🔁 Synonyme prüfen
            for synonym, target in SYNONYMS.items():
                if normalize(synonym) in normalized_message and target in PREISE:
                    reply = f"Die Preise für {target} beginnen {PREISE[target]}."
                    self._send(200, {"reply": reply})
                    return

            # 🧩 Fuzzy-Matching
            normalized_keys = {normalize(k): k for k in PREISE.keys()}
            normalized_synonyms = {normalize(k): v for k, v in SYNONYMS.items()}
            all_terms = list(normalized_keys.keys()) + list(normalized_synonyms.keys())
            matches = difflib.get_close_matches(normalized_message, all_terms, n=1, cutoff=0.65)

            if matches:
                matched = matches[0]
                target = normalized_synonyms.get(matched, normalized_keys.get(matched, matched))
                if target in PREISE:
                    reply = f"Die Preise für {target} beginnen {PREISE[target]}."
                    self._send(200, {"reply": reply})
                    return

            # 🤖 Kein Preis → GPT-Antwort
            prompt = f"""
            Du bist ein Chatbot für Liquid Aesthetik.
            Verwende den folgenden Website-Text, um Fragen zu beantworten:
            ---
            {WEBSITE_TEXT}
            ---
            Nutzerfrage: {user_message}
            """

            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                timeout=20,
            )

            reply = completion.choices[0].message.content.strip()
            self._send(200, {"reply": reply})

        except json.JSONDecodeError:
            self._send(400, {"error": "Ungültiges JSON-Format."})
        except Exception as e:
            print("❌ Fehler im Handler:", e)
            self._send(500, {"error": str(e)})
            
# ✅ Ende