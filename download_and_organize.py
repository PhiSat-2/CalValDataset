import os
import json
import shutil
import zipfile
from huggingface_hub import hf_hub_download

# Flag per attivare/disattivare l'unzipping
UNZIP_FLAG = False

# Percorso base del workspace
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # Sale da Coding/ a root

# Repository Hugging Face
REPO_ID = "lorenzopapa53/CalValDataset"

# Cartelle dei JSON
JSON_DIRS = ["geometry", "image_quality", "radiometry"]

def collect_session_ids():
    session_ids = set()
    for json_dir in JSON_DIRS:
        json_path = os.path.join(os.path.dirname(__file__), json_dir, f"{json_dir}_dataset.json")
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                data = json.load(f)
                for entry in data.get("entries", []):
                    session_id = entry.get("metadata", {}).get("session_id")
                    if session_id:
                        session_ids.add(session_id)
    print(f"Collected {len(session_ids)} unique session IDs.")
    return session_ids

def download_zips(session_ids):
    downloaded_files = []
    for session_id in session_ids:
        filename = f"{session_id}.zip"
        try:
            local_path = hf_hub_download(repo_id=REPO_ID, filename=filename, local_dir=BASE_DIR)
            downloaded_files.append(local_path)
            print(f"Downloaded {filename} to {local_path}")
        except Exception as e:
            print(f"Failed to download {filename}: {e}")
    return downloaded_files

def organize_files():
    for json_dir in JSON_DIRS:
        json_path = os.path.join(os.path.dirname(__file__), json_dir, f"{json_dir}_dataset.json")
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                data = json.load(f)
                for entry in data.get("entries", []):
                    category = entry.get("category")
                    location = entry.get("location")
                    session = entry.get("session")
                    session_id = entry.get("metadata", {}).get("session_id")
                    if category and location and session and session_id:
                        zip_filename = f"{session_id}.zip"
                        zip_path = os.path.join(BASE_DIR, zip_filename)
                        target_dir = os.path.join(BASE_DIR, category, location, session)
                        os.makedirs(target_dir, exist_ok=True)
                        target_zip_path = os.path.join(target_dir, zip_filename)
                        if os.path.exists(zip_path):
                            shutil.move(zip_path, target_zip_path)
                            print(f"Moved {zip_filename} to {target_dir}")
                            if UNZIP_FLAG:
                                with zipfile.ZipFile(target_zip_path, 'r') as zip_ref:
                                    zip_ref.extractall(target_dir)
                                print(f"Unzipped {zip_filename} in {target_dir}")
                        else:
                            print(f"ZIP file {zip_filename} not found for moving.")

if __name__ == "__main__":
    print("Starting download and organization process.")
    session_ids = collect_session_ids()
    downloaded_files = download_zips(session_ids)
    print("Download completed. Starting organization.")
    organize_files()
    print("Organization completed.")