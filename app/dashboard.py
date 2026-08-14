import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


# ==========================================
# CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="AI Exam Monitoring System",
    page_icon="🛡️",
    layout="wide"
)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "exam_monitoring.db"


# ==========================================
# DATABASE FUNCTIONS
# ==========================================

def get_connection():
    return sqlite3.connect(DB_PATH)


def get_sessions():

    connection = get_connection()

    query = """
        SELECT
            session_id,
            start_time,
            end_time,
            status
        FROM sessions
        ORDER BY start_time DESC
    """

    df = pd.read_sql_query(
        query,
        connection
    )

    connection.close()

    return df


def get_events(session_id):

    connection = get_connection()

    query = """
        SELECT
            id,
            timestamp,
            event_type,
            direction,
            duration,
            session_id
        FROM events
        WHERE session_id = ?
        ORDER BY timestamp DESC
    """

    df = pd.read_sql_query(
        query,
        connection,
        params=(session_id,)
    )

    connection.close()

    return df


# ==========================================
# HEADER
# ==========================================

st.title("🛡️ AI Exam Monitoring System")

st.caption(
    "AI-powered examination monitoring dashboard"
)


# ==========================================
# DATABASE CHECK
# ==========================================

if not DB_PATH.exists():

    st.error(
        f"Database not found: {DB_PATH}"
    )

    st.stop()


# ==========================================
# LOAD SESSIONS
# ==========================================

sessions = get_sessions()


if sessions.empty:

    st.warning(
        "No exam sessions have been recorded yet."
    )

    st.stop()


# ==========================================
# SIDEBAR
# ==========================================

st.sidebar.title("⚙️ Controls")

session_ids = sessions["session_id"].tolist()

selected_session = st.sidebar.selectbox(
    "Select Exam Session",
    session_ids
)


# ==========================================
# SELECTED SESSION
# ==========================================

session = sessions[
    sessions["session_id"] == selected_session
].iloc[0]

events = get_events(
    selected_session
)


# ==========================================
# SESSION HEADER
# ==========================================

st.subheader("📋 Exam Session")

col1, col2, col3 = st.columns(3)

with col1:

    st.metric(
        "Session Status",
        session["status"]
    )

with col2:

    st.metric(
        "Total Events",
        len(events)
    )

with col3:

    st.metric(
        "Session ID",
        selected_session
    )


st.write(
    f"**Started:** {session['start_time']}"
)

if pd.notna(session["end_time"]):

    st.write(
        f"**Ended:** {session['end_time']}"
    )


# ==========================================
# EVENT COUNTS
# ==========================================

st.subheader("🚨 Monitoring Summary")


def count_events(event_type):

    return len(
        events[
            events["event_type"] == event_type
        ]
    )


looking_away = count_events(
    "LOOKING_AWAY"
)

eyes_closed = count_events(
    "EYES_CLOSED"
)

face_missing = count_events(
    "FACE_NOT_DETECTED"
)

multiple_faces = count_events(
    "MULTIPLE_FACES"
)


col1, col2, col3, col4 = st.columns(4)

with col1:

    st.metric(
        "👀 Looking Away",
        looking_away
    )

with col2:

    st.metric(
        "👁️ Eyes Closed",
        eyes_closed
    )

with col3:

    st.metric(
        "❌ Face Missing",
        face_missing
    )

with col4:

    st.metric(
        "👥 Multiple Faces",
        multiple_faces
    )


# ==========================================
# EVENT TABLE
# ==========================================

st.subheader("🕒 Event Timeline")


if events.empty:

    st.success(
        "No monitoring events recorded for this session."
    )

else:

    display_events = events[
        [
            "timestamp",
            "event_type",
            "direction",
            "duration"
        ]
    ].copy()

    display_events.columns = [
        "Timestamp",
        "Event",
        "Direction",
        "Duration (seconds)"
    ]

    st.dataframe(
        display_events,
        use_container_width=True,
        hide_index=True
    )


# ==========================================
# EVENT DISTRIBUTION
# ==========================================

st.subheader("📊 Event Distribution")


if not events.empty:

    event_counts = (
        events["event_type"]
        .value_counts()
    )

    st.bar_chart(
        event_counts
    )


# ==========================================
# FOOTER
# ==========================================

st.divider()

st.caption(
    "AI Exam Monitoring System • Final Year Project"
)