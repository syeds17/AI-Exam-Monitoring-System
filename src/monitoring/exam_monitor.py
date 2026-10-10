import time
import threading
import os
import re

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
from src.detection.object_detector import ObjectDetector
from src.detection.object_detection_worker import ObjectDetectionWorker


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

        # ==================================================
        # YOLO OBJECT DETECTION
        # ==================================================

        self.object_detector = ObjectDetector(
            model_path=(
                "runs/detect/runs/object_detection/"
                "exam_objects_v1/weights/best.pt"
            ),
            confidence=0.40,
            image_size=640,
            device="cpu"
        )

        self.object_detection_worker = ObjectDetectionWorker(
            detector=self.object_detector,
            detection_interval=0.30
        )

        self.detected_objects = []
        self.object_count = 0
        self.object_detection_fps = 0.0
        # Object event confirmation state
        self._object_tracking = {}
        self._last_object_result_sequence = 0

        self.OBJECT_MIN_CONFIDENCE = 0.65
        self.OBJECT_MIN_HITS = 3
        self.OBJECT_CONFIRM_SECONDS = 0.8
        self.OBJECT_ABSENCE_RESET_SECONDS = 1.2

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

        # Current processed frame used for one-time monitoring evidence capture.
        self.current_frame = None

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

        self.current_frame = None

        self.additional_person_start = None
        self.additional_person_active = False

        self.detected_objects = []
        self.object_count = 0
        self.object_detection_fps = 0.0

        # -----------------------------------------------
        # START THREADED CAMERA
        # -----------------------------------------------

        try:

            self.camera.start()

            # -------------------------------------------
            # START YOLO PERSON DETECTION WORKER
            # -------------------------------------------

            self.detection_worker.start()

            # -------------------------------------------
            # START YOLO OBJECT DETECTION WORKER
            # -------------------------------------------

            self.object_detection_worker.start()

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

        # Keep the latest displayed frame so confirmed events can save
        # exactly one monitoring-evidence image.
        self.current_frame = frame.copy()

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

        # ==================================================
        # YOLO OBJECT DETECTION
        # ==================================================

        # Send the latest frame to the background object
        # detector. Object inference must not block the
        # MediaPipe face/eye/head-pose pipeline.

        self.object_detection_worker.update_frame(
            frame
        )

        object_detection_result = (
            self.object_detection_worker.get_result()
        )

        self.object_count = object_detection_result.get(
            "object_count",
            0
        )

        self.detected_objects = (
            object_detection_result.get("objects", [])
        )

        self.object_detection_fps = (
            self.object_detection_worker.get_fps()
        )
        
# Keep person detection data for monitoring logic.
        person_count = detection_result.get("person_count", 0)
        yolo_fps = self.detection_worker.get_fps()

        self._check_object_events(object_detection_result)

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

            "object_count":
                self.object_count,

            "objects":
                self.detected_objects,

            "object_detection_fps":
                self.object_detection_fps,

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

        # --------------------------------------------------
        # CAPTURE ONE MONITORING-EVIDENCE IMAGE
        # --------------------------------------------------
        # Evidence is captured only when an event is confirmed.
        # We do not save every webcam frame.
        event = dict(event)

        evidence_path = self._capture_evidence(
            event
        )

        if evidence_path is not None:
            event["evidence_path"] = evidence_path

        self.last_event = event

        self.last_event_time = (
            time.time()
        )

        self.logger.log_event(
            event
        )
        
    
    def _check_object_events(self, detection_result):
        """Create one event after an object is consistently detected."""

        sequence = detection_result.get("result_sequence", 0)

    # Ignore the same inference result being read repeatedly.
        if sequence == self._last_object_result_sequence:
            return

        self._last_object_result_sequence = sequence

        now = time.monotonic()
        objects = detection_result.get("objects", [])

    # Keep the highest-confidence detection for each class.
        current_objects = {}

        for obj in objects:
            class_name = obj.get("class_name")
            confidence = float(obj.get("confidence", 0.0))

            if not class_name or confidence < self.OBJECT_MIN_CONFIDENCE:
                continue

            previous = current_objects.get(class_name)

            if previous is None or confidence > previous["confidence"]:
                current_objects[class_name] = obj

    # Start or update the confirmation timer for each class.
        for class_name, obj in current_objects.items():
            confidence = float(obj["confidence"])
            state = self._object_tracking.get(class_name)

            if (
                state is None
                or now - state["last_seen"] > self.OBJECT_ABSENCE_RESET_SECONDS
            ):
                state = {
                    "start": now,
                    "last_seen": now,
                    "hits": 1,
                    "active": False,
                    "confidence": confidence,
                }
                self._object_tracking[class_name] = state
                continue

            state["last_seen"] = now
            state["hits"] += 1
            state["confidence"] = max(state["confidence"], confidence)

            duration = now - state["start"]

            if (
                not state["active"]
                and state["hits"] >= self.OBJECT_MIN_HITS
                and duration >= self.OBJECT_CONFIRM_SECONDS
            ):
                state["active"] = True

                self._register_event({
                    "type": "OBJECT_DETECTED",
                    "direction": class_name,
                    "duration": round(duration, 2),
                })

                print(
                    f"Confirmed object event: {class_name} "
                    f"(confidence={state['confidence']:.2f}, "
                    f"duration={duration:.2f}s)"
                )

    # Reset a detection episode after the object has disappeared.
        for class_name, state in list(self._object_tracking.items()):
            if (
                class_name not in current_objects
                and now - state["last_seen"]
                > self.OBJECT_ABSENCE_RESET_SECONDS
            ):
                del self._object_tracking[class_name]
    

    def _capture_evidence(self, event):
        """Save one evidence image for a confirmed monitoring event."""

        if self.current_frame is None:
            return None

        if self.session_id is None:
            return None

        try:
            session_dir = os.path.join(
                "data",
                "evidence",
                str(self.session_id)
            )

            os.makedirs(
                session_dir,
                exist_ok=True
            )

            event_type = str(
                event.get("type", "EVENT")
            )

            direction = str(
                event.get("direction", "")
            )

            # Keep filenames Windows-safe and easy to identify.
            label = (
                f"{event_type}_{direction}"
                if direction
                else event_type
            )

            label = re.sub(
                r"[^A-Za-z0-9_-]+",
                "_",
                label
            ).strip("_")

            timestamp = time.strftime(
                "%Y%m%d_%H%M%S"
            )

            milliseconds = int(
                (time.time() % 1) * 1000
            )

            filename = (
                f"{timestamp}_{milliseconds:03d}"
                f"_{label}.jpg"
            )

            full_path = os.path.join(
                session_dir,
                filename
            )

            saved = cv2.imwrite(
                full_path,
                self.current_frame
            )

            if not saved:
                print(
                    f"Evidence save failed: {full_path}"
                )
                return None

            print(
                f"Evidence captured: {full_path}"
            )

            # Store a project-relative path in SQLite.
            return os.path.relpath(
                full_path
            ).replace(os.sep, "/")

        except Exception as e:

            print(
                f"Evidence capture warning: {e}"
            )

            return None

    # ======================================================
    # STOP
    # ======================================================

    def stop(self):

        # -----------------------------------------------
        # STOP YOLO OBJECT DETECTION WORKER
        # -----------------------------------------------

        try:

            self.object_detection_worker.stop()

        except Exception as e:

            print(
                f"Object detection worker stop warning: {e}"
            )

        # -----------------------------------------------
        # STOP YOLO PERSON DETECTION WORKER
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

            "object_count":
                self.object_detection_worker.get_result().get(
                    "object_count",
                    0
                ),

            "objects":
                self.object_detection_worker.get_result().get(
                    "objects",
                    []
                ),

            "object_detection_fps":
                self.object_detection_worker.get_fps(),

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
        # STOP YOLO OBJECT DETECTION WORKER
        # -----------------------------------------------

        try:

            self.object_detection_worker.stop()

        except Exception:
            pass

        # -----------------------------------------------
        # CLOSE YOLO OBJECT DETECTOR
        # -----------------------------------------------

        try:

            self.object_detector.close()

        except Exception:
            pass

        # -----------------------------------------------
        # STOP YOLO PERSON DETECTION WORKER
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