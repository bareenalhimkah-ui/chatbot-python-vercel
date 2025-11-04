from http.server import BaseHTTPRequestHandler
import os, json, re, time
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# 🔐 Environment laden
env_path = os.path.join(os.path.dirname(__file__), "../.env.local")
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)

# 🔑 OpenAI Setup
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
MODEL = "ft:gpt-4o-mini-2024-07-18:bareen::CW6GdbsO"

# 🧭 Systemprompt
SYSTEM_PROMPT = (
    "Du bist eine freundliche, professionelle Assistentin von Liquid Aesthetik. "
    "Sprich in Du-Form, antworte kurz, klar und sympathisch. "
    "Wenn jemand nach Preisen fragt, gib sie exakt aus der Preisliste wieder. "
    "Wenn keine Preisinformation vorhanden ist, sag: 'Dazu liegt mir aktuell kein Preis vor.' "
    "Gib keine internen oder privaten Informationen preis. "
    "Antworte freundlich und hilfsbereit."
)

# 📍 Standorte
STANDORTE = {
    "wiesbaden": {
        "adresse": "Langgasse 20, 65183 Wiesbaden",
        "telefon": "0611 /51 01 85 26",
        "oeffnungszeiten": "Mo–Do 10–18 Uhr, Fr bis 19 Uhr"
    },
    "mannheim": {
        "adresse": "Wird demnächst eröffnet",
        "telefon": "0611 /51 01 85 26",
        "oeffnungszeiten": "Mo–Do 10–18 Uhr, Fr bis 19 Uhr"
    },
    "dortmund": {
        "adresse": "Markt 6, 44137 Dortmund",
        "telefon": "0611 /51 01 85 26",
        "oeffnungszeiten": "Mo–Do 10–18 Uhr, Fr bis 19 Uhr"
    },
}

# 💰 Preise
try:
    PREISE_PATH = os.path.join(os.path.dirname(__file__), "preise.json")
    with open(PREISE_PATH, "r", encoding="utf-8") as f:
        PREISE = json.load(f)
except:
    PREISE = {}

# 🧴 Behandlungen
try:
    BEHANDLUNGEN_PATH = os.path.join(os.path.dirname(__file__), "behandlungen.json")
    with open(BEHANDLUNGEN_PATH, "r", encoding="utf-8") as f:
        BEHANDLUNGEN = json.load(f)
except:
    BEHANDLUNGEN = {}

# 🔄 Synonyme
SYNONYMS = {
    "hyaluronspritze": "hyaluron",
    "faltenunterspritzung": "hyaluron",
    "lippen aufspritzen": "Lippen 1 ml",
    "fettwegspritze": "Lipolyse/Fettwegspritze",
    "kinnfettbehandlung": "Lipolyse/Fettwegspritze",
    "fadenlifting klein": "Mono Fäden 10 Stück",
    "botox": "B. Botox",
}

# 🔤 Text normalisieren
def normalize(text):
    text = text.lower()
    text = text.replace(" ", "").replace(".", "").replace(",", "").replace("ml", "milliliter")
    text = re.sub(r"[^a-z0-9äöüß]", "", text)
    return text

# ⚙️ Hauptklasse
class handler(BaseHTTPRequestHandler):
    def _send(self, status=200, body=None):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if body:
            if isinstance(body, (dict, list)):
                body = json.dumps(body, ensure_ascii=False)
            self.wfile.write(body.encode("utf-8"))

    def do_GET(self):
        self._send(200, {"status": "ok", "time": datetime.now().isoformat()})

    def do_OPTIONS(self):
        self._send(200, "")

    def do_POST(self):
        try:
            length = int(self.headers.get("content-length", "0"))
            data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            user_message = (data.get("message") or "").strip().lower()

            if not user_message:
                self._send(400, {"error": "Keine Nachricht erhalten."})
                return

            normalized = normalize(user_message)

            # 🚫 Datenschutzprüfung
            forbidden = ["iban", "konto", "passwort", "intern", "gehalt", "datenbank", "mitarbeiter"]
            if any(w in normalized for w in forbidden):
                self._send(200, {"reply": "Aus Datenschutzgründen darf ich dazu keine Angaben machen."})
                return

            # 📱 Social Media
            if "instagram" in normalized:
                self._send(200, {"reply": "Unser Instagram-Account ist @liquid.aesthetik."})
                return
            if "tiktok" in normalized:
                self._send(200, {"reply": "Unser TikTok-Account ist @liquid_aesthetik."})
                return

            # 📍 Standort / Adresse
            for ort, daten in STANDORTE.items():
                if ort in normalized:
                    reply = (
                        f"Unsere Praxis in {ort.capitalize()} findest du unter: {daten['adresse']}. "
                        f"Telefon: {daten['telefon']}, Öffnungszeiten: {daten['oeffnungszeiten']}."
                    )
                    self._send(200, {"reply": reply})
                    return

            # 💸 Preis oder Behandlung
            for key, value in PREISE.items():
                if normalize(key) in normalized:
                    if any(x in normalized for x in ["preis", "kosten", "teuer", "ab", "euro", "zahlen"]):
                        reply = f"Die Preise für {key} beginnen {value}."
                    else:
                        reply = f"Ja, {key} bieten wir an. Möchtest du mehr darüber wissen?"
                    self._send(200, {"reply": reply})
                    return

            # 🔁 Synonyme prüfen
            for synonym, target in SYNONYMS.items():
                if normalize(synonym) in normalized:
                    if target in PREISE:
                        reply = f"Die Preise für {target} beginnen {PREISE[target]}."
                    elif target in BEHANDLUNGEN:
                        reply = BEHANDLUNGEN[target]
                    else:
                        reply = f"Ja, {target} bieten wir an. Möchtest du mehr darüber wissen?"
                    self._send(200, {"reply": reply})
                    return

            # 🧠 GPT-Fallback (z. B. allgemeine Fragen)
            prompt = f"""
            Du bist der Chatbot von Liquid Aesthetik.
            Antworte professionell und freundlich basierend auf Praxiswissen.
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

        except Exception as e:
            print("❌ Fehler im Handler:", e)
            self._send(500, {"error": str(e)})

# 💻 Lokaler Test
if __name__ == "__main__":
    from http.server import HTTPServer
    port = 8000
    server = HTTPServer(("127.0.0.1", port), handler)
    print(f"🚀 Server läuft auf http://127.0.0.1:{port}/api/chat")
    server.serve_forever()
