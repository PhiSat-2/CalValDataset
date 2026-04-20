import os
import json
import requests
from pathlib import Path
from tqdm import tqdm
import time
from InsulaWorkflowClient import InsulaOpenIDConnect

# INSULA API
BASE_URL = "https://phisat2.insula.earth"
INSULA_API_BASE = f"{BASE_URL}/secure/api/v2.0"
INSULA_DOWNLOAD_ENDPOINT = f"{INSULA_API_BASE}/platformFiles"

# INSULA credentials
INSULA_USERNAME = "YOUR USERNAME"
INSULA_PASSWORD = "YOUR PASSWORD"

# OAuth2 Endpoints
AUTHORIZATION_ENDPOINT = "https://identity.insula.earth/realms/phisat2/protocol/openid-connect/auth"
TOKEN_ENDPOINT = "https://identity.insula.earth/realms/phisat2/protocol/openid-connect/token"
REDIRECT_URI = "http://localhost:9207/auth"
CLIENT_ID = "api-client"

# Global headers
HEADERS = None

# Base directory
BASE_DIR = os.path.dirname(__file__)

# JSON folders
JSON_DIRS = ["geometry", "image_quality", "radiometry"]


def authenticate():
    """Authenticates to INSULA using OpenID Connect and obtains the bearer token"""
    global HEADERS
    
    print("Authenticating with INSULA using OpenID Connect...")
    
    try:
        # Initialize OpenID Connect client
        insula_auth = InsulaOpenIDConnect(
            authorization_endpoint=AUTHORIZATION_ENDPOINT,
            token_endpoint=TOKEN_ENDPOINT,
            redirect_uri=REDIRECT_URI,
            client_id=CLIENT_ID
        )
        
        # Set credentials
        insula_auth.set_user_credentials(username=INSULA_USERNAME, password=INSULA_PASSWORD)
        
        # Get bearer token
        bearer = insula_auth.get_authorization_header()
        
        # Set headers with token
        HEADERS = {
            "Authorization": bearer,
            "Content-Type": "application/json"
        }
        
        print("✓ Authentication successful\n")
        return True
        
    except Exception as e:
        print(f"✗ Authentication failed: {e}\n")
        return False


def read_all_json_files():
    """Read all 3 JSON files and extract session_id data"""
    session_data = {}
    
    print("=" * 80)
    print("READING JSON FILES")
    print("=" * 80 + "\n")
    
    for json_dir in JSON_DIRS:
        json_path = os.path.join(BASE_DIR, json_dir, f"{json_dir}_dataset.json")
        
        print(f"Reading: {json_dir}_dataset.json")
        
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)
                    entries = data.get("entries", [])
                    count = 0
                    
                    for entry in entries:
                        session_id = entry.get("metadata", {}).get("session_id")
                        if session_id:
                            session_data[session_id] = {
                                "category": entry.get("category"),
                                "location": entry.get("location"),
                                "session": entry.get("session"),
                                "json_dir": json_dir
                            }
                            count += 1
                    
                    print(f"  ✓ Found {count} entries with session_id")
            except Exception as e:
                print(f"  ✗ Error reading file: {e}")
        else:
            print(f"  ✗ File not found: {json_path}")
        
        print()
    
    total = len(session_data)
    print(f"\n{'='*80}")
    print(f"TOTAL SESSION IDs FOUND: {total}")
    print(f"{'='*80}\n")
    
    return session_data


def search_product_on_insula(session_id):
    """Search for the product on INSULA via platformFiles search"""
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
            return {"found": False}
            
    except Exception as e:
        print(f"    ✗ Error searching: {e}")
        return {"found": False}


def download_product(session_id, product_id):
    """Download the product from INSULA"""
    download_url = f"{INSULA_DOWNLOAD_ENDPOINT}/{product_id}/dl"
    
    try:
        response = requests.get(download_url, headers=HEADERS, stream=True, timeout=60)
        response.raise_for_status()
        
        # Get total file size
        total_size = int(response.headers.get('content-length', 0))
        
        # Create temporary file in memory to store content
        zip_data = b''
        
        # Download file with progress bar
        if total_size > 0:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc=f"  Downloading", leave=False) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        zip_data += chunk
                        pbar.update(len(chunk))
        else:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    zip_data += chunk
        
        return True, zip_data
        
    except Exception as e:
        print(f"    ✗ Failed to download: {e}")
        return False, None


def save_zip_to_location(zip_data, session_id, category, location, session, json_dir):
    """Save the downloaded ZIP directly to the final location"""
    try:
        # Create correct folder structure: category/location/session/
        target_dir = os.path.join(BASE_DIR, json_dir, location, session)
        os.makedirs(target_dir, exist_ok=True)
        
        # Create filename based on session_id
        zip_filename = f"{session_id}.zip"
        target_zip_path = os.path.join(target_dir, zip_filename)
        
        # Write ZIP file to final location
        with open(target_zip_path, 'wb') as f:
            f.write(zip_data)
        
        # Get file size for display
        file_size_mb = len(zip_data) / (1024 * 1024)
        print(f"  ✓ Saved to: {os.path.relpath(target_zip_path)} ({file_size_mb:.2f} MB)")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error saving file: {e}")
        return False


def file_already_exists(category, location, session, session_id, json_dir):
    """Check if the ZIP file already exists in the target location"""
    target_dir = os.path.join(BASE_DIR, json_dir, location, session)
    zip_filename = f"{session_id}.zip"
    target_zip_path = os.path.join(target_dir, zip_filename)
    
    if os.path.exists(target_zip_path):
        file_size_mb = os.path.getsize(target_zip_path) / (1024 * 1024)
        print(f"  ⊘ Already downloaded ({file_size_mb:.2f} MB) - skipping")
        return True
    
    return False


def main():
    print("\n")
    print("╔════════════════════════════════════════════════════════════════════════════════╗")
    print("║              INSULA PRODUCT DOWNLOADER - ALL CATEGORIES                        ║")
    print("║                    Download one file at a time                                 ║")
    print("╚════════════════════════════════════════════════════════════════════════════════╝")
    print("\n")
    
    # Authenticate with INSULA
    if not authenticate():
        print("Failed to authenticate. Exiting.")
        return
    
    # Read all JSON files
    session_data = read_all_json_files()
    
    if not session_data:
        print("✗ No session IDs found. Exiting.")
        return
    
    # Download and organize files one by one
    print("=" * 80)
    print("DOWNLOADING PRODUCTS FROM INSULA")
    print("=" * 80 + "\n")
    
    downloaded = []
    not_found = []
    failed = []
    
    total = len(session_data)
    current = 0
    
    for session_id, info in session_data.items():
        current += 1
        category = info["category"]
        location = info["location"]
        session = info["session"]
        json_dir = info["json_dir"]
        
        print(f"[{current}/{total}] {session_id}")
        print(f"  Category: {category} | Location: {location} | Session: {session}")
        
        # Check if file already exists
        if file_already_exists(category, location, session, session_id, json_dir):
            downloaded.append({
                "session_id": session_id,
                "category": category,
                "location": location,
                "session": session
            })
            print()
            time.sleep(0.5)
            continue
        
        # Search for product on INSULA
        print("  Searching on INSULA...")
        search_result = search_product_on_insula(session_id)
        
        if search_result.get("found"):
            product_id = search_result.get("product_id")
            print(f"  ✓ Found on INSULA (Product ID: {product_id})")
            
            # Download the product
            print("  Downloading...")
            success, zip_data = download_product(session_id, product_id)
            
            if success and zip_data:
                print(f"  ✓ Downloaded successfully ({len(zip_data) / (1024*1024):.2f} MB)")
                
                # Save to final location
                if save_zip_to_location(zip_data, session_id, category, location, session, json_dir):
                    downloaded.append({
                        "session_id": session_id,
                        "category": category,
                        "location": location,
                        "session": session
                    })
                else:
                    failed.append(session_id)
            else:
                print(f"  ✗ Download failed")
                failed.append(session_id)
        else:
            print(f"  ✗ NOT FOUND on INSULA")
            not_found.append(session_id)
        
        print()
        
        # Avoid overloading the API
        time.sleep(1)
    
    # Print summary
    print("\n" + "=" * 80)
    print("DOWNLOAD SUMMARY")
    print("=" * 80)
    print(f"\n✓ Successfully downloaded and saved: {len(downloaded)}/{total} products\n")
    
    for item in downloaded:
        structure = f"{item['category']}/{item['location']}/{item['session']}"
        print(f"  • {item['session_id']}")
        print(f"    └─ {structure}/{item['session_id']}.zip")
    
    if not_found:
        print(f"\n✗ NOT FOUND on INSULA: {len(not_found)} products\n")
        for session_id in not_found:
            info = session_data[session_id]
            print(f"  • {session_id} ({info['category']})")
    
    if failed:
        print(f"\n✗ FAILED TO DOWNLOAD: {len(failed)} products\n")
        for session_id in failed:
            info = session_data[session_id]
            print(f"  • {session_id} ({info['category']})")
    
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
