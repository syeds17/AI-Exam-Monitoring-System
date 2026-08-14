import time

from src.monitoring.face_monitor import FaceMonitor


def main():

    monitor = FaceMonitor(
        multiple_face_threshold=1.0,
        no_face_threshold=2.0
    )

    print("Starting Face Monitor test...\n")

    # ==========================================
    # TEST 1: ONE FACE
    # ==========================================

    print("TEST 1: ONE FACE")

    for _ in range(4):

        event = monitor.update(
            face_count=1,
            current_time=time.time()
        )

        print(
            "Faces: 1 | Event:",
            event
        )

        time.sleep(0.5)

    # ==========================================
    # TEST 2: SHORT MULTIPLE FACE
    # ==========================================

    print("\nTEST 2: SHORT MULTIPLE FACE")

    for _ in range(1):

        event = monitor.update(
            face_count=2,
            current_time=time.time()
        )

        print(
            "Faces: 2 | Event:",
            event
        )

        time.sleep(0.5)

    monitor.update(
        face_count=1,
        current_time=time.time()
    )

    # ==========================================
    # TEST 3: MULTIPLE FACE
    # ==========================================

    print("\nTEST 3: MULTIPLE FACE")

    for _ in range(5):

        event = monitor.update(
            face_count=2,
            current_time=time.time()
        )

        print(
            "Faces: 2 | Event:",
            event
        )

        if event:
            print(
                "🚨 EVENT GENERATED:",
                event
            )

        time.sleep(0.5)

    # ==========================================
    # TEST 4: NO FACE
    # ==========================================

    print("\nTEST 4: NO FACE")

    for _ in range(6):

        event = monitor.update(
            face_count=0,
            current_time=time.time()
        )

        print(
            "Faces: 0 | Event:",
            event
        )

        if event:
            print(
                "🚨 EVENT GENERATED:",
                event
            )

        time.sleep(0.5)

    print("\nFace Monitor test complete.")


if __name__ == "__main__":
    main()