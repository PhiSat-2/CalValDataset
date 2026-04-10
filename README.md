# CalVal Dataset

## Description

This repository contains the **CalVal Dataset**, a collection of data for calibration and validation (Cal/Val) of the PhiSat2 satellite. The data is organized into three main categories: `geometry`, `image_quality`, and `radiometry`. Each category includes subfolders for locations and sessions, containing ZIP files of satellite products.

The original data is stored on Hugging Face: [https://huggingface.co/datasets/lorenzopapa53/CalValDataset/tree/main](https://huggingface.co/datasets/lorenzopapa53/CalValDataset/tree/main).

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

| Site | Country | Latitude | Longitude | DATA |
|------|---------|----------|-----------|:---:|
| Railroad Valley Playa | USA | 38.497 N | 115.690 W | ✔︎ |
| La Crau | France | 43.56 N | 4.87 E | ✔︎ |
| Gobabeb (RadCalNet) | Namibia | 23.600 S | 15.120 E | ✔︎ |
| Baotou (RadCalNet) | China | 40.84 N | 109.46 E | ✔︎ |
| Gobabeb (LANDHYPERNET) | Namibia | 23.60153 S | 15.12589 E | ✔︎ |
| Jarvselja | Estonia | 58.281975 N | 27.312959 E | ✘ |
| Jolanda di Savoia | Italy | 44.88 N | 11.98 E | ✘ |
| Lonzee | Belgium | 50.551493 N | 4.745911 E | ✘ |
| Wytham Woods | United Kingdom | 51.777206 N | 1.338494 W | ✘ |
| Princess Elisabeth | Antarctica | 71.940128 S | 23.305260 E | ✘ |
| Libya‑4 | Libya | 28.55 N | 23.39 E | ✔︎ |


## How to Use

### Prerequisites
- Python 3.x installed.
- Install dependencies: `pip install -r requirements.txt`

### Download and Organize Data
1. Run the `download_and_organize.py` script from the `ProjectFolder`:
   ```
   python download_and_organize.py
   ```
2. The script:
   - Reads the JSON files to collect all `session_id`s.
   - Downloads the corresponding ZIP files from Hugging Face.
   - Organizes the ZIPs into the appropriate folders following the `category/location/session` path.
   - Optionally unzips the files (the `UNZIP_FLAG` in the code, currently set to `False`).

During execution, the script prints messages for each main operation (collecting session_id, download, moving).

### Notes
- ZIP files are downloaded to the root folder and then moved to the correct positions.
- If a ZIP file is already present, it is not re-downloaded.
- To enable unzipping, change `UNZIP_FLAG = True` in the code.

## Contributions and Issues
To report issues or contribute, open an issue on GitHub.

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
