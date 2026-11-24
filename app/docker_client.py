import json
import os
from urllib.parse import quote

import requests
from dotenv import load_dotenv

load_dotenv()

DOCKER_API_URL = os.environ.get("DOCKER_API_URL", "http://127.0.0.1:2375").rstrip("/")
LABEL_KEY = "adminapi.managed"
LABEL_VALUE = "true"
TIMEOUT = 10
TIMEOUT_ACTION = 30

session = requests.Session()


class DockerAPIError(Exception):
    pass


class ContainerNotFoundError(Exception):
    pass


class ContainerConflictError(Exception):
    pass


def lister_conteneurs() -> list[dict]:
    filtres = json.dumps({"label": [f"{LABEL_KEY}={LABEL_VALUE}"]})
    try:
        reponse = session.get(
            f"{DOCKER_API_URL}/containers/json",
            params={"all": "true", "filters": filtres},
            timeout=TIMEOUT,
        )
        reponse.raise_for_status()
    except requests.RequestException as exc:
        raise DockerAPIError(f"API Docker injoignable : {exc}") from exc

    conteneurs = []
    for item in reponse.json():
        noms = item.get("Names") or [""]
        conteneurs.append({
            "id": item["Id"],
            "name": noms[0].lstrip("/"),
            "image": item["Image"],
            "state": item["State"],
        })
    return conteneurs


def lire_conteneur(identifiant: str) -> dict | None:
    identifiant_encode = quote(identifiant, safe="")
    try:
        reponse = session.get(
            f"{DOCKER_API_URL}/containers/{identifiant_encode}/json",
            timeout=TIMEOUT,
        )
        if reponse.status_code == 404:
            return None
        reponse.raise_for_status()
    except requests.RequestException as exc:
        raise DockerAPIError(f"API Docker injoignable : {exc}") from exc

    detail = reponse.json()
    labels = detail.get("Config", {}).get("Labels") or {}
    if labels.get(LABEL_KEY) != LABEL_VALUE:
        return None

    return {
        "id": detail["Id"],
        "name": detail["Name"].lstrip("/"),
        "image": detail["Config"]["Image"],
        "state": detail["State"]["Status"],
    }


def _exiger_conteneur_gere(identifiant: str) -> dict:
    conteneur = lire_conteneur(identifiant)
    if conteneur is None:
        raise ContainerNotFoundError("Conteneur introuvable")
    return conteneur


def creer_conteneur(nom: str, image: str) -> dict:
    corps = {
        "Image": image,
        "Labels": {LABEL_KEY: LABEL_VALUE},
    }
    try:
        reponse = session.post(
            f"{DOCKER_API_URL}/containers/create",
            params={"name": nom},
            json=corps,
            timeout=TIMEOUT,
        )
        if reponse.status_code == 409:
            raise ContainerConflictError("Un conteneur portant ce nom existe déjà")
        if reponse.status_code == 404:
            raise DockerAPIError(f"Image absente sur l'hôte Docker : {image}")
        reponse.raise_for_status()

        identifiant = reponse.json()["Id"]
        demarrage = session.post(
            f"{DOCKER_API_URL}/containers/{identifiant}/start",
            timeout=TIMEOUT,
        )
        demarrage.raise_for_status()
    except (ContainerConflictError, DockerAPIError):
        raise
    except requests.RequestException as exc:
        raise DockerAPIError(f"API Docker injoignable : {exc}") from exc

    return _exiger_conteneur_gere(identifiant)
