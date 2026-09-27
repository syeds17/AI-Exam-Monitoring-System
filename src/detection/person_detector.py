import cv2
from ultralytics import YOLO


class PersonDetector:

    # COCO class ID for "person"
    PERSON_CLASS_ID = 0

    def __init__(
        self,
        model_path="yolo11n.pt",
        confidence=0.50
    ):
        self.model_path = model_path
        self.confidence = confidence

        print(f"Loading YOLO model: {model_path}")

        self.model = YOLO(model_path)

        print("YOLO model loaded successfully.")

    def detect(self, frame):
        """
        Detect people in a single OpenCV frame.

        Returns:
            {
                "person_count": int,
                "persons": [
                    {
                        "confidence": float,
                        "bbox": [x1, y1, x2, y2]
                    }
                ]
            }
        """

        results = self.model.predict(
            source=frame,
            imgsz=640,
            classes=[self.PERSON_CLASS_ID],
            conf=self.confidence,
            device="cpu",
            verbose=False
        )

        persons = []

        if not results:
            return {
                "person_count": 0,
                "persons": []
            }

        result = results[0]

        if result.boxes is None:
            return {
                "person_count": 0,
                "persons": []
            }

        boxes = result.boxes

        for index in range(len(boxes)):

            confidence = float(
                boxes.conf[index].item()
            )

            x1, y1, x2, y2 = (
                boxes.xyxy[index]
                .cpu()
                .tolist()
            )

            persons.append(
                {
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
            "person_count": len(persons),
            "persons": persons
        }

    def draw_detections(
        self,
        frame,
        detection_result
    ):
        """
        Draw person bounding boxes on a frame.
        """

        output = frame.copy()

        for person in detection_result["persons"]:

            x1, y1, x2, y2 = person["bbox"]
            confidence = person["confidence"]

            cv2.rectangle(
                output,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )

            label = (
                f"Person "
                f"{confidence:.2f}"
            )

            cv2.putText(
                output,
                label,
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )

        cv2.putText(
            output,
            f"Persons: {detection_result['person_count']}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 255, 0),
            2
        )

        return output