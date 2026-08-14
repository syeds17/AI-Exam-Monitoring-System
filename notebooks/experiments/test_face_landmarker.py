import cv2
import time

from src.face.face_landmarker import FaceLandmarker
from src.face.head_pose import HeadPoseEstimator


MODEL_PATH = "models/face/face_landmarker.task"

CALIBRATION_FRAMES = 75


def main():

    face_landmarker = FaceLandmarker(MODEL_PATH)
    head_pose = HeadPoseEstimator()

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("ERROR: Could not open webcam.")
        face_landmarker.close()
        return

    start_time = time.time()
    frame_count = 0
    timestamp_ms = 0

    calibration_pitch = []
    calibration_yaw = []

    calibrated = False

    try:

        while True:

            success, frame = cap.read()

            if not success:
                print("ERROR: Could not read frame.")
                break

            frame = cv2.flip(frame, 1)

            result = face_landmarker.process(
                frame,
                timestamp_ms
            )

            pitch = None
            yaw = None

            relative_pitch = None
            relative_yaw = None

            direction = "NO FACE"

            # -----------------------------------------
            # FACE DETECTED
            # -----------------------------------------

            if result.face_landmarks:

                h, w, _ = frame.shape

                face = result.face_landmarks[0]

                pitch, yaw = head_pose.get_pose(
                    face,
                    w,
                    h
                )

                # -----------------------------------------
                # CALIBRATION
                # -----------------------------------------

                if not calibrated:

                    calibration_pitch.append(pitch)
                    calibration_yaw.append(yaw)

                    progress = len(calibration_pitch)

                    cv2.putText(
                        frame,
                        "CALIBRATING...",
                        (20, 80),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0, 255, 255),
                        2
                    )

                    cv2.putText(
                        frame,
                        "Look naturally at the screen",
                        (20, 115),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 255),
                        2
                    )

                    cv2.putText(
                        frame,
                        f"Progress: {progress}/{CALIBRATION_FRAMES}",
                        (20, 150),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 255),
                        2
                    )

                    if progress >= CALIBRATION_FRAMES:

                        neutral_pitch = (
                            head_pose.circular_mean(
                                calibration_pitch
                            )
                        )

                        neutral_yaw = (
                            head_pose.circular_mean(
                                calibration_yaw
                            )
                        )

                        head_pose.set_neutral(
                            neutral_pitch,
                            neutral_yaw
                        )

                        calibrated = True

                        print(
                            "\nCalibration complete!"
                        )

                        print(
                            f"Neutral Pitch: {neutral_pitch:.2f}"
                        )

                        print(
                            f"Neutral Yaw: {neutral_yaw:.2f}"
                        )

                # -----------------------------------------
                # LIVE HEAD POSE
                # -----------------------------------------

                else:

                    relative_pitch, relative_yaw = (
                        head_pose.get_relative_pose(
                            pitch,
                            yaw
                        )
                    )

                    direction = head_pose.get_direction(
                        relative_pitch,
                        relative_yaw
                    )

                # -----------------------------------------
                # DRAW LANDMARKS
                # -----------------------------------------

                for landmark in face:

                    x = int(landmark.x * w)
                    y = int(landmark.y * h)

                    if 0 <= x < w and 0 <= y < h:

                        cv2.circle(
                            frame,
                            (x, y),
                            1,
                            (0, 255, 0),
                            -1
                        )

            # -----------------------------------------
            # FPS
            # -----------------------------------------

            frame_count += 1
            timestamp_ms += 33

            elapsed = time.time() - start_time

            fps = (
                frame_count / elapsed
                if elapsed > 0
                else 0
            )

            cv2.putText(
                frame,
                f"FPS: {fps:.1f}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )

            # -----------------------------------------
            # DISPLAY POSE
            # -----------------------------------------

            if pitch is not None:

                cv2.putText(
                    frame,
                    f"Pitch: {pitch:.1f}",
                    (20, 190),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2
                )

                cv2.putText(
                    frame,
                    f"Yaw: {yaw:.1f}",
                    (20, 220),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2
                )

            if calibrated and relative_pitch is not None:

                cv2.putText(
                    frame,
                    f"Relative Pitch: {relative_pitch:.1f}",
                    (20, 250),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2
                )

                cv2.putText(
                    frame,
                    f"Relative Yaw: {relative_yaw:.1f}",
                    (20, 280),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2
                )

                cv2.putText(
                    frame,
                    f"Direction: {direction}",
                    (20, 320),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (255, 255, 0),
                    2
                )

            # -----------------------------------------
            # DISPLAY
            # -----------------------------------------

            cv2.imshow(
                "AI Exam Monitoring - Face Test",
                frame
            )

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:

        cap.release()
        face_landmarker.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()