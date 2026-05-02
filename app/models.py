# app/models.py
# Définition des tables PostgreSQL via SQLAlchemy ORM

from sqlalchemy import (
    Column, Integer, String, Boolean,
    ForeignKey, DateTime, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    email           = Column(String(255), unique=True, index=True, nullable=False)
    username        = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active       = Column(Boolean, default=True, nullable=False)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    # Un user possède plusieurs recettes
    # cascade="all, delete-orphan" : si on supprime un user,
    # toutes ses recettes sont supprimées automatiquement
    recettes = relationship(
        "Recette",
        back_populates="owner",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User id={self.id} username={self.username}>"


class Recette(Base):
    __tablename__ = "recettes"

    id          = Column(Integer, primary_key=True, index=True)
    titre       = Column(String(255), nullable=False)
    description = Column(Text, default="")
    ingredients = Column(Text, nullable=False)
    etapes      = Column(Text, nullable=False)
    categorie   = Column(String(100), default="Autre")
    duree       = Column(Integer, default=0)       # en minutes
    portions    = Column(Integer, default=1)
    image_url   = Column(String(500), default="")
    est_favori  = Column(Boolean, default=False, nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    # Clé étrangère : chaque recette appartient à exactement un user
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner    = relationship("User", back_populates="recettes")

    def __repr__(self):
        return f"<Recette id={self.id} titre={self.titre}>"