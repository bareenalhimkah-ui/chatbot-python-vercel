# booking/routes.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List

from .schemas import AppointmentIn, AppointmentOut, SlotQuery, SlotOut
from .models import Base, Appointment, Customer, Employee
from ..db import engine, SessionLocal
from .email_utils import send_email

router = APIRouter()

# DB initialisieren
Base.metadata.create_all(bind=engine)

def get_db():
db = SessionLocal()
try:
yield db
finally:
db.close()

@router.post("/book", response_model=AppointmentOut)
def book_appointment(payload: AppointmentIn, db: Session = Depends(get_db)):
# Kunde upsert
customer = (
db.query(Customer).filter(Customer.email == payload.customer.email).first()
)
if not customer:
customer = Customer(
name=payload.customer.name,
email=payload.customer.email,
phone=payload.customer.phone,
)
db.add(customer)
db.flush()

# einfache Kollisionserkennung (gleiches Zeitfenster ±30 Min)
start = payload.date - timedelta(minutes=30)
end = payload.date + timedelta(minutes=30)
conflict = (
db.query(Appointment)
.filter(Appointment.date.between(start, end))
.first()
)
if conflict:
raise HTTPException(status_code=409, detail="Zeitfenster bereits belegt")

appt = Appointment(
service=payload.service,
praxis=payload.praxis,
date=payload.date,
customer_id=customer.id,
employee_id=payload.employee_id,
)
db.add(appt)
db.commit()
db.refresh(appt)

# E-Mail bestätigen
dt_str = payload.date.strftime("%d.%m.%Y %H:%M")
subject = "Terminbestätigung – Liquid Aesthetik"
body = (
f"Liebe/r {customer.name},\n\n"
f"dein Termin für {appt.service} ist bestätigt: {dt_str}"
f" in {appt.praxis or 'unserer Praxis'}.\n\nBis bald!\nLiquid Aesthetik"
)
send_email(customer.email, subject, body)

return AppointmentOut(
return {"message": "Termin storniert"}