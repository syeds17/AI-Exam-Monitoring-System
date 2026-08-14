import time

from src.monitoring.attention_tracker import AttentionTracker


def main():

    tracker = AttentionTracker(
        looking_away_threshold=3.0
    )

    print("Starting Attention Tracker test...\n")

    # ==========================================
    # TEST 1: NORMAL
    # ==========================================

    print("TEST 1: CENTER")

    for _ in range(5):

        event = tracker.update(
            "CENTER"
        )

        print("Direction: CENTER | Event:", event)

        time.sleep(0.5)

    # ==========================================
    # TEST 2: SHORT LOOK AWAY
    # ==========================================

    print("\nTEST 2: SHORT LEFT LOOK")

    for _ in range(4):

        event = tracker.update(
            "LEFT"
        )

        print("Direction: LEFT | Event:", event)

        time.sleep(0.5)

    tracker.update("CENTER")

    # ==========================================
    # TEST 3: LONG LOOK AWAY
    # ==========================================

    print("\nTEST 3: LONG LEFT LOOK")

    for _ in range(8):

        event = tracker.update(
            "LEFT"
        )

        print("Direction: LEFT | Event:", event)

        if event:
            print("🚨 EVENT GENERATED:", event)

        time.sleep(0.5)

    tracker.update("CENTER")

    # ==========================================
    # TEST 4: NO FACE
    # ==========================================

    print("\nTEST 4: NO FACE")

    for _ in range(6):

        event = tracker.update(
            "NO FACE"
        )

        print("Direction: NO FACE | Event:", event)

        if event:
            print("🚨 EVENT GENERATED:", event)

        time.sleep(0.5)

    print("\nTest complete.")


if __name__ == "__main__":
    main()