import os
import io
import json
import shutil
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
CREDENTIALS_PATH = os.path.join(BASE_DIR, "gdrive_credentials.json")

# Cargar el FILE_ID dinámicamente
FILE_ID = None

# 1. Intentar cargar desde st.secrets (Nube)
try:
    import streamlit as st
    if "gdrive" in st.secrets and "file_id" in st.secrets["gdrive"]:
        FILE_ID = st.secrets["gdrive"]["file_id"]
except:
    pass

# 2. Si no, intentar cargar desde gdrive_config.json local
if not FILE_ID:
    config_path = os.path.join(BASE_DIR, "gdrive_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                FILE_ID = config_data.get("file_id")
        except Exception as e:
            print(f"Error cargando gdrive_config.json: {e}")

# Estado de sincronización para visualización en la app
LAST_SYNC = {
    "status": "No iniciado",
    "download_time": None,
    "upload_time": None,
    "error": None
}

def asegurar_directorio_backups():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

def obtener_credenciales():
    """
    Intenta obtener credenciales desde st.secrets (Streamlit Cloud)
    o de lo contrario cae en el archivo gdrive_credentials.json local.
    """
    # 1. Intentar cargar desde st.secrets (Nube)
    try:
        import streamlit as st
        if "gdrive" in st.secrets:
            info = dict(st.secrets["gdrive"])
            # Asegurar saltos de línea en la clave privada
            if "private_key" in info:
                info["private_key"] = info["private_key"].replace("\\n", "\n")
            return service_account.Credentials.from_service_account_info(
                info,
                scopes=["https://www.googleapis.com/auth/drive"]
            )
    except Exception as e:
        print(f"Nota: No se usaron secretos de Streamlit: {e}")

    # 2. Si no, intentar cargar desde el archivo local
    if os.path.exists(CREDENTIALS_PATH):
        try:
            return service_account.Credentials.from_service_account_file(
                CREDENTIALS_PATH,
                scopes=["https://www.googleapis.com/auth/drive"]
            )
        except Exception as e:
            print(f"Error cargando archivo de credenciales local: {e}")
            
    return None

def realizar_copia_seguridad_local():
    """
    Genera un respaldo local automático con timestamp de la base de datos y archivos de configuración.
    También sube el archivo a Google Drive.
    """
    try:
        asegurar_directorio_backups()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        db_path = os.path.join(BASE_DIR, "gestion_planta.db")
        if os.path.exists(db_path):
            backup_db_path = os.path.join(BACKUP_DIR, f"gestion_planta_backup_{timestamp}.db")
            shutil.copy2(db_path, backup_db_path)
            
            # Mantener solo los últimos 15 respaldos locales para ahorrar espacio
            backups = sorted([os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR) if f.startswith("gestion_planta_backup_")])
            while len(backups) > 15:
                oldest = backups.pop(0)
                try: os.remove(oldest)
                except: pass
        
        # Sincronizar en la nube
        subir_db_a_gdrive()
        return True
    except Exception as e:
        print(f"Error en respaldo local: {e}")
        return False

def descargar_db_desde_gdrive():
    """
    Descarga gestion_planta.db desde Google Drive al directorio local.
    """
    if not FILE_ID or "PLACEHOLDER" in str(FILE_ID):
        err_msg = "ID de archivo de Google Drive no configurado (FILE_ID vacío)."
        print(f"Advertencia: {err_msg}")
        LAST_SYNC["status"] = "Error"
        LAST_SYNC["error"] = err_msg
        return False

    creds = obtener_credenciales()
    if not creds:
        err_msg = "No se encontraron credenciales válidas (st.secrets o gdrive_credentials.json)."
        print(f"Advertencia: {err_msg}")
        LAST_SYNC["status"] = "Error"
        LAST_SYNC["error"] = err_msg
        return False
    try:
        service = build("drive", "v3", credentials=creds)
        
        request = service.files().get_media(fileId=FILE_ID)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        db_path = os.path.join(BASE_DIR, "gestion_planta.db")
        with open(db_path, "wb") as f:
            f.write(fh.getvalue())
        
        print("Base de datos descargada con éxito de Google Drive.")
        LAST_SYNC["status"] = "OK"
        LAST_SYNC["download_time"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        LAST_SYNC["error"] = None
        return True
    except Exception as e:
        err_msg = f"Error de descarga: {str(e)}"
        print(err_msg)
        LAST_SYNC["status"] = "Error"
        LAST_SYNC["error"] = err_msg
        return False

def subir_db_a_gdrive():
    """
    Sube/actualiza el archivo gestion_planta.db en Google Drive.
    """
    if not FILE_ID or "PLACEHOLDER" in str(FILE_ID):
        err_msg = "ID de archivo de Google Drive no configurado (FILE_ID vacío)."
        print(f"Advertencia: {err_msg}")
        LAST_SYNC["status"] = "Error"
        LAST_SYNC["error"] = err_msg
        return False

    creds = obtener_credenciales()
    if not creds:
        err_msg = "No se encontraron credenciales válidas (st.secrets o gdrive_credentials.json)."
        print(f"Advertencia: {err_msg}")
        LAST_SYNC["status"] = "Error"
        LAST_SYNC["error"] = err_msg
        return False
    db_path = os.path.join(BASE_DIR, "gestion_planta.db")
    if not os.path.exists(db_path):
        err_msg = "No existe el archivo local gestion_planta.db para subir."
        print(f"Error: {err_msg}")
        LAST_SYNC["status"] = "Error"
        LAST_SYNC["error"] = err_msg
        return False
    try:
        service = build("drive", "v3", credentials=creds)
        
        media = MediaFileUpload(db_path, mimetype="application/x-sqlite3")
        service.files().update(
            fileId=FILE_ID,
            media_body=media
        ).execute()
        
        print("Base de datos subida y sincronizada en Google Drive con éxito.")
        LAST_SYNC["status"] = "OK"
        LAST_SYNC["upload_time"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        LAST_SYNC["error"] = None
        return True
    except Exception as e:
        err_msg = f"Error de subida: {str(e)}"
        print(err_msg)
        LAST_SYNC["status"] = "Error"
        LAST_SYNC["error"] = err_msg
        return False
