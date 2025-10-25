from http.server import BaseHTTPRequestHandler
import os, json, re
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM_PROMPT = (
    "Du bist eine freundliche, professionelle Assistentin von Liquid Aesthetik. "
    "Sprich in Du-Form, antworte kurz, klar und sympathisch. "
    "Dein Ton ist warm und weiblich, aber selbstbewusst. "
    "Vermeide übertriebene Floskeln oder lange Erklärungen. "
    "Wenn möglich, klinge einladend und beruhigend – so, als würdest du direkt in der Praxis beraten."
)

# 📄 Versuch, gespeicherte Website-Daten zu laden
try:
    with open("website_data.txt", "r", encoding="utf-8") as f:
        WEBSITE_TEXT = f.read()[:4000]
        print("✅ Website-Daten geladen:", len(WEBSITE_TEXT), "Zeichen")
except Exception as e:
    WEBSITE_TEXT = "Fehler beim Laden der gespeicherten Website."
    print("❌ Website-Daten konnten nicht geladen werden:", e)

# 📚 Vordefinierte Antworten (kostenfrei)
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
}

# 🎯 Schlagwort-Antworten (ebenfalls offline)
KEYWORD_ANSWERS = {
    "hyaluron": "Unsere Hyaluronbehandlung hilft, Volumen und Frische wiederherzustellen. Sie eignet sich besonders für Lippen, Wangen und Falten.",
    "fadenlifting": "Das Fadenlifting ist eine minimal-invasive Methode, um die Haut zu straffen – ohne OP, mit sofort sichtbarem Effekt.",
    "jawline": "Mit Jawline-Contouring wird die Kieferlinie betont und definiert – für ein markantes, harmonisches Gesicht.",
    "lipolyse": "Die Lipolyse reduziert lokale Fettdepots durch Injektionen – ideal für kleine Problemzonen wie Doppelkinn oder Bauch.",
    "augenringe": "Bei Liquid Aesthetik behandeln wir Augenringe mit Hyaluronsäure, um Schatten und Tränensäcke sanft zu mildern.",
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
            user_message = (data.get("message") or "").strip().lower()

            if not user_message:
                self._send(400, {"error": "Feld 'message' ist leer."})
                return

            # 1️⃣ Feste Antworten prüfen
            for key, answer in PREDEFINED_ANSWERS.items():
                if key in user_message:
                    self._send(200, {"reply": answer})
                    return

            # 2️⃣ Schlagwortantworten prüfen
            for key, answer in KEYWORD_ANSWERS.items():
                if key in user_message:
                    self._send(200, {"reply": answer})
                    return

            # 3️⃣ Nutzer nennt eine Zahl (z. B. „Nenne 5 Behandlungen“)
            zahl_match = re.search(r"\b(\d+)\b", user_message)
            if "behandlung" in user_message and zahl_match:
                anzahl = int(zahl_match.group(1))
                behandlungen = [
                    "Hyaluron",
                    "Jawline",
                    "Lipolyse",
                    "Lippen",
                    "Wangenaufbau",
                    "Fadenlifting",
                    "Augenringe",
                    "Nasenkorrektur"
                ]
                antwort = f"Hier sind {anzahl} unserer Behandlungen:\n"
                antwort += "\n".join([f"{i+1}. {b}" for i, b in enumerate(behandlungen[:anzahl])])
                self._send(200, {"reply": antwort})
                return

            # 4️⃣ Wenn nichts passt → KI antwortet
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
