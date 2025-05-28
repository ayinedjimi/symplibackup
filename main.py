"""
FastAPI UrBackup REST API Proxy.
Expose l'API UrBackup via FastAPI.
"""

from typing import Union, Dict, Any
from fastapi import FastAPI, HTTPException, Path
from pydantic import BaseModel
import urbackup_api

URBACKUP_URL = "http://127.0.0.1:55414/x"
URBACKUP_USER = "admin"
URBACKUP_PASS = "123"

app = FastAPI(title="UrBackup REST API Proxy")

def get_urbackup_server():
    """
    Initialise et retourne une instance du serveur UrBackup.
    """
    return urbackup_api.urbackup_server(URBACKUP_URL, URBACKUP_USER, URBACKUP_PASS)

def resolve_client(server, identifier: Union[str, int]) -> Dict[str, Any]:
    """
    Résout un client UrBackup à partir de son nom ou id.
    Retourne le dict client ou lève HTTPException 404 si inconnu.
    """
    clients = server.get_clients()  # pylint: disable=no-member
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
    raise HTTPException(status_code=404, detail=f"Client '{identifier}' not found")

# ===== Pydantic Models =====

class ClientIdentifier(BaseModel):
    """
    Schéma d'identifiant de client (nom ou id).
    """
    client: Union[str, int]

class BackupDeleteRequest(ClientIdentifier):
    """
    Requête de suppression de sauvegarde.
    """
    backup_id: int

class ClientCreateRequest(BaseModel):
    """
    Requête de création de client.
    """
    client: str

class ClientDeleteRequest(ClientIdentifier):
    """
    Requête de suppression de client.
    """
    pass

class ClientRenameRequest(BaseModel):
    """
    Requête de renommage de client.
    """
    old: Union[str, int]
    new: str

class ClientSettingChangeRequest(ClientIdentifier):
    """
    Requête de modification de paramètre client.
    """
    key: str
    new_value: str

class QuotaRequest(ClientIdentifier):
    """
    Requête de modification de quota.
    """
    quota_bytes: int

class BackupRequest(ClientIdentifier):
    """
    Requête de lancement de sauvegarde.
    """
    pass

# ===== ROUTES =====

@app.get("/status")
def get_status():
    """
    Récupère le statut du serveur UrBackup.
    """
    try:
        server = get_urbackup_server()
        return server.get_status()  # pylint: disable=no-member
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.get("/clients")
def get_clients():
    """
    Liste les clients connus du serveur UrBackup.
    """
    try:
        server = get_urbackup_server()
        clients = server.get_clients()  # pylint: disable=no-member
        return [{"name": c["name"], "id": c["id"]} for c in clients]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.get("/client/{client_identifier}")
def get_client_detail(client_identifier: Union[str, int] = Path(...)):
    """
    Récupère le détail d'un client.
    """
    try:
        server = get_urbackup_server()
        client = resolve_client(server, client_identifier)
        return client
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.post("/backup/full")
def launch_full_backup(req: BackupRequest):
    """
    Lance une sauvegarde complète fichiers pour un client.
    """
    try:
        server = get_urbackup_server()
        client = resolve_client(server, req.client)
        return server.start_full_file_backup(client["id"])  # pylint: disable=no-member
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.post("/backup/image")
def launch_image_backup(req: BackupRequest):
    """
    Lance une sauvegarde image complète pour un client.
    """
    try:
        server = get_urbackup_server()
        client = resolve_client(server, req.client)
        return server.start_full_image_backup(client["id"])  # pylint: disable=no-member
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.post("/backup/incremental")
def launch_incremental_backup(req: BackupRequest):
    """
    Lance une sauvegarde incrémentale fichiers pour un client.
    """
    try:
        server = get_urbackup_server()
        client = resolve_client(server, req.client)
        return server.start_incremental_file_backup(client["id"])  # pylint: disable=no-member
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.get("/backups/{client_identifier}")
def get_client_backups(client_identifier: Union[str, int] = Path(...)):
    """
    Liste les sauvegardes d'un client.
    """
    try:
        server = get_urbackup_server()
        client = resolve_client(server, client_identifier)
        return server.get_client_backups(client["id"])  # pylint: disable=no-member
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.post("/backup/delete")
def delete_backup(req: BackupDeleteRequest):
    """
    Supprime une sauvegarde pour un client.
    """
    try:
        server = get_urbackup_server()
        client = resolve_client(server, req.client)
        return server.delete_backup(client["id"], req.backup_id)  # pylint: disable=no-member
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.post("/client/create")
def create_client(req: ClientCreateRequest):
    """
    Crée un nouveau client.
    """
    try:
        server = get_urbackup_server()
        return server.add_client(req.client)  # pylint: disable=no-member
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.post("/client/delete")
def delete_client(req: ClientDeleteRequest):
    """
    Supprime un client.
    """
    try:
        server = get_urbackup_server()
        client = resolve_client(server, req.client)
        return server.remove_client(client["id"])  # pylint: disable=no-member
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.post("/client/rename")
def rename_client(req: ClientRenameRequest):
    """
    Renomme un client.
    """
    try:
        server = get_urbackup_server()
        client = resolve_client(server, req.old)
        return server.rename_client(client["id"], req.new)  # pylint: disable=no-member
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.get("/client/settings/{client_identifier}")
def get_client_settings(client_identifier: Union[str, int] = Path(...)):
    """
    Récupère les paramètres d'un client.
    """
    try:
        server = get_urbackup_server()
        client = resolve_client(server, client_identifier)
        return server.get_client_settings(client["id"])  # pylint: disable=no-member
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.post("/client/settings/change")
def set_client_setting(req: ClientSettingChangeRequest):
    """
    Modifie un paramètre pour un client.
    """
    try:
        server = get_urbackup_server()
        client = resolve_client(server, req.client)
        return server.change_client_setting(client["id"], req.key, req.new_value)  # pylint: disable=no-member
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.get("/client/authkey/{client_identifier}")
def get_client_authkey(client_identifier: Union[str, int] = Path(...)):
    """
    Récupère la clé d'authentification d'un client.
    """
    try:
        server = get_urbackup_server()
        client = resolve_client(server, client_identifier)
        return {"authkey": server.get_client_authkey(client["id"])}  # pylint: disable=no-member
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.get("/logs/{client_identifier}")
def get_client_logs(client_identifier: Union[str, int] = Path(...)):
    """
    Récupère les logs d'un client.
    """
    try:
        server = get_urbackup_server()
        client = resolve_client(server, client_identifier)
        return server.get_client_logs(client["id"])  # pylint: disable=no-member
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.get("/client/{client_identifier}/quota")
def get_client_quota(client_identifier: Union[str, int] = Path(...)):
    """
    Récupère le quota attribué à un client.
    """
    try:
        server = get_urbackup_server()
        client = resolve_client(server, client_identifier)
        settings = server.get_client_settings(client["id"])  # pylint: disable=no-member
        quota = settings.get("quota", {}).get("value")
        return {"client": client["name"], "quota_bytes": int(quota) if quota is not None else None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.post("/client/quota")
def set_client_quota(req: QuotaRequest):
    """
    Modifie le quota attribué à un client.
    """
    try:
        server = get_urbackup_server()
        client = resolve_client(server, req.client)
        result = server.change_client_setting(client["id"], "quota", str(req.quota_bytes))  # pylint: disable=no-member
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.get("/client/{client_identifier}/used_space")
def get_client_used_space(client_identifier: Union[str, int] = Path(...)):
    """
    Récupère l'espace utilisé par un client.
    """
    try:
        server = get_urbackup_server()
        client = resolve_client(server, client_identifier)
        backups = server.get_client_backups(client["id"])  # pylint: disable=no-member
        total_bytes = sum(b.get("total_bytes", 0) for b in backups if b.get("total_bytes") is not None)
        return {"client": client["name"], "used_bytes": total_bytes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
