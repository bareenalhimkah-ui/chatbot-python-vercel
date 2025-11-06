import os
import json
import subprocess

print("🧠 Chatbot Setup – Automatische Projektstruktur mit GitHub-Link")

# === Kundennamen abfragen ===
client_name = input("Bitte Kundennamen eingeben (z. B. liquid, pureaesthetics): ").strip().lower()
if not client_name:
    print("❌ Kein Name eingegeben – Abbruch.")
    exit()

github_user = input("GitHub-Benutzernamen eingeben (z. B. bareenalhimkah-ui): ").strip()
if not github_user:
    print("❌ Kein GitHub-Benutzername angegeben – Abbruch.")
    exit()

# === Ordnerstruktur ===
BASE_DIR = os.getcwd()
project_path = os.path.join(BASE_DIR, f"{client_name}-chatbot")
api_path = os.path.join(project_path, "api")
os.makedirs(api_path, exist_ok=True)

# === Root .gitignore ===
root_gitignore = """.vercel/
.env.local
"""
with open(os.path.join(project_path, ".gitignore"), "w", encoding="utf-8") as f:
    f.write(root_gitignore)

# === API .gitignore ===
api_gitignore = """# Python Cache & Virtualenvs
__pycache__/
*.pyc
*.pyo
*.pyd
venv/
env/
.venv/

# Environment
.env
.env.local

# Schutz: Frontend bleibt auf GitHub
!../index.html
"""
with open(os.path.join(api_path, ".gitignore"), "w", encoding="utf-8") as f:
    f.write(api_gitignore)

# === Backend chat.py ===
chat_py = """from http.server import BaseHTTPRequestHandler
import os, json
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# ENV laden
env_path = os.path.join(os.path.dirname(__file__), "../.env.local")
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
MODEL = os.environ.get("FINETUNED_MODEL", "gpt-4o-mini")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

SYSTEM_PROMPT = (
    f"Du bist die freundliche Assistentin von {CONFIG['praxis']['name']}. "
    "Sprich in Du-Form, antworte warm und professionell. "
    "Veröffentliche oder speichere niemals vertrauliche Daten, "
    "und gib keine internen Unternehmensinformationen preis."
)

class handler(BaseHTTPRequestHandler):
    def _send(self, status=200, body=None):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if body:
            self.wfile.write(json.dumps(body, ensure_ascii=False).encode("utf-8"))

    def do_POST(self):
        try:
            length = int(self.headers.get("content-length", "0"))
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            user_message = data.get("message", "").strip()

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ]

            completion = client.chat.completions.create(
                model=MODEL, messages=messages, temperature=0.4
            )
            reply = completion.choices[0].message.content.strip()
            self._send(200, {"reply": reply})

        except Exception as e:
            self._send(500, {"error": str(e)})
"""
with open(os.path.join(api_path, "chat.py"), "w", encoding="utf-8") as f:
    f.write(chat_py)

# === config.json Vorlage ===
config = {
    "praxis": {
        "name": client_name.capitalize() + " Aesthetik",
        "adresse": "Adresse einfügen",
        "telefon": "Telefonnummer einfügen",
        "email": f"info@{client_name}.de",
        "beschreibung": "Praxisbeschreibung hier einfügen",
        "slogan": "Für natürliche Schönheit.",
    }
}
with open(os.path.join(api_path, "config.json"), "w", encoding="utf-8") as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

# === index.html (Frontend) ===
index_html = f"""<!DOCTYPE html>
<html lang='de'>
<head>
  <meta charset='UTF-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1.0'>
  <title>{client_name.capitalize()} Chatbot</title>
  <style>
    body {{
      font-family: 'Poppins', sans-serif;
      background-color: #f8f4ee;
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
    }}
    .chat {{
      width: 380px;
      height: 560px;
      background: #fffaf4;
      border-radius: 20px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.1);
      display: flex;
      flex-direction: column;
    }}
  </style>
</head>
<body>
  <div class='chat'>
    <h2 style='background:#c9a14a;color:white;padding:15px;text-align:center;border-radius:20px 20px 0 0;'>
      {client_name.capitalize()} Assistentin
    </h2>
    <div style='padding:20px;'>Hallo 👋 Wie kann ich dir helfen?</div>
  </div>
</body>
</html>
"""
with open(os.path.join(project_path, "index.html"), "w", encoding="utf-8") as f:
    f.write(index_html)

# === Git Initialisierung ===
os.chdir(project_path)
subprocess.run(["git", "init"])
subprocess.run(["git", "branch", "-M", "main"])
subprocess.run(["git", "add", "."])
subprocess.run(["git", "commit", "-m", "Initial commit – " + client_name])

remote_url = f"https://github.com/{github_user}/{client_name}-chatbot.git"
subprocess.run(["git", "remote", "add", "origin", remote_url])
print(f"\n📦 Git-Repository vorbereitet: {remote_url}")
print("❗ Falls das Repo auf GitHub noch nicht existiert, bitte dort manuell anlegen und dann:")
print("👉 git push -u origin main")

print(f"\n✅ Fertig! Struktur für '{client_name}-chatbot' erstellt unter:\n{project_path}")
