import cv2
import numpy as np


class HeadPoseEstimator:

    def __init__(self):
        self.neutral_pitch = None
        self.neutral_yaw = None

    @staticmethod
    def angle_difference(current, reference):
        """
        Calculate the shortest difference between two angles.
        Result is always between -180 and +180 degrees.
        """
        return (current - reference + 180) % 360 - 180

    @staticmethod
    def circular_mean(angles):
        """
        Calculate the mean of angles while handling the
        -180/+180 degree boundary correctly.
        """
        radians = np.radians(angles)

        mean_sin = np.mean(np.sin(radians))
        mean_cos = np.mean(np.cos(radians))

        mean_angle = np.arctan2(mean_sin, mean_cos)

        return np.degrees(mean_angle)

    def get_pose(self, landmarks, width, height):

        image_points = np.array([
            [landmarks[1].x * width, landmarks[1].y * height],
            [landmarks[152].x * width, landmarks[152].y * height],
            [landmarks[33].x * width, landmarks[33].y * height],
            [landmarks[263].x * width, landmarks[263].y * height],
            [landmarks[61].x * width, landmarks[61].y * height],
            [landmarks[291].x * width, landmarks[291].y * height],
        ], dtype=np.float64)

        model_points = np.array([
            [0.0, 0.0, 0.0],
            [0.0, -63.6, -12.5],
            [-43.3, 32.7, -26.0],
            [43.3, 32.7, -26.0],
            [-28.9, -28.9, -24.1],
            [28.9, -28.9, -24.1],
        ], dtype=np.float64)

        focal_length = width

        camera_matrix = np.array([
            [focal_length, 0, width / 2],
            [0, focal_length, height / 2],
            [0, 0, 1]
        ], dtype=np.float64)

        dist_coeffs = np.zeros((4, 1))

        success, rotation_vector, translation_vector = cv2.solvePnP(
            model_points,
            image_points,
            camera_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE
        )

        if not success:
            return None, None

        rotation_matrix, _ = cv2.Rodrigues(rotation_vector)

        angles, _, _, _, _, _ = cv2.RQDecomp3x3(
            rotation_matrix
        )

        pitch = float(angles[0])
        yaw = float(angles[1])

        return pitch, yaw

    def set_neutral(self, pitch, yaw):
        """
        Store the student's natural head position.
        """
        self.neutral_pitch = pitch
        self.neutral_yaw = yaw

    def get_relative_pose(self, pitch, yaw):
        """
        Calculate movement relative to the calibrated
        neutral position.
        """
        if self.neutral_pitch is None or self.neutral_yaw is None:
            return None, None

        relative_pitch = self.angle_difference(
            pitch,
            self.neutral_pitch
        )

        relative_yaw = self.angle_difference(
            yaw,
            self.neutral_yaw
        )

        return relative_pitch, relative_yaw

    def get_direction(self, relative_pitch, relative_yaw):

        if relative_pitch is None or relative_yaw is None:
            return "UNKNOWN"

        PITCH_THRESHOLD = 15
        YAW_THRESHOLD = 15

        pitch_magnitude = abs(relative_pitch)
        yaw_magnitude = abs(relative_yaw)

        # If movement is small in both directions
        if (
            pitch_magnitude < PITCH_THRESHOLD
            and yaw_magnitude < YAW_THRESHOLD
        ):
            return "CENTER"

        # Decide which movement is dominant
        if pitch_magnitude >= yaw_magnitude:

            if relative_pitch < -PITCH_THRESHOLD:
                return "UP"

            if relative_pitch > PITCH_THRESHOLD:
                return "DOWN"

        else:

            if relative_yaw < -YAW_THRESHOLD:
                return "RIGHT"

            if relative_yaw > YAW_THRESHOLD:
                return "LEFT"

        return "CENTER"