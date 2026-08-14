import math
import time


class EyeMonitor:

    # MediaPipe Face Landmarker eye landmarks
    LEFT_EYE = [362, 385, 387, 263, 373, 380]
    RIGHT_EYE = [33, 160, 158, 133, 153, 144]

    def __init__(
        self,
        closure_threshold=0.20,
        closed_duration_threshold=2.0
    ):
        self.closure_threshold = closure_threshold
        self.closed_duration_threshold = (
            closed_duration_threshold
        )

        self.closed_start_time = None
        self.eye_closed_event_active = False

    def _distance(self, p1, p2):

        return math.sqrt(
            (p1.x - p2.x) ** 2 +
            (p1.y - p2.y) ** 2
        )

    def _eye_aspect_ratio(
        self,
        landmarks,
        indices
    ):

        p1 = landmarks[indices[0]]
        p2 = landmarks[indices[1]]
        p3 = landmarks[indices[2]]
        p4 = landmarks[indices[3]]
        p5 = landmarks[indices[4]]
        p6 = landmarks[indices[5]]

        vertical_1 = self._distance(p2, p6)
        vertical_2 = self._distance(p3, p5)

        horizontal = self._distance(p1, p4)

        if horizontal == 0:
            return 0.0

        return (
            vertical_1 + vertical_2
        ) / (2.0 * horizontal)

    def get_eye_ratios(self, landmarks):

        left_ear = self._eye_aspect_ratio(
            landmarks,
            self.LEFT_EYE
        )

        right_ear = self._eye_aspect_ratio(
            landmarks,
            self.RIGHT_EYE
        )

        return left_ear, right_ear

    def get_eye_state(self, landmarks):

        left_ear, right_ear = (
            self.get_eye_ratios(landmarks)
        )

        average_ear = (
            left_ear + right_ear
        ) / 2.0

        if average_ear < self.closure_threshold:
            state = "CLOSED"
        else:
            state = "OPEN"

        return {
            "state": state,
            "left_ear": left_ear,
            "right_ear": right_ear,
            "average_ear": average_ear
        }

    def update(
        self,
        landmarks,
        current_time=None
    ):

        if current_time is None:
            current_time = time.time()

        eye_state = self.get_eye_state(
            landmarks
        )

        state = eye_state["state"]

        event = None

        if state == "CLOSED":

            if self.closed_start_time is None:
                self.closed_start_time = current_time

            duration = (
                current_time -
                self.closed_start_time
            )

            if (
                duration >=
                self.closed_duration_threshold
                and
                not self.eye_closed_event_active
            ):

                self.eye_closed_event_active = True

                event = {
                    "type": "EYES_CLOSED",
                    "duration": duration
                }

        else:

            self.closed_start_time = None
            self.eye_closed_event_active = False

        eye_state["event"] = event

        return eye_state