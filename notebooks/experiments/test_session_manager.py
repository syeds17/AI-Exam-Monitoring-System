from src.monitoring.event_logger import EventLogger


def main():

    logger = EventLogger(
        "data/test_sessions.db"
    )

    print("Starting exam session...\n")

    session_id = logger.start_session()

    print("Session ID:")
    print(session_id)

    # Test events
    logger.log_event({
        "type": "LOOKING_AWAY",
        "direction": "LEFT",
        "duration": 3.4
    })

    logger.log_event({
        "type": "FACE_NOT_DETECTED",
        "duration": 2.1
    })

    print("\nEvents for current session:")

    events = logger.get_events()

    for event in events:
        print(event)

    logger.end_session()

    print("\nAll sessions:")

    sessions = logger.get_sessions()

    for session in sessions:
        print(session)

    logger.close()

    print("\nSession test complete.")


if __name__ == "__main__":
    main()