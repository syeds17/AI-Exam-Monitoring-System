import threading
import time


class DetectionWorker:

    def __init__(
        self,
        detector,
        detection_interval=0.15
    ):
        """
        Run an object/person detector in a background thread.

        detection_interval:
            Minimum time between YOLO inferences.
            0.15 sec ≈ maximum of ~6-7 detections/sec.
        """

        self.detector = detector
        self.detection_interval = detection_interval

        self.running = False
        self.thread = None

        self.lock = threading.Lock()

        self.latest_frame = None
        self.latest_result = {
            "person_count": 0,
            "persons": []
        }

        self.last_detection_time = 0.0
        self.detection_count = 0
        self.detection_fps = 0.0

        self._fps_start_time = None
        self._fps_count = 0

    # ==========================================
    # START
    # ==========================================

    def start(self):

        if self.running:
            return

        self.running = True

        self.latest_frame = None
        self.latest_result = {
            "person_count": 0,
            "persons": []
        }

        self.last_detection_time = 0.0
        self.detection_count = 0

        self._fps_start_time = time.perf_counter()
        self._fps_count = 0

        self.thread = threading.Thread(
            target=self._worker_loop,
            daemon=True
        )

        self.thread.start()

    # ==========================================
    # UPDATE FRAME
    # ==========================================

    def update_frame(self, frame):

        if frame is None:
            return

        with self.lock:
            self.latest_frame = frame.copy()

    # ==========================================
    # WORKER LOOP
    # ==========================================

    def _worker_loop(self):

        while self.running:

            current_time = time.perf_counter()

            # Don't run YOLO too frequently.
            if (
                current_time - self.last_detection_time
                < self.detection_interval
            ):
                time.sleep(0.005)
                continue

            with self.lock:

                if self.latest_frame is None:
                    frame = None
                else:
                    frame = self.latest_frame.copy()

            if frame is None:
                time.sleep(0.005)
                continue

            # ==================================
            # RUN DETECTOR
            # ==================================

            try:

                result = self.detector.detect(frame)

            except Exception as error:

                print(
                    f"Detection worker error: {error}"
                )

                time.sleep(0.05)
                continue

            self.last_detection_time = (
                time.perf_counter()
            )

            # ==================================
            # STORE RESULT
            # ==================================

            with self.lock:

                self.latest_result = result
                self.detection_count += 1
                self._fps_count += 1

            # ==================================
            # DETECTION FPS
            # ==================================

            elapsed = (
                time.perf_counter()
                - self._fps_start_time
            )

            if elapsed >= 1.0:

                with self.lock:

                    self.detection_fps = (
                        self._fps_count / elapsed
                    )

                    self._fps_count = 0

                self._fps_start_time = (
                    time.perf_counter()
                )

    # ==========================================
    # GET RESULT
    # ==========================================

    def get_result(self):

        with self.lock:

            return {
                "person_count": (
                    self.latest_result["person_count"]
                ),
                "persons": [
                    person.copy()
                    for person in
                    self.latest_result["persons"]
                ]
            }

    # ==========================================
    # GET FPS
    # ==========================================

    def get_fps(self):

        with self.lock:
            return self.detection_fps

    # ==========================================
    # GET DETECTION COUNT
    # ==========================================

    def get_detection_count(self):

        with self.lock:
            return self.detection_count

    # ==========================================
    # STOP
    # ==========================================

    def stop(self):

        self.running = False

        if self.thread is not None:

            self.thread.join(
                timeout=2.0
            )

            self.thread = None

        with self.lock:

            self.latest_frame = None

    # ==========================================
    # STATUS
    # ==========================================

    def is_running(self):

        return self.running