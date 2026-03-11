"""
Routeur API pour les postes
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.schemas.poste import PosteCreate, PosteUpdate, PosteResponse, PosteListResponse, PosteStatistics
from app.services.poste_service import PosteService

router = APIRouter(
    prefix="/postes",
    tags=["Postes"],
    responses={404: {"description": "Poste non trouvé"}},
)


@router.get("/", response_model=PosteListResponse, summary="Lister tous les postes")
def list_postes(
    skip: int = Query(0, ge=0, description="Nombre d'enregistrements à sauter"),
    limit: int = Query(100, ge=1, le=1000, description="Limite par page"),
    statut: Optional[str] = Query(None, description="Filtrer par statut"),
    departement: Optional[str] = Query(None, description="Filtrer par département"),
    db: Session = Depends(get_db)
):
    """
    Lister tous les postes avec pagination et filtres optionnels
    
    **Paramètres:**
    - skip: Nombre d'enregistrements à sauter (défaut: 0)
    - limit: Nombre d'enregistrements à retourner (défaut: 100, max: 1000)
    - statut: Filtrer par statut (actif, inactif, suspendu, obsolete)
    - departement: Filtrer par département
    """
    postes, total = PosteService.list_all(
        db=db,
        skip=skip,
        limit=limit,
        statut=statut,
        departement=departement
    )
    
    return PosteListResponse(
        total=total,
        page=skip // limit + 1,
        limit=limit,
        postes=postes
    )


@router.post("/", response_model=PosteResponse, status_code=201, summary="Créer un nouveau poste")
def create_poste(
    poste_create: PosteCreate,
    db: Session = Depends(get_db),
    current_user: str = "system"  # À remplacer par auth réelle
):
    """
    Créer un nouveau poste
    
    **Corps de la requête:**
    - nom: Nom du poste (requis, unique)
    - code_poste: Code unique du poste (optionnel)
    - description: Description du poste (optionnel)
    - departement: Département (optionnel)
    - niveau_hierarchique: Niveau hiérarchique 1-10 (optionnel)
    - niveau_grade: Grade du poste (optionnel)
    - salaire_min: Salaire minimum (optionnel)
    - salaire_max: Salaire maximum >= salaire_min (optionnel)
    - statut: État du poste (défaut: actif)
    - nombre_postes_disponibles: Nombre de postes (défaut: 1)
    - competences_requises: Liste de compétences (optionnel)
    """
    # Vérifier que le nom est unique
    if PosteService.get_by_nom(db, poste_create.nom):
        raise HTTPException(
            status_code=400,
            detail=f"Un poste avec le nom '{poste_create.nom}' existe déjà"
        )
    
    # Vérifier que le code est unique si fourni
    if poste_create.code_poste and PosteService.get_by_code(db, poste_create.code_poste):
        raise HTTPException(
            status_code=400,
            detail=f"Un poste avec le code '{poste_create.code_poste}' existe déjà"
        )
    
    poste = PosteService.create(db, poste_create, current_user)
    return poste


@router.get("/search", response_model=list[PosteResponse], summary="Rechercher des postes")
def search_postes(
    q: str = Query(..., min_length=1, description="Terme de recherche"),
    db: Session = Depends(get_db)
):
    """
    Rechercher des postes par nom, code ou description
    
    **Paramètres:**
    - q: Terme de recherche (requis)
    """
    postes = PosteService.search(db, q)
    return postes


@router.get("/statistics", response_model=PosteStatistics, summary="Statistiques des postes")
def get_statistics(db: Session = Depends(get_db)):
    """
    Obtenir les statistiques globales sur les postes
    """
    return PosteService.get_statistics(db)


@router.get("/departement/{departement}", response_model=list[PosteResponse], summary="Postes par département")
def get_by_departement(
    departement: str,
    db: Session = Depends(get_db)
):
    """
    Lister tous les postes d'un département
    
    **Paramètres:**
    - departement: Nom du département
    """
    postes = PosteService.get_by_departement(db, departement)
    return postes


@router.get("/available", response_model=list[PosteResponse], summary="Postes avec places libres")
def get_available_postes(db: Session = Depends(get_db)):
    """
    Lister les postes actifs avec des places libres
    """
    postes = PosteService.get_available_postes(db)
    return postes


@router.get("/active", response_model=list[PosteResponse], summary="Postes actifs")
def get_active_postes(db: Session = Depends(get_db)):
    """
    Lister tous les postes actifs
    """
    postes = PosteService.get_active_postes(db)
    return postes


@router.get("/{poste_id}", response_model=PosteResponse, summary="Récupérer un poste")
def get_poste(
    poste_id: int,
    db: Session = Depends(get_db)
):
    """
    Récupérer les détails d'un poste spécifique
    
    **Paramètres:**
    - poste_id: ID du poste (requis)
    """
    poste = PosteService.get_by_id(db, poste_id)
    if not poste:
        raise HTTPException(status_code=404, detail="Poste non trouvé")
    return poste


@router.put("/{poste_id}", response_model=PosteResponse, summary="Mettre à jour un poste")
def update_poste(
    poste_id: int,
    poste_update: PosteUpdate,
    db: Session = Depends(get_db),
    current_user: str = "system"  # À remplacer par auth réelle
):
    """
    Mettre à jour un poste
    
    **Paramètres:**
    - poste_id: ID du poste à mettre à jour
    
    **Corps de la requête:**
    - Tous les champs sont optionnels, seuls les champs fournis seront mis à jour
    """
    poste = PosteService.update(db, poste_id, poste_update, current_user)
    if not poste:
        raise HTTPException(status_code=404, detail="Poste non trouvé")
    return poste


@router.patch("/{poste_id}/pourvus", response_model=PosteResponse, summary="Mettre à jour le nombre de postes pourvus")
def update_pourvus(
    poste_id: int,
    nombre_pourvus: int = Query(..., ge=0, description="Nouveau nombre de postes pourvus"),
    db: Session = Depends(get_db)
):
    """
    Mettre à jour le nombre de postes occupés
    
    **Paramètres:**
    - poste_id: ID du poste
    - nombre_pourvus: Nouveau nombre (doit être <= nombre_postes_disponibles)
    """
    try:
        poste = PosteService.update_nombre_pourvus(db, poste_id, nombre_pourvus)
        if not poste:
            raise HTTPException(status_code=404, detail="Poste non trouvé")
        return poste
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{poste_id}", status_code=204, summary="Supprimer un poste")
def delete_poste(
    poste_id: int,
    db: Session = Depends(get_db)
):
    """
    Supprimer un poste
    
    **Paramètres:**
    - poste_id: ID du poste à supprimer
    """
    if not PosteService.delete(db, poste_id):
        raise HTTPException(status_code=404, detail="Poste non trouvé")
    return None
