from pathlib import Path
import shutil


# ============================================================
# PATHS
# ============================================================

BOOK_DATASET = Path(r"C:\Users\PCM\Documents\Book_Dataset")

PROJECT_DATASET = Path("data/object_detection")


# Book dataset class 0 → our class 3
BOOK_SOURCE_CLASS = 0
BOOK_TARGET_CLASS = 3


IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}


def build_image_lookup(image_dir):
    lookup = {}

    for image_file in image_dir.iterdir():

        if not image_file.is_file():
            continue

        if image_file.suffix.lower() not in IMAGE_EXTENSIONS:
            continue

        lookup[image_file.stem] = image_file

    return lookup


def process_split(source_split, target_split):

    source_images = BOOK_DATASET / source_split / "images"
    source_labels = BOOK_DATASET / source_split / "labels"

    target_images = PROJECT_DATASET / "images" / target_split
    target_labels = PROJECT_DATASET / "labels" / target_split

    target_images.mkdir(parents=True, exist_ok=True)
    target_labels.mkdir(parents=True, exist_ok=True)

    print()
    print("=" * 60)
    print(f"BOOK DATASET: {source_split.upper()} → {target_split.upper()}")
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

    images_added = 0
    annotations_added = 0
    skipped_no_image = 0
    invalid_labels = 0

    for label_file in label_files:

        image_file = image_lookup.get(label_file.stem)

        if image_file is None:
            skipped_no_image += 1
            continue

        output_lines = []

        lines = label_file.read_text(
            encoding="utf-8"
        ).splitlines()

        for line in lines:

            line = line.strip()

            if not line:
                continue

            parts = line.split()

            # YOLO detection format:
            # class x_center y_center width height
            if len(parts) != 5:
                invalid_labels += 1
                continue

            try:
                class_id = int(parts[0])

                coordinates = [
                    float(value)
                    for value in parts[1:]
                ]

            except ValueError:
                invalid_labels += 1
                continue

            # This dataset should contain only class 0
            if class_id != BOOK_SOURCE_CLASS:
                invalid_labels += 1
                continue

            # Validate normalized coordinates
            if any(
                value < 0 or value > 1
                for value in coordinates
            ):
                invalid_labels += 1
                continue

            x_center, y_center, width, height = coordinates

            if width <= 0 or height <= 0:
                invalid_labels += 1
                continue

            # Convert Book class 0 → our class 3
            output_lines.append(
                f"{BOOK_TARGET_CLASS} "
                f"{x_center:.6f} "
                f"{y_center:.6f} "
                f"{width:.6f} "
                f"{height:.6f}"
            )

            annotations_added += 1

        if not output_lines:
            continue

        # Prefix filename to avoid collisions with existing dataset
        new_stem = f"book_{label_file.stem}"

        output_image = (
            target_images /
            f"{new_stem}{image_file.suffix.lower()}"
        )

        output_label = (
            target_labels /
            f"{new_stem}.txt"
        )

        shutil.copy2(
            image_file,
            output_image
        )

        output_label.write_text(
            "\n".join(output_lines) + "\n",
            encoding="utf-8",
        )

        images_added += 1

    print()
    print(f"Images added       : {images_added}")
    print(f"Annotations added  : {annotations_added}")
    print(f"Skipped no image   : {skipped_no_image}")
    print(f"Invalid labels     : {invalid_labels}")


def main():

    print("=" * 60)
    print("ADDING BOOK DATASET")
    print("=" * 60)

    print(f"Source : {BOOK_DATASET}")
    print(f"Target : {PROJECT_DATASET}")

    process_split("train", "train")
    process_split("valid", "val")

    print()
    print("=" * 60)
    print("BOOK DATASET MERGE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()