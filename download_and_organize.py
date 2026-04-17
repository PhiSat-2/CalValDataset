import os
import json
import shutil
import zipfile
import requests
from pathlib import Path
from tqdm import tqdm
import time
from InsulaWorkflowClient import InsulaOpenIDConnect

# Flag per attivare/disattivare l'unzipping
UNZIP_FLAG = True

# Percorso base del workspace
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# API INSULA
BASE_URL = "https://phisat2.insula.earth"
INSULA_API_BASE = f"{BASE_URL}/secure/api/v2.0"
INSULA_SEARCH_ENDPOINT = f"{INSULA_API_BASE}/search"
INSULA_DOWNLOAD_ENDPOINT = f"{INSULA_API_BASE}/platformFiles"

# Credenziali INSULA
INSULA_USERNAME = "YOUR USERNAME"
INSULA_PASSWORD = "YOUR PSW"

# OAuth2 Endpoints
AUTHORIZATION_ENDPOINT = "https://identity.insula.earth/realms/phisat2/protocol/openid-connect/auth"
TOKEN_ENDPOINT = "https://identity.insula.earth/realms/phisat2/protocol/openid-connect/token"
REDIRECT_URI = "http://localhost:9207/auth"
CLIENT_ID = "api-client"

# Header globale
HEADERS = None

# Cartelle dei JSON
JSON_DIRS = ["geometry", "image_quality", "radiometry"]


def authenticate():
    """Autentica su INSULA usando OpenID Connect e ottiene il bearer token"""
    global HEADERS
    
    print("Authenticating with INSULA using OpenID Connect...")
    
    try:
        # Inizializza il client OpenID Connect
        insula_auth = InsulaOpenIDConnect(
            authorization_endpoint=AUTHORIZATION_ENDPOINT,
            token_endpoint=TOKEN_ENDPOINT,
            redirect_uri=REDIRECT_URI,
            client_id=CLIENT_ID
        )
        
        # Imposta le credenziali
        insula_auth.set_user_credentials(username=INSULA_USERNAME, password=INSULA_PASSWORD)
        
        # Ottieni il bearer token
        bearer = insula_auth.get_authorization_header()
        
        # Imposta gli header con il token
        HEADERS = {
            "Authorization": bearer,
            "Content-Type": "application/json"
        }
        
        print("✓ Authentication successful")
        return True
        
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        return False


def collect_session_ids():
    """Raccogli tutti i session_id dai file JSON con le loro informazioni"""
    session_data = {}
    
    for json_dir in JSON_DIRS:
        json_path = os.path.join(
            os.path.dirname(__file__), 
            json_dir, 
            f"{json_dir}_dataset.json"
        )
        
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                data = json.load(f)
                for entry in data.get("entries", []):
                    session_id = entry.get("metadata", {}).get("session_id")
                    if session_id:
                        session_data[session_id] = {
                            "category": entry.get("category"),
                            "location": entry.get("location"),
                            "session": entry.get("session"),
                            "json_dir": json_dir
                        }
    
    print(f"✓ Collected {len(session_data)} unique session IDs")
    return session_data


def collect_image_quality_session_ids():
    """Raccogli solo i session_id dal file image_quality_dataset.json (TEST)"""
    session_data = {}
    
    json_path = os.path.join(
        os.path.dirname(__file__), 
        "image_quality", 
        "image_quality_dataset.json"
    )
    
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            data = json.load(f)
            for entry in data.get("entries", []):
                session_id = entry.get("metadata", {}).get("session_id")
                if session_id:
                    session_data[session_id] = {
                        "category": entry.get("category"),
                        "location": entry.get("location"),
                        "session": entry.get("session"),
                        "json_dir": "image_quality"
                    }
    
    print(f"✓ Collected {len(session_data)} session IDs from image_quality_dataset.json")
    return session_data


def search_product_on_insula(session_id):
    """Cerca il prodotto su INSULA tramite platformFiles search"""
    params = {
        "filter": session_id,
        "resultsPerPage": 1
    }
    
    try:
        search_url = f"{INSULA_API_BASE}/platformFiles/search/parametricFind"
        response = requests.get(search_url, params=params, headers=HEADERS, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            files = data.get("_embedded", {}).get("platformFiles", [])
            
            if files:
                # Prendi il primo risultato
                product = files[0]
                product_id = product.get("id")
                
                return {
                    "found": True,
                    "product_id": product_id,
                    "filename": product.get("filename")
                }
            else:
                return {"found": False}
        else:
            print(f"    ✗ Search failed (Status: {response.status_code})")
            return {"found": False}
            
    except requests.exceptions.RequestException as e:
        print(f"    ✗ Error searching: {e}")
        return {"found": False}


def download_product(session_id, product_id, temp_dir):
    """Scarica il prodotto da INSULA in una cartella temporanea"""
    download_url = f"{INSULA_DOWNLOAD_ENDPOINT}/{product_id}/dl"
    
    try:
        response = requests.get(download_url, headers=HEADERS, stream=True, timeout=30)
        response.raise_for_status()
        
        # Prepara il percorso di salvataggio temporaneo
        os.makedirs(temp_dir, exist_ok=True)
        zip_path = os.path.join(temp_dir, f"{session_id}.zip")
        
        # Scarica il file con progress bar
        total_size = int(response.headers.get('content-length', 0))
        
        with open(zip_path, 'wb') as f:
            if total_size > 0:
                with tqdm(total=total_size, unit='B', unit_scale=True, desc=f"  Downloading", leave=False) as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
            else:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        
        return True, zip_path
        
    except requests.exceptions.RequestException as e:
        print(f"    ✗ Failed to download: {e}")
        return False, None


def cleanup_temp_downloads(temp_dir):
    """Elimina la cartella temporanea dei download con retry logic"""
    if not os.path.exists(temp_dir):
        return
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Piccolo delay per garantire che i file non siano più in uso
            time.sleep(0.5)
            shutil.rmtree(temp_dir)
            print(f"✓ Cleaned up temporary folder: {os.path.relpath(temp_dir)}")
            return
        except PermissionError:
            retry_count += 1
            if retry_count < max_retries:
                time.sleep(1)  # Aspetta prima di riprovare
            else:
                print(f"⚠ Could not delete temporary folder (permission denied): {os.path.relpath(temp_dir)}")
        except Exception as e:
            print(f"⚠ Failed to clean up temporary folder: {e}")
            return


def unzip_and_organize(zip_path, category, location, session, json_dir):
    """Decompatta il file ZIP nella struttura category/location/session/ e elimina il ZIP se riuscito"""
    try:
        # Crea la struttura di cartelle corretta: category/location/session/
        target_dir = os.path.join(
            os.path.dirname(__file__),
            json_dir,
            location,
            session
        )
        
        os.makedirs(target_dir, exist_ok=True)
        
        # Decompatta il ZIP
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(target_dir)
        
        print(f"  ✓ Extracted to: {os.path.relpath(target_dir)}")
        
        # Se l'unzip è andato a buon fine, elimina il ZIP
        try:
            os.remove(zip_path)
            print(f"  ✓ Deleted ZIP file")
        except Exception as e:
            print(f"  ⚠ Failed to delete ZIP: {e}")
        
        return True
        
    except zipfile.BadZipFile:
        print(f"  ✗ Invalid zip file: {zip_path}")
        return False
    except Exception as e:
        print(f"  ✗ Error during extraction: {e}")
        return False


def organize_files(session_data):
    """Scarica, decompatta e organizza i file"""
    print("\n" + "="*80)
    print("DOWNLOADING PRODUCTS FROM INSULA")
    print("="*80 + "\n")
    
    downloaded = []
    not_found = []
    
    total = len(session_data)
    current = 0
    
    # Cartella temporanea per i download
    temp_dir = os.path.join(os.path.dirname(__file__), ".temp_downloads")
    
    for session_id, info in session_data.items():
        current += 1
        category = info["category"]
        location = info["location"]
        session = info["session"]
        json_dir = info["json_dir"]
        
        print(f"[{current}/{total}] {session_id}")
        print(f"  Category: {category} | Location: {location} | Session: {session}")
        
        # Cerca il prodotto su INSULA
        search_result = search_product_on_insula(session_id)
        
        if search_result.get("found"):
            product_id = search_result.get("product_id")
            print(f"  ✓ Found on INSULA (Product ID: {product_id})")
            
            # Scarica il prodotto
            success, zip_path = download_product(session_id, product_id, temp_dir)
            
            if success:
                print(f"  ✓ Downloaded successfully")
                
                # Decompatta e organizza
                if UNZIP_FLAG:
                    if unzip_and_organize(zip_path, category, location, session, json_dir):
                        downloaded.append({
                            "session_id": session_id,
                            "category": category,
                            "location": location,
                            "session": session
                        })
                    else:
                        not_found.append(session_id)
                else:
                    downloaded.append({
                        "session_id": session_id,
                        "category": category,
                        "location": location,
                        "session": session
                    })
            else:
                not_found.append(session_id)
        else:
            print(f"  ✗ NOT FOUND on INSULA")
            not_found.append(session_id)
        
        print()
        
        # Evita di sovraccaricare l'API
        time.sleep(1)
    
    # Pulisci la cartella temporanea
    cleanup_temp_downloads(temp_dir)
    
    # Stampa il riepilogo
    print("="*80)
    print("DOWNLOAD & EXTRACTION SUMMARY")
    print("="*80)
    print(f"\n✓ Successfully processed: {len(downloaded)} products\n")
    
    for item in downloaded:
        structure = f"{item['category']}/{item['location']}/{item['session']}"
        print(f"  • {item['session_id']}")
        print(f"    └─ {structure}/")
    
    if not_found:
        print(f"\n✗ FAILED/NOT FOUND: {len(not_found)} products\n")
        for session_id in not_found:
            info = session_data[session_id]
            print(f"  • {session_id} ({info['category']})")
    
    print(f"\nUNZIP MODE: {'ENABLED' if UNZIP_FLAG else 'DISABLED'}")
    print("="*80 + "\n")
    
    return downloaded, not_found


def main():
    print("\n")
    print("╔════════════════════════════════════════════════════════════════════════════════╗")
    print("║              INSULA PRODUCT DOWNLOADER - IMAGE_QUALITY TEST                    ║")
    print("╚════════════════════════════════════════════════════════════════════════════════╝")
    print("\n")
    
    # Autentica su INSULA
    if not authenticate():
        print("Failed to authenticate. Exiting.")
        return
    
    print()
    
    # Raccogli i session_id solo da image_quality (TEST)
    session_data = collect_image_quality_session_ids()
    print()
    
    if not session_data:
        print("✗ No session IDs found in image_quality_dataset.json")
        return
    
    # Scarica, decompatta e organizza
    downloaded, not_found = organize_files(session_data)


if __name__ == "__main__":
    main()
