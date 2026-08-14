import cv2
import time

from src.face.face_landmarker import FaceLandmarker
from src.face.head_pose import HeadPoseEstimator
from src.monitoring.attention_tracker import AttentionTracker
from src.monitoring.event_logger import EventLogger
from src.monitoring.face_monitor import FaceMonitor
from src.eyes.eye_monitor import EyeMonitor


MODEL_PATH = "models/face/face_landmarker.task"

CALIBRATION_FRAMES = 75


def main():

    face_landmarker = FaceLandmarker(MODEL_PATH)
    head_pose = HeadPoseEstimator()

    tracker = AttentionTracker(
        looking_away_threshold=3.0,
    )
    
    face_monitor = FaceMonitor(
        multiple_face_threshold=1.0,
        no_face_threshold=2.0
    )
    
    eye_monitor = EyeMonitor(
        closure_threshold=0.20,
        closed_duration_threshold=2.0
    )
    
    logger = EventLogger(
        "data/exam_monitoring.db"
    )
    session_id = logger.start_session()

    print("\n===================================")
    print("       EXAM SESSION STARTED")
    print("===================================")
    print(f"Session ID: {session_id}")
    print("===================================\n")

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

    last_event = None
    last_event_time = 0

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

            # ==========================================
            # FACE DETECTED
            # ==========================================

            if result.face_landmarks:

                h, w, _ = frame.shape

                face = result.face_landmarks[0]
                
                # ==========================================
# EYE MONITOR
# ==========================================

                eye_state = eye_monitor.update(
                    face,
                    time.time()
                )

                eye_status = eye_state["state"]

                eye_event = eye_state["event"]

                if eye_event is not None:

                    last_event = eye_event
                    last_event_time = time.time()

                    print(
                        "\n🚨 EYE EVENT:",
                        eye_event
                    )

                    logger.log_event(eye_event)

                pitch, yaw = head_pose.get_pose(
                    face,
                    w,
                    h
                )

                # ==========================================
                # CALIBRATION
                # ==========================================

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
                    
                    cv2.putText(
                        frame,
                        f"Eyes: {eye_status}",
                        (20, 365),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (255, 255, 0),
                        2
                    )
                    
                    cv2.putText(
                        frame,
                        f"EAR: {eye_state['average_ear']:.3f}",
                        (20, 400),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 255, 0),
                        2
                    )

                    if progress >= CALIBRATION_FRAMES:

                        neutral_pitch = head_pose.circular_mean(
                            calibration_pitch
                        )

                        neutral_yaw = head_pose.circular_mean(
                            calibration_yaw
                        )

                        head_pose.set_neutral(
                            neutral_pitch,
                            neutral_yaw
                        )

                        calibrated = True

                        print("\nCalibration complete!")
                        print(
                            f"Neutral Pitch: {neutral_pitch:.2f}"
                        )
                        print(
                            f"Neutral Yaw: {neutral_yaw:.2f}"
                        )

                # ==========================================
                # HEAD POSE
                # ==========================================

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

                # ==========================================
                # DRAW LANDMARKS
                # ==========================================

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

            # ==========================================
            # UPDATE ATTENTION TRACKER
            # ==========================================

            # ==========================================
# ATTENTION TRACKER
# ==========================================

            if calibrated:

                attention_event = tracker.update(direction)

                if attention_event is not None:

                    last_event = attention_event
                    last_event_time = time.time()

                    print(
                        "\n🚨 ATTENTION EVENT:",
                        attention_event
                    )

                    logger.log_event(attention_event)


# ==========================================
# FACE MONITOR
# ==========================================

            face_count = 0

            if result.face_landmarks:
                face_count = len(result.face_landmarks)

            face_event = face_monitor.update(
                face_count=face_count,
                current_time=time.time()
            )

            if face_event is not None:

                last_event = face_event
                last_event_time = time.time()

                print(
                    "\n🚨 FACE EVENT:",
                    face_event
                )

                logger.log_event(face_event)

            # ==========================================
            # FPS
            # ==========================================

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

            # ==========================================
            # DIRECTION
            # ==========================================

            cv2.putText(
                frame,
                f"Direction: {direction}",
                (20, 190),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 0),
                2
            )
            
            cv2.putText(
                frame,
                f"Faces: {face_count}",
                (20, 330),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 0),
                2
            )

            # ==========================================
            # RELATIVE POSE
            # ==========================================

            if calibrated and relative_pitch is not None:

                cv2.putText(
                    frame,
                    f"Rel Pitch: {relative_pitch:.1f}",
                    (20, 225),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2
                )

                cv2.putText(
                    frame,
                    f"Rel Yaw: {relative_yaw:.1f}",
                    (20, 255),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2
                )

            # ==========================================
            # ATTENTION STATUS
            # ==========================================

            if face_count == 0:

                status = "NO FACE"

            elif face_count > 1:

                status = "MULTIPLE FACES"

            elif direction == "CENTER":

                status = "NORMAL"

            else:

                duration = tracker.get_away_duration()

                status = (
                    f"LOOKING AWAY: {duration:.1f}s"
                )

            cv2.putText(
                frame,
                f"Status: {status}",
                (20, 295),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )

            # ==========================================
            # LAST EVENT
            # ==========================================

            if last_event is not None:

                # Keep event visible for 4 seconds
                if time.time() - last_event_time < 4:

                    event_text = last_event["type"]

                    cv2.putText(
                        frame,
                        f"EVENT: {event_text}",
                        (20, 335),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 0, 255),
                        2
                    )

            # ==========================================
            # DISPLAY
            # ==========================================

            cv2.imshow(
                "AI Exam Monitoring - Attention Monitor",
                frame
            )

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:

        cap.release()
        face_landmarker.close()
        
        cv2.destroyAllWindows()
        
        logger.end_session()
        logger.close()


if __name__ == "__main__":
    main()