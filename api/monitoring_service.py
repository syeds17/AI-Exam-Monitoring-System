import threading
import time

import cv2

from src.monitoring.exam_monitor import ExamMonitor
from src.monitoring.assessment_manager import AssessmentManager


class MonitoringService:

    def __init__(self):

        # ======================================================
        # MONITOR
        # ======================================================

        self.monitor = None

        self.running = False
        self.thread = None

        self.lock = threading.Lock()

        self.frame_condition = threading.Condition(
            self.lock
        )

        self.latest_frame = None
        self.latest_state = None

        self.frame_sequence = 0

        # ======================================================
        # CURRENT SESSION
        # ======================================================

        self.session_id = None

        self.assessment_id = None

        self.candidate_record_id = None

        self.last_error = None

        # ======================================================
        # EVENT HISTORY
        # ======================================================

        self.event_history = []

        self.event_sequence = 0

        # ======================================================
        # ASSESSMENT MANAGER
        # ======================================================

        self.assessment_manager = AssessmentManager(
            "data/exam_monitoring.db"
        )

    # ==========================================================
    # ASSESSMENTS
    # ==========================================================

    def create_assessment(
        self,
        assessment_name: str,
        organization: str,
        assessment_type: str,
        scheduled_at: str | None,
        duration_minutes: int,
        candidate_limit: int = 50,
    ):

        return self.assessment_manager.create_assessment(
            assessment_name=assessment_name,
            organization=organization,
            assessment_type=assessment_type,
            scheduled_at=scheduled_at,
            duration_minutes=duration_minutes,
            candidate_limit=candidate_limit,
        )

    def get_assessments(self):

        return self.assessment_manager.get_assessments()

    def get_assessment(
        self,
        assessment_id: str
    ):

        return self.assessment_manager.get_assessment(
            assessment_id
        )

    def get_assessment_by_access_token(
        self,
        access_token: str
    ):

        return (
            self.assessment_manager
            .get_assessment_by_access_token(
                access_token
            )
        )

    # ==========================================================
    # ASSESSMENT LIFECYCLE
    # ==========================================================

    def activate_assessment(
        self,
        assessment_id: str
    ):

        return (
            self.assessment_manager
            .activate_assessment(
                assessment_id
            )
        )

    def deactivate_assessment(
        self,
        assessment_id: str
    ):

        return (
            self.assessment_manager
            .deactivate_assessment(
                assessment_id
            )
        )

    # ==========================================================
    # CANDIDATES
    # ==========================================================

    def request_candidate_access(
        self,
        assessment_id: str,
        candidate_name: str,
        candidate_id: str = "",
    ):

        return (
            self.assessment_manager
            .request_candidate_access(
                assessment_id=assessment_id,
                candidate_name=candidate_name,
                candidate_id=candidate_id,
            )
        )

    def get_candidates(
        self,
        assessment_id: str
    ):

        return (
            self.assessment_manager
            .get_candidates(
                assessment_id
            )
        )

    def get_candidate(
        self,
        assessment_id: str,
        candidate_record_id: str
    ):

        return (
            self.assessment_manager
            .get_candidate(
                assessment_id=assessment_id,
                candidate_record_id=candidate_record_id,
            )
        )

    def get_candidate_by_access_code(
        self,
        access_code: str
    ):

        return (
            self.assessment_manager
            .get_candidate_by_access_code(
                access_code
            )
        )

    def approve_candidate(
        self,
        assessment_id: str,
        candidate_record_id: str
    ):

        return (
            self.assessment_manager
            .approve_candidate(
                assessment_id=assessment_id,
                candidate_record_id=candidate_record_id,
            )
        )

    def reject_candidate(
        self,
        assessment_id: str,
        candidate_record_id: str
    ):

        return (
            self.assessment_manager
            .reject_candidate(
                assessment_id=assessment_id,
                candidate_record_id=candidate_record_id,
            )
        )

    def get_candidate_counts(
        self,
        assessment_id: str
    ):

        return (
            self.assessment_manager
            .get_candidate_counts(
                assessment_id
            )
        )

    # ==========================================================
    # START CANDIDATE MONITORING
    # ==========================================================

    def start(
        self,
        assessment_id: str,
        candidate_record_id: str,
    ):

        # ------------------------------------------------------
        # PREVENT DUPLICATE START
        # ------------------------------------------------------

        if self.running:

            if (
                self.assessment_id == assessment_id
                and
                self.candidate_record_id
                == candidate_record_id
            ):
                return self.session_id

            raise ValueError(
                "Another candidate monitoring session is already running."
            )

        # ------------------------------------------------------
        # ASSESSMENT VALIDATION
        # ------------------------------------------------------

        assessment = (
            self.assessment_manager
            .get_assessment(
                assessment_id
            )
        )

        if assessment is None:

            raise ValueError(
                "Assessment not found."
            )

        if assessment["status"] != "ACTIVE":

            raise ValueError(
                "Assessment is not active."
            )

        # ------------------------------------------------------
        # CANDIDATE VALIDATION
        # ------------------------------------------------------

        candidate = (
            self.assessment_manager
            .get_candidate(
                assessment_id=assessment_id,
                candidate_record_id=candidate_record_id,
            )
        )

        if candidate is None:

            raise ValueError(
                "Candidate not found."
            )

        if candidate["assignment_status"] != "AUTHORIZED":

            raise ValueError(
                "Candidate is not authorized."
            )

        # ------------------------------------------------------
        # CREATE MONITOR
        # ------------------------------------------------------

        self.monitor = ExamMonitor()

        try:

            self.session_id = (
                self.monitor.start()
            )

        except Exception:

            self.monitor = None

            raise

        # ------------------------------------------------------
        # STORE CURRENT SESSION
        # ------------------------------------------------------

        self.assessment_id = assessment_id

        self.candidate_record_id = (
            candidate_record_id
        )

        # ------------------------------------------------------
        # LINK SESSION TO CANDIDATE
        # ------------------------------------------------------

        self.assessment_manager.link_session(
            assessment_id,
            self.session_id,
            candidate_record_id,
        )

        # ------------------------------------------------------
        # MARK CANDIDATE STARTED
        # ------------------------------------------------------

        self.assessment_manager.mark_candidate_started(
            assessment_id=assessment_id,
            candidate_record_id=candidate_record_id,
        )

        # ------------------------------------------------------
        # RESET SERVICE STATE
        # ------------------------------------------------------

        self.running = True

        self.last_error = None

        self.latest_frame = None

        self.latest_state = None

        self.frame_sequence = 0

        self.event_history = []

        self.event_sequence = 0

        # ------------------------------------------------------
        # START MONITOR THREAD
        # ------------------------------------------------------

        self.thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
        )

        self.thread.start()

        return self.session_id

    # ==========================================================
    # MONITOR LOOP
    # ==========================================================

    def _monitor_loop(self):

        while self.running:

            try:

                state = (
                    self.monitor.process_frame()
                )

                if state is None:

                    continue

                frame = state.get(
                    "frame"
                )

                if frame is None:

                    continue

                # ----------------------------------------------
                # PROCESS NEW EVENT
                # ----------------------------------------------

                event = state.get(
                    "last_event"
                )

                if event is not None:

                    self._register_event(
                        event
                    )

                # ----------------------------------------------
                # ENCODE FRAME
                # ----------------------------------------------

                success, encoded = cv2.imencode(
                    ".jpg",
                    frame,
                    [
                        cv2.IMWRITE_JPEG_QUALITY,
                        80,
                    ],
                )

                if not success:

                    continue

                frame_bytes = (
                    encoded.tobytes()
                )

                # ----------------------------------------------
                # CLEAN STATE
                # ----------------------------------------------

                clean_state = {

                    key: value

                    for key, value
                    in state.items()

                    if key != "frame"
                }

                # ----------------------------------------------
                # UPDATE SHARED STATE
                # ----------------------------------------------

                with self.frame_condition:

                    self.latest_frame = (
                        frame_bytes
                    )

                    self.latest_state = (
                        clean_state
                    )

                    self.frame_sequence += 1

                    self.frame_condition.notify_all()

            except Exception as error:

                self.last_error = str(
                    error
                )

                self.running = False

                with self.frame_condition:

                    self.frame_condition.notify_all()

                break

    # ==========================================================
    # EVENT REGISTRATION
    # ==========================================================

    def _register_event(
        self,
        event
    ):

        event_type = (
            event.get(
                "type",
                event.get(
                    "event_type",
                    "UNKNOWN",
                ),
            )
        )

        direction = event.get(
            "direction"
        )

        duration = event.get(
            "duration"
        )

        evidence_path = event.get(
            "evidence_path"
        )

        self.event_sequence += 1

        event_record = {

            "id":
                self.event_sequence,

            "type":
                event_type,

            "direction":
                direction,

            "duration":
                duration,

            "timestamp":
                time.strftime(
                    "%H:%M:%S"
                ),

            "session_id":
                self.session_id,

            "assessment_id":
                self.assessment_id,

            "candidate_record_id":
                self.candidate_record_id,

            "evidence_path":
                evidence_path,
        }

        with self.lock:

            self.event_history.append(
                event_record
            )

    # ==========================================================
    # FRAME
    # ==========================================================

    def get_frame(self):

        with self.lock:

            return self.latest_frame

    # ==========================================================
    # WAIT FOR NEW FRAME
    # ==========================================================

    def wait_for_frame(
        self,
        last_sequence,
        timeout=1.0,
    ):

        with self.frame_condition:

            if (
                self.frame_sequence
                == last_sequence
            ):

                self.frame_condition.wait(
                    timeout=timeout
                )

            if (
                self.latest_frame is None
                or
                self.frame_sequence
                == last_sequence
            ):

                return (
                    None,
                    last_sequence,
                )

            return (
                self.latest_frame,
                self.frame_sequence,
            )

    # ==========================================================
    # STATE
    # ==========================================================

    def get_state(self):

        with self.lock:

            if self.latest_state is None:

                return None

            return (
                self.latest_state.copy()
            )

    # ==========================================================
    # EVENTS
    # ==========================================================

    def get_events(self):

        with self.lock:

            return [
                event.copy()
                for event
                in self.event_history
            ]
            
    # ==========================================================
    # GET CANDIDATE REVIEW
    # ==========================================================

    def get_candidate_review(
        self,
        assessment_id,
        candidate_record_id
    ):

        candidate = (
            self.assessment_manager.get_candidate(
                assessment_id,
                candidate_record_id
            )
        )

        if not candidate:
            raise ValueError(
                "Candidate not found"
            )

        # ------------------------------------------------------
        # FIND SESSION
        # ------------------------------------------------------

        connection = (
            self.assessment_manager._connect()
        )

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                assessment_id,
                candidate_record_id,
                session_id,
                created_at
            FROM assessment_sessions
            WHERE assessment_id = ?
              AND candidate_record_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (
                assessment_id,
                candidate_record_id
            )
        )

        row = cursor.fetchone()

        connection.close()

        if row is None:
            return {
                "candidate": candidate,
                "session": None,
                "events": [],
            }

        session = dict(row)

        # ------------------------------------------------------
        # GET PERSISTENT EVENTS
        # ------------------------------------------------------

        events = (
            self.assessment_manager
            .get_events_for_session(
                session["session_id"]
            )
        )

        return {
            "candidate": candidate,
            "session": session,
            "events": events,
        }

    # ==========================================================
    # STOP CANDIDATE MONITORING
    # ==========================================================

    def stop(self):

        self.running = False

        with self.frame_condition:

            self.frame_condition.notify_all()

        # ------------------------------------------------------
        # WAIT FOR MONITOR THREAD
        # ------------------------------------------------------

        if self.thread is not None:

            self.thread.join(
                timeout=2.0
            )

            self.thread = None

        # ------------------------------------------------------
        # SAVE SESSION INFORMATION
        # ------------------------------------------------------

        session_id = self.session_id

        assessment_id = (
            self.assessment_id
        )

        candidate_record_id = (
            self.candidate_record_id
        )

        # ------------------------------------------------------
        # STOP EXAM MONITOR
        # ------------------------------------------------------

        if self.monitor is not None:

            try:

                self.monitor.stop()

            except Exception as error:

                self.last_error = str(
                    error
                )

            self.monitor = None

        # ------------------------------------------------------
        # MARK CANDIDATE COMPLETED
        # ------------------------------------------------------

        if (
            assessment_id is not None
            and
            candidate_record_id is not None
        ):

            try:

                self.assessment_manager.mark_candidate_completed(
                    assessment_id=assessment_id,
                    candidate_record_id=candidate_record_id,
                )

            except Exception as error:

                self.last_error = str(
                    error
                )

        # ------------------------------------------------------
        # CLEAR ACTIVE SESSION
        # ------------------------------------------------------

        self.latest_frame = None

        self.latest_state = None

        self.session_id = None

        self.assessment_id = None

        self.candidate_record_id = None

        return session_id

    # ==========================================================
    # STATUS
    # ==========================================================

    def get_status(self):

        with self.lock:

            state = (
                self.latest_state.copy()
                if self.latest_state is not None
                else None
            )

            events = [
                event.copy()
                for event
                in self.event_history
            ]

            return {

                "running":
                    self.running,

                "session_id":
                    self.session_id,

                "assessment_id":
                    self.assessment_id,

                "candidate_record_id":
                    self.candidate_record_id,

                "state":
                    state,

                "events":
                    events,

                "error":
                    self.last_error,
            }


# ==========================================================
# GLOBAL SERVICE INSTANCE
# ==========================================================

monitoring_service = MonitoringService()