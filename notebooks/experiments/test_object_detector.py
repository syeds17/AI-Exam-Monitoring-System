import cv2

from src.detection.object_detector import ObjectDetector


MODEL_PATH = (
    "runs/detect/runs/object_detection/"
    "exam_objects_v1/weights/best.pt"
)


def main():
    print("Initializing object detector...")

    detector = ObjectDetector(
        model_path=MODEL_PATH,
        confidence=0.40,
        image_size=640,
        device="cpu",
    )

    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not camera.isOpened():
        print("ERROR: Could not open webcam.")
        detector.close()
        return

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    print("\nObject detector test started.")
    print("Press Q to quit.\n")

    try:
        while True:
            success, frame = camera.read()

            if not success:
                print("ERROR: Could not read frame.")
                break

            detection_result = detector.detect(frame)

            output = detector.draw_detections(
                frame,
                detection_result,
            )

            # Print detections only when objects are found.
            objects = detection_result["objects"]

            if objects:
                print("\nDetected objects:")

                for obj in objects:
                    print(
                        f"  {obj['class_name']} "
                        f"({obj['confidence']:.2f}) "
                        f"bbox={obj['bbox']}"
                    )

            cv2.imshow(
                "Custom Object Detector Test",
                output,
            )

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break

    except KeyboardInterrupt:
        print("\nTest interrupted.")

    finally:
        camera.release()
        cv2.destroyAllWindows()
        detector.close()

        print("\nObject detector test stopped.")


if __name__ == "__main__":
    main()