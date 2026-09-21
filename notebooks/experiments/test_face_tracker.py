from src.tracking.face_tracker import FaceTracker


class MockLandmark:

    def __init__(self, x, y):

        self.x = x
        self.y = y


def create_face(center_x, center_y):

    return [
        MockLandmark(
            center_x - 0.05,
            center_y - 0.05
        ),
        MockLandmark(
            center_x + 0.05,
            center_y - 0.05
        ),
        MockLandmark(
            center_x - 0.05,
            center_y + 0.05
        ),
        MockLandmark(
            center_x + 0.05,
            center_y + 0.05
        )
    ]


def main():

    print("Starting Face Tracker test...\n")

    tracker = FaceTracker(
        max_distance=0.20
    )

    # ==========================================
    # TEST 1
    # ==========================================

    print("TEST 1: FIRST FACE")

    face_a = create_face(
        0.50,
        0.50
    )

    result = tracker.update(
        [face_a]
    )

    print(result)

    assert result["tracked"] is True
    assert result["face_index"] == 0

    # ==========================================
    # TEST 2
    # ==========================================

    print("\nTEST 2: SAME FACE MOVES")

    face_a = create_face(
        0.52,
        0.51
    )

    result = tracker.update(
        [face_a]
    )

    print(result)

    assert result["tracked"] is True
    assert result["face_index"] == 0

    # ==========================================
    # TEST 3
    # ==========================================

    print("\nTEST 3: MULTIPLE FACES")

    face_a = create_face(
        0.54,
        0.52
    )

    face_b = create_face(
        0.85,
        0.50
    )

    result = tracker.update(
        [
            face_a,
            face_b
        ]
    )

    print(result)

    assert result["tracked"] is True
    assert result["face_index"] == 0

    # ==========================================
    # TEST 4
    # ==========================================

    print("\nTEST 4: NO FACE")

    result = tracker.update([])

    print(result)

    assert result["tracked"] is False
    assert result["face_index"] is None

    # ==========================================
    # TEST 5
    # ==========================================

    print("\nTEST 5: RESET")

    tracker.reset()

    assert tracker.previous_center is None
    assert tracker.tracking is False

    print("Tracker reset successfully.")

    # ==========================================
    # COMPLETE
    # ==========================================

    print("\n✅ Face Tracker test PASSED")


if __name__ == "__main__":

    main()