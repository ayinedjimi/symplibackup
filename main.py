"""
FastAPI Symplibackup REST API Proxy.
Expose l'API Symplibackup via FastAPI avec documentation Swagger personnalisée,
et protège l'accès à la documentation par un login/mot de passe.
"""
from typing import Union, Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Path as ApiPath, Query, Body, Depends, status
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
import urbackup_api
import pathlib
import os
import secrets

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

# Authentification HTTP Basic pour la documentation SEULEMENT
security = HTTPBasic()

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, "apiadmin")
    correct_password = secrets.compare_digest(credentials.password, "apiadmin@2025")
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiant ou mot de passe invalide",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html(auth: bool = Depends(authenticate)):
    """
    Documentation Swagger custom protégée par identifiant/mot de passe.
    """
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

# ==== ROUTES API (non protégées) ====

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

# ==== Les autres routes avancées sont aussi NON PROTÉGÉES ====
# (voir version précédente pour la liste complète)

# Fin du fichier