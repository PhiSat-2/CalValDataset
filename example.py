import json
import argparse
from pathlib import Path
import numpy as np
import rasterio
from skimage.exposure import rescale_intensity
import matplotlib.pyplot as plt


# ------------------------------
# Dataset loading
# ------------------------------

def load_dataset(process_type):
    json_filename = f"{process_type}.json"
    json_path = Path(json_filename)

    if not json_path.exists():
        raise FileNotFoundError(f"Dataset file '{json_filename}' not found.")

    with open(json_path, "r") as f:
        return json.load(f)


def find_entry(data, location, session):
    for entry in data["entries"]:
        if entry["location"] == location and entry["session"] == session:
            return entry
    return None


# ------------------------------
# Band loading + normalization
# ------------------------------

def open_band(entry, band_key):
    if band_key not in entry["bands"]:
        raise ValueError(f"Band '{band_key}' not found in this entry.")

    img_path = entry["bands"][band_key]

    if not Path(img_path).exists():
        raise FileNotFoundError(f"Image file '{img_path}' does not exist.")

    # Load band with rasterio
    with rasterio.open(img_path) as src:
        band = src.read(1).astype(np.float32)

    # Normalize 0–1
    band = rescale_intensity(band, in_range='image', out_range=(0, 1))

    return band


# ------------------------------
# Cropping
# ------------------------------

def crop_with_bbox(image, bbox):
    x_min, y_min = bbox["x_min"], bbox["y_min"]
    x_max, y_max = bbox["x_max"], bbox["y_max"]
    return image[y_min:y_max, x_min:x_max]


# ------------------------------
# Image visualization
# ------------------------------

def show_image(img, save_path):
    plt.imshow(img, cmap="gray")
    plt.axis("off")
    plt.savefig(save_path + '/example_output.png', dpi=150, bbox_inches="tight", pad_inches=0)
    plt.close()
    print(f"📁 Image saved to: {save_path}")


# ------------------------------
# Arg parsing
# ------------------------------

def parse_arguments():
    parser = argparse.ArgumentParser(description="TIFF band extractor with bounding box.")

    parser.add_argument("--process_type", type=str, required=True, help="Processing type (e.g., image_quality)")
    parser.add_argument("--location", type=str, required=True, help="Location name (e.g., BOAT)")
    parser.add_argument("--session", type=str, required=True, help="Session ID (e.g., Session1)")
    parser.add_argument("--band", type=str, required=True, help="Band key to open (e.g., b_3)")

    return parser.parse_args()


# ------------------------------
# Main
# ------------------------------

def main():
    args = parse_arguments()

    PROCESS_TYPE = args.process_type
    LOCATION = args.location
    SESSION = args.session
    BAND = args.band

    dataset = load_dataset("./" + PROCESS_TYPE + "/" + PROCESS_TYPE + "_dataset")

    entry = find_entry(dataset, LOCATION, SESSION)
    if entry is None:
        print(f"\n⚠️ No entry found for location={LOCATION} session={SESSION}")
        return

    print(f"\nOpening band: {BAND}")
    img = open_band(entry, BAND)
    bbox = entry["bbox"][0]

    cropped = crop_with_bbox(img, bbox)
    show_image(cropped, save_path='./')

    print("\n=== OUTPUT INFORMATION ===")
    print("Label:", bbox["label"])

if __name__ == "__main__":
    main()
