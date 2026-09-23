import cv2
import threading
import time


class ThreadedCamera:

    def __init__(
        self,
        camera_index=0,
        width=1280,
        height=720,
        target_fps=30
    ):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.target_fps = target_fps

        self.cap = None
        self.thread = None

        self.running = False
        self.lock = threading.Lock()

        self.latest_frame = None
        self.frame_count = 0

        self.actual_fps = 0.0

        self._fps_start_time = None
        self._fps_frame_count = 0

    # ======================================================
    # START CAMERA
    # ======================================================

    def start(self):

        if self.running:
            return

        # Use DirectShow on Windows.
        # This avoids the repeated MSMF grabFrame warnings.
        self.cap = cv2.VideoCapture(
            self.camera_index,
            cv2.CAP_DSHOW
        )

        if not self.cap.isOpened():

            self.cap.release()
            self.cap = None

            raise RuntimeError(
                f"Could not open camera "
                f"{self.camera_index} using DirectShow."
            )

        # Camera settings
        self.cap.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            self.width
        )

        self.cap.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            self.height
        )

        self.cap.set(
            cv2.CAP_PROP_FPS,
            self.target_fps
        )

        # Request a small buffer so old frames
        # do not accumulate.
        self.cap.set(
            cv2.CAP_PROP_BUFFERSIZE,
            1
        )

        self.running = True

        self.latest_frame = None
        self.frame_count = 0

        self.actual_fps = 0.0

        self._fps_start_time = (
            time.perf_counter()
        )

        self._fps_frame_count = 0

        self.thread = threading.Thread(
            target=self._capture_loop,
            daemon=True
        )

        self.thread.start()

        # Wait for the first frame.
        start_wait = time.perf_counter()

        while self.latest_frame is None:

            if (
                time.perf_counter()
                - start_wait
                > 2.0
            ):

                self.stop()

                raise RuntimeError(
                    "Camera started but "
                    "no frame was received."
                )

            time.sleep(0.01)

    # ======================================================
    # CAPTURE LOOP
    # ======================================================

    def _capture_loop(self):

        while self.running:

            success, frame = self.cap.read()

            if not success:

                time.sleep(0.005)

                continue

            with self.lock:

                self.latest_frame = frame
                self.frame_count += 1

            self._fps_frame_count += 1

            elapsed = (
                time.perf_counter()
                - self._fps_start_time
            )

            if elapsed >= 1.0:

                self.actual_fps = (
                    self._fps_frame_count
                    / elapsed
                )

                self._fps_frame_count = 0

                self._fps_start_time = (
                    time.perf_counter()
                )

    # ======================================================
    # READ LATEST FRAME
    # ======================================================

    def read(self):

        with self.lock:

            if self.latest_frame is None:
                return None

            return self.latest_frame.copy()

    # ======================================================
    # FPS
    # ======================================================

    def get_fps(self):

        return self.actual_fps

    # ======================================================
    # FRAME COUNT
    # ======================================================

    def get_frame_count(self):

        with self.lock:

            return self.frame_count

    # ======================================================
    # STOP
    # ======================================================

    def stop(self):

        self.running = False

        if self.thread is not None:

            self.thread.join(
                timeout=2.0
            )

            self.thread = None

        if self.cap is not None:

            self.cap.release()
            self.cap = None

        with self.lock:

            self.latest_frame = None

    # ======================================================
    # STATUS
    # ======================================================

    def is_running(self):

        return self.running