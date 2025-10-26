from http.server import BaseHTTPRequestHandler
import os, json, re, time, difflib
from datetime import datetime
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# 💬 System Prompt (freundlich, sicher, preisklar)
SYSTEM_PROMPT = (
    "Du bist eine freundliche, professionelle Assistentin einer ästhetischen Praxis. "
    "Sprich in Du-Form, antworte kurz, klar und sympathisch. "
    "Dein Ton ist warm, einladend und kompetent. "
    "Beantworte offen und ehrlich Fragen zu Behandlungen, Preisen, Terminen und allgemeinen Praxisinformationen. "
    "Wenn genaue Preise im Website-Text oder in der Preisliste genannt sind, gib sie exakt wieder. "
    "Wenn du keine Preisinformation findest, sage: 'Ich habe dazu leider keine Preisangabe gefunden.' "
    "Gib niemals geschätzte oder erfundene Preise aus. "
    "Verwende Zahlen normal und nenne Preise vollständig. "
    "Gib keine vertraulichen Daten, IBANs, Mitarbeiteradressen oder internen Informationen preis. "
    "In solchen Fällen antworte: 'Aus Datenschutzgründen darf ich dazu keine Angaben machen.' "
    "Fokussiere dich immer auf die konkrete Nutzerfrage und vermeide Floskeln."
)

# 📁 Website-Cache-Einstellungen
CACHE_FILE = "website_data.txt"
SCRAPER_SCRIPT = "scrape_site.py"
MAX_CACHE_AGE_HOURS = 24

def ensure_website_data():
    if os.path.exists(CACHE_FILE):
        age_hours = (time.time() - os.path.getmtime(CACHE_FILE)) / 3600
        if age_hours > MAX_CACHE_AGE_HOURS:
            print("♻️ Website-Daten älter als 24h – aktualisiere...")
            os.system(f"python {SCRAPER_SCRIPT}")
    else:
        print("🌐 Website-Daten fehlen – lade neu herunter...")
        os.system(f"python {SCRAPER_SCRIPT}")

# 🧭 Website-Text laden
ensure_website_data()
try:
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        WEBSITE_TEXT = f.read()[:16000]
        print("✅ Website-Daten geladen:", len(WEBSITE_TEXT), "Zeichen")
        print(f"📅 Letztes Update: {time.ctime(os.path.getmtime(CACHE_FILE))}")
except Exception as e:
    WEBSITE_TEXT = "Fehler beim Laden der gespeicherten Website."
    print("❌ Fehler beim Laden der Website:", e)

# 💰 Preisdatei laden
try:
    with open("preise.json", "r", encoding="utf-8") as f:
        PREISE = json.load(f)
        print(f"✅ Preisdatei geladen: {len(PREISE)} Einträge")
except FileNotFoundError:
    PREISE = {}
    print("⚠️ Keine preise.json gefunden.")
except Exception as e:
    PREISE = {}
    print("⚠️ Fehler beim Laden der preise.json:", e)

# 💬 Synonyme für Preisanfragen
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

# 📚 Vordefinierte Antworten
PREDEFINED_ANSWERS = {
    "behandlungen": "Wir bieten verschiedene Behandlungen an – Hyaluron, Jawline, Lipolyse, Lippen, Wangenaufbau, Fadenlifting, Augenringe, Nasenkorrektur.",
    "kontakt": "Du kannst uns so erreichen:\n📍 Hegelstraße 40, 55122 Mainz\n📞 +49 176 12345678\n✉️ info@liquid-aesthetik.de",
    "preise": "Unsere Preise variieren je nach Behandlung und individuellem Bedarf. Eine genaue Preisliste erhältst du nach einem kostenlosen Beratungsgespräch.",
    "öffnungszeiten": "Unsere Praxis ist Montag bis Freitag von 9:00 bis 18:00 Uhr geöffnet. Termine nach Vereinbarung.",
    "instagram": "Wir heißen @liquid_aesthetik auf Instagram! Schau gerne vorbei für Einblicke in unsere Arbeit."
}

# 🎯 Schlagwort-Antworten
KEYWORD_ANSWERS = {
    "hyaluron": "Unsere Hyaluronbehandlung hilft, Volumen und Frische wiederherzustellen – ideal für Lippen, Wangen und Falten.",
    "fadenlifting": "Das Fadenlifting strafft die Haut sanft – ohne OP, mit sofort sichtbarem Effekt.",
    "jawline": "Mit Jawline-Contouring wird die Kieferlinie betont – für ein markantes, harmonisches Gesicht.",
    "lipolyse": "Die Lipolyse reduziert lokale Fettdepots – ideal für Doppelkinn oder kleine Problemzonen.",
    "augenringe": "Unsere Behandlung mildert Augenringe sanft mit Hyaluronsäure."
}

class handler(BaseHTTPRequestHandler):
    def _send(self, status=200, body=None, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.end_headers()
        if body:
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
            user_message = (data.get("message") or "").strip().lower()

            if not user_message:
                self._send(400, {"error": "Feld 'message' ist leer."})
                return

            # 🔒 Datenschutzfilter
            if re.search(r"(iban|straße|telefon|adresse|geheim|email)", user_message, re.IGNORECASE):
                reply = "Aus Datenschutzgründen darf ich dazu keine Angaben machen."
                self._send(200, {"reply": reply})
                return

            # 💰 Preis-Logik mit Synonym- & Tippfehlererkennung (robust)
            def normalize(text):
                """Entfernt Sonderzeichen, Punkte, Leerzeichen und wandelt in Kleinbuchstaben um."""
                return re.sub(r"[^a-z0-9äöüß]", "", text.lower())

            normalized_message = normalize(user_message)

            # Direkter Treffer mit JSON-Keys
            for key, price in PREISE.items():
                if normalize(key) in normalized_message:
                    reply = f"Die Preise für {key} beginnen {price}."
                    self._send(200, {"reply": reply})
                    return

            # Synonyme prüfen
            for synonym, target in SYNONYMS.items():
                if normalize(synonym) in normalized_message and target in PREISE:
                    reply = f"Die Preise für {target} beginnen {PREISE[target]}."
                    self._send(200, {"reply": reply})
                    return

            # Tippfehler / Fuzzy Matching
            all_terms = list(PREISE.keys()) + list(SYNONYMS.keys())
            matches = difflib.get_close_matches(user_message, all_terms, n=1, cutoff=0.7)
            if matches:
                match = matches[0]
                target = SYNONYMS.get(match, match)
                if target in PREISE:
                    reply = f"Die Preise für {target} beginnen {PREISE[target]}."
                    self._send(200, {"reply": reply})
                    return

            # 📌 Feste Antworten
            for key, answer in PREDEFINED_ANSWERS.items():
                if key in user_message:
                    self._send(200, {"reply": answer})
                    return

            # 📌 Schlagwortantworten
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
                timeout=15
            )

            reply = completion.choices[0].message.content
            self._send(200, {"reply": reply})

        except Exception as e:
            self._send(500, {"error": str(e)})
# Test Comment 