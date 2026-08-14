from src.monitoring.exam_monitor import ExamMonitor


def main():

    monitor = ExamMonitor()

    try:

        # ==================================
        # SESSION 1
        # ==================================

        print("\nStarting Session 1...")

        session_1 = monitor.start()

        print(
            f"Session 1 ID: {session_1}"
        )

        print("Processing frames...")

        for _ in range(100):

            state = monitor.process_frame()

            if state is None:
                break

        print(
            f"Session 1 events: "
            f"{state['last_event']}"
        )

        monitor.stop()

        print("Session 1 stopped.")

        # ==================================
        # SESSION 2
        # ==================================

        print("\nStarting Session 2...")

        session_2 = monitor.start()

        print(
            f"Session 2 ID: {session_2}"
        )

        print("Processing frames...")

        for _ in range(100):

            state = monitor.process_frame()

            if state is None:
                break

        print(
            f"Session 2 events: "
            f"{state['last_event']}"
        )

        monitor.stop()

        print("Session 2 stopped.")

        # ==================================
        # VERIFY
        # ==================================

        if session_1 != session_2:

            print(
                "\n✅ Session lifecycle test PASSED"
            )

        else:

            print(
                "\n❌ Session IDs are identical"
            )

    finally:

        monitor.close()

        print(
            "ExamMonitor closed."
        )


if __name__ == "__main__":
    main()