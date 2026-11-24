import os

import requests
from dotenv import load_dotenv

load_dotenv()

NETBOX_URL = os.environ.get("NETBOX_URL", "http://127.0.0.1:8080").rstrip("/")
NETBOX_TOKEN = os.environ["NETBOX_TOKEN"]
if not NETBOX_TOKEN:
    raise RuntimeError("La variable d'environnement NETBOX_TOKEN est vide")

CLUSTER_NAME = "docker-local"
TIMEOUT = 10

session = requests.Session()
session.headers.update({
    "Authorization": f"Bearer {NETBOX_TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json",
})


class NetBoxAPIError(Exception):
    pass


def obtenir_cluster_id(nom: str = CLUSTER_NAME) -> int:
    try:
        reponse = session.get(
            f"{NETBOX_URL}/api/virtualization/clusters/",
            params={"name": nom},
            timeout=TIMEOUT,
        )
        reponse.raise_for_status()
    except requests.RequestException as exc:
        raise NetBoxAPIError(f"API NetBox injoignable : {exc}") from exc

    resultats = reponse.json().get("results", [])
    if not resultats:
        raise NetBoxAPIError(f"Cluster NetBox introuvable : {nom}")
    return resultats[0]["id"]


def _trouver_vm(nom: str, cluster_id: int) -> dict | None:
    try:
        reponse = session.get(
            f"{NETBOX_URL}/api/virtualization/virtual-machines/",
            params={"name": nom, "cluster_id": cluster_id},
            timeout=TIMEOUT,
        )
        reponse.raise_for_status()
    except requests.RequestException as exc:
        raise NetBoxAPIError(f"API NetBox injoignable : {exc}") from exc

    resultats = reponse.json().get("results", [])
    return resultats[0] if resultats else None


def creer_vm(nom: str) -> None:
    cluster_id = obtenir_cluster_id()
    existante = _trouver_vm(nom, cluster_id)
    try:
        if existante is not None:
            reponse = session.patch(
                f"{NETBOX_URL}/api/virtualization/virtual-machines/{existante['id']}/",
                json={"status": "active"},
                timeout=TIMEOUT,
            )
        else:
            reponse = session.post(
                f"{NETBOX_URL}/api/virtualization/virtual-machines/",
                json={"name": nom, "cluster": cluster_id, "status": "active"},
                timeout=TIMEOUT,
            )
        reponse.raise_for_status()
    except requests.RequestException as exc:
        raise NetBoxAPIError(f"Impossible de créer la VM dans NetBox : {exc}") from exc


def maj_statut_vm(nom: str, statut: str) -> None:
    cluster_id = obtenir_cluster_id()
    vm = _trouver_vm(nom, cluster_id)
    try:
        if vm is None:
            reponse = session.post(
                f"{NETBOX_URL}/api/virtualization/virtual-machines/",
                json={"name": nom, "cluster": cluster_id, "status": statut},
                timeout=TIMEOUT,
            )
        else:
            reponse = session.patch(
                f"{NETBOX_URL}/api/virtualization/virtual-machines/{vm['id']}/",
                json={"status": statut},
                timeout=TIMEOUT,
            )
        reponse.raise_for_status()
    except requests.RequestException as exc:
        raise NetBoxAPIError(f"Impossible de mettre à jour la VM dans NetBox : {exc}") from exc


def supprimer_vm(nom: str) -> None:
    cluster_id = obtenir_cluster_id()
    vm = _trouver_vm(nom, cluster_id)
    if vm is None:
        return
    try:
        reponse = session.delete(
            f"{NETBOX_URL}/api/virtualization/virtual-machines/{vm['id']}/",
            timeout=TIMEOUT,
        )
        if reponse.status_code == 404:
            return
        reponse.raise_for_status()
    except requests.RequestException as exc:
        raise NetBoxAPIError(f"Impossible de supprimer la VM dans NetBox : {exc}") from exc