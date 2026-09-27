import time
import cv2

from src.detection.person_detector import PersonDetector
from src.detection.detection_worker import DetectionWorker


def main():

    print("=" * 60)
    print("       BACKGROUND PERSON DETECTION TEST")
    print("=" * 60)

    # ==========================================
    # LOAD DETECTOR
    # ==========================================

    detector = PersonDetector(
        model_path="yolo11n.pt",
        confidence=0.50
    )

    # ==========================================
    # CREATE WORKER
    # ==========================================

    worker = DetectionWorker(
        detector=detector,
        detection_interval=0.15
    )

    # ==========================================
    # CAMERA
    # ==========================================

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

    print("\nCamera started.")

    # ==========================================
    # START YOLO THREAD
    # ==========================================

    worker.start()

    print("Detection worker started.")
    print("\nPress Q to stop.\n")

    frame_count = 0

    start_time = time.perf_counter()

    try:

        while True:

            success, frame = camera.read()

            if not success:
                continue

            frame_count += 1

            # ==================================
            # SEND LATEST FRAME TO WORKER
            # ==================================

            worker.update_frame(frame)

            # ==================================
            # GET LATEST YOLO RESULT
            # ==================================

            detection = worker.get_result()

            # ==================================
            # DRAW RESULT
            # ==================================

            display = frame.copy()

            for person in detection["persons"]:

                x1, y1, x2, y2 = (
                    person["bbox"]
                )

                confidence = (
                    person["confidence"]
                )

                cv2.rectangle(
                    display,
                    (x1, y1),
                    (x2, y2),
                    (0, 255, 0),
                    2
                )

                cv2.putText(
                    display,
                    f"Person {confidence:.2f}",
                    (
                        x1,
                        max(y1 - 10, 20)
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2
                )

            # ==================================
            # FPS
            # ==================================

            elapsed = (
                time.perf_counter()
                - start_time
            )

            camera_fps = (
                frame_count / elapsed
                if elapsed > 0
                else 0
            )

            detection_fps = (
                worker.get_fps()
            )

            cv2.putText(
                display,
                f"Persons: "
                f"{detection['person_count']}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 255, 0),
                2
            )

            cv2.putText(
                display,
                f"Camera FPS: "
                f"{camera_fps:.1f}",
                (20, 75),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2
            )

            cv2.putText(
                display,
                f"YOLO FPS: "
                f"{detection_fps:.1f}",
                (20, 105),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2
            )

            cv2.imshow(
                "Background Person Detection",
                display
            )

            # ==================================
            # LOG
            # ==================================

            if frame_count % 60 == 0:

                print(
                    f"Persons: "
                    f"{detection['person_count']} | "
                    f"Camera FPS: "
                    f"{camera_fps:.1f} | "
                    f"YOLO FPS: "
                    f"{detection_fps:.1f}"
                )

            # ==================================
            # STOP
            # ==================================

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break

    finally:

        worker.stop()

        camera.release()

        cv2.destroyAllWindows()

    elapsed = (
        time.perf_counter()
        - start_time
    )

    final_camera_fps = (
        frame_count / elapsed
        if elapsed > 0
        else 0
    )

    print("\n==========================================")
    print("TEST COMPLETE")
    print("==========================================")

    print(
        f"Total camera frames: "
        f"{frame_count}"
    )

    print(
        f"Camera FPS: "
        f"{final_camera_fps:.2f}"
    )

    print(
        f"YOLO detection FPS: "
        f"{worker.get_fps():.2f}"
    )

    print(
        f"YOLO detections: "
        f"{worker.get_detection_count()}"
    )

    print(
        "\n✅ Background detection test complete."
    )


if __name__ == "__main__":
    main()