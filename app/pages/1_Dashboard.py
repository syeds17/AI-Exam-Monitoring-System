import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


# ==========================================
# CONFIG
# ==========================================

st.set_page_config(
    page_title="Exam Dashboard",
    page_icon="📊",
    layout="wide"
)


# ==========================================
# DATABASE
# ==========================================

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "data" / "exam_monitoring.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


# ==========================================
# LOAD DATA
# ==========================================

def load_sessions():

    conn = get_connection()

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
        conn
    )

    conn.close()

    return df


def load_events():

    conn = get_connection()

    query = """
        SELECT
            id,
            timestamp,
            event_type,
            direction,
            duration,
            session_id
        FROM events
        ORDER BY timestamp DESC
    """

    df = pd.read_sql_query(
        query,
        conn
    )

    conn.close()

    return df


# ==========================================
# HEADER
# ==========================================

st.title("📊 Exam Monitoring Dashboard")

st.caption(
    "AI-powered examination monitoring analytics"
)


# ==========================================
# REFRESH
# ==========================================

if st.button("🔄 Refresh Dashboard"):

    st.rerun()


# ==========================================
# LOAD
# ==========================================

try:

    sessions = load_sessions()
    events = load_events()

except Exception as e:

    st.error(
        f"Could not load database: {e}"
    )

    st.stop()


# ==========================================
# METRICS
# ==========================================

total_sessions = len(sessions)

total_events = len(events)

active_events = len(
    events[
        events["event_type"].isin(
            [
                "LOOKING_AWAY",
                "EYES_CLOSED",
                "FACE_NOT_DETECTED",
                "MULTIPLE_FACES"
            ]
        )
    ]
)


if not events.empty:

    total_violation_time = events[
        "duration"
    ].fillna(0).sum()

else:

    total_violation_time = 0


col1, col2, col3, col4 = st.columns(4)


with col1:

    st.metric(
        "📋 Total Sessions",
        total_sessions
    )


with col2:

    st.metric(
        "🚨 Total Events",
        total_events
    )


with col3:

    st.metric(
        "⚠️ Monitoring Events",
        active_events
    )


with col4:

    st.metric(
        "⏱️ Event Duration",
        f"{total_violation_time:.1f}s"
    )


st.divider()


# ==========================================
# EVENT ANALYTICS
# ==========================================

st.subheader("📈 Event Analytics")


if events.empty:

    st.info(
        "No monitoring events recorded yet."
    )

else:

    event_counts = (
        events["event_type"]
        .value_counts()
        .rename_axis("Event")
        .reset_index(name="Count")
    )

    col1, col2 = st.columns(2)


    with col1:

        st.markdown(
            "### Event Distribution"
        )

        st.bar_chart(
            event_counts.set_index("Event")
        )


    with col2:

        st.markdown(
            "### Event Counts"
        )

        st.dataframe(
            event_counts,
            use_container_width=True,
            hide_index=True
        )


st.divider()


# ==========================================
# RECENT EVENTS
# ==========================================

st.subheader("🚨 Recent Events")


if events.empty:

    st.info(
        "No events recorded."
    )

else:

    recent_events = events.head(10).copy()

    recent_events.columns = [
        "ID",
        "Timestamp",
        "Event",
        "Direction",
        "Duration",
        "Session ID"
    ]

    st.dataframe(
        recent_events,
        use_container_width=True,
        hide_index=True
    )


st.divider()


# ==========================================
# SESSIONS
# ==========================================

st.subheader("📝 Exam Sessions")


if sessions.empty:

    st.info(
        "No exam sessions recorded yet."
    )

else:

    display_sessions = sessions.copy()

    display_sessions.columns = [
        "Session ID",
        "Start Time",
        "End Time",
        "Status"
    ]

    st.dataframe(
        display_sessions,
        use_container_width=True,
        hide_index=True
    )


st.divider()


# ==========================================
# SESSION EVENT SUMMARY
# ==========================================

st.subheader("🔎 Session Event Summary")


if not sessions.empty and not events.empty:

    session_summary = (
        events
        .groupby("session_id")
        .agg(
            total_events=("id", "count"),
            total_duration=("duration", "sum")
        )
        .reset_index()
        .sort_values(
            "total_events",
            ascending=False
        )
    )

    session_summary.columns = [
        "Session ID",
        "Events",
        "Total Duration (s)"
    ]

    st.dataframe(
        session_summary,
        use_container_width=True,
        hide_index=True
    )

else:

    st.info(
        "Not enough data for session analysis."
    )