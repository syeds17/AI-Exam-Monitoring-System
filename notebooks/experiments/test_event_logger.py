from src.monitoring.event_logger import EventLogger


def main():

    logger = EventLogger(
        "data/test_events.db"
    )

    print("Starting logging test...\n")

    # --------------------------------
    # START SESSION
    # --------------------------------

    session_id = logger.start_session()

    print(
        f"Session started: {session_id}\n"
    )

    # --------------------------------
    # TEST EVENTS
    # --------------------------------

    events = [

        {
            "type": "LOOKING_AWAY",
            "direction": "LEFT",
            "duration": 3.2
        },

        {
            "type": "LOOKING_AWAY",
            "direction": "RIGHT",
            "duration": 4.1
        },

        {
            "type": "FACE_NOT_DETECTED",
            "duration": 2.3
        }
    ]

    for event in events:

        logger.log_event(event)

        print(
            "Logged:",
            event
        )

    # --------------------------------
    # READ EVENTS
    # --------------------------------

    print(
        "\nEvents stored in database:\n"
    )

    stored_events = logger.get_events(
        session_id
    )

    for event in stored_events:

        print(event)

    # --------------------------------
    # END SESSION
    # --------------------------------

    logger.end_session()

    print(
        "\nSession ended."
    )

    print(
        "\nEvent Logger test complete."
    )

    logger.close()


if __name__ == "__main__":
    main()