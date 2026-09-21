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

    def start(self):

        if self.running:
            return

        # Windows: use DirectShow instead of MSMF.
        self.cap = cv2.VideoCapture(
            self.camera_index,
            cv2.CAP_DSHOW
        )

        if not self.cap.isOpened():
            # Fallback to default backend.
            self.cap.release()

            self.cap = cv2.VideoCapture(
                self.camera_index
            )

        if not self.cap.isOpened():
            raise RuntimeError(
                f"Could not open camera {self.camera_index}"
            )

        # Camera configuration.
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

        # Keep only the newest frame.
        self.cap.set(
            cv2.CAP_PROP_BUFFERSIZE,
            1
        )

        self.running = True

        self.latest_frame = None
        self.frame_count = 0

        self.actual_fps = 0.0

        self._fps_start_time = time.perf_counter()
        self._fps_frame_count = 0

        self.thread = threading.Thread(
            target=self._capture_loop,
            daemon=True
        )

        self.thread.start()

        # Wait until the first frame arrives.
        start_wait = time.perf_counter()

        while self.latest_frame is None:

            if (
                time.perf_counter()
                - start_wait
                > 2.0
            ):
                self.stop()

                raise RuntimeError(
                    "Camera started but no frame "
                    "was received."
                )

            time.sleep(0.01)

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

    def read(self):

        with self.lock:

            if self.latest_frame is None:
                return None

            return self.latest_frame.copy()

    def get_fps(self):

        return self.actual_fps

    def get_frame_count(self):

        with self.lock:
            return self.frame_count

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

    def is_running(self):

        return self.running