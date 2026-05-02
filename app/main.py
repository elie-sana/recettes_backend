# app/main.py
# Point d'entrée de l'application FastAPI

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routers import users, recettes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Remplace l'ancien @app.on_event("startup") — déprécié.
    Crée toutes les tables au démarrage si elles n'existent pas.
    En production on utilisera Alembic pour les migrations,
    mais create_all est correct pour démarrer.
    """
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Recettes API",
    description="Backend FastAPI pour l'application de recettes Flutter",
    version="1.0.0",
    lifespan=lifespan,
)

# ─────────────────────────────────────────────
#  CORS
# ─────────────────────────────────────────────
# Flutter mobile n'a pas d'origine fixe (pas de domaine)
# On autorise tout en développement — à restreindre en production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
#  ROUTERS
# ─────────────────────────────────────────────
app.include_router(users.router)
app.include_router(recettes.router)


@app.get("/", tags=["Santé"])
def health_check():
    """
    Endpoint de vérification — Railway et les load balancers
    appellent cette route pour savoir si le service est vivant.
    """
    return {
        "status": "ok",
        "message": "Recettes API opérationnelle",
        "version": "1.0.0",
    }