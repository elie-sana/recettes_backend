# app/routers/recettes.py
# CRUD complet des recettes — toutes les routes sont protégées par JWT

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/recettes", tags=["Recettes"])


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
        # ilike = case-insensitive LIKE — fonctionne sur PostgreSQL
        query = query.filter(models.Recette.titre.ilike(f"%{search}%"))

    if categorie:
        query = query.filter(models.Recette.categorie == categorie)

    if favoris_seulement:
        query = query.filter(models.Recette.est_favori == True)  # noqa: E712

    return query.order_by(models.Recette.created_at.desc()).all()


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
        models.Recette.owner_id == current_user.id,  # isolation stricte par user
    ).first()

    if not recette:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recette introuvable"
        )
    return recette


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

    # exclude_unset=True : ne met à jour que les champs explicitement fournis
    # Si le client envoie {"titre": "nouveau"}, seul le titre change
    for field, value in recette_data.model_dump(exclude_unset=True).items():
        setattr(recette, field, value)

    db.commit()
    db.refresh(recette)
    return recette


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

    db.delete(recette)
    db.commit()
    # 204 No Content — pas de corps dans la réponse


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