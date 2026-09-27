import time
import cv2

from src.detection.person_detector import PersonDetector


def main():

    print("=" * 60)
    print("           PERSON DETECTOR TEST")
    print("=" * 60)

    print("\nLoading detector...")

    detector = PersonDetector(
        model_path="yolo11n.pt",
        confidence=0.50
    )

    print("\nOpening camera...")

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

    print("Camera started.")
    print("\nPress Q to stop.\n")

    frame_count = 0
    start_time = time.perf_counter()

    while True:

        success, frame = camera.read()

        if not success:
            print("Failed to read frame.")
            continue

        detection = detector.detect(frame)

        frame_count += 1

        elapsed = (
            time.perf_counter()
            - start_time
        )

        fps = (
            frame_count / elapsed
            if elapsed > 0
            else 0
        )

        display = detector.draw_detections(
            frame,
            detection
        )

        cv2.putText(
            display,
            f"Detection FPS: {fps:.1f}",
            (20, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2
        )

        cv2.imshow(
            "Person Detection Test",
            display
        )

        if frame_count % 30 == 0:

            print(
                f"Persons: "
                f"{detection['person_count']} | "
                f"FPS: {fps:.1f}"
            )

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

    camera.release()
    cv2.destroyAllWindows()

    elapsed = (
        time.perf_counter()
        - start_time
    )

    final_fps = (
        frame_count / elapsed
        if elapsed > 0
        else 0
    )

    print("\nCamera stopped.")

    print(
        f"Total frames: {frame_count}"
    )

    print(
        f"Average detection FPS: "
        f"{final_fps:.2f}"
    )

    print(
        "\n✅ Person detector test complete."
    )


if __name__ == "__main__":
    main()