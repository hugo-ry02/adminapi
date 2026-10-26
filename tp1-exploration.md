# TP 1 — Exploration des API Docker et NetBox

## 1. API Docker Engine (127.0.0.1:2375)

### Consultation de la version
- **Commande** : `curl -i -s http://127.0.0.1:2375/version`
- **Code HTTP** : 200 OK

### Liste de tous les conteneurs
- **Commande** : `curl -s "http://127.0.0.1:2375/containers/json?all=true"`
- **Code HTTP** : 200 OK
- **Observation** : Les conteneurs `web1` et `intrus` sont tous les deux présents.

### Liste filtrée sur le label adminapi.managed=true
- **Commande** : `curl -s --get http://127.0.0.1:2375/containers/json --data-urlencode 'all=true' --data-urlencode 'filters={"label":["adminapi.managed=true"]}'`
- **Code HTTP** : 200 OK
- **Observation** : Seul le conteneur `web1` apparaît.

### Détail du conteneur web1
- **Commande** : `curl -i -s http://127.0.0.1:2375/containers/web1/json`
- **Code HTTP** : 200 OK

### Changements d'état et idempotence
- **Arrêt initial de web1** : `curl -i -X POST http://127.0.0.1:2375/containers/web1/stop`
  - Code HTTP : 204 No Content
- **Deuxième arrêt de web1** : `curl -i -X POST http://127.0.0.1:2375/containers/web1/stop`
  - Code HTTP : 304 Not Modified *(le conteneur était déjà arrêté)*
- **Conteneur inexistant** : `curl -i -s http://127.0.0.1:2375/containers/inexistant/json`
  - Code HTTP : 404 Not Found
- **Redémarrage de web1** : `curl -i -X POST http://127.0.0.1:2375/containers/web1/start`
  - Code HTTP : 204 No Content

---

## 2. API NetBox (127.0.0.1:8080/api)

### Provisionnement du token d'administration
- **Route** : `POST /api/users/tokens/provision/`
- **Code HTTP** : 201 Created
- **Format du token** : Assemblage de `key` et `token` sous la forme `nbt_<key>.<token>`, transmis dans l'en-tête `Authorization: Bearer <token>`.

### Création du type de cluster "Docker"
- **Route** : `POST /api/virtualization/cluster-types/`
- **Code HTTP** : 201 Created

### Création du cluster "docker-local"
- **Route** : `POST /api/virtualization/clusters/`
- **Code HTTP** : 201 Created
- **Résultat** : Le cluster est visible dans l'interface web sous Virtualization > Clusters.