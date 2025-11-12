# main.py
import os
import json
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import OpenAI

from booking.routes import router as booking_router
from booking.models import Base
from db import engine

# ENV laden
load_dotenv(".env.local")

# DB-Tabellen sicherstellen
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Liquid Aesthetik – Chat & Booking API")

# CORS
allowed = os.getenv("APP_ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
MODEL = os.getenv("FINETUNED_MODEL", "gpt-4o-mini")

# Praxisdaten laden
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

with open(CONFIG_PATH, "r") as f:
    CONFIG = json.load(f)

PRAXEN = CONFIG.get("praxen", {})

SYSTEM_PROMPT = (
    "Du bist die freundliche, professionelle Assistentin von Liquid Aesthetik. "
    "Sprich in Du-Form, antworte warm, ruhig und kompetent. "
    "Wenn Preise, Öffnungszeiten oder Kontaktdaten bekannt sind, verwende sie direkt aus den Praxisdaten. "
    "Wenn eine Stadt genannt wird (z. B. Wiesbaden, Mannheim oder Dortmund), nutze die passenden Informationen dieser Praxis. "
    "Wenn etwas nicht in den Daten steht, sag höflich, dass du dazu leider keine Information hast. "
    "Gib niemals vertrauliche oder interne Informationen weiter. "
    "Erfinde nichts. Bei Unsicherheit: 'Dazu liegen mir leider keine verlässlichen Informationen vor.' "
    "Keine individuellen medizinischen Diagnosen. Verweise freundlich auf Beratung in der Praxis."
)

@app.get("/")
def root():
    return {"status": "ok", "time": datetime.now().isoformat()}

# Chat-Route
@app.post("/api/chat")
async def chat(request: Request):
    data = await request.json()
    user_message = (data.get("message") or "").strip().lower()

    # Standort erkennen
    selected_praxis = None
    for key, praxis in PRAXEN.items():
        if key.lower() in user_message:
            selected_praxis = praxis
            break

    context = f"Standort: {selected_praxis['stadt'] if selected_praxis else 'unbekannt'}"

    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{context}\n\n{user_message}"},
        ],
    )

    return {"reply": completion.choices[0].message.content.strip()}

# Booking-Routen aktivieren
app.include_router(booking_router, prefix="/api/booking", tags=["booking"])
