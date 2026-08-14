class FaceMonitor:

    def __init__(
        self,
        multiple_face_threshold=1.0,
        no_face_threshold=2.0
    ):
        self.multiple_face_threshold = multiple_face_threshold
        self.no_face_threshold = no_face_threshold

        # Timers
        self.multiple_face_start_time = None
        self.no_face_start_time = None

        # Prevent repeated events
        self.multiple_face_event_active = False
        self.no_face_event_active = False

    # ==========================================
    # UPDATE
    # ==========================================

    def update(self, face_count, current_time):

        # ======================================
        # NO FACE
        # ======================================

        if face_count == 0:

            if self.no_face_start_time is None:
                self.no_face_start_time = current_time
                self.no_face_event_active = False

            duration = (
                current_time -
                self.no_face_start_time
            )

            if (
                duration >= self.no_face_threshold
                and not self.no_face_event_active
            ):

                self.no_face_event_active = True

                return {
                    "type": "FACE_NOT_DETECTED",
                    "duration": duration
                }

        else:

            # Face detected again → reset
            self.no_face_start_time = None
            self.no_face_event_active = False

        # ======================================
        # MULTIPLE FACES
        # ======================================

        if face_count > 1:

            if self.multiple_face_start_time is None:
                self.multiple_face_start_time = current_time
                self.multiple_face_event_active = False

            duration = (
                current_time -
                self.multiple_face_start_time
            )

            if (
                duration >= self.multiple_face_threshold
                and not self.multiple_face_event_active
            ):

                self.multiple_face_event_active = True

                return {
                    "type": "MULTIPLE_FACES",
                    "face_count": face_count,
                    "duration": duration
                }

        else:

            # Back to one/no face → reset
            self.multiple_face_start_time = None
            self.multiple_face_event_active = False

        return None

    # ==========================================
    # RESET
    # ==========================================

    def reset(self):

        self.multiple_face_start_time = None
        self.no_face_start_time = None

        self.multiple_face_event_active = False
        self.no_face_event_active = False