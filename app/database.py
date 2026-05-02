# app/database.py
# Gestion de la connexion à PostgreSQL via SQLAlchemy

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv
import os

# Charge les variables du fichier .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL manquante dans le fichier .env")

# Railway fournit des URLs "postgres://" mais SQLAlchemy exige "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# create_engine crée le pool de connexions vers PostgreSQL
# pool_pre_ping=True vérifie que la connexion est vivante avant chaque requête
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# SessionLocal est la fabrique de sessions — chaque requête HTTP aura sa propre session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base classe dont hériteront tous nos modèles SQLAlchemy
class Base(DeclarativeBase):
    pass

def get_db():
    """
    Dépendance injectable FastAPI.
    Ouvre une session DB pour la requête, la ferme proprement après.
    Usage : db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()