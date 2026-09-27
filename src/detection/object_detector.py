import cv2
from ultralytics import YOLO


class ObjectDetector:
    """
    YOLO-based object detector for exam monitoring.

    Phase 1 uses the pretrained YOLO11n COCO model.
    Only classes that exist in the pretrained model are enabled initially.

    Supported pretrained classes relevant to our project:
        - cell phone -> mobile phone
        - book
        - laptop
    """

    # COCO class IDs used by YOLO
    CLASS_MAP = {
        63: "mobile phone",
        73: "book",
        67: "laptop",
    }

    TARGET_CLASSES = [
        "mobile phone",
        "earphones",
        "smartwatch",
        "book",
        "paper",
        "laptop",
        "tablet",
    ]

    PRETRAINED_SUPPORTED_CLASSES = {
        "mobile phone",
        "book",
        "laptop",
    }

    def __init__(
        self,
        model_path="yolo11n.pt",
        confidence=0.50
    ):
        self.model_path = model_path
        self.confidence = confidence

        print(f"Loading YOLO object model: {model_path}")

        self.model = YOLO(model_path)

        print("YOLO object model loaded successfully.")

        print("\nTarget object classes:")
        for target in self.TARGET_CLASSES:
            if target in self.PRETRAINED_SUPPORTED_CLASSES:
                print(f"  [PRETRAINED] {target}")
            else:
                print(f"  [NEEDS TRAINING] {target}")

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
                "objects": []
            }

        results = self.model.predict(
            source=frame,
            imgsz=640,
            conf=self.confidence,
            device="cpu",
            verbose=False
        )

        if not results:
            return {
                "object_count": 0,
                "objects": []
            }

        result = results[0]

        if result.boxes is None:
            return {
                "object_count": 0,
                "objects": []
            }

        objects = []

        boxes = result.boxes

        for index in range(len(boxes)):
            class_id = int(boxes.cls[index].item())

            # Ignore classes outside our monitoring requirements.
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
                        int(y2)
                    ]
                }
            )

        return {
            "object_count": len(objects),
            "objects": objects
        }

    def draw_detections(self, frame, detection_result):
        """
        Draw detected monitoring objects on the frame.
        """

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
                2
            )

            label = f"{class_name} {confidence:.2f}"

            cv2.putText(
                output,
                label,
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                2
            )

        cv2.putText(
            output,
            f"Objects: {detection_result.get('object_count', 0)}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 255),
            2
        )

        return output

    def get_supported_classes(self):
        """
        Return classes that can currently be detected
        by the pretrained model.
        """

        return sorted(
            self.PRETRAINED_SUPPORTED_CLASSES
        )

    def get_training_required_classes(self):
        """
        Return target classes that will require
        additional training/fine-tuning.
        """

        return sorted(
            set(self.TARGET_CLASSES)
            - self.PRETRAINED_SUPPORTED_CLASSES
        )