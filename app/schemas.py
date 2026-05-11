# app/schemas.py
# Schémas Pydantic : validation des données entrantes et sortantes

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime


# ─────────────────────────────────────────────
#  AUTH
# ─────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_valide(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Le nom d'utilisateur doit faire au moins 3 caractères")
        if len(v) > 50:
            raise ValueError("Le nom d'utilisateur ne peut pas dépasser 50 caractères")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Le nom d'utilisateur ne peut contenir que lettres, chiffres, _ et -")
        return v

    @field_validator("password")
    @classmethod
    def password_valide(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Le mot de passe doit faire au moins 8 caractères")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id:         int
    email:      str
    username:   str
    is_active:  bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    user:          UserResponse


# ─────────────────────────────────────────────
#  RECETTES
# ─────────────────────────────────────────────

class RecetteCreate(BaseModel):
    titre:         str
    description:   Optional[str]        = ""
    ingredients:   List[str]            = []
    etapes:        List[str]            = []
    # Durées par étape en minutes — null = pas de minuteur pour cette étape
    durees_etapes: List[Optional[int]]  = []
    categorie:     Optional[str]        = "Autre"
    duree:         Optional[int]        = 0
    portions:      Optional[int]        = 1
    image_url:     Optional[str]        = None
    est_favori:    Optional[bool]       = False

    @field_validator("titre")
    @classmethod
    def titre_valide(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Le titre doit faire au moins 2 caractères")
        if len(v) > 255:
            raise ValueError("Le titre ne peut pas dépasser 255 caractères")
        return v

    @field_validator("duree", "portions")
    @classmethod
    def valeur_positive(cls, v: int) -> int:
        if v is not None and v < 0:
            raise ValueError("La valeur doit être positive")
        return v


class RecetteUpdate(BaseModel):
    titre:         Optional[str]               = None
    description:   Optional[str]               = None
    ingredients:   Optional[List[str]]          = None
    etapes:        Optional[List[str]]          = None
    durees_etapes: Optional[List[Optional[int]]] = None
    categorie:     Optional[str]               = None
    duree:         Optional[int]               = None
    portions:      Optional[int]               = None
    image_url:     Optional[str]               = None
    est_favori:    Optional[bool]              = None


class RecetteResponse(BaseModel):
    id:            int
    titre:         str
    description:   str
    ingredients:   List[str]
    etapes:        List[str]
    durees_etapes: List[Optional[int]]  = []
    categorie:     str
    duree:         int
    portions:      int
    image_url:     Optional[str]
    est_favori:    bool
    owner_id:      int
    created_at:    datetime

    model_config = {"from_attributes": True}