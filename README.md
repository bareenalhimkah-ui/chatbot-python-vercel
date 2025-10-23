# Chatbot (Python + Vercel)

Ein minimaler, aber solider Chatbot: Frontend (HTML/JS) + Python-Serverless-Function auf Vercel, die die OpenAI API nutzt.

## Projektstruktur

```
.
├── api/
│   └── chat.py           # Python-API-Route: POST /api/chat
├── index.html            # Einfache Chat-Oberfläche
├── requirements.txt      # Python-Abhängigkeiten (wird von Vercel installiert)
└── vercel.json           # (Optional) Funktions-Config
```

## Lokale Vorbereitung (VS Code / Visual Studio)

1. **Dieses Projekt entpacken** und in VS Code/Visual Studio öffnen.
2. **Python installieren** (>= 3.11, empfohlen 3.12).  
3. **Vercel CLI (optional)**: `npm i -g vercel`.  
4. **OpenAI API Key setzen** (lokal als Datei, wird NICHT eingecheckt):  
   Erstelle eine Datei `.env.local` im Projekt-Root und trage ein:  
   ```
   OPENAI_API_KEY=dein_schluessel
   ```
   Alternativ kannst du die Variable auch als System-Env setzen.
5. Optional: Lokaler Test über `vercel dev` (liest `.env.local` automatisch ein).

> **Wichtig:** API Keys NIEMALS im Client/Frontend hartkodieren – nur serverseitig als Umgebungsvariable nutzen.

## GitHub & Vercel (sauberer Weg ohne Doppelordner)

1. **Neues GitHub-Repo** erstellen (leer, ohne Vorlage).  
2. In diesem Projekt-Ordner:
   ```bash
   git init
   git add .
   git commit -m "init: python vercel chatbot"
   git branch -M main
   git remote add origin <URL-deines-GitHub-Repos>
   git push -u origin main
   ```
3. **Vercel Dashboard** → *New Project* → **Import GitHub Repo** (dieses).  
4. Unter *Settings → Environment Variables* **OPENAI_API_KEY** hinzufügen (Scope: Production + Preview + Development).  
5. Deploy klicken. Danach ist dein Chatbot unter der Vercel-URL erreichbar.

## FAQ / Troubleshooting

- **404 auf /api/chat**: Stelle sicher, dass die Datei `api/chat.py` heißt und im Repo-Root liegt (kein zusätzlicher Oberordner).
- **ImportError: openai nicht gefunden**: Prüfe, dass `requirements.txt` vorhanden ist und `openai` enthält.
- **500 Fehler (Server)**: Schau die Vercel-Logs an (Project → Deployments → Logs). Häufig ist der API Key nicht gesetzt.
- **Mehr Sicherheit**: Entferne in `chat.py` die genaue Fehlerausgabe an den Client und logge stattdessen intern.

## Lizenz

MIT
