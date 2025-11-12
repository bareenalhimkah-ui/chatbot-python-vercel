# booking/schemas.py
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List

class CustomerIn(BaseModel):
name: str = Field(..., min_length=2)
email: EmailStr
phone: Optional[str] = None

class AppointmentIn(BaseModel):
service: str
praxis: Optional[str] = None # "wiesbaden" | "mannheim" | "dortmund"
date: datetime # ISO-8601, z.B. 2025-11-12T14:00:00
customer: CustomerIn
employee_id: Optional[int] = None

class AppointmentOut(BaseModel):
id: int
service: str
praxis: Optional[str]
date: datetime
status: str
customer_name: str

class Config:
from_attributes = True

class SlotQuery(BaseModel):
praxis: Optional[str] = None
service: Optional[str] = None
day: Optional[str] = None # YYYY-MM-DD

class SlotOut(BaseModel):
start: datetime
end: datetime
employee_id: Optional[int] = None