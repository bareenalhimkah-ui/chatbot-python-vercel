# db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./database.db"

echo = False # auf True setzen, wenn SQL im Log erscheinen soll
engine = create_engine(
DATABASE_URL,
connect_args={"check_same_thread": False},
echo=echo,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)