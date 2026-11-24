from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Response
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
    redemarrer_conteneur,
    supprimer_conteneur,
)
from app.netbox_client import (
    NetBoxAPIError,
    creer_vm,
    maj_statut_vm,
    supprimer_vm,
)
from app.securite import exiger_admin, exiger_lecture, exiger_webhook_secret

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


class Alerte(BaseModel):
    alert: Literal["container_down"]
    container: str = Field(pattern=r"^[a-z][a-z0-9-]{1,30}$", examples=["web1"])


class ReponseWebhook(BaseModel):
    status: Literal["remediee", "ignoree"]
    container: str


@app.get("/health", summary="Vérifie que l'API répond")
def sante():
    return {"status": "ok"}


@app.get(
    "/containers",
    summary="Liste les conteneurs gérés",
    response_model=list[Conteneur],
    responses={
        401: {"description": "Token absent ou inconnu"},
        502: {"description": "API Docker injoignable"},
    },
)
def lister(role: str = Depends(exiger_lecture)):
    try:
        return lister_conteneurs()
    except DockerAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.get(
    "/containers/{identifiant}",
    summary="Détail d'un conteneur géré",
    response_model=Conteneur,
    responses={
        401: {"description": "Token absent ou inconnu"},
        404: {"description": "Conteneur inconnu ou non géré par l'API"},
        502: {"description": "API Docker injoignable"},
    },
)
def lire(identifiant: str, role: str = Depends(exiger_lecture)):
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
        401: {"description": "Token absent ou inconnu"},
        403: {"description": "Action réservée au rôle admin"},
        409: {"description": "Nom de conteneur déjà utilisé"},
        502: {"description": "API Docker ou NetBox injoignable"},
    },
)
def creer(demande: ConteneurACreer, role: str = Depends(exiger_admin)):
    try:
        conteneur = creer_conteneur(demande.name, demande.image)
    except ContainerConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except DockerAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    # Stratégie de compensation : si NetBox échoue après la création Docker, on supprime le conteneur créé.
    try:
        creer_vm(conteneur["name"])
    except NetBoxAPIError as exc:
        try:
            supprimer_conteneur(conteneur["id"])
        except (DockerAPIError, ContainerNotFoundError):
            pass
        raise HTTPException(status_code=502, detail=str(exc))

    return conteneur


@app.post(
    "/containers/{identifiant}/stop",
    summary="Arrête un conteneur géré",
    response_model=Conteneur,
    responses={
        401: {"description": "Token absent ou inconnu"},
        403: {"description": "Action réservée au rôle admin"},
        404: {"description": "Conteneur inconnu ou non géré par l'API"},
        409: {"description": "Conteneur déjà arrêté"},
        502: {"description": "API Docker ou NetBox injoignable"},
    },
)
def arreter(identifiant: str, role: str = Depends(exiger_admin)):
    try:
        conteneur = arreter_conteneur(identifiant)
    except ContainerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ContainerConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except DockerAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    try:
        maj_statut_vm(conteneur["name"], "offline")
    except NetBoxAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return conteneur


@app.post(
    "/containers/{identifiant}/start",
    summary="Démarre un conteneur géré",
    response_model=Conteneur,
    responses={
        401: {"description": "Token absent ou inconnu"},
        403: {"description": "Action réservée au rôle admin"},
        404: {"description": "Conteneur inconnu ou non géré par l'API"},
        409: {"description": "Conteneur déjà démarré"},
        502: {"description": "API Docker ou NetBox injoignable"},
    },
)
def demarrer(identifiant: str, role: str = Depends(exiger_admin)):
    try:
        conteneur = demarrer_conteneur(identifiant)
    except ContainerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ContainerConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except DockerAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    try:
        maj_statut_vm(conteneur["name"], "active")
    except NetBoxAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return conteneur


@app.delete(
    "/containers/{identifiant}",
    status_code=204,
    summary="Supprime un conteneur géré",
    responses={
        401: {"description": "Token absent ou inconnu"},
        403: {"description": "Action réservée au rôle admin"},
        404: {"description": "Conteneur inconnu ou non géré par l'API"},
        502: {"description": "API Docker ou NetBox injoignable"},
    },
)
def supprimer(identifiant: str, role: str = Depends(exiger_admin)):
    try:
        conteneur = supprimer_conteneur(identifiant)
    except ContainerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except DockerAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    try:
        supprimer_vm(conteneur["name"])
    except NetBoxAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return Response(status_code=204)


@app.post(
    "/webhooks/alerts",
    status_code=202,
    summary="Reçoit une alerte et redémarre le conteneur si nécessaire",
    response_model=ReponseWebhook,
    responses={
        401: {"description": "Secret de webhook absent ou faux"},
        404: {"description": "Conteneur inconnu ou non géré par l'API"},
        502: {"description": "API Docker ou NetBox injoignable"},
    },
)
def recevoir_alerte(
    alerte: Alerte,
    _: None = Depends(exiger_webhook_secret),
):
    try:
        conteneur = lire_conteneur(alerte.container)
    except DockerAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    if conteneur is None:
        raise HTTPException(status_code=404, detail="Conteneur introuvable")

    if conteneur["state"] == "running":
        return {"status": "ignoree", "container": conteneur["name"]}

    try:
        redemarrer_conteneur(conteneur["id"])
    except ContainerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except DockerAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    try:
        maj_statut_vm(conteneur["name"], "active")
    except NetBoxAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {"status": "remediee", "container": conteneur["name"]}   