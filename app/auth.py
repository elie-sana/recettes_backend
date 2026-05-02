# app/auth.py
# Gestion de l'authentification : hashage des mots de passe et tokens JWT

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from . import models
from .database import get_db
import os

# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────

SECRET_KEY                  = os.getenv("SECRET_KEY")
ALGORITHM                   = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS   = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

if not SECRET_KEY:
    raise ValueError("SECRET_KEY manquante dans le fichier .env")

# ─────────────────────────────────────────────
#  HASHAGE MOT DE PASSE
# ─────────────────────────────────────────────

# bcrypt est l'algorithme standard pour hasher les mots de passe
# Il est intentionnellement lent pour résister aux attaques brute-force
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Retourne le hash bcrypt du mot de passe. Ne jamais stocker en clair."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compare le mot de passe fourni avec le hash stocké en base."""
    return pwd_context.verify(plain_password, hashed_password)

# ─────────────────────────────────────────────
#  TOKENS JWT
# ─────────────────────────────────────────────

# FastAPI utilise ce scheme pour extraire le token du header Authorization
# Le client envoie : Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")

def _create_token(data: dict, expires_delta: timedelta) -> str:
    """
    Fonction interne — crée un JWT signé avec SECRET_KEY.
    Préfixée _ car elle ne doit pas être appelée directement depuis les routes.
    """
    payload = data.copy()
    # datetime.now(timezone.utc) est la bonne pratique — utcnow() est déprécié
    payload["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def create_access_token(user_id: int) -> str:
    """
    Token de courte durée (30 min par défaut).
    Utilisé pour authentifier chaque requête API.
    """
    return _create_token(
        {"sub": str(user_id), "type": "access"},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

def create_refresh_token(user_id: int) -> str:
    """
    Token de longue durée (7 jours par défaut).
    Utilisé uniquement pour obtenir un nouvel access token sans se reconnecter.
    """
    return _create_token(
        {"sub": str(user_id), "type": "refresh"},
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )

# ─────────────────────────────────────────────
#  DÉPENDANCE PROTECTION DES ROUTES
# ─────────────────────────────────────────────

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> models.User:
    """
    Dépendance injectable FastAPI.
    Toute route qui déclare Depends(get_current_user) est automatiquement protégée.

    Processus :
    1. Extrait le token du header Authorization
    2. Décode et vérifie la signature JWT
    3. Vérifie que c'est bien un access token (pas un refresh)
    4. Charge et retourne l'utilisateur depuis la base
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload    = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id    = payload.get("sub")
        token_type = payload.get("type")

        # Vérifie que le token contient les bonnes données
        if user_id is None or token_type != "access":
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(
        models.User.id == int(user_id)
    ).first()

    # Vérifie que l'utilisateur existe et est actif
    if user is None or not user.is_active:
        raise credentials_exception

    return user