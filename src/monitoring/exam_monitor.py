import time

import cv2

from src.face.face_landmarker import FaceLandmarker
from src.face.head_pose import HeadPoseEstimator
from src.monitoring.attention_tracker import AttentionTracker
from src.monitoring.event_logger import EventLogger
from src.monitoring.face_monitor import FaceMonitor
from src.eyes.eye_monitor import EyeMonitor


MODEL_PATH = "models/face/face_landmarker.task"
CALIBRATION_FRAMES = 75


class ExamMonitor:

    def __init__(self, camera_index=0):

        self.camera_index = camera_index

        # ==========================================
        # AI COMPONENTS
        # ==========================================

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

        # ==========================================
        # EVENT LOGGER
        # ==========================================

        self.logger = EventLogger(
            "data/exam_monitoring.db"
        )

        self.session_id = None

        # ==========================================
        # CAMERA
        # ==========================================

        self.cap = None

        # ==========================================
        # CALIBRATION
        # ==========================================

        self.calibration_pitch = []
        self.calibration_yaw = []

        self.calibrated = False

        # ==========================================
        # FRAME DATA
        # ==========================================

        # IMPORTANT:
        # Do NOT reset this inside start().
        # MediaPipe requires timestamps to be
        # monotonically increasing.
        self.timestamp_ms = 0

        self.frame_count = 0
        self.start_time = None

        # ==========================================
        # CURRENT STATE
        # ==========================================

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

    # ==========================================
    # START EXAM
    # ==========================================

    def start(self):

        # ------------------------------------------
        # START DATABASE SESSION
        # ------------------------------------------

        self.session_id = (
            self.logger.start_session()
        )

        # ------------------------------------------
        # RESET MONITOR COMPONENTS
        # ------------------------------------------

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

        # ------------------------------------------
        # OPEN CAMERA
        # ------------------------------------------

        self.cap = cv2.VideoCapture(
            self.camera_index
        )

        if not self.cap.isOpened():

            self.logger.end_session()

            raise RuntimeError(
                "Could not open webcam."
            )

        # ------------------------------------------
        # RESET CALIBRATION
        # ------------------------------------------

        self.calibration_pitch = []
        self.calibration_yaw = []

        self.calibrated = False

        # ------------------------------------------
        # RESET FRAME STATE
        # ------------------------------------------

        # DO NOT RESET timestamp_ms HERE.
        #
        # MediaPipe FaceLandmarker is being reused,
        # so timestamps must continue increasing.

        self.frame_count = 0
        self.start_time = time.time()

        # ------------------------------------------
        # RESET CURRENT STATE
        # ------------------------------------------

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

        return self.session_id

    # ==========================================
    # PROCESS ONE FRAME
    # ==========================================

    def process_frame(self):

        if self.cap is None:

            raise RuntimeError(
                "Exam session has not been started."
            )

        # Clear previous event.
        # If a new event occurs during this frame,
        # _register_event() will replace it.
        self.last_event = None

        # ------------------------------------------
        # READ CAMERA FRAME
        # ------------------------------------------

        success, frame = self.cap.read()

        if not success:

            return None

        frame = cv2.flip(
            frame,
            1
        )

        # ------------------------------------------
        # FACE LANDMARKS
        # ------------------------------------------

        result = self.face_landmarker.process(
            frame,
            self.timestamp_ms
        )

        self.pitch = None
        self.yaw = None

        self.relative_pitch = None
        self.relative_yaw = None

        self.direction = "NO FACE"
        self.face_count = 0

        # ------------------------------------------
        # FACE DETECTION
        # ------------------------------------------

        if result.face_landmarks:

            h, w, _ = frame.shape

            self.face_count = len(
                result.face_landmarks
            )

            face = result.face_landmarks[0]

            # ======================================
            # EYE MONITOR
            # ======================================

            eye_state = self.eye_monitor.update(
                face,
                time.time()
            )

            self.eye_status = eye_state["state"]

            self.average_ear = (
                eye_state["average_ear"]
            )

            eye_event = eye_state["event"]

            if eye_event is not None:

                self._register_event(
                    eye_event
                )

            # ======================================
            # HEAD POSE
            # ======================================

            self.pitch, self.yaw = (
                self.head_pose.get_pose(
                    face,
                    w,
                    h
                )
            )

            # ======================================
            # CALIBRATION
            # ======================================

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
                    f"{progress}/{CALIBRATION_FRAMES}"
                )

                if progress >= CALIBRATION_FRAMES:

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

            # ======================================
            # HEAD DIRECTION
            # ======================================

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

            # ======================================
            # DRAW LANDMARKS
            # ======================================

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

        # ==========================================
        # ATTENTION TRACKER
        # ==========================================

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

        # ==========================================
        # FACE MONITOR
        # ==========================================

        face_event = self.face_monitor.update(
            face_count=self.face_count,
            current_time=time.time()
        )

        if face_event is not None:

            self._register_event(
                face_event
            )

        # ==========================================
        # STATUS
        # ==========================================

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

        # ==========================================
        # FPS
        # ==========================================

        self.frame_count += 1

        # IMPORTANT:
        # Keep increasing timestamp for MediaPipe.
        self.timestamp_ms += 33

        elapsed = (
            time.time() - self.start_time
        )

        fps = (
            self.frame_count / elapsed
            if elapsed > 0
            else 0
        )

        # ==========================================
        # RETURN STATE
        # ==========================================

        state = {

            "frame": frame,

            "session_id": self.session_id,

            "fps": fps,

            "face_count": self.face_count,

            "direction": self.direction,

            "status": self.status,

            "eye_status": self.eye_status,

            "average_ear": self.average_ear,

            "pitch": self.pitch,

            "yaw": self.yaw,

            "relative_pitch": (
                self.relative_pitch
            ),

            "relative_yaw": (
                self.relative_yaw
            ),

            "last_event": self.last_event,

            "calibrated": self.calibrated,

            "calibration_progress": len(
                self.calibration_pitch
            ),
        }

        return state

    # ==========================================
    # EVENT HANDLING
    # ==========================================

    def _register_event(self, event):

        self.last_event = event

        self.last_event_time = time.time()

        self.logger.log_event(
            event
        )

    # ==========================================
    # STOP EXAM
    # ==========================================

    def stop(self):

        # ------------------------------------------
        # RELEASE CAMERA
        # ------------------------------------------

        if self.cap is not None:

            self.cap.release()

            self.cap = None

        # ------------------------------------------
        # END DATABASE SESSION
        # ------------------------------------------

        if self.session_id is not None:

            self.logger.end_session()

        self.status = "COMPLETED"

    # ==========================================
    # GET CURRENT STATE
    # ==========================================

    def get_state(self):

        return {

            "session_id": self.session_id,

            "face_count": self.face_count,

            "direction": self.direction,

            "status": self.status,

            "eye_status": self.eye_status,

            "average_ear": self.average_ear,

            "fps": (
                self.frame_count /
                (time.time() - self.start_time)
                if self.start_time
                else 0
            ),

            "calibrated": self.calibrated,

            "last_event": self.last_event,
        }

    # ==========================================
    # FINAL CLEANUP
    # ==========================================

    def close(self):

        # ------------------------------------------
        # RELEASE CAMERA
        # ------------------------------------------

        if self.cap is not None:

            self.cap.release()

            self.cap = None

        # ------------------------------------------
        # CLOSE MEDIAPIPE
        # ------------------------------------------

        if self.face_landmarker is not None:

            self.face_landmarker.close()

            self.face_landmarker = None

        # ------------------------------------------
        # CLOSE DATABASE
        # ------------------------------------------

        if self.logger is not None:

            self.logger.close()

            self.logger = None