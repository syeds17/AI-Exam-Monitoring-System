import threading
import time

import cv2

from src.monitoring.exam_monitor import ExamMonitor


class MonitoringService:

    def __init__(self):

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

        self.session_id = None

        self.last_error = None

        # Persistent events for the current session.
        self.event_history = []

        self.event_sequence = 0

        self._event_active = False
        self._last_event_signature = None

    # --------------------------------------------------
    # START
    # --------------------------------------------------

    def start(self):

        if self.running:
            return self.session_id

        self.monitor = ExamMonitor()

        self.session_id = self.monitor.start()

        self.running = True

        self.last_error = None

        self.latest_frame = None
        self.latest_state = None

        self.frame_sequence = 0

        self.event_history = []

        self.event_sequence = 0

        self._event_active = False
        self._last_event_signature = None

        self.thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )

        self.thread.start()

        return self.session_id

    # --------------------------------------------------
    # MONITOR LOOP
    # --------------------------------------------------

    def _monitor_loop(self):

        while self.running:

            try:

                state = self.monitor.process_frame()

                if state is None:
                    continue

                frame = state.get("frame")

                if frame is None:
                    continue

                # ------------------------------------------
                # Encode frame for browser
                # ------------------------------------------

                success, encoded = cv2.imencode(
                    ".jpg",
                    frame,
                    [
                        cv2.IMWRITE_JPEG_QUALITY,
                        80
                    ]
                )

                if not success:
                    continue

                frame_bytes = encoded.tobytes()

                # ------------------------------------------
                # Extract event
                # ------------------------------------------

                event = self._extract_event(state)

                if event is not None:

                    self._register_event(event)

                # ------------------------------------------
                # Store latest state
                # ------------------------------------------

                clean_state = {
                    key: value
                    for key, value in state.items()
                    if key != "frame"
                }

                with self.frame_condition:

                    self.latest_frame = frame_bytes

                    self.latest_state = clean_state

                    self.frame_sequence += 1

                    self.frame_condition.notify_all()

            except Exception as e:

                self.last_error = str(e)

                self.running = False

                with self.frame_condition:

                    self.frame_condition.notify_all()

                break

    # --------------------------------------------------
    # EVENT EXTRACTION
    # --------------------------------------------------

    def _extract_event(self, state):

        possible_keys = [
            "event",
            "new_event",
            "alert"
        ]

        for key in possible_keys:

            event = state.get(key)

            if isinstance(event, dict):

                return event

        # Some versions may return an events list.
        events = state.get("events")

        if isinstance(events, list) and events:

            last_event = events[-1]

            if isinstance(last_event, dict):

                return last_event

        return None

    # --------------------------------------------------
    # EVENT REGISTRATION
    # --------------------------------------------------

    def _register_event(self, event):

        event_type = event.get(
            "type",
            event.get(
                "event_type",
                "UNKNOWN"
            )
        )

        direction = event.get(
            "direction"
        )

        duration = event.get(
            "duration"
        )

        signature = (
            event_type,
            direction
        )

        # Prevent the same event from being
        # registered repeatedly while it is active.
        if (
            self._event_active
            and signature == self._last_event_signature
        ):
            return

        self.event_sequence += 1

        event_record = {
            "id": self.event_sequence,
            "type": event_type,
            "direction": direction,
            "duration": duration,
            "timestamp": time.strftime(
                "%H:%M:%S"
            ),
            "session_id": self.session_id
        }

        self.event_history.append(
            event_record
        )

        self._event_active = True

        self._last_event_signature = signature

    # --------------------------------------------------
    # FRAME ACCESS
    # --------------------------------------------------

    def get_frame(self):

        with self.lock:

            return self.latest_frame

    # --------------------------------------------------
    # WAIT FOR NEW FRAME
    # --------------------------------------------------

    def wait_for_frame(
        self,
        last_sequence,
        timeout=1.0
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
                or self.frame_sequence
                == last_sequence
            ):

                return None, last_sequence

            return (
                self.latest_frame,
                self.frame_sequence
            )

    # --------------------------------------------------
    # STATE
    # --------------------------------------------------

    def get_state(self):

        with self.lock:

            if self.latest_state is None:
                return None

            return self.latest_state.copy()

    # --------------------------------------------------
    # EVENTS
    # --------------------------------------------------

    def get_events(self):

        with self.lock:

            return [
                event.copy()
                for event in self.event_history
            ]

    # --------------------------------------------------
    # STOP
    # --------------------------------------------------

    def stop(self):

        self.running = False

        with self.frame_condition:

            self.frame_condition.notify_all()

        if self.thread is not None:

            self.thread.join(
                timeout=2.0
            )

            self.thread = None

        if self.monitor is not None:

            try:

                self.monitor.stop()

            except Exception as e:

                self.last_error = str(e)

            self.monitor = None

        session_id = self.session_id

        self.session_id = None

        self.latest_frame = None
        self.latest_state = None

        return session_id

    # --------------------------------------------------
    # STATUS
    # --------------------------------------------------

    def get_status(self):

        with self.lock:

            state = (
                self.latest_state.copy()
                if self.latest_state is not None
                else None
            )

            events = [
                event.copy()
                for event in self.event_history
            ]

            return {
                "running": self.running,
                "session_id": self.session_id,
                "state": state,
                "events": events,
                "error": self.last_error
            }


monitoring_service = MonitoringService()