import cv2
import mediapipe as mp


class FaceLandmarker:

    def __init__(self, model_path: str):

        self.model_path = model_path

        # ==========================================
        # MEDIAPIPE CONFIGURATION
        # ==========================================

        BaseOptions = mp.tasks.BaseOptions
        FaceLandmarkerOptions = (
            mp.tasks.vision.FaceLandmarkerOptions
        )
        RunningMode = mp.tasks.vision.RunningMode

        self.options = FaceLandmarkerOptions(
            base_options=BaseOptions(
                model_asset_path=model_path
            ),

            # VIDEO mode enables MediaPipe tracking
            running_mode=RunningMode.VIDEO,

            # We currently monitor one primary face
            num_faces=1,

            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        self.landmarker = (
            mp.tasks.vision.FaceLandmarker
            .create_from_options(
                self.options
            )
        )

    # ==========================================
    # PROCESS FRAME
    # ==========================================

    def process(self, frame, timestamp_ms):

        rgb_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb_frame
        )

        return self.landmarker.detect_for_video(
            mp_image,
            timestamp_ms
        )

    # ==========================================
    # GET FACE CENTER
    # ==========================================

    def get_face_center(
        self,
        face_landmarks,
        frame_width,
        frame_height
    ):
        """
        Calculate the center point of the detected face.

        Uses all available face landmarks and returns
        the average X/Y position in pixel coordinates.
        """

        if not face_landmarks:

            return None

        total_x = 0.0
        total_y = 0.0

        landmark_count = len(
            face_landmarks
        )

        for landmark in face_landmarks:

            total_x += landmark.x
            total_y += landmark.y

        center_x = (
            total_x / landmark_count
        ) * frame_width

        center_y = (
            total_y / landmark_count
        ) * frame_height

        return (
            int(center_x),
            int(center_y)
        )

    # ==========================================
    # CLOSE
    # ==========================================

    def close(self):

        if self.landmarker is not None:

            self.landmarker.close()

            self.landmarker = None