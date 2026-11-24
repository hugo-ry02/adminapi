from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.docker_client import DockerAPIError, lire_conteneur, lister_conteneurs

app = FastAPI(title="API d'administration de conteneurs")


class Conteneur(BaseModel):
    id: str
    name: str
    image: str
    state: str


@app.get("/health", summary="Vérifie que l'API répond")
def sante():
    return {"status": "ok"}


@app.get(
    "/containers",
    summary="Liste les conteneurs gérés",
    response_model=list[Conteneur],
    responses={
        502: {"description": "API Docker injoignable"},
    },
)
def lister():
    try:
        return lister_conteneurs()
    except DockerAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.get(
    "/containers/{identifiant}",
    summary="Détail d'un conteneur géré",
    response_model=Conteneur,
    responses={
        404: {"description": "Conteneur inconnu ou non géré par l'API"},
        502: {"description": "API Docker injoignable"},
    },
)
def lire(identifiant: str):
    try:
        conteneur = lire_conteneur(identifiant)
    except DockerAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    if conteneur is None:
        raise HTTPException(status_code=404, detail="Conteneur introuvable")

    return conteneur