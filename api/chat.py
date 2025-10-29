from http.server import BaseHTTPRequestHandler
import os, json, re, time, difflib
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv


MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")

# ⚙️ Modell aus ENV wählen: erst FINETUNED_MODEL, dann OPENAI_MODEL, sonst Fallback
MODEL = (
    os.environ.get("FINETUNED_MODEL")
    or os.environ.get("OPENAI_MODEL")
    or "gpt-4o"
)


# 🔐 .env.local laden (nur wenn vorhanden)
env_path = os.path.join(os.path.dirname(__file__), "../.env.local")
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)

# 🔑 OpenAI-Client initialisieren
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

#Fine-Tuning-Modell
MODEL = "ft:gpt-4o-mini-2024-07-18:bareen::CW6GdbsO"

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
    CACHE_FILE = os.path.join(os.path.dirname(__file__), "website_data.txt")
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            WEBSITE_TEXT = f.read()[:16000]
            print(f"✅ Website statisch geladen ({len(WEBSITE_TEXT)} Zeichen)")
    else:
        WEBSITE_TEXT = (
            "Liquid Aesthetik ist eine moderne Praxis für ästhetische Medizin in Wiesbaden. "
            "Wir bieten Behandlungen mit Botox, Hyaluron und Fadenlifting an."
        )
        print("⚠️ Keine Website-Datei gefunden – Fallback-Text geladen.")
except Exception as e:
    WEBSITE_TEXT = (
        "Liquid Aesthetik ist eine moderne Praxis für ästhetische Medizin in Wiesbaden."
    )
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
    "b botox": "B. Botox",
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

            # 📱 Social Media Erkennung
            if any(word in normalized_message for word in ["instagram", "tiktok", "social", "netzwerk"]):
                if "instagram" in normalized_message:
                    reply = "Unser Instagram-Account ist @liquid.aesthetik."
                elif "tiktok" in normalized_message:
                    reply = "Unser TikTok-Account ist @liquid_aesthetik."
                else:
                    reply = "Du findest uns auf Instagram unter @liquid.aesthetik und auf TikTok unter @liquid_aesthetik."
                self._send(200, {"reply": reply})
                return

            # 🚫 Sicherheitsprüfung
            forbidden_keywords = [
                "geheim", "iban", "bank", "konto", "passwort", "intern",
                "login", "gehalt", "zugang", "server", "datenbank",
                "privat", "vertraulich", "daten", "nummer", "pin", "firmendaten", "mitarbeiter"
            ]

            if any(word in normalized_message for word in forbidden_keywords):
                reply = (
                    "Aus Datenschutz- und Sicherheitsgründen darf ich darüber leider keine Angaben machen. "
                    "Ich helfe dir aber gern bei allen Fragen zu Behandlungen, Preisen oder Terminen. 💬"
                )
                self._send(200, {"reply": reply})
                return

            normalized_message = normalize(user_message)

            # 🔤 Nachricht normalisieren (erneut nach früheren Returns)
            normalized_message = normalize(user_message)

            # 🚫 Sicherheits- & Datenschutzprüfung
            forbidden_keywords = [
                "geheim",
                "iban",
                "bank",
                "konto",
                "passwort",
                "intern",
                "login",
                "gehalt",
                "zugang",
                "server",
                "datenbank",
                "privat",
                "vertraulich",
                "daten",
                "nummer",
                "pin",
                "firmendaten",
                "mitarbeiter",
            ]

            if any(word in normalized_message for word in forbidden_keywords):
                reply = (
                    "Aus Datenschutz- und Sicherheitsgründen darf ich darüber leider keine Angaben machen. "
                    "Ich helfe dir aber gern bei allen Fragen zu Behandlungen, Preisen oder Terminen. 💬"
                )
                self._send(200, {"reply": reply})
                return


            # 🧭 Anfahrt / Entfernung → GPT beantworten lassen
            if any(
                k in user_message
                for k in [
                    "wie weit",
                    "wie lange",
                    "entfernt",
                    "fahrzeit",
                    "fahrt",
                    "anfahrt",
                    "route",
                    "weg",
                    "von mir",
                    "nach wiesbaden",
                ]
            ):

                prompt = f"""
                Du bist die Assistentin von Liquid Aesthetik.
                Adresse der Praxis: Langgasse 20, 65183 Wiesbaden.
                
                AUFGABE:

                - Kurz antworten, freundlich
                - Bei Städten grobe Zeitspannen „je nach Verkehr“
                - Adresse immer nennen
                - Google Maps für genaue Zeit erwähnen
                

                - Beantworte Anfahrts- oder Entfernungsfragen kurz (1–2 Sätze), freundlich und ehrlich.
                - Wenn der Nutzer einen Ort nennt (z. B. Mainz, Frankfurt, Rüsselsheim, Darmstadt):
                  * Gib eine grobe, realistische Zeitspanne für das Rhein-Main-Gebiet als Schätzung an
                    (z. B. Mainz 20–40 Min, Frankfurt 30–50 Min, Rüsselsheim 15–30 Min, Darmstadt 35–55 Min – jeweils „je nach Verkehr“).
                - Wenn kein Startort genannt wird:
                  * Bitte freundlich in einem einzigen Satz um den Startort.
                - Nenne immer die Praxisadresse und erwähne kurz, dass Google Maps die genaueste Zeit liefert.
                - Gib bei Anfahrtszeiten immer eine grobe Schätzung (z. B. 20–40 Minuten) und sag 'je nach Verkehr'. Erfinde keine exakten Kilometer oder Zeiten. 

                Nutzerfrage: {user_message}
                """
                completion = client.chat.completions.create(
                    model=MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                    timeout=20,
                )
                reply = completion.choices[0].message.content.strip()
                self._send(200, {"reply": reply})
                return

            # 📄 Kurzbeschreibung laden
            try:
                with open(
                    os.path.join(os.path.dirname(__file__), "kurzbeschreibung.txt"),
                    "r",
                    encoding="utf-8",
                ) as f:
                    kurzbeschreibung = f.read()
            except:
                kurzbeschreibung = ""

            # 💸 Preis-/Behandlungserkennung
            found_key = None
            for key in PREISE.keys():
                if normalize(key) in normalized_message:
                    found_key = key
                    break

            if found_key:
                fragt_nach_preis = any(
                    word in normalized_message
                    for word in ["preis", "kosten", "teuer", "ab", "wie viel", "anfang"]
                )
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
                    fragt_nach_preis = any(
                        word in normalized_message
                        for word in [
                            "preis",
                            "kosten",
                            "teuer",
                            "ab",
                            "wie viel",
                            "anfang",
                            "bietet",
                        ]
                    )
                    if fragt_nach_preis and target in PREISE:
                        reply = f"Die Preise für {target} beginnen {PREISE[target]}."
                    elif target in BEHANDLUNGEN:
                        reply = BEHANDLUNGEN[target]
                    else:
                        reply = f"Ja, {target} bieten wir an. Möchtest du mehr darüber wissen?"
                    self._send(200, {"reply": reply})
                    return

            medizinische_keywords = [
                "behandlung",
                "botox",
                "hyaluron",
                "lippen",
                "falten",
                "lifting",
                "praxis",
                "kosmetik",
            ]


            # 🧠 Nicht-medizinische Fragen → GPT

            # 📱 Social Media Erkennung (Fallback – falls oben nicht gegriffen)
            if any(word in normalized_message for word in ["instagram", "tiktok", "social", "netzwerk"]):
                if "instagram" in normalized_message:
                    reply = "Unser Instagram-Account ist @liquid.aesthetik."
                elif "tiktok" in normalized_message:
                    reply = "Unser TikTok-Account ist @liquid_aesthetik."
                else:
                    reply = "Du findest uns auf Instagram unter @liquid.aesthetik und auf TikTok unter @liquid_aesthetik."
                self._send(200, {"reply": reply})
                return

            # 🧠 Allgemeine Themen (nicht medizinisch)

            if not any(word in normalized_message for word in medizinische_keywords):
                prompt = f"""
                Du bist der Chatbot von Liquid Aesthetik.
                Antworte basierend auf den Praxisinformationen.
                ---
                {kurzbeschreibung}
                ---
                Nutzerfrage: {user_message}
                """
                completion = client.chat.completions.create(
                    model=MODEL,
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

        except json.JSONDecodeError:
            self._send(400, {"error": "Ungültiges JSON-Format."})
        except Exception as e:
            print("❌ Fehler im Handler:", e)
            self._send(500, {"error": str(e)})


# 💻 Lokaler Testmodus
if __name__ == "__main__":
    from http.server import HTTPServer
    port = 8000
    server = HTTPServer(("127.0.0.1", port), handler)
    print(f"🚀 Server läuft auf http://127.0.0.1:{port}/api/chat")
    server.serve_forever()
