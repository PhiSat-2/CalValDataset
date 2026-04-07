import os
import json
import shutil
import zipfile
from huggingface_hub import hf_hub_download

# Flag per attivare/disattivare l'unzipping
UNZIP_FLAG = False

# Percorso base del workspace (cartella CalValSimeraDataset dove è lo script)
SCRIPT_DIR = os.path.dirname(__file__)

# Repository Hugging Face
REPO_ID = "lorenzopapa53/CalValSimeraDataset"

# Cartelle dei JSON
JSON_DIRS = ["geometry", "image_quality", "radiometry"]

def collect_session_mapping():
    """Raccoglie la mappatura session_id -> (category, location, session, target_dir)"""
    session_mapping = {}
    for json_dir in JSON_DIRS:
        json_path = os.path.join(SCRIPT_DIR, json_dir, f"{json_dir}_dataset.json")
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                data = json.load(f)
                for entry in data.get("entries", []):
                    category = entry.get("category")
                    location = entry.get("location")
                    session = entry.get("session")
                    session_id = entry.get("metadata", {}).get("session_id")
                    if category and location and session and session_id:
                        target_dir = os.path.join(SCRIPT_DIR, category, location, session)
                        session_mapping[session_id] = {
                            "category": category,
                            "location": location,
                            "session": session,
                            "target_dir": target_dir,
                            "filename": f"{session_id}.zip"
                        }
    print(f"Collected {len(session_mapping)} unique session IDs from JSON files.")
    return session_mapping

def download_zips(session_mapping):
    """Scarica i file ZIP direttamente nelle cartelle di destinazione"""
    downloaded_count = 0
    for session_id, info in session_mapping.items():
        filename = info["filename"]
        target_dir = info["target_dir"]
        
        # Crea la cartella di destinazione
        os.makedirs(target_dir, exist_ok=True)
        
        try:
            local_path = hf_hub_download(
                repo_id=REPO_ID, 
                filename=filename, 
                local_dir=target_dir, 
                repo_type="dataset"
            )
            print(f"Downloaded {filename} to {target_dir}")
            downloaded_count += 1
            
            # Pulisci la cache di Hugging Face nella cartella di destinazione
            cache_dir = os.path.join(target_dir, ".cache")
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir)
                print(f"Cleaned cache in {target_dir}")
            
            # Se UNZIP_FLAG è True, unzippa il file
            if UNZIP_FLAG:
                with zipfile.ZipFile(local_path, 'r') as zip_ref:
                    zip_ref.extractall(target_dir)
                print(f"Unzipped {filename} in {target_dir}")
        except Exception as e:
            print(f"Failed to download {filename}: {e}")
    
    return downloaded_count

if __name__ == "__main__":
    print("Starting download and organization process.")
    session_mapping = collect_session_mapping()
    download_count = download_zips(session_mapping)
    print(f"Download completed. {download_count}/{len(session_mapping)} files downloaded successfully.")