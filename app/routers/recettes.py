# app/routers/recettes.py
# CRUD complet des recettes — toutes les routes sont protégées par JWT

import os
import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/recettes", tags=["Recettes"])

cloudinary.config(
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key    = os.getenv("CLOUDINARY_API_KEY"),
    api_secret = os.getenv("CLOUDINARY_API_SECRET"),
    secure     = True,
)

EXTENSIONS_AUTORISEES = {".jpg", ".jpeg", ".png", ".webp"}
TAILLE_MAX_OCTETS = 5 * 1024 * 1024  # 5 Mo


@router.get("/", response_model=List[schemas.RecetteResponse], summary="Lister ses recettes")
def get_recettes(
    search:            Optional[str]  = None,
    categorie:         Optional[str]  = None,
    favoris_seulement: bool           = False,
    db:                Session        = Depends(get_db),
    current_user:      models.User    = Depends(auth.get_current_user),
):
    query = db.query(models.Recette).filter(
        models.Recette.owner_id == current_user.id
    )
    if search:
        query = query.filter(models.Recette.titre.ilike(f"%{search}%"))
    if categorie:
        query = query.filter(models.Recette.categorie == categorie)
    if favoris_seulement:
        query = query.filter(models.Recette.est_favori == True)
    return query.order_by(models.Recette.created_at.desc()).all()


@router.post("/", response_model=schemas.RecetteResponse, status_code=status.HTTP_201_CREATED, summary="Créer une recette")
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


@router.get("/{recette_id}", response_model=schemas.RecetteResponse, summary="Obtenir une recette")
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recette introuvable")
    return recette


@router.put("/{recette_id}", response_model=schemas.RecetteResponse, summary="Modifier une recette")
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recette introuvable")

    # exclude_unset=False pour s'assurer que durees_etapes est toujours inclus
    # même si sa valeur contient des null — c'est intentionnel.
    for field, value in recette_data.model_dump(exclude_unset=False).items():
        if value is not None or field == 'durees_etapes':
            setattr(recette, field, value)

    db.commit()
    db.refresh(recette)
    return recette


@router.delete("/{recette_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer une recette")
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recette introuvable")

    if recette.image_url and "cloudinary.com" in recette.image_url:
        try:
            partie = recette.image_url.split("/recettes/")[-1]
            public_id = f"recettes/{partie.rsplit('.', 1)[0]}"
            cloudinary.uploader.destroy(public_id)
        except Exception:
            pass

    db.delete(recette)
    db.commit()


@router.patch("/{recette_id}/favori", response_model=schemas.RecetteResponse, summary="Basculer le statut favori")
def toggle_favori(
    recette_id:   int,
    db:           Session     = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    recette = db.query(models.Recette).filter(
        models.Recette.id       == recette_id,
        models.Recette.owner_id == current_user.id,
    ).first()
    if not recette:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recette introuvable")

    recette.est_favori = not recette.est_favori
    db.commit()
    db.refresh(recette)
    return recette


@router.post("/{recette_id}/image", response_model=schemas.RecetteResponse, summary="Uploader une image pour une recette")
async def upload_image(
    recette_id:   int,
    fichier:      UploadFile        = File(...),
    db:           Session           = Depends(get_db),
    current_user: models.User       = Depends(auth.get_current_user),
):
    recette = db.query(models.Recette).filter(
        models.Recette.id       == recette_id,
        models.Recette.owner_id == current_user.id,
    ).first()
    if not recette:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recette introuvable")

    _, ext = os.path.splitext(fichier.filename or "")
    ext = ext.lower()
    if ext not in EXTENSIONS_AUTORISEES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Extension non autorisée. Acceptées : {', '.join(EXTENSIONS_AUTORISEES)}"
        )

    contenu = await fichier.read()
    if len(contenu) > TAILLE_MAX_OCTETS:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Fichier trop volumineux (max 5 Mo)")

    if recette.image_url and "cloudinary.com" in recette.image_url:
        try:
            partie = recette.image_url.split("/recettes/")[-1]
            public_id = f"recettes/{partie.rsplit('.', 1)[0]}"
            cloudinary.uploader.destroy(public_id)
        except Exception:
            pass

    try:
        resultat = cloudinary.uploader.upload(
            contenu,
            folder        = "recettes",
            resource_type = "image",
            transformation = [{"width": 1200, "crop": "limit", "quality": "auto"}],
        )
        image_url = resultat["secure_url"]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erreur upload Cloudinary : {str(e)}")

    recette.image_url = image_url
    db.commit()
    db.refresh(recette)
    return recette