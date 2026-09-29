from pathlib import Path

import cv2
from ultralytics import YOLO


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_PATH = Path(
    "runs/detect/runs/object_detection/exam_objects_v1/weights/best.pt"
)

CONFIDENCE = 0.40
IMAGE_SIZE = 640

CLASS_NAMES = {
    0: "mobile_phone",
    1: "earphones",
    2: "smartwatch",
    3: "book",
    4: "paper_notes",
    5: "laptop",
    6: "tablet",
}


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("CUSTOM OBJECT DETECTOR TEST")
    print("=" * 60)

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found:\n{MODEL_PATH}"
        )

    print(f"Model: {MODEL_PATH}")
    print()

    model = YOLO(str(MODEL_PATH))

    print("Available classes:")
    for class_id, name in CLASS_NAMES.items():
        print(f"  {class_id}: {name}")

    print()
    print("=" * 60)
    print("OPENING CAMERA")
    print("=" * 60)
    print()
    print("Controls:")
    print("  Q → quit")
    print()

    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not camera.isOpened():
        raise RuntimeError("Could not open camera.")

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    while True:
        success, frame = camera.read()

        if not success:
            print("Failed to read camera frame.")
            break

        results = model.predict(
            source=frame,
            imgsz=IMAGE_SIZE,
            conf=CONFIDENCE,
            device="cpu",
            verbose=False,
        )

        result = results[0]

        annotated_frame = result.plot()

        detections = []

        if result.boxes is not None:
            for box in result.boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])

                class_name = CLASS_NAMES.get(
                    class_id,
                    f"class_{class_id}",
                )

                x1, y1, x2, y2 = map(
                    int,
                    box.xyxy[0].tolist(),
                )

                detections.append(
                    {
                        "class_id": class_id,
                        "class_name": class_name,
                        "confidence": confidence,
                        "bbox": (x1, y1, x2, y2),
                    }
                )

        # ----------------------------------------------------
        # Detection information
        # ----------------------------------------------------

        y_offset = 30

        cv2.putText(
            annotated_frame,
            f"Detections: {len(detections)}",
            (20, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
        )

        for detection in detections:
            y_offset += 30

            text = (
                f"{detection['class_name']} "
                f"{detection['confidence']:.2f}"
            )

            cv2.putText(
                annotated_frame,
                text,
                (20, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 0),
                2,
            )

        cv2.imshow(
            "Custom Object Detector Test",
            annotated_frame,
        )

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

    camera.release()
    cv2.destroyAllWindows()

    print()
    print("=" * 60)
    print("OBJECT DETECTOR TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()