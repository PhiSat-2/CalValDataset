# CalVal Dataset

## Description

This repository contains the **CalVal Dataset**, a collection of data for calibration and validation (Cal/Val) of the PhiSat2 satellite. The data is organized into three main categories: `geometry`, `image_quality`, and `radiometry`. Each category includes subfolders for locations and sessions, containing ZIP files of satellite products.

The dataset is accessed and downloaded directly through the official **INSULA PHISAT-2 API**.  
Users must first register to the INSULA platform and then provide their credentials in the download script to retrieve the data.

## Data Structure

The dataset structure is as follows:

```
CalValDataset/
├── download_and_organize.py    # Python script to download and organize data
├── requirements.txt            # Required Python dependencies
├── example.py                  # Example code 
├── geometry/
|   ├── [location]/
|   │   └── [session]/
|   │       └── [file.zip]          # Organized ZIP files
│   └── geometry_dataset.json   # Metadata for geometry category
├── image_quality/
|   ├── [location]/
|   │   └── [session]/
|   │       └── [file.zip]          # Organized ZIP files
│   └── image_quality_dataset.json   # Metadata for image_quality category
├── radiometry/
|   ├── [location]/
|   │   └── [session]/
|   │       └── [file.zip]          # Organized ZIP files
│   └── radiometry_dataset.json   # Metadata for radiometry category
├── LICENSE 
└── README.md                  
```

Each JSON file in the `ProjectFolder/geometry/`, `ProjectFolder/image_quality/`, and `ProjectFolder/radiometry/` folders contains metadata for the products, including:
- `session_id`: Unique identifier corresponding to the PhiSat2 product (ZIP file).
- `category`: Data category (geometry, image_quality, radiometry).
- `location`: Location of the captured PhiSat2 product. 
- `session`: If multiple acquisitions are present in the same location 
- Other metadata such as bounding box, resolution, coordinates, etc.

## PHISAT‑2 Reference Sites

The table below lists all PHISAT‑2 reference sites included in the dataset, together with their geographic location and the availability of **PHISAT‑2 Level‑1 ZIP files**.

✔︎ = ZIP files available  
✘ = no ZIP files available

| Site | Country | Latitude | Longitude | DATA | Sessions |
|------|---------|----------|-----------|:---:|:--------:|
| Railroad Valley Playa (RVUS) | USA | 38.497 N | 115.690 W | ✔︎ | 1 |
| La Crau (LCFR) | France | 43.56 N | 4.87 E | ✔︎ | 2 |
| Gobabeb (GONA) | Namibia | 23.600 S | 15.120 E | ✘ | 0 |
| Baotou (BAOT) | China | 40.84 N | 109.46 E | ✔︎ | 2 |
| Shadnagar (SHAD) | India | 17.033 N | 78.183 E | ✘ | 0 |
| Gobabeb (GHNA) | Namibia | 23.60153 S | 15.12589 E | ✔︎ | 1 |
| Jarvselja (JAES) | Estonia | 58.281975 N | 27.312959 E | ✘ | 0 |
| Jolanda di Savoia (JSIT) | Italy | 44.88 N | 11.98 E | ✘ | 0 |
| Lonzee (LOBE) | Belgium | 50.551493 N | 4.745911 E | ✘ | 0 |
| Wytham Woods (WWUK) | United Kingdom | 51.777206 N | 1.338494 W | ✘ | 0 |
| Princess Elisabeth (PEAN) | Antarctica | 71.940128 S | 23.305260 E | ✘ | 0 |
| Libya‑4 (LYB4) | Libya | 28.55 N | 23.39 E | ✔︎ | 1 |
| Libya‑1 (LYB1) | Libya | 24.42 N | 13.35 E | ✘ | 0 |
| Algeria‑3 (ALG3) | Algeria | 30.32 N | 7.66 E | ✔︎ | 2 |
| Piedmont (PIED) | Italy | 44.6724 N | 7.2665 E | ✘ | 0 |
| Grosseto (GROS) | Italy | 42.76 N | 11.06 E | ✘ | 0 |
| Pueblo Range (PRING) | USA | 38.28 N | 104.61 W | ✔︎ | 3 |
| Sioux Falls Range (SFRG) | USA | 43.56 N | 96.46 W | ✔︎ | 2 |


### To‑Do / Next Steps
- Increase the number of acquisitions per site
- Add dedicated acquisitions for cross‑talk analysis


## How to Use

### Prerequisites
- Python 3.x installed.
- Install dependencies: `pip install -r requirements.txt`

### INSULA Account Setup
Before downloading the data, you must create an account on the INSULA PHISAT-2 platform:

https://identity.insula.earth/realms/phisat2/protocol/openid-connect/auth?client_id=webapp-client&redirect_uri=https%3A%2F%2Fphisat2.insula.earth%2Fperception%2Fauth&response_type=code&scope=openid+profile+email

After registration, open the file `download_and_organize.py` and insert your credentials:

    # INSULA credentials
    INSULA_USERNAME = "YOUR USERNAME"
    INSULA_PASSWORD = "YOUR PSW"

### Download and Organize Data
1. Run the `download_and_organize.py` script from the `ProjectFolder`:

        python download_and_organize.py

2. The script:
   - Authenticates with the INSULA PHISAT-2 API using your credentials.
   - Reads the JSON files to collect all `session_id`s.
   - Downloads the corresponding ZIP files from the INSULA API.
   - Organizes the ZIPs into the appropriate folders following the `category/location/session` path.
   - Optionally unzips the files (the `UNZIP_FLAG` in the code, currently set to `False`).

During execution, the script prints messages for each main operation (authentication, collecting session_id, download, moving).

### Notes
- ZIP files are downloaded to the root folder and then moved to the correct positions.
- If a ZIP file is already present, it is not re-downloaded.
- To enable unzipping, change `UNZIP_FLAG = True` in the code.

## Contributions and Issues

Users and collaborators are encouraged to **propose new reference sites or locations of interest** to be considered for future acquisitions.

Proposals should be submitted by opening a **GitHub Issue** in this repository.

When creating an Issue, please include the following information:
- **Site name**
- **Approximate geographic coordinates**
- **Type of interest** (e.g. radiometry, geometry, image quality, cross‑talk)
- **Motivation and expected benefits** for the PHISAT‑2 dataset

Community feedback and discussion through GitHub Issues will support the selection and prioritization of future acquisition targets.

## Citation
If you use this dataset in your research, cite as follows:

**CalVal Dataset**, author: Lorenzo Papa.

Example BibTeX citation:
```
@dataset{papa_calval_dataset,
  title={CalVal Dataset},
  author={Papa, Lorenzo},
  year={2026},
  url={https://huggingface.co/datasets/lorenzopapa53/CalValDataset}
}
```
