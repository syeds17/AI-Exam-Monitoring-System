import cv2
from ultralytics import YOLO


class ObjectDetector:
    """
    YOLO-based object detector for exam monitoring.

    Uses the custom-trained YOLO model for the 7 target
    exam-monitoring object classes.

    Target classes:
        0 - mobile_phone
        1 - earphones
        2 - smartwatch
        3 - book
        4 - paper_notes
        5 - laptop
        6 - tablet
    """

    CLASS_MAP = {
        0: "mobile_phone",
        1: "earphones",
        2: "smartwatch",
        3: "book",
        4: "paper_notes",
        5: "laptop",
        6: "tablet",
    }

    TARGET_CLASSES = [
        "mobile_phone",
        "earphones",
        "smartwatch",
        "book",
        "paper_notes",
        "laptop",
        "tablet",
    ]

    def __init__(
        self,
        model_path=(
            "runs/detect/runs/object_detection/"
            "exam_objects_v1/weights/best.pt"
        ),
        confidence=0.40,
        image_size=640,
        device="cpu",
    ):
        self.model_path = model_path
        self.confidence = confidence
        self.image_size = image_size
        self.device = device

        print(f"Loading YOLO object model: {model_path}")

        self.model = YOLO(model_path)

        print("YOLO object model loaded successfully.")

        print("\nTarget object classes:")
        for class_id, class_name in self.CLASS_MAP.items():
            print(f"  [{class_id}] {class_name}")

    def detect(self, frame):
        """
        Run object detection on a frame.

        Returns:
            {
                "object_count": int,
                "objects": [
                    {
                        "class_id": int,
                        "class_name": str,
                        "confidence": float,
                        "bbox": [x1, y1, x2, y2]
                    }
                ]
            }
        """

        if frame is None:
            return {
                "object_count": 0,
                "objects": [],
            }

        results = self.model.predict(
            source=frame,
            imgsz=self.image_size,
            conf=self.confidence,
            device=self.device,
            verbose=False,
        )

        if not results:
            return {
                "object_count": 0,
                "objects": [],
            }

        result = results[0]

        if result.boxes is None:
            return {
                "object_count": 0,
                "objects": [],
            }

        objects = []

        boxes = result.boxes

        for index in range(len(boxes)):
            class_id = int(boxes.cls[index].item())

            # Ignore unexpected class IDs.
            if class_id not in self.CLASS_MAP:
                continue

            confidence = float(boxes.conf[index].item())

            x1, y1, x2, y2 = (
                boxes.xyxy[index]
                .cpu()
                .tolist()
            )

            class_name = self.CLASS_MAP[class_id]

            objects.append(
                {
                    "class_id": class_id,
                    "class_name": class_name,
                    "confidence": confidence,
                    "bbox": [
                        int(x1),
                        int(y1),
                        int(x2),
                        int(y2),
                    ],
                }
            )

        return {
            "object_count": len(objects),
            "objects": objects,
        }

    def draw_detections(self, frame, detection_result):
        """
        Draw detected monitoring objects on the frame.
        """

        if frame is None:
            return frame

        output = frame.copy()

        for obj in detection_result.get("objects", []):
            x1, y1, x2, y2 = obj["bbox"]

            class_name = obj["class_name"]
            confidence = obj["confidence"]

            cv2.rectangle(
                output,
                (x1, y1),
                (x2, y2),
                (0, 255, 255),
                2,
            )

            label = f"{class_name} {confidence:.2f}"

            cv2.putText(
                output,
                label,
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                2,
            )

        cv2.putText(
            output,
            f"Objects: {detection_result.get('object_count', 0)}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 255),
            2,
        )

        return output

    def detect_and_draw(self, frame):
        """
        Run detection and draw the results.

        Returns:
            (
                detection_result,
                annotated_frame
            )
        """

        detection_result = self.detect(frame)

        annotated_frame = self.draw_detections(
            frame,
            detection_result,
        )

        return detection_result, annotated_frame

    def get_detected_classes(self, detection_result):
        """
        Return unique detected class names.
        """

        return list(
            dict.fromkeys(
                obj["class_name"]
                for obj in detection_result.get("objects", [])
            )
        )

    def get_supported_classes(self):
        """
        Return all classes supported by the
        custom-trained model.
        """

        return self.TARGET_CLASSES.copy()

    def close(self):
        """
        Release the YOLO model reference.
        """

        self.model = None