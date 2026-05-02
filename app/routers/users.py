# app/routers/users.py
# Endpoints d'authentification : inscription, connexion, profil

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/users", tags=["Authentification"])


@router.post(
    "/register",
    response_model=schemas.TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un nouveau compte"
)
def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Inscription d'un nouvel utilisateur.
    Retourne directement les tokens — l'utilisateur est connecté après inscription.
    """
    # Vérification unicité email
    if db.query(models.User).filter(
        models.User.email == user_data.email
    ).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cet email est déjà utilisé"
        )

    # Vérification unicité username
    if db.query(models.User).filter(
        models.User.username == user_data.username
    ).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce nom d'utilisateur est déjà pris"
        )

    # Création de l'utilisateur — mot de passe haché, jamais en clair
    user = models.User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=auth.hash_password(user_data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)  # recharge l'objet depuis la DB pour avoir l'id et created_at

    return schemas.TokenResponse(
        access_token=auth.create_access_token(user.id),
        refresh_token=auth.create_refresh_token(user.id),
        user=schemas.UserResponse.model_validate(user),
    )


@router.post(
    "/login",
    response_model=schemas.TokenResponse,
    summary="Se connecter"
)
def login(credentials: schemas.LoginRequest, db: Session = Depends(get_db)):
    """
    Connexion avec email + mot de passe.
    Retourne access_token et refresh_token.
    """
    user = db.query(models.User).filter(
        models.User.email == credentials.email
    ).first()

    # Message volontairement vague : ne pas révéler si c'est
    # l'email ou le mot de passe qui est incorrect (sécurité)
    if not user or not auth.verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce compte est désactivé"
        )

    return schemas.TokenResponse(
        access_token=auth.create_access_token(user.id),
        refresh_token=auth.create_refresh_token(user.id),
        user=schemas.UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=schemas.UserResponse,
    summary="Obtenir son profil"
)
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    """
    Route protégée — retourne le profil de l'utilisateur connecté.
    Aucun paramètre nécessaire : l'identité vient du token JWT.
    """
    return current_user