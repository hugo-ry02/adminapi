import os
import secrets

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

load_dotenv()


def _lire_secret(nom: str) -> str:
    valeur = os.environ[nom]
    if not valeur:
        raise RuntimeError(f"La variable d'environnement {nom} est vide")
    return valeur


API_TOKEN_ADMIN = _lire_secret("API_TOKEN_ADMIN")
API_TOKEN_READER = _lire_secret("API_TOKEN_READER")
WEBHOOK_SECRET = _lire_secret("WEBHOOK_SECRET")

bearer = HTTPBearer(auto_error=False)


def role_de(token: HTTPAuthorizationCredentials | None) -> str:
    if token is not None:
        recu = token.credentials.encode()
        if secrets.compare_digest(recu, API_TOKEN_ADMIN.encode()):
            return "admin"
        if secrets.compare_digest(recu, API_TOKEN_READER.encode()):
            return "lecteur"
    raise HTTPException(
        status_code=401,
        detail="Token absent ou inconnu",
        headers={"WWW-Authenticate": "Bearer"},
    )


def exiger_lecture(token: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
    return role_de(token)


def exiger_admin(token: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
    role = role_de(token)
    if role != "admin":
        raise HTTPException(status_code=403, detail="Action réservée au rôle admin")
    return role