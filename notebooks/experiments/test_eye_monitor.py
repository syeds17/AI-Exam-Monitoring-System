import cv2
import time

from src.face.face_landmarker import FaceLandmarker
from src.eyes.eye_monitor import EyeMonitor


MODEL_PATH = "models/face/face_landmarker.task"


def main():

    print("Starting Eye Monitor test...")

    face_landmarker = FaceLandmarker(
        MODEL_PATH
    )

    eye_monitor = EyeMonitor(
        closure_threshold=0.20,
        closed_duration_threshold=2.0
    )

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():

        print("ERROR: Could not open webcam.")

        face_landmarker.close()

        return

    timestamp_ms = 0

    try:

        while True:

            success, frame = cap.read()

            if not success:

                print(
                    "ERROR: Could not read frame."
                )

                break

            frame = cv2.flip(
                frame,
                1
            )

            result = face_landmarker.process(
                frame,
                timestamp_ms
            )

            timestamp_ms += 33

            eye_text = "NO FACE"

            if result.face_landmarks:

                face = result.face_landmarks[0]

                eye_state = eye_monitor.update(
                    face,
                    time.time()
                )

                state = eye_state["state"]

                left_ear = eye_state[
                    "left_ear"
                ]

                right_ear = eye_state[
                    "right_ear"
                ]

                eye_text = state

                cv2.putText(
                    frame,
                    f"Eyes: {state}",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2
                )

                cv2.putText(
                    frame,
                    f"Left EAR: {left_ear:.3f}",
                    (20, 75),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2
                )

                cv2.putText(
                    frame,
                    f"Right EAR: {right_ear:.3f}",
                    (20, 105),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2
                )

                if eye_state["event"]:

                    print(
                        "\n🚨 EYE EVENT:",
                        eye_state["event"]
                    )

            else:

                cv2.putText(
                    frame,
                    "Eyes: NO FACE",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2
                )

            cv2.imshow(
                "AI Exam Monitoring - Eye Test",
                frame
            )

            if (
                cv2.waitKey(1) & 0xFF
                == ord("q")
            ):
                break

    finally:

        cap.release()

        face_landmarker.close()

        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
    