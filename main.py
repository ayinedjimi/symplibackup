"""
FastAPI Symplibackup REST API Proxy.
Expose l'API Symplibackup via FastAPI avec documentation Swagger personnalisée,
enrichi avec des routes avancées (sauvegardes, logs, groupes, planifications...).
Toutes les descriptions de routes sont en français.
"""
from typing import Union, Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Path as ApiPath, Query, Body
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import urbackup_api
import pathlib
import os

# Variables de connexion (à adapter si besoin)
URBACKUP_URL = "http://127.0.0.1:55414/x"
URBACKUP_USER = "admin"
URBACKUP_PASS = "123"

app = FastAPI(
    title="API Symplibackup",
    version="1.1",
    description="Documentation de l’API Symplibackup, proxy REST pour UrBackup.",
    docs_url=None,  # Désactive la route /docs par défaut pour la remplacer par Swagger custom
    redoc_url=None
)

# Swagger UI custom HTML (route /docs)
static_dir = pathlib.Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    openapi_url = app.openapi_url
    html_path = pathlib.Path(__file__).parent / "templates" / "swagger.html"
    if not html_path.exists():
        return HTMLResponse("<h1>swagger.html non trouvé</h1>", status_code=404)
    html_content = html_path.read_text(encoding="utf-8")
    html_content = html_content.replace("{{ openapi_url | tojson }}", f'"{openapi_url}"')
    return HTMLResponse(html_content)

# ==== Fonctions utilitaires ====

def get_urbackup_server():
    return urbackup_api.urbackup_server(URBACKUP_URL, URBACKUP_USER, URBACKUP_PASS)

def resolve_client(server, identifier: Union[str, int]) -> Dict[str, Any]:
    clients = server.get_clients()
    try:
        int_id = int(identifier)
        for c in clients:
            if c.get("id") == int_id:
                return c
    except (ValueError, TypeError):
        identifier = str(identifier)
        for c in clients:
            if c.get("name") == identifier:
                return c
    raise HTTPException(status_code=404, detail=f"Client '{identifier}' non trouvé")

def get_client_backup_by_id(server, client_id: int, backup_id: int):
    backups = server.get_client_backups(client_id)
    for backup in backups:
        if backup.get("id") == int(backup_id):
            return backup
    raise HTTPException(status_code=404, detail=f"Sauvegarde '{backup_id}' non trouvée pour le client {client_id}")

def get_backup_files(backup: Dict[str, Any]) -> List[str]:
    if "files" in backup and backup["files"]:
        return backup["files"]
    if "path" in backup and os.path.exists(backup["path"]):
        file_list = []
        for root, dirs, files in os.walk(backup["path"]):
            for f in files:
                file_list.append(os.path.relpath(os.path.join(root, f), backup["path"]))
        return file_list
    return []

# ==== Modèles Pydantic ====

class ClientIdentifier(BaseModel):
    client: Union[str, int]

class BackupRequest(ClientIdentifier):
    pass

class BackupDeleteRequest(ClientIdentifier):
    backup_id: int

class ClientCreateRequest(BaseModel):
    client: str

class ClientDeleteRequest(ClientIdentifier):
    pass

class ClientRenameRequest(BaseModel):
    old: Union[str, int]
    new: str

class ClientSettingChangeRequest(ClientIdentifier):
    key: str
    new_value: str

class QuotaRequest(ClientIdentifier):
    quota_bytes: int

# ==== ROUTES EXISTANTES EN FRANÇAIS ====

@app.get("/status", summary="Statut du serveur", description="Obtenir le statut global du serveur UrBackup.")
def get_status():
    try:
        server = get_urbackup_server()
        return server.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/clients", summary="Lister les clients", description="Lister tous les clients avec leurs noms et identifiants.")
def get_clients():
    try:
        server = get_urbackup_server()
        clients = server.get_clients()
        return [{"name": c["name"], "id": c["id"]} for c in clients]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/client/{client_identifier}", summary="Détail d'un client", description="Obtenir les détails d'un client par son identifiant ou son nom.")
def get_client_detail(client_identifier: Union[str, int] = ApiPath(..., description="Identifiant ou nom du client")):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, client_identifier)
        return client
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/backup/full", summary="Lancer une sauvegarde complète", description="Lancer une sauvegarde complète des fichiers pour un client.")
def launch_full_backup(req: BackupRequest):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, req.client)
        return server.start_full_file_backup(client["id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/backup/image", summary="Lancer une image disque", description="Lancer une sauvegarde complète d'image disque pour un client.")
def launch_image_backup(req: BackupRequest):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, req.client)
        return server.start_full_image_backup(client["id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/backup/incremental", summary="Lancer une sauvegarde incrémentale", description="Lancer une sauvegarde incrémentale des fichiers pour un client.")
def launch_incremental_backup(req: BackupRequest):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, req.client)
        return server.start_incremental_file_backup(client["id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/backups/{client_identifier}", summary="Lister les sauvegardes d'un client", description="Lister toutes les sauvegardes d'un client donné.")
def get_client_backups(client_identifier: Union[str, int] = ApiPath(..., description="Identifiant ou nom du client")):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, client_identifier)
        return server.get_client_backups(client["id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/backup/delete", summary="Supprimer une sauvegarde", description="Supprimer une sauvegarde spécifique d'un client donné.")
def delete_backup(req: BackupDeleteRequest):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, req.client)
        return server.delete_backup(client["id"], req.backup_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/client/create", summary="Créer un client", description="Créer un nouveau client UrBackup.")
def create_client(req: ClientCreateRequest):
    try:
        server = get_urbackup_server()
        return server.add_client(req.client)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/client/delete", summary="Supprimer un client", description="Supprimer un client UrBackup existant.")
def delete_client(req: ClientDeleteRequest):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, req.client)
        return server.remove_client(client["id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/client/rename", summary="Renommer un client", description="Renommer un client UrBackup existant.")
def rename_client(req: ClientRenameRequest):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, req.old)
        return server.rename_client(client["id"], req.new)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/client/settings/{client_identifier}", summary="Paramètres d'un client", description="Obtenir les paramètres d'un client.")
def get_client_settings(client_identifier: Union[str, int] = ApiPath(..., description="Identifiant ou nom du client")):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, client_identifier)
        return server.get_client_settings(client["id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/client/settings/change", summary="Changer un paramètre client", description="Modifier un paramètre spécifique d'un client.")
def set_client_setting(req: ClientSettingChangeRequest):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, req.client)
        return server.change_client_setting(client["id"], req.key, req.new_value)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/client/authkey/{client_identifier}", summary="Clé d'authentification du client", description="Obtenir la clé d'authentification pour un client.")
def get_client_authkey(client_identifier: Union[str, int] = ApiPath(..., description="Identifiant ou nom du client")):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, client_identifier)
        return {"authkey": server.get_client_authkey(client["id"])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logs/{client_identifier}", summary="Logs d'un client", description="Récupérer les logs d'un client donné.")
def get_client_logs(client_identifier: Union[str, int] = ApiPath(..., description="Identifiant ou nom du client")):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, client_identifier)
        return server.get_client_logs(client["id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/client/{client_identifier}/quota", summary="Quota d'un client", description="Consulter le quota de stockage attribué à un client.")
def get_client_quota(client_identifier: Union[str, int] = ApiPath(..., description="Identifiant ou nom du client")):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, client_identifier)
        settings = server.get_client_settings(client["id"])
        quota = settings.get("quota", {})
        return {"client": client["name"], "quota_bytes": int(quota.get("value")) if quota is not None else None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/client/quota", summary="Définir le quota d'un client", description="Définir ou modifier le quota de stockage pour un client.")
def set_client_quota(req: QuotaRequest):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, req.client)
        result = server.change_client_setting(client["id"], "quota", str(req.quota_bytes))
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/client/{client_identifier}/used_space", summary="Espace utilisé par un client", description="Afficher l'espace de stockage utilisé par les sauvegardes d'un client.")
def get_client_used_space(client_identifier: Union[str, int] = ApiPath(..., description="Identifiant ou nom du client")):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, client_identifier)
        backups = server.get_client_backups(client["id"])
        total_bytes = sum(b.get("total_bytes", 0) for b in backups if b.get("total_bytes") is not None)
        return {"client": client["name"], "used_bytes": total_bytes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==== NOUVELLES ROUTES AVANCÉES EN FRANÇAIS ====

@app.get("/backups/{client_identifier}/{backup_id}/files", summary="Lister les fichiers d'une sauvegarde", description="Lister tous les fichiers présents dans une sauvegarde donnée d'un client.")
def list_files_in_backup(client_identifier: Union[str, int] = ApiPath(..., description="Identifiant ou nom du client"), backup_id: int = ApiPath(..., description="Identifiant de la sauvegarde")):
    server = get_urbackup_server()
    client = resolve_client(server, client_identifier)
    backup = get_client_backup_by_id(server, client["id"], backup_id)
    files = get_backup_files(backup)
    return {"files": files}

@app.post("/backups/{client_identifier}/{backup_id}/restore", summary="Restaurer une sauvegarde", description="Démarrer la restauration d'une sauvegarde spécifique pour un client.")
def restore_backup(client_identifier: Union[str, int] = ApiPath(..., description="Identifiant ou nom du client"), backup_id: int = ApiPath(..., description="Identifiant de la sauvegarde")):
    server = get_urbackup_server()
    client = resolve_client(server, client_identifier)
    try:
        result = server.restore_backup(client["id"], backup_id)
        return {"status": "restauration lancée", "resultat": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/backups/{client_identifier}/latest", summary="Dernière sauvegarde d'un client", description="Obtenir la dernière sauvegarde réalisée pour un client donné.")
def get_latest_backup(client_identifier: Union[str, int] = ApiPath(..., description="Identifiant ou nom du client")):
    server = get_urbackup_server()
    client = resolve_client(server, client_identifier)
    backups = server.get_client_backups(client["id"])
    if not backups:
        raise HTTPException(status_code=404, detail="Aucune sauvegarde trouvée")
    latest = max(backups, key=lambda b: b.get("backup_time", 0))
    return latest

@app.get("/backups/{client_identifier}/{backup_id}/download", summary="Télécharger un fichier d'une sauvegarde", description="Télécharger un fichier spécifique depuis une sauvegarde d'un client.")
def download_file_from_backup(
    client_identifier: Union[str, int] = ApiPath(..., description="Identifiant ou nom du client"),
    backup_id: int = ApiPath(..., description="Identifiant de la sauvegarde"),
    filepath: str = Query(..., description="Chemin relatif du fichier à télécharger")
):
    server = get_urbackup_server()
    client = resolve_client(server, client_identifier)
    backup = get_client_backup_by_id(server, client["id"], backup_id)
    backup_path = backup.get("path")
    if not backup_path:
        raise HTTPException(status_code=404, detail="Chemin de sauvegarde introuvable")
    file_abs_path = os.path.abspath(os.path.join(backup_path, filepath))
    if not os.path.isfile(file_abs_path):
        raise HTTPException(status_code=404, detail="Fichier non trouvé")
    return FileResponse(file_abs_path, filename=os.path.basename(file_abs_path))

@app.get("/logs/server", summary="Logs du serveur", description="Récupérer les logs globaux du serveur UrBackup.")
def get_server_logs():
    log_path = "/var/log/urbackup.log"  # À adapter selon installation
    if not os.path.isfile(log_path):
        raise HTTPException(status_code=404, detail="Fichier log introuvable")
    def log_streamer():
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                yield line
    return StreamingResponse(log_streamer(), media_type="text/plain")

@app.get("/logs/{client_identifier}/search", summary="Recherche dans les logs d'un client", description="Rechercher une chaîne de caractères dans les logs d'un client.")
def search_logs_client(client_identifier: Union[str, int] = ApiPath(..., description="Identifiant ou nom du client"), query: str = Query(..., description="Texte ou expression à rechercher")):
    log_path = f"/var/log/urbackup_{client_identifier}.log"  # À adapter selon installation
    if not os.path.isfile(log_path):
        raise HTTPException(status_code=404, detail="Fichier log du client introuvable")
    results = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            if query.lower() in line.lower():
                results.append(line.strip())
    return {"results": results}

@app.get("/groups", summary="Lister les groupes", description="Lister tous les groupes de clients configurés.")
def list_groups():
    server = get_urbackup_server()
    try:
        groups = server.get_groups()
        return {"groups": groups}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/groups/{group_id}/clients", summary="Lister les clients d'un groupe", description="Afficher la liste des clients appartenant à un groupe donné.")
def list_clients_in_group(group_id: Union[str, int] = ApiPath(..., description="Identifiant du groupe")):
    server = get_urbackup_server()
    try:
        clients = server.get_group_clients(group_id)
        return {"clients": clients}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/groups/create", summary="Créer un groupe", description="Créer un nouveau groupe de clients.")
def create_group(group_name: str = Query(..., description="Nom du groupe à créer")):
    server = get_urbackup_server()
    try:
        group = server.create_group(group_name)
        return {"status": "groupe créé", "groupe": group}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/groups/{group_id}/delete", summary="Supprimer un groupe", description="Supprimer un groupe de clients par son identifiant.")
def delete_group(group_id: Union[str, int] = ApiPath(..., description="Identifiant du groupe")):
    server = get_urbackup_server()
    try:
        result = server.delete_group(group_id)
        return {"status": "groupe supprimé", "resultat": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/schedules", summary="Lister les tâches planifiées", description="Afficher toutes les tâches de sauvegarde planifiées.")
def list_schedules():
    server = get_urbackup_server()
    try:
        schedules = server.get_schedules()
        return {"schedules": schedules}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/schedules/create", summary="Créer une tâche planifiée", description="Créer une nouvelle tâche planifiée pour les sauvegardes.")
def create_schedule(schedule_data: dict = Body(..., description="Données de la tâche planifiée")):
    server = get_urbackup_server()
    try:
        schedule = server.create_schedule(schedule_data)
        return {"status": "tâche planifiée créée", "schedule": schedule}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/schedules/{schedule_id}/delete", summary="Supprimer une tâche planifiée", description="Supprimer une tâche planifiée par son identifiant.")
def delete_schedule(schedule_id: Union[str, int] = ApiPath(..., description="Identifiant de la tâche planifiée")):
    server = get_urbackup_server()
    try:
        result = server.delete_schedule(schedule_id)
        return {"status": "tâche planifiée supprimée", "resultat": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health", summary="Santé du proxy et du serveur", description="Vérifier l’état de santé du proxy FastAPI et du serveur UrBackup.")
def health_check():
    try:
        server = get_urbackup_server()
        status = server.get_status()
        return {"proxy": "ok", "urbackup": status}
    except Exception as e:
        return {"proxy": "ok", "urbackup": f"Erreur: {e}"}

@app.get("/version", summary="Version de l'API et du serveur", description="Obtenir la version de l’API Symplibackup et du serveur UrBackup.")
def get_version():
    try:
        server = get_urbackup_server()
        urbackup_version = server.get_server_version()
        return {"api_version": "1.1", "urbackup_version": urbackup_version}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/alerts", summary="Liste des alertes", description="Lister toutes les alertes ou notifications récentes (échecs, quotas dépassés, etc.).")
def list_alerts():
    server = get_urbackup_server()
    try:
        alerts = server.get_alerts()
        return {"alerts": alerts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/client/{client_identifier}/quota/history", summary="Historique du quota", description="Afficher l'historique d'utilisation du quota pour un client.")
def quota_history(client_identifier: Union[str, int] = ApiPath(..., description="Identifiant ou nom du client")):
    server = get_urbackup_server()
    client = resolve_client(server, client_identifier)
    try:
        history = server.get_quota_history(client["id"])
        return {"historique_quota": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/server/settings", summary="Paramètres globaux du serveur", description="Obtenir les paramètres globaux actuels du serveur UrBackup.")
def get_server_settings():
    server = get_urbackup_server()
    try:
        settings = server.get_server_settings()
        return {"settings": settings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/server/settings", summary="Modifier les paramètres du serveur", description="Modifier les paramètres globaux du serveur UrBackup.")
def update_server_settings(settings: dict = Body(..., description="Nouveaux paramètres globaux du serveur")):
    server = get_urbackup_server()
    try:
        result = server.update_server_settings(settings)
        return {"status": "paramètres serveur mis à jour", "resultat": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/client/{client_identifier}/activity", summary="Activité d'un client", description="Afficher l'historique des activités détaillées pour un client.")
def client_activity(client_identifier: Union[str, int] = ApiPath(..., description="Identifiant ou nom du client")):
    server = get_urbackup_server()
    client = resolve_client(server, client_identifier)
    try:
        activity = server.get_client_activity(client["id"])
        return {"activité": activity}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))