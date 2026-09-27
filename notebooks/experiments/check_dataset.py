from pathlib import Path
from collections import Counter


DATASET = Path(r"C:\Users\PCM\Documents\New folder")

SOURCE_CLASSES = {
    0: "Apple-Pencil",
    1: "Bag",
    2: "Calculator",
    3: "Charging-cable",
    4: "Earphones",
    5: "Glasses",
    6: "Keyboard",
    7: "Keys",
    8: "Laptop",
    9: "Lecture-notes",
    10: "Markers",
    11: "Mobile phone",
    12: "Mouse",
    13: "PC",
    14: "Pen",
    15: "Screen",
    16: "StudentID_card",
    17: "Wallet",
    18: "Watch",
    19: "Water bottle",
    20: "iPad-Air",
    21: "iPad-Pro",
}


def inspect_split(split):
    labels_dir = DATASET / split / "labels"
    images_dir = DATASET / split / "images"

    labels = list(labels_dir.glob("*.txt"))
    images = list(images_dir.glob("*"))

    counts = Counter()

    for label_file in labels:
        for line in label_file.read_text(
            encoding="utf-8"
        ).splitlines():

            if not line.strip():
                continue

            parts = line.split()

            if len(parts) >= 5:
                class_id = int(parts[0])
                counts[class_id] += 1

    print()
    print("=" * 60)
    print(split.upper())
    print("=" * 60)

    print(f"Images: {len(images)}")
    print(f"Label files: {len(labels)}")

    print("\nAnnotations by class:")

    for class_id in range(22):
        print(
            f"{class_id:2d} | "
            f"{SOURCE_CLASSES[class_id]:20s} | "
            f"{counts[class_id]}"
        )


def main():
    print("=" * 60)
    print("RAW DATASET INSPECTION")
    print("=" * 60)

    print(f"\nDataset:\n{DATASET}")

    inspect_split("train")
    inspect_split("valid")
    inspect_split("test")


if __name__ == "__main__":
    main()