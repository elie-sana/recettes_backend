# app/routers/recettes.py
# CRUD complet des recettes — toutes les routes sont protégées par JWT

import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/recettes", tags=["Recettes"])

# ─── Configuration upload ─────────────────────────────────────────────────────
# UPLOAD_DIR : défini par variable d'env sur Railway, "uploads" en local
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

EXTENSIONS_AUTORISEES = {".jpg", ".jpeg", ".png", ".webp"}
TAILLE_MAX_OCTETS = 5 * 1024 * 1024  # 5 Mo


# ─── GET / ────────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=List[schemas.RecetteResponse],
    summary="Lister ses recettes"
)
def get_recettes(
    search:            Optional[str]  = None,
    categorie:         Optional[str]  = None,
    favoris_seulement: bool           = False,
    db:                Session        = Depends(get_db),
    current_user:      models.User    = Depends(auth.get_current_user),
):
    """
    Retourne uniquement les recettes de l'utilisateur connecté.
    Supporte la recherche par titre, le filtre par catégorie et par favoris.
    """
    query = db.query(models.Recette).filter(
        models.Recette.owner_id == current_user.id
    )

    if search:
        query = query.filter(models.Recette.titre.ilike(f"%{search}%"))

    if categorie:
        query = query.filter(models.Recette.categorie == categorie)

    if favoris_seulement:
        query = query.filter(models.Recette.est_favori == True)  # noqa: E712

    return query.order_by(models.Recette.created_at.desc()).all()


# ─── POST / ───────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=schemas.RecetteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une recette"
)
def create_recette(
    recette_data: schemas.RecetteCreate,
    db:           Session     = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    recette = models.Recette(
        **recette_data.model_dump(),
        owner_id=current_user.id
    )
    db.add(recette)
    db.commit()
    db.refresh(recette)
    return recette


# ─── GET /{id} ────────────────────────────────────────────────────────────────

@router.get(
    "/{recette_id}",
    response_model=schemas.RecetteResponse,
    summary="Obtenir une recette"
)
def get_recette(
    recette_id:   int,
    db:           Session     = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    recette = db.query(models.Recette).filter(
        models.Recette.id       == recette_id,
        models.Recette.owner_id == current_user.id,
    ).first()

    if not recette:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recette introuvable"
        )
    return recette


# ─── PUT /{id} ────────────────────────────────────────────────────────────────

@router.put(
    "/{recette_id}",
    response_model=schemas.RecetteResponse,
    summary="Modifier une recette"
)
def update_recette(
    recette_id:   int,
    recette_data: schemas.RecetteUpdate,
    db:           Session     = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    recette = db.query(models.Recette).filter(
        models.Recette.id       == recette_id,
        models.Recette.owner_id == current_user.id,
    ).first()

    if not recette:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recette introuvable"
        )

    for field, value in recette_data.model_dump(exclude_unset=True).items():
        setattr(recette, field, value)

    db.commit()
    db.refresh(recette)
    return recette


# ─── DELETE /{id} ─────────────────────────────────────────────────────────────

@router.delete(
    "/{recette_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une recette"
)
def delete_recette(
    recette_id:   int,
    db:           Session     = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    recette = db.query(models.Recette).filter(
        models.Recette.id       == recette_id,
        models.Recette.owner_id == current_user.id,
    ).first()

    if not recette:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recette introuvable"
        )

    # Supprime le fichier image associé s'il existe
    if recette.image_url and "/uploads/" in recette.image_url:
        nom_fichier = recette.image_url.split("/uploads/")[-1]
        chemin = os.path.join(UPLOAD_DIR, nom_fichier)
        if os.path.exists(chemin):
            os.remove(chemin)

    db.delete(recette)
    db.commit()


# ─── PATCH /{id}/favori ───────────────────────────────────────────────────────

@router.patch(
    "/{recette_id}/favori",
    response_model=schemas.RecetteResponse,
    summary="Basculer le statut favori"
)
def toggle_favori(
    recette_id:   int,
    db:           Session     = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Toggle : si favori → non favori, si non favori → favori."""
    recette = db.query(models.Recette).filter(
        models.Recette.id       == recette_id,
        models.Recette.owner_id == current_user.id,
    ).first()

    if not recette:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recette introuvable"
        )

    recette.est_favori = not recette.est_favori
    db.commit()
    db.refresh(recette)
    return recette


# ─── POST /{id}/image ─────────────────────────────────────────────────────────

@router.post(
    "/{recette_id}/image",
    response_model=schemas.RecetteResponse,
    summary="Uploader une image pour une recette"
)
async def upload_image(
    recette_id:   int,
    fichier:      UploadFile        = File(...),
    db:           Session           = Depends(get_db),
    current_user: models.User       = Depends(auth.get_current_user),
):
    """
    Reçoit un fichier image en multipart/form-data.
    Sauvegarde le fichier sur disque, met à jour image_url en base,
    supprime l'ancienne image si elle existait.
    """
    # ── Vérification propriété ───────────────────────────────────────────────
    recette = db.query(models.Recette).filter(
        models.Recette.id       == recette_id,
        models.Recette.owner_id == current_user.id,
    ).first()

    if not recette:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recette introuvable"
        )

    # ── Validation extension — whitelist stricte ─────────────────────────────
    _, ext = os.path.splitext(fichier.filename or "")
    ext = ext.lower()
    if ext not in EXTENSIONS_AUTORISEES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Extension non autorisée. Acceptées : {', '.join(EXTENSIONS_AUTORISEES)}"
        )

    # ── Validation taille ────────────────────────────────────────────────────
    contenu = await fichier.read()
    if len(contenu) > TAILLE_MAX_OCTETS:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Fichier trop volumineux (max 5 Mo)"
        )

    # ── Sauvegarde avec nom UUID — évite collisions et path traversal ────────
    nom_fichier = f"{uuid.uuid4().hex}{ext}"
    chemin = os.path.join(UPLOAD_DIR, nom_fichier)
    with open(chemin, "wb") as f:
        f.write(contenu)

    # ── Supprime l'ancienne image ────────────────────────────────────────────
    if recette.image_url and "/uploads/" in recette.image_url:
        ancien_nom = recette.image_url.split("/uploads/")[-1]
        ancien_chemin = os.path.join(UPLOAD_DIR, ancien_nom)
        if os.path.exists(ancien_chemin):
            os.remove(ancien_chemin)

    # ── Met à jour la base ───────────────────────────────────────────────────
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    recette.image_url = f"{base_url}/uploads/{nom_fichier}"
    db.commit()
    db.refresh(recette)
    return recette