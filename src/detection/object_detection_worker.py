import threading
import time


class ObjectDetectionWorker:
    """
    Runs ObjectDetector in a background thread.

    The worker receives the latest camera frame and periodically
    performs object detection without blocking the main monitoring loop.
    """

    def __init__(
        self,
        detector,
        detection_interval=0.15,
    ):
        self.detector = detector
        self.detection_interval = detection_interval

        self.running = False
        self.thread = None

        self.lock = threading.Lock()

        self.latest_frame = None
        self.latest_result = {
            "object_count": 0,
            "objects": [],
        }

        self.detection_fps = 0.0
        self.detection_count = 0

        self.last_detection_time = 0.0

    def start(self):
        """
        Start the background detection worker.
        """

        if self.running:
            return

        self.running = True

        self.latest_frame = None
        self.latest_result = {
            "object_count": 0,
            "objects": [],
        }

        self.detection_fps = 0.0
        self.detection_count = 0
        self.last_detection_time = 0.0

        self.thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="ObjectDetectionWorker",
        )

        self.thread.start()

        print("Object detection worker started.")

    def update_frame(self, frame):
        """
        Provide the worker with the latest camera frame.

        Only the most recent frame is kept.
        """

        if frame is None:
            return

        with self.lock:
            self.latest_frame = frame.copy()

    def _worker_loop(self):
        """
        Background detection loop.
        """

        while self.running:
            loop_start = time.perf_counter()

            with self.lock:
                if self.latest_frame is None:
                    frame = None
                else:
                    frame = self.latest_frame.copy()

            if frame is None:
                time.sleep(0.01)
                continue

            try:
                detection_result = self.detector.detect(frame)

                detection_time = (
                    time.perf_counter() - loop_start
                )

                if detection_time > 0:
                    current_fps = 1.0 / detection_time
                else:
                    current_fps = 0.0

                with self.lock:
                    self.latest_result = detection_result
                    self.detection_fps = current_fps
                    self.detection_count += 1
                    self.last_detection_time = time.time()

            except Exception as exc:
                print(
                    f"Object detection worker error: {exc}"
                )

            elapsed = time.perf_counter() - loop_start

            sleep_time = self.detection_interval - elapsed

            if sleep_time > 0:
                time.sleep(sleep_time)

    def get_result(self):
        """
        Return the latest object detection result.
        """

        with self.lock:
            result = {
                "object_count": self.latest_result.get(
                    "object_count",
                    0,
                ),
                "objects": [],
            }

            for obj in self.latest_result.get(
                "objects",
                [],
            ):
                result["objects"].append(
                    {
                        "class_id": obj["class_id"],
                        "class_name": obj["class_name"],
                        "confidence": obj["confidence"],
                        "bbox": list(obj["bbox"]),
                    }
                )

            return result

    def get_fps(self):
        """
        Return the current object detection FPS.
        """

        with self.lock:
            return self.detection_fps

    def get_detection_count(self):
        """
        Return the total number of completed detections.
        """

        with self.lock:
            return self.detection_count

    def get_last_detection_time(self):
        """
        Return the Unix timestamp of the latest detection.
        """

        with self.lock:
            return self.last_detection_time

    def is_running(self):
        """
        Return whether the worker is currently running.
        """

        return self.running

    def stop(self):
        """
        Stop the background detection worker.
        """

        if not self.running:
            return

        self.running = False

        if self.thread is not None:
            self.thread.join(timeout=2.0)

        self.thread = None

        with self.lock:
            self.latest_frame = None

        print("Object detection worker stopped.")