#!/usr/bin/env python
"""Utility to create an *administrator* user in the production HR database.

FastAPI's login endpoint consults ``app.models.prod.user_prod.UserProd`` in
``rhunigom__database_production``; this script transparently creates the
corresponding table if it does not already exist, hashes the password with
bcrypt and inserts a row with ``roleId=1`` and ``isActive=True``.

Usage
-----
$ python create_admin.py me@example.com s3cr3t

The script is idempotent: if a user with the given email already exists it
prints a message and exits without modifying anything.
"""
import sys

from app.core.security import hash_password
from app.database import ProdSessionLocal, prod_engine
from app.models.prod.user_prod import UserProd

# ensure the production schema is present; this is essentially the same as the
# corresponding Alembic migration but avoids needing to rerun the container
# build when doing one‑off user creation.
from app.database import ProdBase
ProdBase.metadata.create_all(prod_engine)


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python create_admin.py <email> <password>")
        sys.exit(1)

    email, password = sys.argv[1], sys.argv[2]

    db = ProdSessionLocal()
    try:
        existing = db.query(UserProd).filter(UserProd.email == email).first()
        if existing:
            print(f"user {email!r} already exists in production DB")
            return

        user = UserProd(
            email=email,
            password=hash_password(password),
            roleId=1,
            isActive=True,
        )
        db.add(user)
        db.commit()
        print(f"created production user {email!r}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
