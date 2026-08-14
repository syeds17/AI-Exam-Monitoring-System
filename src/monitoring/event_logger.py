import sqlite3
from pathlib import Path
from datetime import datetime
import uuid


class EventLogger:

    def __init__(self, db_path="data/exam_monitoring.db"):

        self.db_path = Path(db_path)

        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.connection = sqlite3.connect(
            self.db_path
        )

        self.session_id = None

        self._create_tables()

    def _create_tables(self):

        cursor = self.connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                start_time TEXT NOT NULL,
                end_time TEXT,
                status TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                direction TEXT,
                duration REAL
            )
        """)
        
        cursor.execute("PRAGMA table_info(events)")
        
        columns = [
            row[1]
            for row in cursor.fetchall()
        ]
        
        if "session_id" not in columns:

            cursor.execute("""
                ALTER TABLE events
                ADD COLUMN session_id TEXT
            """)


        self.connection.commit()

    def start_session(self):

        self.session_id = (
            datetime.now().strftime("%Y%m%d_%H%M%S")
            + "_"
            + uuid.uuid4().hex[:6]
        )

        start_time = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        cursor = self.connection.cursor()

        cursor.execute(
            """
            INSERT INTO sessions (
                session_id,
                start_time,
                status
            )
            VALUES (?, ?, ?)
            """,
            (
                self.session_id,
                start_time,
                "ACTIVE"
            )
        )

        self.connection.commit()

        return self.session_id

    def end_session(self):

        if self.session_id is None:
            return

        end_time = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        cursor = self.connection.cursor()

        cursor.execute(
            """
            UPDATE sessions
            SET end_time = ?, status = ?
            WHERE session_id = ?
            """,
            (
                end_time,
                "COMPLETED",
                self.session_id
            )
        )

        self.connection.commit()

    def log_event(self, event):

        if event is None:
            return

        if self.session_id is None:
            raise RuntimeError(
                "No active exam session."
            )

        timestamp = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        event_type = event.get(
            "type",
            "UNKNOWN"
        )

        direction = event.get(
            "direction"
        )

        duration = event.get(
            "duration"
        )

        cursor = self.connection.cursor()

        cursor.execute(
            """
            INSERT INTO events (
                session_id,
                timestamp,
                event_type,
                direction,
                duration
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                self.session_id,
                timestamp,
                event_type,
                direction,
                duration
            )
        )

        self.connection.commit()

    def get_events(self, session_id=None):

        cursor = self.connection.cursor()

        if session_id is None:
            session_id = self.session_id

        cursor.execute(
            """
            SELECT
                id,
                session_id,
                timestamp,
                event_type,
                direction,
                duration
            FROM events
            WHERE session_id = ?
            ORDER BY id DESC
            """,
            (session_id,)
        )

        return cursor.fetchall()

    def get_sessions(self):

        cursor = self.connection.cursor()

        cursor.execute("""
            SELECT
                session_id,
                start_time,
                end_time,
                status
            FROM sessions
            ORDER BY start_time DESC
        """)

        return cursor.fetchall()

    def close(self):

        self.connection.close()