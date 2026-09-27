from pathlib import Path
import shutil


# ============================================================
# PATHS
# ============================================================

SOURCE_ROOT = Path(r"C:\Users\PCM\Documents\New folder")
OUTPUT_ROOT = Path("data/object_detection")


# ============================================================
# SOURCE → TARGET CLASS MAPPING
# ============================================================

# Roboflow Study Desk Items class IDs
# converted into our 7 target classes

CLASS_MAPPING = {
    4: 1,    # Earphones      → earphones
    8: 5,    # Laptop         → laptop
    9: 4,    # Lecture-notes  → paper_notes
    11: 0,   # Mobile phone   → mobile_phone
    18: 2,   # Watch           → smartwatch
    20: 6,   # iPad-Air        → tablet
    21: 6,   # iPad-Pro        → tablet
}


TARGET_NAMES = {
    0: "mobile_phone",
    1: "earphones",
    2: "smartwatch",
    3: "book",
    4: "paper_notes",
    5: "laptop",
    6: "tablet",
}


# ============================================================
# DATASET SPLITS
# ============================================================

SPLITS = {
    "train": "train",
    "valid": "val",
}


# ============================================================
# HELPERS
# ============================================================

def build_image_lookup(image_dir):
    """
    Build a lookup from image filename stem to image path.
    Supports jpg, jpeg, png and webp.
    """

    lookup = {}

    for image_file in image_dir.iterdir():

        if not image_file.is_file():
            continue

        if image_file.suffix.lower() not in {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        }:
            continue

        lookup[image_file.stem] = image_file

    return lookup


def polygon_to_bbox(values):
    """
    Convert YOLO segmentation polygon coordinates into
    a YOLO detection bounding box.

    Input:
        x1 y1 x2 y2 x3 y3 ...

    Output:
        x_center y_center width height
    """

    if len(values) < 6:
        return None

    # Separate X and Y coordinates
    xs = values[0::2]
    ys = values[1::2]

    if not xs or not ys:
        return None

    min_x = min(xs)
    max_x = max(xs)
    min_y = min(ys)
    max_y = max(ys)

    width = max_x - min_x
    height = max_y - min_y

    if width <= 0 or height <= 0:
        return None

    x_center = (min_x + max_x) / 2
    y_center = (min_y + max_y) / 2

    return x_center, y_center, width, height


# ============================================================
# PROCESS SPLIT
# ============================================================

def process_split(source_split, target_split):

    source_images = SOURCE_ROOT / source_split / "images"
    source_labels = SOURCE_ROOT / source_split / "labels"

    target_images = OUTPUT_ROOT / "images" / target_split
    target_labels = OUTPUT_ROOT / "labels" / target_split

    target_images.mkdir(parents=True, exist_ok=True)
    target_labels.mkdir(parents=True, exist_ok=True)

    print()
    print("=" * 60)
    print(f"PROCESSING: {source_split.upper()} → {target_split.upper()}")
    print("=" * 60)

    if not source_images.exists():
        print(f"ERROR: Image directory not found:")
        print(source_images)
        return

    if not source_labels.exists():
        print(f"ERROR: Label directory not found:")
        print(source_labels)
        return

    image_lookup = build_image_lookup(source_images)

    label_files = list(source_labels.glob("*.txt"))

    print(f"Source images : {len(image_lookup)}")
    print(f"Source labels : {len(label_files)}")

    counts = {name: 0 for name in TARGET_NAMES.values()}

    images_copied = 0
    annotations_kept = 0
    skipped_no_image = 0
    skipped_no_target = 0
    invalid_annotations = 0

    for label_file in label_files:

        image_file = image_lookup.get(label_file.stem)

        if image_file is None:
            skipped_no_image += 1
            continue

        target_annotations = []

        try:
            lines = label_file.read_text(encoding="utf-8").splitlines()
        except Exception as exc:
            print(f"Could not read {label_file.name}: {exc}")
            continue

        for line in lines:

            line = line.strip()

            if not line:
                continue

            parts = line.split()

            if len(parts) < 7:
                invalid_annotations += 1
                continue

            try:
                source_class = int(parts[0])
                coordinates = [float(value) for value in parts[1:]]
            except ValueError:
                invalid_annotations += 1
                continue

            # Ignore classes we don't need
            if source_class not in CLASS_MAPPING:
                continue

            target_class = CLASS_MAPPING[source_class]

            bbox = polygon_to_bbox(coordinates)

            if bbox is None:
                invalid_annotations += 1
                continue

            x_center, y_center, width, height = bbox

            target_annotations.append(
                f"{target_class} "
                f"{x_center:.6f} "
                f"{y_center:.6f} "
                f"{width:.6f} "
                f"{height:.6f}"
            )

            counts[TARGET_NAMES[target_class]] += 1
            annotations_kept += 1

        # Only copy images that contain at least one target object
        if not target_annotations:
            skipped_no_target += 1
            continue

        # Copy image
        output_image = target_images / image_file.name
        shutil.copy2(image_file, output_image)

        # Write converted detection label
        output_label = target_labels / f"{label_file.stem}.txt"
        output_label.write_text(
            "\n".join(target_annotations) + "\n",
            encoding="utf-8",
        )

        images_copied += 1

    print()
    print(f"Images copied          : {images_copied}")
    print(f"Annotations kept       : {annotations_kept}")
    print(f"Skipped - no image     : {skipped_no_image}")
    print(f"Skipped - no target    : {skipped_no_target}")
    print(f"Invalid annotations   : {invalid_annotations}")

    print()
    print("TARGET CLASS COUNTS")
    print("-" * 40)

    for class_id, class_name in TARGET_NAMES.items():
        print(f"{class_id}: {class_name:<15} {counts[class_name]}")

    print()


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("OBJECT DETECTION DATASET PREPARATION")
    print("=" * 60)

    print(f"Source : {SOURCE_ROOT}")
    print(f"Output : {OUTPUT_ROOT}")

    for source_split, target_split in SPLITS.items():
        process_split(source_split, target_split)

    print()
    print("=" * 60)
    print("DATASET CONVERSION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()