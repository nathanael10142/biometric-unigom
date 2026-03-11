from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator


class PosteBase(BaseModel):
    """Schéma de base pour les données communes"""
    nom: str = Field(..., min_length=1, max_length=255, description="Nom du poste")
    code_poste: Optional[str] = Field(None, max_length=50, description="Code unique du poste")
    description: Optional[str] = Field(None, description="Description du poste")
    departement: Optional[str] = Field(None, max_length=255, description="Département")
    niveau_hierarchique: Optional[int] = Field(None, ge=1, le=10, description="Niveau hiérarchique")
    niveau_grade: Optional[str] = Field(None, max_length=100, description="Grade du poste")
    salaire_min: Optional[float] = Field(None, ge=0, description="Salaire minimum")
    salaire_max: Optional[float] = Field(None, ge=0, description="Salaire maximum")
    statut: str = Field(default="actif", description="État du poste")
    nombre_postes_disponibles: int = Field(default=1, ge=1, description="Nombre de postes disponibles")
    nombre_postes_pourvus: int = Field(default=0, ge=0, description="Nombre de postes occupés")
    competences_requises: Optional[List[str]] = Field(None, description="Compétences requises")
    diplomes_requis: Optional[str] = Field(None, max_length=255, description="Diplômes requis")
    experience_requise: Optional[int] = Field(None, ge=0, description="Années d'expérience requises")
    notes: Optional[str] = Field(None, description="Notes additionnelles")
    created_by: Optional[str] = Field(None, max_length=255, description="Créé par")
    updated_by: Optional[str] = Field(None, max_length=255, description="Modifié par")

    @field_validator('statut')
    @classmethod
    def validate_statut(cls, v):
        """Vérifier que le statut est valide"""
        valid_status = ['actif', 'inactif', 'suspendu', 'obsolete']
        if v not in valid_status:
            raise ValueError(f"Statut doit être l'un de: {', '.join(valid_status)}")
        return v

    @field_validator('salaire_max')
    @classmethod
    def validate_salaire_range(cls, v, info):
        """Vérifier que salaire_max >= salaire_min"""
        if v is not None and 'salaire_min' in info.data:
            if info.data['salaire_min'] and v < info.data['salaire_min']:
                raise ValueError("salaire_max doit être >= salaire_min")
        return v

    @field_validator('nombre_postes_pourvus')
    @classmethod
    def validate_postes_pourvus(cls, v, info):
        """Vérifier que pourvus <= disponibles"""
        if 'nombre_postes_disponibles' in info.data:
            if v > info.data['nombre_postes_disponibles']:
                raise ValueError("Postes pourvus ne peuvent pas dépasser les postes disponibles")
        return v


class PosteCreate(PosteBase):
    """Schéma pour créer un nouveau poste"""
    nom: str = Field(..., min_length=1, max_length=255)


class PosteUpdate(BaseModel):
    """Schéma pour mettre à jour un poste"""
    nom: Optional[str] = Field(None, min_length=1, max_length=255)
    code_poste: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    departement: Optional[str] = Field(None, max_length=255)
    niveau_hierarchique: Optional[int] = Field(None, ge=1, le=10)
    niveau_grade: Optional[str] = Field(None, max_length=100)
    salaire_min: Optional[float] = Field(None, ge=0)
    salaire_max: Optional[float] = Field(None, ge=0)
    statut: Optional[str] = None
    nombre_postes_disponibles: Optional[int] = Field(None, ge=1)
    nombre_postes_pourvus: Optional[int] = Field(None, ge=0)
    competences_requises: Optional[List[str]] = None
    diplomes_requis: Optional[str] = Field(None, max_length=255)
    experience_requise: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None
    updated_by: Optional[str] = Field(None, max_length=255)

    @field_validator('statut')
    @classmethod
    def validate_statut(cls, v):
        if v is not None:
            valid_status = ['actif', 'inactif', 'suspendu', 'obsolete']
            if v not in valid_status:
                raise ValueError(f"Statut doit être l'un de: {', '.join(valid_status)}")
        return v


class PosteResponse(PosteBase):
    """Schéma pour la réponse API"""
    id: int
    date_creation: datetime
    date_modification: datetime
    salaire_moyen: Optional[float] = None
    postes_libres: int
    pourcentage_pourvu: float
    is_active: bool
    is_available: bool

    class Config:
        from_attributes = True


class PosteListResponse(BaseModel):
    """Réponse pour la liste des postes"""
    total: int
    page: int
    limit: int
    postes: List[PosteResponse]


class PosteStatistics(BaseModel):
    """Statistiques sur les postes"""
    total_postes: int
    postes_actifs: int
    total_positions_disponibles: int
    total_positions_pourvues: int
    pourcentage_occupancy: float
    departements: dict
    niveaux_hierarchiques: dict
