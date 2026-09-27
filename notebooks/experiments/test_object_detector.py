import cv2

from src.detection.object_detector import ObjectDetector


def main():

    print("=" * 60)
    print("YOLO OBJECT DETECTOR TEST")
    print("=" * 60)

    detector = ObjectDetector(
        model_path="yolo11n.pt",
        confidence=0.50
    )

    print("\nPretrained classes currently supported:")
    for class_name in detector.get_supported_classes():
        print(f"  - {class_name}")

    print("\nClasses requiring training:")
    for class_name in detector.get_training_required_classes():
        print(f"  - {class_name}")

    print("\nStarting webcam...")
    print("Press Q to quit.")

    camera = cv2.VideoCapture(
        0,
        cv2.CAP_DSHOW
    )

    if not camera.isOpened():
        raise RuntimeError(
            "Could not open webcam."
        )

    camera.set(
        cv2.CAP_PROP_FRAME_WIDTH,
        1280
    )

    camera.set(
        cv2.CAP_PROP_FRAME_HEIGHT,
        720
    )

    detection_count = 0

    try:

        while True:

            success, frame = camera.read()

            if not success:
                print("Failed to read frame.")
                continue

            frame = cv2.flip(frame, 1)

            detection_result = detector.detect(frame)

            detection_count += 1

            display_frame = detector.draw_detections(
                frame,
                detection_result
            )

            detected_objects = detection_result.get(
                "objects",
                []
            )

            if detected_objects:

                print("\nDetected objects:")

                for obj in detected_objects:

                    print(
                        f"  {obj['class_name']} "
                        f"({obj['confidence']:.2f})"
                    )

            cv2.imshow(
                "YOLO Object Detector Test",
                display_frame
            )

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break

    finally:

        camera.release()
        cv2.destroyAllWindows()

        print("\n" + "=" * 60)
        print("OBJECT DETECTOR TEST FINISHED")
        print(f"Frames processed: {detection_count}")
        print("=" * 60)


if __name__ == "__main__":
    main()