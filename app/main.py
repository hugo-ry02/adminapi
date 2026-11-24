from typing import Literal

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

from app.docker_client import (
    ContainerConflictError,
    ContainerNotFoundError,
    DockerAPIError,
    arreter_conteneur,
    creer_conteneur,
    demarrer_conteneur,
    lire_conteneur,
    lister_conteneurs,
    supprimer_conteneur,
)

app = FastAPI(title="API d'administration de conteneurs")

ImageAutorisee = Literal["nginx:alpine", "redis:alpine", "httpd:alpine"]


class Conteneur(BaseModel):
    id: str
    name: str
    image: str
    state: str


class ConteneurACreer(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9-]{1,30}$", examples=["web1"])
    image: ImageAutorisee


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


@app.post(
    "/containers",
    status_code=201,
    summary="Crée et démarre un conteneur",
    response_model=Conteneur,
    responses={
        409: {"description": "Nom de conteneur déjà utilisé"},
        502: {"description": "API Docker injoignable"},
    },
)
def creer(demande: ConteneurACreer):
    try:
        return creer_conteneur(demande.name, demande.image)
    except ContainerConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except DockerAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.post(
    "/containers/{identifiant}/stop",
    summary="Arrête un conteneur géré",
    response_model=Conteneur,
    responses={
        404: {"description": "Conteneur inconnu ou non géré par l'API"},
        409: {"description": "Conteneur déjà arrêté"},
        502: {"description": "API Docker injoignable"},
    },
)
def arreter(identifiant: str):
    try:
        return arreter_conteneur(identifiant)
    except ContainerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ContainerConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except DockerAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.post(
    "/containers/{identifiant}/start",
    summary="Démarre un conteneur géré",
    response_model=Conteneur,
    responses={
        404: {"description": "Conteneur inconnu ou non géré par l'API"},
        409: {"description": "Conteneur déjà démarré"},
        502: {"description": "API Docker injoignable"},
    },
)
def demarrer(identifiant: str):
    try:
        return demarrer_conteneur(identifiant)
    except ContainerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ContainerConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except DockerAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.delete(
    "/containers/{identifiant}",
    status_code=204,
    summary="Supprime un conteneur géré",
    responses={
        404: {"description": "Conteneur inconnu ou non géré par l'API"},
        502: {"description": "API Docker injoignable"},
    },
)
def supprimer(identifiant: str):
    try:
        supprimer_conteneur(identifiant)
    except ContainerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except DockerAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return Response(status_code=204)