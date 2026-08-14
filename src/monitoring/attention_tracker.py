import time


class AttentionTracker:

    def __init__(self, looking_away_threshold=3.0):

        self.looking_away_threshold = looking_away_threshold

        # Current direction
        self.current_direction = "CENTER"

        # When the current away period started
        self.away_start_time = None

        # Prevents the same continuous away period
        # from generating multiple events
        self.away_event_active = False

    # ==========================================
    # UPDATE
    # ==========================================

    def update(self, direction, current_time=None):

        if current_time is None:
            current_time = time.time()

        # --------------------------------------
        # NO FACE
        # --------------------------------------
        #
        # FaceMonitor handles NO FACE.
        # AttentionTracker simply ignores it.
        #

        if direction == "NO FACE":

            return None

        # --------------------------------------
        # CENTER
        # --------------------------------------

        if direction == "CENTER":

            self.current_direction = "CENTER"

            self.away_start_time = None

            self.away_event_active = False

            return None

        # --------------------------------------
        # DIRECTION CHANGED
        # --------------------------------------

        if direction != self.current_direction:

            self.current_direction = direction

            self.away_start_time = current_time

            self.away_event_active = False

            return None

        # --------------------------------------
        # START NEW AWAY PERIOD
        # --------------------------------------

        if self.away_start_time is None:

            self.away_start_time = current_time

            self.away_event_active = False

        # --------------------------------------
        # CALCULATE DURATION
        # --------------------------------------

        duration = (
            current_time - self.away_start_time
        )

        # --------------------------------------
        # GENERATE EVENT
        # --------------------------------------

        if (
            duration >= self.looking_away_threshold
            and not self.away_event_active
        ):

            self.away_event_active = True

            return {
                "type": "LOOKING_AWAY",
                "direction": self.current_direction,
                "duration": duration
            }

        return None

    # ==========================================
    # GET AWAY DURATION
    # ==========================================

    def get_away_duration(self, current_time=None):

        if current_time is None:
            current_time = time.time()

        if self.away_start_time is None:

            return 0.0

        return (
            current_time - self.away_start_time
        )

    # ==========================================
    # RESET
    # ==========================================

    def reset(self):

        self.current_direction = "CENTER"

        self.away_start_time = None

        self.away_event_active = False