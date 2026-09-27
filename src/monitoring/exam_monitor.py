import time
import threading

import cv2

from src.camera.threaded_camera import ThreadedCamera
from src.face.face_landmarker import FaceLandmarker
from src.face.head_pose import HeadPoseEstimator
from src.monitoring.attention_tracker import AttentionTracker
from src.monitoring.event_logger import EventLogger
from src.monitoring.face_monitor import FaceMonitor
from src.eyes.eye_monitor import EyeMonitor

from src.detection.person_detector import PersonDetector
from src.detection.detection_worker import DetectionWorker


MODEL_PATH = "models/face/face_landmarker.task"

CALIBRATION_FRAMES = 75


class ExamMonitor:

    def __init__(self, camera_index=0):

        self.camera_index = camera_index

        # ==================================================
        # AI COMPONENTS
        # ==================================================

        self.face_landmarker = FaceLandmarker(
            MODEL_PATH
        )

        self.head_pose = HeadPoseEstimator()

        self.tracker = AttentionTracker(
            looking_away_threshold=3.0
        )

        self.face_monitor = FaceMonitor(
            multiple_face_threshold=1.0,
            no_face_threshold=2.0
        )

        self.eye_monitor = EyeMonitor(
            closure_threshold=0.20,
            closed_duration_threshold=2.0
        )

        # ==================================================
        # YOLO PERSON DETECTION
        # ==================================================

        self.person_detector = PersonDetector(
            model_path="yolo11n.pt",
            confidence=0.50
        )

        self.detection_worker = DetectionWorker(
            detector=self.person_detector,
            detection_interval=0.15
        )

        self.additional_person_start = None
        self.additional_person_active = False

        # ==================================================
        # DATABASE
        # ==================================================

        self.logger = EventLogger(
            "data/exam_monitoring.db"
        )

        self.session_id = None

        # ==================================================
        # THREADED CAMERA
        # ==================================================

        self.camera = ThreadedCamera(
            camera_index=self.camera_index,
            width=1280,
            height=720,
            target_fps=30
        )

        # ==================================================
        # CALIBRATION
        # ==================================================

        self.calibration_pitch = []
        self.calibration_yaw = []

        self.calibrated = False

        # ==================================================
        # TIMESTAMP
        # ==================================================

        self.timestamp_ms = 0

        # ==================================================
        # PROCESS LOCK
        # ==================================================

        self.process_lock = threading.Lock()

        # ==================================================
        # FRAME DATA
        # ==================================================

        self.frame_count = 0
        self.start_time = None

        # ==================================================
        # CURRENT STATE
        # ==================================================

        self.direction = "NO FACE"

        self.status = "NOT STARTED"

        self.face_count = 0

        self.eye_status = "UNKNOWN"

        self.average_ear = 0.0

        self.pitch = None
        self.yaw = None

        self.relative_pitch = None
        self.relative_yaw = None

        self.last_event = None
        self.last_event_time = 0

    # ======================================================
    # START EXAM
    # ======================================================

    def start(self):

        # -----------------------------------------------
        # DATABASE SESSION
        # -----------------------------------------------

        self.session_id = (
            self.logger.start_session()
        )

        # -----------------------------------------------
        # RESET MONITORS
        # -----------------------------------------------

        self.tracker = AttentionTracker(
            looking_away_threshold=3.0
        )

        self.face_monitor = FaceMonitor(
            multiple_face_threshold=1.0,
            no_face_threshold=2.0
        )

        self.eye_monitor = EyeMonitor(
            closure_threshold=0.20,
            closed_duration_threshold=2.0
        )

        self.head_pose = HeadPoseEstimator()

        # -----------------------------------------------
        # RESET CALIBRATION
        # -----------------------------------------------

        self.calibration_pitch = []
        self.calibration_yaw = []

        self.calibrated = False

        # -----------------------------------------------
        # RESET STATE
        # -----------------------------------------------

        self.frame_count = 0

        self.start_time = time.time()

        self.direction = "NO FACE"

        self.status = "CALIBRATING"

        self.face_count = 0

        self.eye_status = "UNKNOWN"

        self.average_ear = 0.0

        self.pitch = None
        self.yaw = None

        self.relative_pitch = None
        self.relative_yaw = None

        self.last_event = None
        self.last_event_time = 0

        self.additional_person_start = None
        self.additional_person_active = False

        # -----------------------------------------------
        # START THREADED CAMERA
        # -----------------------------------------------

        try:

            self.camera.start()

            # -------------------------------------------
            # START YOLO DETECTION WORKER
            # -------------------------------------------

            self.detection_worker.start()

            self.additional_person_start = None

        except Exception:

            self.logger.end_session()

            raise

        return self.session_id

    # ======================================================
    # PROCESS ONE FRAME
    # ======================================================

    def process_frame(self):

        with self.process_lock:

            return self._process_frame()

    # ======================================================
    # INTERNAL FRAME PROCESSING
    # ======================================================

    def _process_frame(self):

        if not self.camera.is_running():

            raise RuntimeError(
                "Camera is not running."
            )

        # Clear event for this frame.
        self.last_event = None

        # -----------------------------------------------
        # GET LATEST CAMERA FRAME
        # -----------------------------------------------

        frame = self.camera.read()

        if frame is None:

            return None

        # Mirror image.
        frame = cv2.flip(
            frame,
            1
        )

        # ==================================================
        # YOLO PERSON DETECTION
        # ==================================================

        # Send the latest frame to the background
        # YOLO worker. This does NOT block the
        # MediaPipe processing pipeline.

        self.detection_worker.update_frame(
            frame
        )

        # Get the latest completed YOLO result.

        detection_result = (
            self.detection_worker.get_result()
        )

        # -----------------------------------------------
        # ADDITIONAL PERSON CONFIRMATION
        # -----------------------------------------------

        additional_person_event = (
            self._check_additional_person(
                detection_result,
                time.monotonic()
            )
        )

        if additional_person_event is not None:

            self._register_event(
                additional_person_event
            )

        # -----------------------------------------------
        # MEDIAPIPE TIMESTAMP
        # -----------------------------------------------

        current_timestamp_ms = int(
            time.monotonic() * 1000
        )

        if (
            current_timestamp_ms
            <= self.timestamp_ms
        ):

            current_timestamp_ms = (
                self.timestamp_ms + 1
            )

        self.timestamp_ms = (
            current_timestamp_ms
        )

        # -----------------------------------------------
        # FACE LANDMARKS
        # -----------------------------------------------

        result = self.face_landmarker.process(
            frame,
            self.timestamp_ms
        )

        # Reset current face state.

        self.pitch = None
        self.yaw = None

        self.relative_pitch = None
        self.relative_yaw = None

        self.direction = "NO FACE"

        self.face_count = 0

        # -----------------------------------------------
        # FACE DETECTION
        # -----------------------------------------------

        if result.face_landmarks:

            h, w, _ = frame.shape

            self.face_count = len(
                result.face_landmarks
            )

            face = result.face_landmarks[0]

            # ==========================================
            # EYE MONITOR
            # ==========================================

            eye_state = (
                self.eye_monitor.update(
                    face,
                    time.time()
                )
            )

            self.eye_status = (
                eye_state["state"]
            )

            self.average_ear = (
                eye_state["average_ear"]
            )

            eye_event = (
                eye_state["event"]
            )

            if eye_event is not None:

                self._register_event(
                    eye_event
                )

            # ==========================================
            # HEAD POSE
            # ==========================================

            (
                self.pitch,
                self.yaw
            ) = self.head_pose.get_pose(
                face,
                w,
                h
            )

            # ==========================================
            # CALIBRATION
            # ==========================================

            if not self.calibrated:

                self.calibration_pitch.append(
                    self.pitch
                )

                self.calibration_yaw.append(
                    self.yaw
                )

                progress = len(
                    self.calibration_pitch
                )

                self.status = (
                    f"CALIBRATING "
                    f"{progress}/"
                    f"{CALIBRATION_FRAMES}"
                )

                if (
                    progress
                    >= CALIBRATION_FRAMES
                ):

                    neutral_pitch = (
                        self.head_pose.circular_mean(
                            self.calibration_pitch
                        )
                    )

                    neutral_yaw = (
                        self.head_pose.circular_mean(
                            self.calibration_yaw
                        )
                    )

                    self.head_pose.set_neutral(
                        neutral_pitch,
                        neutral_yaw
                    )

                    self.calibrated = True

                    self.status = "NORMAL"

                    print(
                        "\nCalibration complete!"
                    )

                    print(
                        f"Neutral Pitch: "
                        f"{neutral_pitch:.2f}"
                    )

                    print(
                        f"Neutral Yaw: "
                        f"{neutral_yaw:.2f}"
                    )

            # ==========================================
            # HEAD DIRECTION
            # ==========================================

            else:

                (
                    self.relative_pitch,
                    self.relative_yaw
                ) = self.head_pose.get_relative_pose(
                    self.pitch,
                    self.yaw
                )

                self.direction = (
                    self.head_pose.get_direction(
                        self.relative_pitch,
                        self.relative_yaw
                    )
                )

            # ==========================================
            # DRAW FACE LANDMARKS
            # ==========================================

            for landmark in face:

                x = int(
                    landmark.x * w
                )

                y = int(
                    landmark.y * h
                )

                if (
                    0 <= x < w
                    and
                    0 <= y < h
                ):

                    cv2.circle(
                        frame,
                        (x, y),
                        1,
                        (0, 255, 0),
                        -1
                    )

        # ==================================================
        # DRAW YOLO PERSON DETECTIONS
        # ==================================================

        for person in detection_result.get(
            "persons",
            []
        ):

            x1, y1, x2, y2 = (
                person["bbox"]
            )

            confidence = (
                person["confidence"]
            )

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (255, 0, 0),
                2
            )

            label = (
                f"Person "
                f"{confidence:.2f}"
            )

            cv2.putText(
                frame,
                label,
                (
                    x1,
                    max(y1 - 10, 20)
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 0, 0),
                2
            )

        # ==================================================
        # PERSON COUNT DISPLAY
        # ==================================================

        person_count = (
            detection_result.get(
                "person_count",
                0
            )
        )

        yolo_fps = (
            self.detection_worker.get_fps()
        )

        cv2.putText(
            frame,
            f"Persons: {person_count}",
            (20, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 0, 0),
            2
        )

        cv2.putText(
            frame,
            f"YOLO FPS: {yolo_fps:.1f}",
            (20, 105),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 0, 0),
            2
        )

        # ==================================================
        # ATTENTION TRACKER
        # ==================================================

        if self.calibrated:

            attention_event = (
                self.tracker.update(
                    self.direction
                )
            )

            if attention_event is not None:

                self._register_event(
                    attention_event
                )

        # ==================================================
        # FACE MONITOR
        # ==================================================

        face_event = (
            self.face_monitor.update(
                face_count=self.face_count,
                current_time=time.time()
            )
        )

        if face_event is not None:

            self._register_event(
                face_event
            )

        # ==================================================
        # STATUS
        # ==================================================

        if self.face_count == 0:

            self.status = "NO FACE"

        elif self.face_count > 1:

            self.status = "MULTIPLE FACES"

        elif not self.calibrated:

            self.status = (
                f"CALIBRATING "
                f"{len(self.calibration_pitch)}/"
                f"{CALIBRATION_FRAMES}"
            )

        elif self.direction == "CENTER":

            self.status = "NORMAL"

        else:

            duration = (
                self.tracker.get_away_duration()
            )

            self.status = (
                f"LOOKING AWAY: "
                f"{duration:.1f}s"
            )

        # ==================================================
        # ADDITIONAL PERSON STATUS
        # ==================================================

        if person_count > 1:

            self.status = "ADDITIONAL PERSON"

        # ==================================================
        # FPS
        # ==================================================

        self.frame_count += 1

        elapsed = (
            time.time()
            - self.start_time
        )

        processing_fps = (
            self.frame_count / elapsed
            if elapsed > 0
            else 0
        )

        capture_fps = (
            self.camera.get_fps()
        )

        # ==================================================
        # RETURN STATE
        # ==================================================

        return {

            "frame": frame,

            "session_id":
                self.session_id,

            "fps":
                processing_fps,

            "capture_fps":
                capture_fps,

            "yolo_fps":
                yolo_fps,

            "face_count":
                self.face_count,

            "person_count":
                person_count,

            "persons":
                detection_result.get(
                    "persons",
                    []
                ),

            "direction":
                self.direction,

            "status":
                self.status,

            "eye_status":
                self.eye_status,

            "average_ear":
                self.average_ear,

            "pitch":
                self.pitch,

            "yaw":
                self.yaw,

            "relative_pitch":
                self.relative_pitch,

            "relative_yaw":
                self.relative_yaw,

            "last_event":
                self.last_event,

            "calibrated":
                self.calibrated,

            "calibration_progress":
                len(
                    self.calibration_pitch
                )
        }

    # ======================================================
    # ADDITIONAL PERSON DETECTION
    # ======================================================

    def _check_additional_person(
        self,
        detection_result,
        current_time
    ):

        person_count = (
            detection_result.get(
                "person_count",
                0
            )
        )

        # --------------------------------------------------
        # One person or no person
        # --------------------------------------------------

        if person_count <= 1:

            self.additional_person_start = None
            self.additional_person_active = False

            return None

        # --------------------------------------------------
        # ADDITIONAL PERSON DETECTED
        # --------------------------------------------------

        if self.additional_person_active:

            return None
        
        # --------------------------------------------------
        # START CONFIRMATION TIMER
        # --------------------------------------------------
        
        if self.additional_person_start is None:
            
            self.additional_person_start = (
                current_time
            )
            
            return None

        # --------------------------------------------------
        # Calculate duration
        # --------------------------------------------------

        duration = (
            current_time
            - self.additional_person_start
        )

        # --------------------------------------------------
        # Confirm after 1 second
        # --------------------------------------------------

        if duration >= 1.0:

            self.additional_person_active = True

            return {
                "type": "ADDITIONAL_PERSON",
                "duration": duration
            }

        return None

    # ======================================================
    # EVENT HANDLING
    # ======================================================

    def _register_event(self, event):

        self.last_event = event

        self.last_event_time = (
            time.time()
        )

        self.logger.log_event(
            event
        )

    # ======================================================
    # STOP
    # ======================================================

    def stop(self):

        # -----------------------------------------------
        # STOP YOLO WORKER
        # -----------------------------------------------

        try:

            self.detection_worker.stop()

        except Exception as e:

            print(
                f"YOLO worker stop warning: {e}"
            )

        # -----------------------------------------------
        # STOP CAMERA
        # -----------------------------------------------

        try:

            self.camera.stop()

        except Exception as e:

            print(
                f"Camera stop warning: {e}"
            )

        # -----------------------------------------------
        # END DATABASE SESSION
        # -----------------------------------------------

        if self.session_id is not None:

            try:

                self.logger.end_session()

            except Exception as e:

                print(
                    f"Session end warning: {e}"
                )

        self.status = "COMPLETED"

    # ======================================================
    # GET STATE
    # ======================================================

    def get_state(self):

        elapsed = 0

        if self.start_time:

            elapsed = (
                time.time()
                - self.start_time
            )

        fps = (
            self.frame_count / elapsed
            if elapsed > 0
            else 0
        )

        detection_result = (
            self.detection_worker.get_result()
        )

        return {

            "session_id":
                self.session_id,

            "face_count":
                self.face_count,

            "person_count":
                detection_result.get(
                    "person_count",
                    0
                ),

            "persons":
                detection_result.get(
                    "persons",
                    []
                ),

            "direction":
                self.direction,

            "status":
                self.status,

            "eye_status":
                self.eye_status,

            "average_ear":
                self.average_ear,

            "fps":
                fps,

            "capture_fps":
                self.camera.get_fps(),

            "yolo_fps":
                self.detection_worker.get_fps(),

            "calibrated":
                self.calibrated,

            "last_event":
                self.last_event
        }

    # ======================================================
    # FINAL CLEANUP
    # ======================================================

    def close(self):

        # -----------------------------------------------
        # STOP YOLO WORKER
        # -----------------------------------------------

        try:

            self.detection_worker.stop()

        except Exception:
            pass

        # -----------------------------------------------
        # STOP CAMERA
        # -----------------------------------------------

        try:

            self.camera.stop()

        except Exception:
            pass

        # -----------------------------------------------
        # CLOSE FACE LANDMARKER
        # -----------------------------------------------

        if self.face_landmarker is not None:

            try:

                self.face_landmarker.close()

            except Exception:
                pass

            self.face_landmarker = None

        # -----------------------------------------------
        # CLOSE DATABASE LOGGER
        # -----------------------------------------------

        if self.logger is not None:

            try:

                self.logger.close()

            except Exception:
                pass

            self.logger = None