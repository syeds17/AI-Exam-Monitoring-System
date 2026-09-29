from pathlib import Path

from ultralytics import YOLO


# ============================================================
# CONFIGURATION
# ============================================================

BASE_MODEL = Path(
    "runs/detect/runs/object_detection/exam_objects_v1/weights/best.pt"
)

DATASET = "data/object_detection/data.yaml"

EPOCHS = 30
IMAGE_SIZE = 416
BATCH_SIZE = 8

PROJECT = "runs/object_detection"
RUN_NAME = "exam_objects_fast_v1"


# ============================================================
# TRAINING
# ============================================================

def main():
    print("=" * 60)
    print("FAST CUSTOM OBJECT DETECTION TRAINING")
    print("=" * 60)

    print(f"Starting model : {BASE_MODEL}")
    print(f"Dataset        : {DATASET}")
    print(f"Epochs         : {EPOCHS}")
    print(f"Image size     : {IMAGE_SIZE}")
    print(f"Batch size     : {BATCH_SIZE}")
    print("Device         : CPU")
    print("=" * 60)

    if not BASE_MODEL.exists():
        raise FileNotFoundError(
            f"Starting model not found:\n{BASE_MODEL}"
        )

    model = YOLO(str(BASE_MODEL))

    model.train(
        data=DATASET,
        epochs=EPOCHS,
        imgsz=IMAGE_SIZE,
        batch=BATCH_SIZE,
        device="cpu",
        workers=0,

        project=PROJECT,
        name=RUN_NAME,

        pretrained=False,

        patience=8,

        save=True,
        plots=True,
        verbose=True,
    )

    print()
    print("=" * 60)
    print("FAST TRAINING COMPLETE")
    print("=" * 60)
    print(
        f"Results: {PROJECT}/{RUN_NAME}"
    )
    print(
        f"Best model: "
        f"{PROJECT}/{RUN_NAME}/weights/best.pt"
    )


if __name__ == "__main__":
    main()