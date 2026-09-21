import math


class FaceTracker:

    def __init__(self, max_distance=0.20):

        # Maximum normalized distance allowed
        # between the previous candidate position
        # and a new face position.
        self.max_distance = max_distance

        # Previous tracked face center
        self.previous_center = None

        # Whether a candidate is currently being tracked
        self.tracking = False

    # ==========================================
    # FACE CENTER
    # ==========================================

    def _get_face_center(self, landmarks):

        if not landmarks:
            return None

        x_values = [
            landmark.x
            for landmark in landmarks
        ]

        y_values = [
            landmark.y
            for landmark in landmarks
        ]

        center_x = sum(x_values) / len(x_values)
        center_y = sum(y_values) / len(y_values)

        return center_x, center_y

    # ==========================================
    # DISTANCE
    # ==========================================

    def _distance(self, point_a, point_b):

        return math.sqrt(
            (point_a[0] - point_b[0]) ** 2
            +
            (point_a[1] - point_b[1]) ** 2
        )

    # ==========================================
    # UPDATE
    # ==========================================

    def update(self, face_landmarks):

        # --------------------------------------
        # NO FACES
        # --------------------------------------

        if not face_landmarks:

            self.tracking = False

            return {
                "tracked": False,
                "face_index": None,
                "center": None,
                "distance": None
            }

        # --------------------------------------
        # CALCULATE CENTERS
        # --------------------------------------

        centers = []

        for landmarks in face_landmarks:

            center = self._get_face_center(
                landmarks
            )

            centers.append(center)

        # --------------------------------------
        # FIRST DETECTION
        # --------------------------------------

        if self.previous_center is None:

            # Start with the first detected face.
            self.previous_center = centers[0]

            self.tracking = True

            return {
                "tracked": True,
                "face_index": 0,
                "center": centers[0],
                "distance": 0.0
            }

        # --------------------------------------
        # FIND CLOSEST FACE
        # --------------------------------------

        best_index = None
        best_distance = float("inf")

        for index, center in enumerate(centers):

            distance = self._distance(
                self.previous_center,
                center
            )

            if distance < best_distance:

                best_distance = distance
                best_index = index

        # --------------------------------------
        # TRACKING SUCCESS
        # --------------------------------------

        if (
            best_index is not None
            and
            best_distance <= self.max_distance
        ):

            self.previous_center = (
                centers[best_index]
            )

            self.tracking = True

            return {
                "tracked": True,
                "face_index": best_index,
                "center": centers[best_index],
                "distance": best_distance
            }

        # --------------------------------------
        # TRACKING LOST
        # --------------------------------------

        self.tracking = False

        return {
            "tracked": False,
            "face_index": None,
            "center": None,
            "distance": best_distance
        }

    # ==========================================
    # RESET
    # ==========================================

    def reset(self):

        self.previous_center = None

        self.tracking = False