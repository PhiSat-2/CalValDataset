# CalVal Simera Dataset

## Description

This repository contains the **CalVal Simera Dataset**, a collection of data for calibration and validation (Calibration and Validation) of the Simera satellite. The data is organized into three main categories: `geometry`, `image_quality`, and `radiometry`. Each category includes subfolders for locations and sessions, containing ZIP files of satellite products.

The original data is stored on Hugging Face: [https://huggingface.co/datasets/lorenzopapa53/CalValSimeraDataset/tree/main](https://huggingface.co/datasets/lorenzopapa53/CalValSimeraDataset/tree/main).

## Data Structure

The dataset structure is as follows:

```
CalValSimeraDataset/
├── Coding/
│   ├── download_and_organize.py    # Python script to download and organize data
│   ├── requirements.txt            # Required Python dependencies
│   ├── geometry/
│   │   └── geometry_dataset.json   # Metadata for geometry category
│   ├── image_quality/
│   │   └── image_quality_dataset.json  # Metadata for image_quality category
│   ├── radiometry/
│   │   └── radiometry_dataset.json # Metadata for radiometry category
│   └── README.md                   # This file
├── geometry/
│   ├── [location]/
│   │   └── [session]/
│   │       └── [file.zip]          # Organized ZIP files
├── image_quality/
│   └── [location]/
│       └── [session]/
│           └── [file.zip]
└── radiometry/
    └── [location]/
        └── [session]/
            └── [file.zip]
```

Each JSON file in the `Coding/geometry/`, `Coding/image_quality/`, and `Coding/radiometry/` folders contains metadata for the products, including:
- `session_id`: Unique identifier corresponding to the ZIP file name.
- `category`: Data category (geometry, image_quality, radiometry).
- `location`: Subfolder of the category.
- `session`: Subfolder of the location.
- Other metadata such as bounding box, resolution, coordinates, etc.

## How to Use

### Prerequisites
- Python 3.x installed.
- Install dependencies: `pip install -r requirements.txt`

### Download and Organize Data
1. Run the `download_and_organize.py` script from the `Coding` folder:
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
  title={CalVal Simera Dataset},
  author={Papa, Lorenzo},
  year={2026},
  url={https://huggingface.co/datasets/lorenzopapa53/CalValSimeraDataset}
}
```
