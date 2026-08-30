import sys
from pathlib import Path
import time

import cv2
import streamlit as st

# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.monitoring.exam_monitor import ExamMonitor


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Live Exam Monitor",
    page_icon="🎥",
    layout="wide"
)


# ============================================================
# SESSION STATE
# ============================================================

if "monitor" not in st.session_state:
    st.session_state.monitor = None

if "running" not in st.session_state:
    st.session_state.running = False

if "session_id" not in st.session_state:
    st.session_state.session_id = None

if "event_history" not in st.session_state:
    st.session_state.event_history = []

if "event_counts" not in st.session_state:
    st.session_state.event_counts = {
        "LOOKING_AWAY": 0,
        "EYES_CLOSED": 0,
        "FACE_NOT_DETECTED": 0,
        "MULTIPLE_FACES": 0
    }


# ============================================================
# HEADER
# ============================================================

st.title("🎥 Live Exam Monitor")

st.caption(
    "AI-powered real-time examination monitoring"
)


# ============================================================
# START / STOP
# ============================================================

col1, col2 = st.columns(2)


with col1:

    start_clicked = st.button(
        "▶️ Start Exam",
        use_container_width=True,
        disabled=st.session_state.running
    )


with col2:

    stop_clicked = st.button(
        "⏹️ Stop Exam",
        use_container_width=True,
        disabled=not st.session_state.running
    )


# ============================================================
# START EXAM
# ============================================================

if start_clicked:

    try:

        monitor = ExamMonitor()

        session_id = monitor.start()

        st.session_state.monitor = monitor
        st.session_state.session_id = session_id
        st.session_state.running = True

        # Reset event history
        st.session_state.event_history = []

        st.session_state.event_counts = {
            "LOOKING_AWAY": 0,
            "EYES_CLOSED": 0,
            "FACE_NOT_DETECTED": 0,
            "MULTIPLE_FACES": 0
        }

        st.success(
            f"Exam started — Session ID: {session_id}"
        )

        st.rerun()

    except Exception as e:

        st.error(
            f"Failed to start exam: {e}"
        )


# ============================================================
# STOP EXAM
# ============================================================

if stop_clicked:

    if st.session_state.monitor is not None:

        try:

            st.session_state.monitor.stop()

        except Exception as e:

            st.warning(
                f"Stop warning: {e}"
            )

    st.session_state.monitor = None
    st.session_state.running = False

    st.success("Exam stopped successfully.")

    st.rerun()


# ============================================================
# LIVE MONITOR
# ============================================================

if st.session_state.running:

    monitor = st.session_state.monitor

    # --------------------------------------------------------
    # STATUS HEADER
    # --------------------------------------------------------

    st.success(
        f"🟢 EXAM RUNNING — `{st.session_state.session_id}`"
    )

    # --------------------------------------------------------
    # PLACEHOLDERS
    # --------------------------------------------------------

    camera_placeholder = st.empty()

    status_placeholder = st.empty()

    event_placeholder = st.empty()

    metrics_placeholder = st.empty()

    history_placeholder = st.empty()


    # ========================================================
    # ONE FRAME PROCESSOR
    # ========================================================

    @st.fragment(run_every=0.1)
    def live_frame():

        if not st.session_state.running:
            return

        # ----------------------------------------------------
        # PROCESS FRAME
        # ----------------------------------------------------

        try:

            state = monitor.process_frame()

        except Exception as e:

            st.session_state.monitor_error = str(e)
            
            try:
                
                monitor.stop()
                
            except Exception as stop_error:
                
                st.session_state.monitor_error += (
                    f" | Stop error: {stop_error}"
                )
            
            st.session_state.monitor = None   
            st.session_state.running = False
            
            st.error(
                f"🚨 Monitoring error: {e}"
            )
            st.error(
                "Exam session ended because of a monitoring error."
            )
 
            return


        if state is None:

            st.error(
                "Camera frame could not be read."
            )

            return


        # ====================================================
        # FRAME
        # ====================================================

        frame = state["frame"]

        frame_rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        camera_placeholder.image(
            frame_rgb,
            channels="RGB",
            use_container_width=True
        )


        # ====================================================
        # CURRENT EVENT
        # ====================================================

        event = state.get("last_event")

        event_time = getattr(
            monitor,
            "last_event_time",
            0
        )

        current_time = time.time()

        # Show event only for 3 seconds
        event_is_recent = (
            event is not None
            and
            event_time > 0
            and
            current_time - event_time <= 3
        )


        if event_is_recent:

            event_type = event.get(
                "type",
                "UNKNOWN"
            )

            if event_type == "LOOKING_AWAY":

                direction = event.get(
                    "direction",
                    "UNKNOWN"
                )

                event_text = (
                    f"🚨 LOOKING AWAY — {direction}"
                )

            elif event_type == "EYES_CLOSED":

                event_text = (
                    "🚨 EYES CLOSED"
                )

            elif event_type == "FACE_NOT_DETECTED":

                event_text = (
                    "🚨 FACE NOT DETECTED"
                )

            elif event_type == "MULTIPLE_FACES":

                event_text = (
                    "🚨 MULTIPLE FACES DETECTED"
                )

            else:

                event_text = (
                    f"🚨 {event_type}"
                )


            event_placeholder.error(
                event_text
            )

        else:

            event_placeholder.empty()


        # ====================================================
        # EVENT COUNTING
        # ====================================================

        # Only add event once
        if event is not None and event_time > 0:

            event_key = (
                event_time,
                event.get("type")
            )

            existing_keys = [
                x["key"]
                for x in st.session_state.event_history
            ]

            if event_key not in existing_keys:

                event_type = event.get(
                    "type",
                    "UNKNOWN"
                )

                if event_type not in st.session_state.event_counts:

                    st.session_state.event_counts[
                        event_type
                    ] = 0

                st.session_state.event_counts[
                    event_type
                ] += 1


                st.session_state.event_history.insert(
                    0,
                    {
                        "key": event_key,
                        "time": time.strftime(
                            "%H:%M:%S",
                            time.localtime(event_time)
                        ),
                        "type": event_type,
                        "direction": event.get(
                            "direction",
                            "-"
                        ),
                        "duration": event.get(
                            "duration",
                            0
                        )
                    }
                )


        # ====================================================
        # STATUS
        # ====================================================

        status = state.get(
            "status",
            "UNKNOWN"
        )

        direction = state.get(
            "direction",
            "UNKNOWN"
        )

        eye_status = state.get(
            "eye_status",
            "UNKNOWN"
        )

        face_count = state.get(
            "face_count",
            0
        )

        fps = state.get(
            "fps",
            0
        )


        # ====================================================
        # METRICS
        # ====================================================

        c1, c2, c3, c4, c5 = (
            metrics_placeholder.columns(5)
        )


        with c1:

            st.metric(
                "Status",
                status
            )


        with c2:

            st.metric(
                "Faces",
                face_count
            )


        with c3:

            st.metric(
                "Direction",
                direction
            )


        with c4:

            st.metric(
                "Eyes",
                eye_status
            )


        with c5:

            st.metric(
                "FPS",
                f"{fps:.1f}"
            )


        # ====================================================
        # EVENT HISTORY
        # ====================================================

        with history_placeholder.container():

            st.subheader(
                "🚨 Recent Events"
            )

            if st.session_state.event_history:

                display_events = []

                for item in st.session_state.event_history[:10]:

                    display_events.append(
                        {
                            "Time": item["time"],
                            "Event": item["type"],
                            "Direction": item["direction"],
                            "Duration": (
                                f"{item['duration']:.1f}s"
                                if isinstance(
                                    item["duration"],
                                    (int, float)
                                )
                                else "-"
                            )
                        }
                    )

                st.dataframe(
                    display_events,
                    use_container_width=True,
                    hide_index=True
                )

            else:

                st.info(
                    "No monitoring events detected yet."
                )


    # ========================================================
    # RUN LIVE MONITOR
    # ========================================================

    live_frame()


# ============================================================
# NOT RUNNING
# ============================================================

else:

    st.info(
        "Click **Start Exam** to begin live monitoring."
    )