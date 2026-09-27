from pathlib import Path


DATASET_ROOT = Path("data/object_detection")

SPLITS = ["train", "val"]

CLASS_NAMES = {
    0: "mobile_phone",
    1: "earphones",
    2: "smartwatch",
    3: "book",
    4: "paper_notes",
    5: "laptop",
    6: "tablet",
}


def validate_split(split):
    label_dir = DATASET_ROOT / "labels" / split
    image_dir = DATASET_ROOT / "images" / split

    print()
    print("=" * 60)
    print(f"VALIDATING: {split.upper()}")
    print("=" * 60)

    label_files = list(label_dir.glob("*.txt"))
    image_files = []

    for extension in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
        image_files.extend(image_dir.glob(extension))

    print(f"Images : {len(image_files)}")
    print(f"Labels : {len(label_files)}")

    errors = []
    annotation_count = 0
    class_counts = {class_id: 0 for class_id in CLASS_NAMES}

    image_stems = {image.stem for image in image_files}

    # Check every label file
    for label_file in label_files:

        if label_file.stem not in image_stems:
            errors.append(
                f"Label has no matching image: {label_file.name}"
            )

        try:
            lines = label_file.read_text(
                encoding="utf-8"
            ).splitlines()
        except Exception as exc:
            errors.append(
                f"Could not read {label_file.name}: {exc}"
            )
            continue

        for line_number, line in enumerate(lines, start=1):

            line = line.strip()

            if not line:
                continue

            parts = line.split()

            # YOLO detection must have exactly 5 values
            if len(parts) != 5:
                errors.append(
                    f"{label_file.name}:{line_number} "
                    f"has {len(parts)} values instead of 5"
                )
                continue

            try:
                class_id = int(parts[0])

                x_center = float(parts[1])
                y_center = float(parts[2])
                width = float(parts[3])
                height = float(parts[4])

            except ValueError:
                errors.append(
                    f"{label_file.name}:{line_number} "
                    f"contains invalid numbers"
                )
                continue

            # Check class ID
            if class_id not in CLASS_NAMES:
                errors.append(
                    f"{label_file.name}:{line_number} "
                    f"invalid class ID {class_id}"
                )
                continue

            # Coordinates must be normalized
            values = [
                x_center,
                y_center,
                width,
                height,
            ]

            if any(value < 0 or value > 1 for value in values):
                errors.append(
                    f"{label_file.name}:{line_number} "
                    f"coordinates outside 0-1 range"
                )
                continue

            # Width and height must be positive
            if width <= 0 or height <= 0:
                errors.append(
                    f"{label_file.name}:{line_number} "
                    f"invalid width/height"
                )
                continue

            annotation_count += 1
            class_counts[class_id] += 1

    print()
    print("CLASS COUNTS")
    print("-" * 40)

    for class_id, name in CLASS_NAMES.items():
        print(
            f"{class_id}: {name:<15} "
            f"{class_counts[class_id]}"
        )

    print()
    print(f"Valid annotations : {annotation_count}")
    print(f"Errors             : {len(errors)}")

    if errors:
        print()
        print("FIRST 20 ERRORS")
        print("-" * 60)

        for error in errors[:20]:
            print(error)

    else:
        print()
        print("✅ ALL LABELS ARE VALID YOLO DETECTION LABELS")


def main():

    print("=" * 60)
    print("OBJECT DETECTION DATASET VALIDATION")
    print("=" * 60)

    for split in SPLITS:
        validate_split(split)

    print()
    print("=" * 60)
    print("VALIDATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()