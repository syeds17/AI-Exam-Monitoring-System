from ultralytics import YOLO


# ============================================================
# CONFIGURATION
# ============================================================

MODEL = "yolo11n.pt"
DATA = "data/object_detection/data.yaml"

EPOCHS = 50
IMAGE_SIZE = 640
BATCH_SIZE = 4

PROJECT = "runs/object_detection"
NAME = "exam_objects_v1"


# ============================================================
# TRAINING
# ============================================================

def main():
    print("=" * 60)
    print("CUSTOM OBJECT DETECTION TRAINING")
    print("=" * 60)

    print(f"Model       : {MODEL}")
    print(f"Dataset     : {DATA}")
    print(f"Epochs      : {EPOCHS}")
    print(f"Image size  : {IMAGE_SIZE}")
    print(f"Batch size  : {BATCH_SIZE}")
    print("Device      : CPU")
    print("=" * 60)

    model = YOLO(MODEL)

    results = model.train(
        data=DATA,
        epochs=EPOCHS,
        imgsz=IMAGE_SIZE,
        batch=BATCH_SIZE,
        device="cpu",
        workers=0,

        project=PROJECT,
        name=NAME,

        pretrained=True,

        patience=10,

        save=True,
        plots=True,
        verbose=True,
    )

    print()
    print("=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"Results saved in: {PROJECT}/{NAME}")
    print()
    print("Best model:")
    print(f"{PROJECT}/{NAME}/weights/best.pt")


if __name__ == "__main__":
    main()