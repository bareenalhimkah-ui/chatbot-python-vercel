from http.server import BaseHTTPRequestHandler
import os, json, re, time
from datetime import datetime
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

try:
    with open("preise.json", "r", encoding="utf-8") as f:
        PREISE = json.load(f)
except:
    PREISE = {}

# Automatische Preis-Erkennung
for key, price in PREISE.items():
    if key in user_message:
        reply = f"Die Preise für {key.capitalize()}-Behandlungen beginnen {price}."
        self._send(200, {"reply": reply})
        return



SYSTEM_PROMPT = (
    "Du bist eine freundliche, professionelle Assistentin einer ästhetischen Praxis. "
    "Sprich in Du-Form, antworte kurz, klar und sympathisch. "
    "Dein Ton ist warm, einladend und kompetent. "
    "Beantworte offen und ehrlich Fragen zu Behandlungen, Preisen, Terminen und allgemeinen Praxisinformationen, "
    "sofern sie im Website-Text enthalten sind oder allgemein bekannt sein dürfen. "
    "Wenn kein exakter Preis im Website-Text steht, antworte mit: "
    "'Dazu liegen mir keine genauen Informationen vor. Die Preise beginnen in der Regel ab etwa ... Euro laut Website.' "
    "Gib niemals geschätzte, erfundene oder vertrauliche Informationen weiter. "
    "Gib keine personenbezogenen Daten, Mitarbeiterdaten, IBANs oder internen Informationen preis. "
    "In solchen Fällen antworte freundlich: 'Aus Datenschutzgründen darf ich dazu keine Angaben machen.' "
    "Vermeide unnötige Phrasen und konzentriere dich immer auf die konkrete Nutzerfrage."
)


# 📁 Website-Cache-Einstellungen
CACHE_FILE = "website_data.txt"
SCRAPER_SCRIPT = "scrape_site.py"  # Dein Scraper-Skript
MAX_CACHE_AGE_HOURS = 24  # Nach 24h neu laden

def ensure_website_data():
    """Stellt sicher, dass die Website-Daten vorhanden und aktuell sind."""
    if os.path.exists(CACHE_FILE):
        age_hours = (time.time() - os.path.getmtime(CACHE_FILE)) / 3600
        if age_hours > MAX_CACHE_AGE_HOURS:
            print("♻️ Website-Daten älter als 24h – aktualisiere...")
            os.system(f"python {SCRAPER_SCRIPT}")
    else:
        print("🌐 Website-Daten fehlen – lade neu herunter...")
        os.system(f"python {SCRAPER_SCRIPT}")

# 🧭 Website-Text laden oder aktualisieren
ensure_website_data()
try:
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        WEBSITE_TEXT = f.read()[:16000]
        print("✅ Website-Daten geladen:", len(WEBSITE_TEXT), "Zeichen")
except Exception as e:
    WEBSITE_TEXT = "Fehler beim Laden der gespeicherten Website."
    print("❌ Website-Daten konnten nicht geladen werden:", e)

# 📚 Vordefinierte Antworten
PREDEFINED_ANSWERS = {
    "behandlungen": """Bei Liquid Aesthetik bieten wir eine Vielzahl von Behandlungen an, die darauf abzielen, ein natürlich junges Aussehen zu fördern. Zu unseren Hauptbehandlungen gehören:
1. Hyaluron
2. Jawline
3. Lipolyse
4. Lippen
5. Wangenaufbau
6. Fadenlifting
7. Augenringe
8. Nasenkorrektur""",

    "kontakt": """Du kannst Liquid Aesthetik so erreichen:
📍 Hegelstraße 40, 55122 Mainz
📞 +49 176 12345678
✉️ info@liquid-aesthetik.de
Instagram: @liquid_aesthetik""",

    "preise": """Unsere Preise variieren je nach Behandlung und individuellem Bedarf.
Eine genaue Preisliste erhältst du nach einem kostenlosen Beratungsgespräch in der Praxis.""",

    "öffnungszeiten": """Unsere Praxis ist Montag bis Freitag von 9:00 bis 18:00 Uhr geöffnet. Termine nach Vereinbarung.""",

    "instagram": "Wir heißen @liquid_aesthetik auf Instagram! Schau gerne vorbei für Einblicke in unsere Arbeit und Neuigkeiten."
}

# 🎯 Schlagwort-Antworten
KEYWORD_ANSWERS = {
    "hyaluron": "Unsere Hyaluronbehandlung hilft, Volumen und Frische wiederherzustellen. Sie eignet sich besonders für Lippen, Wangen und Falten.",
    "fadenlifting": "Das Fadenlifting ist eine minimal-invasive Methode, um die Haut zu straffen – ohne OP, mit sofort sichtbarem Effekt.",
    "jawline": "Mit Jawline-Contouring wird die Kieferlinie betont und definiert – für ein markantes, harmonisches Gesicht.",
    "lipolyse": "Die Lipolyse reduziert lokale Fettdepots durch Injektionen – ideal für kleine Problemzonen wie Doppelkinn oder Bauch.",
    "augenringe": "Bei Liquid Aesthetik behandeln wir Augenringe mit Hyaluronsäure, um Schatten und Tränensäcke sanft zu mildern.",
}

# 🔢 Wörter in Zahlen umwandeln
WORD_NUMBERS = {
    "eins": 1, "eine": 1, "ein": 1,
    "zwei": 2, "drei": 3, "vier": 4, "fünf": 5, "sechs": 6,
    "sieben": 7, "acht": 8, "neun": 9, "zehn": 10
}


class handler(BaseHTTPRequestHandler):
    def _send(self, status=200, body=None, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
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

            # 🧩 Datenschutz: Eingaben automatisch anonymisieren
            user_message = (data.get("message") or "").strip()
            user_message = re.sub(r"\b[A-ZÄÖÜ][a-zäöü]+\b", user_message)
            user_message = re.sub(r"\d{3,}", user_message)
            user_message = user_message.lower()

            if not user_message:
                self._send(400, {"error": "Feld 'message' ist leer."})
                return

            # 🔒 Datenschutz-Filter (blockiert sensible Infos)
            if re.search(r"(iban|straße|telefon|adresse|geheim)", user_message, re.IGNORECASE):
                reply = "Aus Datenschutzgründen kann ich dazu keine Angaben machen."
                self._send(200, {"reply": reply})
                return

            # 🔎 Zahl (Ziffer oder Wort) erkennen
            zahl_match = re.search(r"\b(\d+)\b", user_message)
            anzahl = None
            if not zahl_match:
                for word, num in WORD_NUMBERS.items():
                    if re.search(rf"\b{word}\b", user_message):
                        anzahl = num
                        break
            else:
                anzahl = int(zahl_match.group(1)) if zahl_match else anzahl

            # 📋 Wenn Zahl erkannt + passendes Thema
            if anzahl is not None and re.search(r"behandlung|angebot|leistung|preise|optionen|möglichkeiten", user_message):
                behandlungen = [
                    "Hyaluron", "Jawline", "Lipolyse", "Lippen",
                    "Wangenaufbau", "Fadenlifting", "Augenringe", "Nasenkorrektur"
                ]
                anzahl = min(anzahl, len(behandlungen))
                antwort = f"Hier sind {anzahl} unserer Behandlungen:\n"
                antwort += "\n".join([f"{i+1}. {b}" for i, b in enumerate(behandlungen[:anzahl])])
                self._send(200, {"reply": antwort})
                return

            # 📌 Feste Antworten prüfen
            for key, answer in PREDEFINED_ANSWERS.items():
                if key in user_message:
                    self._send(200, {"reply": answer})
                    return

            # 📌 Schlagwortantworten prüfen
            for key, answer in KEYWORD_ANSWERS.items():
                if key in user_message:
                    self._send(200, {"reply": answer})
                    return

            # 🤖 Wenn nichts passt → KI antwortet
            prompt = f"""
            Du bist ein Chatbot für Liquid Aesthetik.
            Verwende den folgenden Website-Text, um auf Fragen zu antworten:
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
            )

            reply = completion.choices[0].message.content
            self._send(200, {"reply": reply})

        except Exception as e:
            self._send(500, {"error": str(e)})

# Test comment
