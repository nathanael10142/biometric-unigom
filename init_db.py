#!/usr/bin/env python3


import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.core.security import hash_password
from app.database import Base, SessionLocal, engine

import app.models.admin       # noqa: F401
import app.models.employee    # noqa: F401
import app.models.attendance  # noqa: F401

from app.models.admin import Admin
from app.models.employee import Employee


# ── Credentials admin par défaut ──────────────────────────────────────────────
DEFAULT_USERNAME = os.getenv("ADMIN_USERNAME", "nathanaelbatera@gmail.com")
DEFAULT_PASSWORD = os.getenv("ADMIN_PASSWORD", "nathanael1209ba")


# ── Données de seed ───────────────────────────────────────────────────────────
SEED_EMPLOYEES = [
    {
        "biometric_id": "00000001",
        "name": "Espoir Amani Bauma",
        "department": "Sécurité",
        "position": "Agent de Sécurité",
        "email": "e.amani@unigom.ac.cd",
        "phone": "+243 975 001 001",
        "is_active": True,
    },
    {
        "biometric_id": "00000002",
        "name": "Dr. Pascal Kambale Siviri",
        "department": "Faculté des Sciences",
        "position": "Professeur Titulaire",
        "email": "p.kambale@unigom.ac.cd",
        "phone": "+243 975 002 001",
        "is_active": True,
    },
    {
        "biometric_id": "00000003",
        "name": "Mme Solange Muhindo Katembo",
        "department": "Secrétariat Général",
        "position": "Secrétaire Principale",
        "email": "s.muhindo@unigom.ac.cd",
        "phone": "+243 975 003 001",
        "is_active": True,
    },
    {
        "biometric_id": "00000004",
        "name": "Jean-Baptiste Paluku Ndungo",
        "department": "Faculté de Droit",
        "position": "Assistant Académique",
        "email": "jb.paluku@unigom.ac.cd",
        "phone": "+243 975 004 001",
        "is_active": True,
    },
    {
        "biometric_id": "00000005",
        "name": "Ir. Gentille Masika Vivalya",
        "department": "Faculté Polytechnique",
        "position": "Chef de Travaux",
        "email": "g.masika@unigom.ac.cd",
        "phone": "+243 975 005 001",
        "is_active": True,
    },
    {
        "biometric_id": "00000006",
        "name": "Théodore Mwangaza Bisimwa",
        "department": "Informatique",
        "position": "Technicien Réseau",
        "email": "t.mwangaza@unigom.ac.cd",
        "phone": "+243 975 006 001",
        "is_active": True,
    },
    {
        "biometric_id": "00000007",
        "name": "Fiston Mawazo Kasereka",
        "department": "Administration",
        "position": "Comptable",
        "email": "f.mawazo@unigom.ac.cd",
        "phone": "+243 975 007 001",
        "is_active": True,
    },
    {
        "biometric_id": "00000008",
        "name": "Dr. Joëlle Byamungu Ndakala",
        "department": "Faculté de Médecine",
        "position": "Maître de Conférences",
        "email": "j.byamungu@unigom.ac.cd",
        "phone": "+243 975 008 001",
        "is_active": True,
    },
    {
        "biometric_id": "00000009",
        "name": "Fidèle Birungi Kambale",
        "department": "Bibliothèque",
        "position": "Bibliothécaire Principal",
        "email": "f.birungi@unigom.ac.cd",
        "phone": "+243 975 009 001",
        "is_active": True,
    },
    {
        "biometric_id": "00000010",
        "name": "Aline Mapendo Siku",
        "department": "Ressources Humaines",
        "position": "Chargée des RH",
        "email": "a.mapendo@unigom.ac.cd",
        "phone": "+243 975 010 001",
        "is_active": True,
    },
]


def init_db() -> None:
    print("\n  ══════════════════════════════════════════════════")
    print("    UNIGOM — Initialisation de la base de données")
    print("  ══════════════════════════════════════════════════")
    # we only create/localise tables in the *presence* database
    # (the prod DB is read‑only, used by agent sync).
    print(f"  PRESENCE_DB_URL : {settings.DATABASE_PRESENCE_URL}\n")

    # ── 1. Créer les tables ────────────────────────────────────────────────
    print("  [1/3] Création des tables …", end=" ", flush=True)
    Base.metadata.create_all(bind=engine)
    print("✓")

    db = SessionLocal()
    try:
        # ── 2. Compte admin ───────────────────────────────────────────────
        print("  [2/3] Compte administrateur …", end=" ", flush=True)
        existing_admin: Admin | None = (
            db.query(Admin).filter(Admin.username == DEFAULT_USERNAME).first()
        )
        if existing_admin is None:
            admin = Admin(
                username=DEFAULT_USERNAME,
                hashed_password=hash_password(DEFAULT_PASSWORD),
                is_active=True,
            )
            db.add(admin)
            db.commit()
            print("créé ✓")
            print(f"\n  ⚠  Compte par défaut :")
            print(f"      username : {DEFAULT_USERNAME}")
            print(f"      password : {DEFAULT_PASSWORD}")
            print("  ⚠  CHANGEZ CE MOT DE PASSE EN PRODUCTION !\n")
        else:
            print(f"existe déjà (id={existing_admin.id}) ✓")

        # ── 3. Seed des employés ──────────────────────────────────────────
        print("  [3/3] Insertion des employés …")
        created = 0
        skipped = 0
        for emp_data in SEED_EMPLOYEES:
            existing_emp: Employee | None = (
                db.query(Employee)
                .filter(Employee.biometric_id == emp_data["biometric_id"])
                .first()
            )
            if existing_emp is None:
                emp = Employee(**emp_data)
                db.add(emp)
                created += 1
                marker = "  ✚"
            else:
                skipped += 1
                marker = "  ─"
            status = "créé" if existing_emp is None else "existe"
            print(
                f"{marker} [{emp_data['biometric_id']}] "
                f"{emp_data['name']:<35} · {emp_data['position']:<30} "
                f"({status})"
            )
        if created:
            db.commit()

        print(f"\n  Résultat : {created} créé(s), {skipped} ignoré(s)")

    finally:
        db.close()

    print("\n  ══════════════════════════════════════════════════")
    print("  Initialisation terminée ✓")
    print("  ══════════════════════════════════════════════════\n")
    print("  Pour démarrer le backend :")
    print("    uvicorn app.main:app --reload --port 8000\n")


if __name__ == "__main__":
    init_db()
