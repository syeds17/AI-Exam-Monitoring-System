from pathlib import Path

from ultralytics import YOLO


CHECKPOINT = Path(
    "runs/detect/runs/object_detection/exam_objects_v1/weights/last.pt"
)


def main():
    print("=" * 60)
    print("RESUMING OBJECT DETECTOR TRAINING")
    print("=" * 60)

    if not CHECKPOINT.exists():
        raise FileNotFoundError(
            f"Checkpoint not found:\n{CHECKPOINT}"
        )

    print(f"Checkpoint : {CHECKPOINT}")
    print("Resuming   : original 640px training")
    print("=" * 60)

    model = YOLO(str(CHECKPOINT))

    model.train(resume=True)

    print()
    print("=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()