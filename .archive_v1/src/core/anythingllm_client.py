import os
import requests
import json
import sqlite3
from typing import List, Optional
from pathlib import Path

# Try to import path_manager, fallback for standalone testing
try:
    from src.core.path_manager import path_manager
    from src.core.logger import get_logger
except ImportError:
    from core.path_manager import path_manager
    from core.logger import get_logger

logger = get_logger("AnythingLLMClient", "anythingllm_client.log")

class AnythingLLMClient:
    def __init__(self, base_url: str = "http://localhost:3001"):
        self.base_url = base_url.rstrip("/")
        self.api_key = self._get_api_key()
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }

    def _get_api_key(self) -> str:
        """
        Retrieves the API key directly from the AnythingLLM SQLite database.
        This allows Zero-Conf access without manual setup.
        """
        try:
            # Construct path to DB: STORAGE_ROOT/anythingllm-storage/anythingllm.db
            storage_root = path_manager.get_storage_root()
            db_path = storage_root / "anythingllm-storage" / "anythingllm.db"
            
            if not db_path.exists():
                logger.error(f"AnythingLLM DB not found at {db_path}")
                return ""

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT secret FROM api_keys ORDER BY id ASC LIMIT 1")
            row = cursor.fetchone()
            conn.close()

            if row:
                return row[0]
            else:
                logger.warning("No API key found in AnythingLLM DB.")
                return ""
        except Exception as e:
            logger.error(f"Error retrieving API key from DB: {e}")
            return ""

    def ensure_auth(self):
        """Refreshes key if missing."""
        if not self.api_key:
            self.api_key = self._get_api_key()
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    def check_health(self) -> bool:
        """Simple ping to check if UI is reachable."""
        try:
            # There isn't a strict /health endpoint publicly documented that doesn't require auth sometimes,
            # but we can try fetching workspaces which is a read op.
            self.ensure_auth()
            r = requests.get(f"{self.base_url}/api/v1/workspaces", headers=self.headers, timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def create_workspace(self, name: str) -> Optional[str]:
        """
        Creates a workspace if it doesn't exist, otherwise returns the existing one's slug.
        Returns the workspace slug on success, None on error.
        """
        self.ensure_auth()
        try:
            # FIRST: Check if workspace already exists
            existing_slug = self.get_workspace_slug_by_name(name)
            if existing_slug:
                logger.info(f"✅ Workspace '{name}' already exists (slug: {existing_slug})")
                return existing_slug
            
            # SECOND: Create new workspace if it doesn't exist
            payload = {"name": name, "onboardingComplete": False}
            r = requests.post(f"{self.base_url}/api/v1/workspace/new", json=payload, headers=self.headers)
            
            if r.status_code == 200:
                data = r.json()
                slug = data.get("workspace", {}).get("slug")
                logger.info(f"✅ Workspace '{name}' created (slug: {slug})")
                return slug
            else:
                # If creation failed and workspace doesn't exist, it's an error
                logger.error(f"Failed to create workspace '{name}': {r.status_code} {r.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating workspace: {e}")
            return None

    def get_workspace_slug_by_name(self, name: str) -> Optional[str]:
        self.ensure_auth()
        try:
            r = requests.get(f"{self.base_url}/api/v1/workspaces", headers=self.headers)
            if r.status_code == 200:
                workspaces = r.json().get("workspaces", [])
                for ws in workspaces:
                    if ws.get("name") == name:
                        return ws.get("slug")
        except Exception as e:
            logger.error(f"Error fetching workspaces: {e}")
        return None

    def upload_document(self, file_path: str) -> Optional[str]:
        """Uploads a file and returns its location path (internal path)."""
        self.ensure_auth()
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                # Form data upload does not need Content-Type header usually (requests sets it)
                # But we need Auth
                r = requests.post(
                    f"{self.base_url}/api/v1/document/upload", 
                    files=files, 
                    headers={"Authorization": self.headers["Authorization"]} 
                )
                
            if r.status_code == 200:
                data = r.json()
                # Assuming response structure: { success: true, documents: [{ location: ... }] }
                # Or { location: ... } depending on version. 
                # Let's handle generic format based on standard
                if "documents" in data and len(data["documents"]) > 0:
                    return data["documents"][0].get("location")
                return data.get("location") # fallback
            else:
                logger.error(f"Upload failed for {file_path}: {r.text}")
                return None
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return None

    def update_embeddings(self, slug: str, adds: List[str], deletes: List[str] = []) -> bool:
        """Trigger embedding update."""
        self.ensure_auth()
        try:
            payload = {
                "adds": adds,
                "deletes": deletes,
                "similarityThreshold": 0.25 # Default
            }
            r = requests.post(f"{self.base_url}/api/v1/workspace/{slug}/update-embeddings", json=payload, headers=self.headers)
            return r.status_code == 200
        except Exception as e:
            logger.error(f"Error updating embeddings: {e}")
            return False

    def add_watched_folder(self, slug: str, folder_path: str) -> bool:
        """
        Add a local folder path to a workspace (creates a document_path in DB).
        This tells AnythingLLM to scan and index files from this folder.
        Returns True if successful.
        """
        self.ensure_auth()
        try:
            # AnythingLLM API endpoint for adding watched folders
            payload = {
                "path": folder_path,
                "accessibleToXAmount": 2  # Default: user and system
            }
            r = requests.post(
                f"{self.base_url}/api/v1/workspace/{slug}/watched-folder",
                json=payload,
                headers=self.headers
            )
            
            if r.status_code == 200:
                logger.info(f"✅ Watched folder added to workspace '{slug}': {folder_path}")
                return True
            elif r.status_code == 400:
                logger.warning(f"⚠️ Folder may already be watched: {folder_path}")
                return True  # Not an error, could already exist
            else:
                logger.error(f"Failed to add watched folder: {r.text}")
                return False
        except Exception as e:
            logger.error(f"Error adding watched folder: {e}")
            return False
