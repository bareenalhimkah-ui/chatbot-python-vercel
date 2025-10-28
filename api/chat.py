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
    "Wenn jemand nach Öffnungszeiten, Standort oder Kontaktinformationen fragt, antworte präzise mit den korrekten Angaben von Liquid Aesthetik."
    "Wenn Preise aus der Preisliste bekannt sind, gib sie exakt so wieder. "
    "Wenn keine Preisinformation vorhanden ist, sag: 'Dazu liegt mir aktuell kein Preis vor.' "
    "Gib keine IBANs oder interne Informationen preis. Dazu gehören nicht Informationen wie Adressen oder Telefonnummern. "
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


# 🔄 Website statisch laden (Vercel: Read-only Fix)
try:
    CACHE_FILE = os.path.join(os.path.dirname(__file__), "website.txt")
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        WEBSITE_TEXT = f.read()[:16000]
        print(f"✅ Website statisch geladen ({len(WEBSITE_TEXT)} Zeichen)")
except Exception as e:
    WEBSITE_TEXT = "Fehler beim Laden der statischen Website."
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


# 💆 Behandlungen ohne Preise
with open(os.path.join(os.path.dirname(__file__), "behandlungen.json"), "r", encoding="utf-8") as f:
    BEHANDLUNGEN = json.load(f)


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

            # 📄 Kurzbeschreibung laden
            try:
                with open(os.path.join(os.path.dirname(__file__), "kurzbeschreibung.txt"), "r", encoding="utf-8") as f:
                    kurzbeschreibung = f.read()
            except:
                kurzbeschreibung = ""
                
            # 💸 Preis- und Behandlungs-Erkennung (intelligent)
            found_key = None
            for key in PREISE.keys():
                if normalize(key) in normalized_message:
                    found_key = key
                    break

            # Wenn ein Schlüssel (z. B. "B. Botox") gefunden wurde
            if found_key:
                fragt_nach_preis = any(word in normalized_message for word in ["preis", "kosten", "teuer", "ab", "wie viel", "anfang"])
                if fragt_nach_preis:
                    reply = f"Die Preise für {found_key} beginnen {PREISE[found_key]}."
                elif found_key in BEHANDLUNGEN:
                    reply = BEHANDLUNGEN[found_key]
                else:
                    reply = f"Ja, {found_key} bieten wir an. Möchtest du mehr darüber wissen?"
                self._send(200, {"reply": reply})
                return

            # 🔁 Synonyme prüfen
            for synonym, target in SYNONYMS.items():
                if normalize(synonym) in normalized_message:
                    fragt_nach_preis = any(word in normalized_message for word in ["preis", "kosten", "teuer", "ab", "wie viel", "anfang", "bietet"])
                    if fragt_nach_preis and target in PREISE:
                        reply = f"Die Preise für {target} beginnen {PREISE[target]}."
                    elif target in BEHANDLUNGEN:
                        reply = BEHANDLUNGEN[target]
                    else:
                        reply = f"Ja, {target} bieten wir an. Möchtest du mehr darüber wissen?"
                    self._send(200, {"reply": reply})
                    return

            # 🔁 Synonyme prüfen (Doppelprüfung)
            for synonym, target in SYNONYMS.items():
                if normalize(synonym) in normalized_message and target in PREISE:
                    reply = f"Die Preise für {target} beginnen {PREISE[target]}."
                    self._send(200, {"reply": reply})
                    return

                # ⚙️ Schlüsselwörter für medizinische Themen
            medizinische_keywords = [
             "behandlung", "botox", "hyaluron", "lippen", "falten", "lifting", "praxis", "kosmetik"
             ]

                   # 📱 Social Media Erkennung (direkte Antwort)
        if any(word in normalized_message for word in ["instagram", "tiktok", "social", "netzwerk"]):
            if "instagram" in normalized_message:
                reply = "Unser Instagram-Account ist @liquid.aesthetik."
            elif "tiktok" in normalized_message:
                reply = "Unser TikTok-Account ist @liquid_aesthetik."
            else:
                reply = "Du findest uns auf Instagram unter @liquid.aesthetik und auf TikTok unter @liquid_aesthetik."
            self._send(200, {"reply": reply})
            return



           
            if not any(word in normalized_message for word in medizinische_keywords):
                # Kein relevanter Begriff → GPT antworten lassen
                prompt = f"""
                Du bist der Chatbot von Liquid Aesthetik.
                Antworte basierend auf den Praxisinformationen.
                ---
                {kurzbeschreibung}
                ---
                Nutzerfrage: {user_message}
                """
                completion = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    timeout=20,
                )
                reply = completion.choices[0].message.content.strip()
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

            # 📍 Erkennung: Nutzer fragt nach Adresse, Öffnungszeiten oder Kontakt
            if any(word in normalized_message for word in ["adresse", "wo seid", "standort", "wo befindet", "anfahrt"]):
                reply = "Unsere Praxis befindet sich in der Langgasse 20, 65183 Wiesbaden."
                self._send(200, {"reply": reply})
                return

            if any(word in normalized_message for word in ["telefon", "nummer", "anrufen", "kontakt", "mail", "email"]):
                reply = "Du erreichst uns unter 0157 – 880 588 48 oder per Mail an info@liquid-aesthetik.de."
                self._send(200, {"reply": reply})
                return

            if any(word in normalized_message for word in ["öffnungszeit", "wann offen", "wann habt ihr auf", "zeiten"]):
                reply = "Wir vergeben Termine nach Vereinbarung – melde dich einfach telefonisch oder per WhatsApp!"
                self._send(200, {"reply": reply})
                return

            # 📄 Kurzbeschreibung nutzen, falls vorhanden
            try:
                with open(os.path.join(os.path.dirname(__file__), "kurzbeschreibung.txt"), "r", encoding="utf-8") as f:
                    kurzbeschreibung = f.read()
            except:
                kurzbeschreibung = ""

            # 🤖 Kein Preis → GPT-Antwort
            prompt = f"""
Du bist der Chatbot von Liquid Aesthetik.

Hier sind strukturierte Praxisdaten:
[ALLGEMEIN]
{kurzbeschreibung}

[WEBSITE]
{WEBSITE_TEXT[:8000]}

[PREISE]
{json.dumps(PREISE, ensure_ascii=False, indent=2)}

[BEHANDLUNGEN]
{json.dumps(BEHANDLUNGEN, ensure_ascii=False, indent=2)}

Antworte klar und freundlich, in Du-Form. Nutze immer die Daten aus den passenden Abschnitten:
- Wenn es um Adresse, Philosophie oder Slogan geht → nimm [ALLGEMEIN].
- Wenn es um Preise geht → nimm [PREISE].
- Wenn es um Behandlungen geht → nimm [BEHANDLUNGEN].
- Wenn es um allgemeine Infos geht → nutze [WEBSITE].
Nutzerfrage: {user_message}
"""

            completion = client.chat.completions.create(
                model="gpt-4o",
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

        # Reset conversational context
        self.last_topic = None

        #NUR LOkal testennnnn.:
        if __name__ == "__main__":
            from http.server import HTTPServer
            port = 8000
            server = HTTPServer(("127.0.0.1", port), handler)
            print(f"🚀 Server läuft auf http://127.0.0.1:{port}/api/chat")
            server.serve_forever()
