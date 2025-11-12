# booking/models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class Customer(Base):
__tablename__ = "customers"
id = Column(Integer, primary_key=True)
name = Column(String, nullable=False)
email = Column(String, nullable=False, unique=False)
phone = Column(String, nullable=True)

class Employee(Base):
__tablename__ = "employees"
id = Column(Integer, primary_key=True)
name = Column(String, nullable=False)
email = Column(String, nullable=True)
role = Column(String, nullable=True)

class Appointment(Base):
__tablename__ = "appointments"
id = Column(Integer, primary_key=True)
service = Column(String, nullable=False)
praxis = Column(String, nullable=True) # wiesbaden/mannheim/dortmund
date = Column(DateTime, nullable=False)
status = Column(String, default="gebucht")
customer_id = Column(Integer, ForeignKey("customers.id"))
employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
created_at = Column(DateTime, default=datetime.utcnow)

customer = relationship("Customer")
employee = relationship("Employee")