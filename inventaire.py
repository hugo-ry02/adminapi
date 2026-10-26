import os
import sys
import requests

# 1. Configuration depuis l'environnement
DOCKER_URL = os.environ.get("DOCKER_API_URL", "http://127.0.0.1:2375")
NETBOX_URL = os.environ.get("NETBOX_URL", "http://127.0.0.1:8080")
NETBOX_TOKEN = os.environ.get("NETBOX_TOKEN")

if not NETBOX_TOKEN:
    sys.exit("Erreur : la variable d'environnement NETBOX_TOKEN est absente.")

# 2. Création d'une session HTTP
session = requests.Session()

# 3. Récupération des conteneurs avec gestion d'erreur (requis par le TP)
try:
    reponse = session.get(f"{DOCKER_URL}/containers/json", params={"all": "true"}, timeout=5)
    reponse.raise_for_status()
except requests.RequestException as err:
    # Code de retour non nul si Docker ne répond pas
    sys.exit(f"Erreur lors de la communication avec l'API Docker : {err}")

conteneurs = reponse.json()
print(f"Nombre total de conteneurs détectés : {len(conteneurs)}")

resultats_conteneurs = []

for c in conteneurs:
    c_id = c["Id"]
    nom = c["Names"][0].lstrip("/") # Supprime le slash initial (ex: '/web1' -> 'web1')
    image = c["Image"]
    etat = c["State"]
    
    cpu_val = None
    mem_val = None
    
    # On ne calcule les métriques que si le conteneur est démarré
    if etat == "running":
        try:
            r_stats = session.get(f"{DOCKER_URL}/containers/{c_id}/stats", params={"stream": "false"}, timeout=5)
            stats = r_stats.json()
            
            cpu = stats["cpu_stats"]
            avant = stats["precpu_stats"]
            delta_cpu = cpu["cpu_usage"]["total_usage"] - avant["cpu_usage"]["total_usage"]
            delta_systeme = cpu["system_cpu_usage"] - avant.get("system_cpu_usage", 0)
            nb_cpus = cpu.get("online_cpus", 1)
            
            cpu_val = round((delta_cpu / delta_systeme * nb_cpus * 100), 2) if delta_systeme > 0 else 0.0
            mem_val = round(stats["memory_stats"]["usage"] / (1024 * 1024), 2)
        except Exception as e:
            print(f"Impossible de récupérer les stats pour {nom}: {e}")

    resultats_conteneurs.append({
        "id": c_id,
        "nom": nom,
        "image": image,
        "etat": etat,
        "cpu_pourcent": cpu_val,
        "memoire_mo": mem_val
    })
    
    print(f"- {nom} ({etat}) : CPU={cpu_val}%, RAM={mem_val} Mo")

    import json
from datetime import datetime, timezone

# --- Interrogation de NetBox ---
headers_netbox = {
    "Authorization": f"Bearer {NETBOX_TOKEN}",
    "Accept": "application/json"
}

try:
    # 1. Version de NetBox
    r_status = session.get(f"{NETBOX_URL}/api/status/", headers=headers_netbox, timeout=5)
    r_status.raise_for_status()
    version_netbox = r_status.json().get("netbox-version")
    
    # 2. Pagination des types d'objets
    url_pagination = f"{NETBOX_URL}/api/core/object-types/?limit=50"
    total_types_objets = 0
    total_attendu = None

    while url_pagination:
        r_page = session.get(url_pagination, headers=headers_netbox, timeout=5)
        r_page.raise_for_status()
        data_page = r_page.json()
        
        if total_attendu is None:
            total_attendu = data_page.get("count")
            
        total_types_objets += len(data_page.get("results", []))
        url_pagination = data_page.get("next") # Devient None à la dernière page

    print(f"\nNetBox version : {version_netbox}")
    print(f"Types d'objets NetBox comptés : {total_types_objets} (Total annoncé : {total_attendu})")

except requests.RequestException as err:
    sys.exit(f"Erreur lors de la communication avec NetBox : {err}")

# --- Écriture du fichier inventaire.json ---
donnees_inventaire = {
    "date": datetime.now(timezone.utc).isoformat(),
    "docker": {
        "total_conteneurs": len(resultats_conteneurs),
        "conteneurs": resultats_conteneurs
    },
    "netbox": {
        "version": version_netbox,
        "types_objets_total": total_types_objets
    }
}

with open("inventaire.json", "w", encoding="utf-8") as f:
    json.dump(donnees_inventaire, f, indent=2, ensure_ascii=False)

print("\nInventaire sauvegardé avec succès dans inventaire.json !")