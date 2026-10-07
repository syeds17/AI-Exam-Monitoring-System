import sqlite3
import uuid
from datetime import datetime


class AssessmentManager:

    def __init__(
        self,
        db_path="data/exam_monitoring.db"
    ):

        self.db_path = db_path

        self._initialize_database()

    # ==========================================================
    # DATABASE CONNECTION
    # ==========================================================

    def _connect(self):

        connection = sqlite3.connect(
            self.db_path
        )

        connection.row_factory = sqlite3.Row

        return connection

    # ==========================================================
    # INITIALIZE DATABASE
    # ==========================================================

    def _initialize_database(self):

        connection = self._connect()

        cursor = connection.cursor()

        # ------------------------------------------------------
        # ASSESSMENTS
        # ------------------------------------------------------

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS assessments (

                assessment_id TEXT PRIMARY KEY,

                assessment_name TEXT NOT NULL,

                organization TEXT,

                assessment_type TEXT NOT NULL,

                candidate_name TEXT,

                candidate_id TEXT,

                candidate_limit INTEGER NOT NULL DEFAULT 50,

                access_token TEXT UNIQUE,

                scheduled_at TEXT,

                duration_minutes INTEGER NOT NULL DEFAULT 60,

                status TEXT NOT NULL DEFAULT 'READY',

                created_at TEXT NOT NULL
            )
            """
        )

        # ------------------------------------------------------
        # CANDIDATES
        # ------------------------------------------------------

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS candidates (

                candidate_record_id TEXT PRIMARY KEY,

                candidate_name TEXT NOT NULL,

                candidate_id TEXT,

                created_at TEXT NOT NULL
            )
            """
        )

        # ------------------------------------------------------
        # ASSESSMENT ↔ CANDIDATES
        # ------------------------------------------------------

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS assessment_candidates (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                assessment_id TEXT NOT NULL,

                candidate_record_id TEXT NOT NULL,

                status TEXT NOT NULL DEFAULT 'AUTHORIZED',

                access_code TEXT UNIQUE,

                authorized_at TEXT,

                started_at TEXT,

                completed_at TEXT,

                reviewer_decision TEXT,

                reviewer_notes TEXT,

                FOREIGN KEY (
                    assessment_id
                )
                REFERENCES assessments (
                    assessment_id
                ),

                FOREIGN KEY (
                    candidate_record_id
                )
                REFERENCES candidates (
                    candidate_record_id
                ),

                UNIQUE (
                    assessment_id,
                    candidate_record_id
                )
            )
            """
        )

        # ------------------------------------------------------
        # ASSESSMENT SESSIONS
        # ------------------------------------------------------

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS assessment_sessions (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                assessment_id TEXT NOT NULL,

                candidate_record_id TEXT,

                session_id TEXT NOT NULL UNIQUE,

                created_at TEXT NOT NULL,

                FOREIGN KEY (
                    assessment_id
                )
                REFERENCES assessments (
                    assessment_id
                ),

                FOREIGN KEY (
                    candidate_record_id
                )
                REFERENCES candidates (
                    candidate_record_id
                )
            )
            """
        )

        # ------------------------------------------------------
        # MIGRATE OLD assessment_sessions TABLE
        # ------------------------------------------------------
        # Existing databases may have been created before
        # candidate_record_id was added to the schema.
        # CREATE TABLE IF NOT EXISTS does not modify an
        # already-existing table, so add the column explicitly.
        cursor.execute(
            "PRAGMA table_info(assessment_sessions)"
        )

        session_columns = {
            row["name"]
            for row in cursor.fetchall()
        }

        if "candidate_record_id" not in session_columns:
            cursor.execute(
                """
                ALTER TABLE assessment_sessions
                ADD COLUMN candidate_record_id TEXT
                """
            )

        # ------------------------------------------------------
        # MIGRATE ASSESSMENTS TABLE
        # ------------------------------------------------------
        cursor.execute("PRAGMA table_info(assessments)")
        assessment_columns = {
            row["name"]
            for row in cursor.fetchall()
        }

        if "candidate_limit" not in assessment_columns:
            cursor.execute(
                """
                ALTER TABLE assessments
                ADD COLUMN candidate_limit INTEGER NOT NULL DEFAULT 50
                """
            )

        if "access_token" not in assessment_columns:
            cursor.execute(
                """
                ALTER TABLE assessments
                ADD COLUMN access_token TEXT
                """
            )

        # Give existing assessments a public token.
        cursor.execute(
            """
            SELECT assessment_id
            FROM assessments
            WHERE access_token IS NULL OR access_token = ''
            """
        )

        for row in cursor.fetchall():
            token = self._generate_assessment_token()
            cursor.execute(
                """
                UPDATE assessments
                SET access_token = ?
                WHERE assessment_id = ?
                """,
                (token, row["assessment_id"])
            )

        connection.commit()

        # ------------------------------------------------------
        # MIGRATE EXISTING SINGLE-CANDIDATE ASSESSMENTS
        # ------------------------------------------------------

        self._migrate_existing_candidates(
            connection
        )

        connection.close()

    # ==========================================================
    # MIGRATE OLD CANDIDATE DATA
    # ==========================================================

    def _migrate_existing_candidates(
        self,
        connection
    ):

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                assessment_id,
                candidate_name,
                candidate_id
            FROM assessments
            WHERE candidate_name IS NOT NULL
              AND candidate_name != ''
            """
        )

        old_assessments = cursor.fetchall()

        for assessment in old_assessments:

            assessment_id = (
                assessment["assessment_id"]
            )

            candidate_name = (
                assessment["candidate_name"]
            )

            candidate_id = (
                assessment["candidate_id"]
            )

            # --------------------------------------------------
            # Check whether already migrated
            # --------------------------------------------------

            cursor.execute(
                """
                SELECT ac.id
                FROM assessment_candidates ac

                WHERE ac.assessment_id = ?
                """,
                (
                    assessment_id,
                )
            )

            existing = cursor.fetchone()

            if existing is not None:

                continue

            # --------------------------------------------------
            # Create candidate
            # --------------------------------------------------

            candidate_record_id = (
                self._generate_candidate_record_id()
            )

            created_at = (
                self._now()
            )

            cursor.execute(
                """
                INSERT INTO candidates (

                    candidate_record_id,
                    candidate_name,
                    candidate_id,
                    created_at

                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    candidate_record_id,
                    candidate_name,
                    candidate_id,
                    created_at
                )
            )

            # --------------------------------------------------
            # Link candidate to assessment
            # --------------------------------------------------

            access_code = (
                self._generate_access_code()
            )

            cursor.execute(
                """
                INSERT INTO assessment_candidates (

                    assessment_id,
                    candidate_record_id,
                    status,
                    access_code,
                    authorized_at

                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    assessment_id,
                    candidate_record_id,
                    "AUTHORIZED",
                    access_code,
                    created_at
                )
            )

        connection.commit()

    # ==========================================================
    # HELPERS
    # ==========================================================

    def _now(self):

        return datetime.now().isoformat(
            timespec="seconds"
        )

    def _generate_assessment_id(self):

        return (
            "ASM-"
            + uuid.uuid4()
            .hex[:10]
            .upper()
        )

    def _generate_assessment_token(self):

        return uuid.uuid4().hex[:12].upper()

    def _generate_candidate_record_id(self):

        return (
            "CAN-"
            + uuid.uuid4()
            .hex[:10]
            .upper()
        )

    def _generate_access_code(self):

        return (
            "ACCESS-"
            + uuid.uuid4()
            .hex[:8]
            .upper()
        )

    # ==========================================================
    # CREATE ASSESSMENT
    # ==========================================================

    def create_assessment(
        self,
        assessment_name,
        organization,
        assessment_type,
        candidate_name="",
        candidate_id="",
        scheduled_at=None,
        duration_minutes=60,
        candidate_limit=50
    ):

        assessment_id = (
            self._generate_assessment_id()
        )

        access_token = self._generate_assessment_token()

        created_at = (
            self._now()
        )

        connection = self._connect()

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO assessments (

                assessment_id,
                assessment_name,
                organization,
                assessment_type,
                candidate_name,
                candidate_id,
                candidate_limit,
                access_token,
                scheduled_at,
                duration_minutes,
                status,
                created_at

            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                assessment_id,
                assessment_name,
                organization,
                assessment_type,
                candidate_name,
                candidate_id,
                candidate_limit,
                access_token,
                scheduled_at,
                duration_minutes,
                "READY",
                created_at
            )
        )

        connection.commit()

        connection.close()

        # ------------------------------------------------------
        # Backward-compatible initial candidate
        # ------------------------------------------------------

        if candidate_name:

            self.add_candidate(
                assessment_id=assessment_id,
                candidate_name=candidate_name,
                candidate_id=candidate_id
            )

        return assessment_id

    # ==========================================================
    # GET ALL ASSESSMENTS
    # ==========================================================

    def get_assessments(self):

        connection = self._connect()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM assessments
            ORDER BY created_at DESC
            """
        )

        assessments = []

        for row in cursor.fetchall():

            assessment = dict(row)

            assessment[
                "candidates"
            ] = self.get_candidates(
                assessment[
                    "assessment_id"
                ]
            )

            assessment[
                "candidate_count"
            ] = len(
                assessment[
                    "candidates"
                ]
            )

            assessments.append(
                assessment
            )

        connection.close()

        return assessments

    # ==========================================================
    # GET SINGLE ASSESSMENT
    # ==========================================================

    def get_assessment(
        self,
        assessment_id
    ):

        connection = self._connect()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM assessments
            WHERE assessment_id = ?
            """,
            (
                assessment_id,
            )
        )

        row = cursor.fetchone()

        connection.close()

        if row is None:

            return None

        assessment = dict(row)

        assessment[
            "candidates"
        ] = self.get_candidates(
            assessment_id
        )

        assessment[
            "candidate_count"
        ] = len(
            assessment[
                "candidates"
            ]
        )

        return assessment

    # ==========================================================
    # GET ASSESSMENT BY PUBLIC TOKEN
    # ==========================================================

    def get_assessment_by_access_token(
        self,
        access_token
    ):

        connection = self._connect()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM assessments
            WHERE access_token = ?
            LIMIT 1
            """,
            (access_token,)
        )

        row = cursor.fetchone()
        connection.close()

        if row is None:
            return None

        assessment = dict(row)
        assessment["candidates"] = self.get_candidates(
            assessment["assessment_id"]
        )
        assessment["candidate_count"] = len(
            assessment["candidates"]
        )

        return assessment

    # ==========================================================
    # REQUEST CANDIDATE ACCESS
    # ==========================================================

    def request_candidate_access(
        self,
        assessment_id,
        candidate_name,
        candidate_id=""
    ):

        assessment = self.get_assessment(assessment_id)

        if assessment is None:
            raise ValueError("Assessment not found.")

        if assessment["status"] != "ACTIVE":
            raise ValueError("Assessment is not active.")

        current_count = len(
            self.get_candidates(assessment_id)
        )

        candidate_limit = assessment.get(
            "candidate_limit",
            50
        )

        if current_count >= candidate_limit:
            raise ValueError("Candidate limit reached.")

        connection = self._connect()
        cursor = connection.cursor()

        candidate_record_id = self._generate_candidate_record_id()
        created_at = self._now()

        cursor.execute(
            """
            INSERT INTO candidates (
                candidate_record_id,
                candidate_name,
                candidate_id,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                candidate_record_id,
                candidate_name,
                candidate_id,
                created_at
            )
        )

        cursor.execute(
            """
            INSERT INTO assessment_candidates (
                assessment_id,
                candidate_record_id,
                status,
                access_code
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                assessment_id,
                candidate_record_id,
                "PENDING",
                None
            )
        )

        connection.commit()
        connection.close()

        return self.get_candidate(
            assessment_id,
            candidate_record_id
        )

    # ==========================================================
    # APPROVE CANDIDATE
    # ==========================================================

    def approve_candidate(
        self,
        assessment_id,
        candidate_record_id
    ):

        candidate = self.get_candidate(
            assessment_id,
            candidate_record_id
        )

        if candidate is None:
            raise ValueError("Candidate not found.")

        access_code = self._generate_access_code()
        authorized_at = self._now()

        connection = self._connect()
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE assessment_candidates
            SET
                status = 'AUTHORIZED',
                access_code = ?,
                authorized_at = ?
            WHERE assessment_id = ?
              AND candidate_record_id = ?
            """,
            (
                access_code,
                authorized_at,
                assessment_id,
                candidate_record_id
            )
        )

        connection.commit()
        connection.close()

        return self.get_candidate(
            assessment_id,
            candidate_record_id
        )

    # ==========================================================
    # REJECT CANDIDATE
    # ==========================================================

    def reject_candidate(
        self,
        assessment_id,
        candidate_record_id
    ):

        candidate = self.get_candidate(
            assessment_id,
            candidate_record_id
        )

        if candidate is None:
            raise ValueError("Candidate not found.")

        connection = self._connect()
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE assessment_candidates
            SET status = 'REJECTED'
            WHERE assessment_id = ?
              AND candidate_record_id = ?
            """,
            (
                assessment_id,
                candidate_record_id
            )
        )

        connection.commit()
        connection.close()

        return self.get_candidate(
            assessment_id,
            candidate_record_id
        )

    # ==========================================================
    # ACTIVATE ASSESSMENT
    # ==========================================================

    def activate_assessment(
        self,
        assessment_id
    ):

        assessment = self.get_assessment(assessment_id)

        if assessment is None:
            raise ValueError("Assessment not found.")

        connection = self._connect()
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE assessments
            SET status = 'ACTIVE'
            WHERE assessment_id = ?
            """,
            (assessment_id,)
        )

        connection.commit()
        connection.close()

        return self.get_assessment(assessment_id)

    # ==========================================================
    # DEACTIVATE ASSESSMENT
    # ==========================================================

    def deactivate_assessment(
        self,
        assessment_id
    ):

        assessment = self.get_assessment(assessment_id)

        if assessment is None:
            raise ValueError("Assessment not found.")

        connection = self._connect()
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE assessments
            SET status = 'DEACTIVATED'
            WHERE assessment_id = ?
            """,
            (assessment_id,)
        )

        connection.commit()
        connection.close()

        return self.get_assessment(assessment_id)

    # ==========================================================
    # ADD CANDIDATE
    # ==========================================================

    def add_candidate(
        self,
        assessment_id,
        candidate_name,
        candidate_id=""
    ):

        assessment = (
            self.get_assessment(
                assessment_id
            )
        )

        if assessment is None:

            raise ValueError(
                "Assessment not found."
            )

        current_count = len(
            self.get_candidates(assessment_id)
        )

        candidate_limit = assessment.get(
            "candidate_limit",
            50
        )

        if current_count >= candidate_limit:
            raise ValueError("Candidate limit reached.")

        connection = self._connect()

        cursor = connection.cursor()

        candidate_record_id = (
            self._generate_candidate_record_id()
        )

        created_at = (
            self._now()
        )

        cursor.execute(
            """
            INSERT INTO candidates (

                candidate_record_id,
                candidate_name,
                candidate_id,
                created_at

            )
            VALUES (?, ?, ?, ?)
            """,
            (
                candidate_record_id,
                candidate_name,
                candidate_id,
                created_at
            )
        )

        access_code = (
            self._generate_access_code()
        )

        cursor.execute(
            """
            INSERT INTO assessment_candidates (

                assessment_id,
                candidate_record_id,
                status,
                access_code,
                authorized_at

            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                assessment_id,
                candidate_record_id,
                "AUTHORIZED",
                access_code,
                created_at
            )
        )

        connection.commit()

        connection.close()

        return self.get_candidate(
            assessment_id,
            candidate_record_id
        )

    # ==========================================================
    # GET CANDIDATES
    # ==========================================================

    def get_candidates(
        self,
        assessment_id
    ):

        connection = self._connect()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT

                c.candidate_record_id,
                c.candidate_name,
                c.candidate_id,
                c.created_at,

                ac.id AS assignment_id,
                ac.status AS assignment_status,
                ac.access_code,
                ac.authorized_at,
                ac.started_at,
                ac.completed_at,
                ac.reviewer_decision,
                ac.reviewer_notes

            FROM candidates c

            INNER JOIN assessment_candidates ac

                ON c.candidate_record_id =
                   ac.candidate_record_id

            WHERE ac.assessment_id = ?

            ORDER BY c.created_at ASC
            """,
            (
                assessment_id,
            )
        )

        candidates = [
            dict(row)
            for row in cursor.fetchall()
        ]

        connection.close()

        return candidates

    # ==========================================================
    # GET ONE CANDIDATE
    # ==========================================================

    def get_candidate(
        self,
        assessment_id,
        candidate_record_id
    ):

        candidates = (
            self.get_candidates(
                assessment_id
            )
        )

        for candidate in candidates:

            if (
                candidate[
                    "candidate_record_id"
                ]
                ==
                candidate_record_id
            ):

                return candidate

        return None

    # ==========================================================
    # FIND CANDIDATE BY ACCESS CODE
    # ==========================================================

    def get_candidate_by_access_code(
        self,
        access_code
    ):

        connection = self._connect()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT

                a.assessment_id,
                a.assessment_name,
                a.organization,
                a.assessment_type,
                a.scheduled_at,
                a.duration_minutes,
                a.status AS assessment_status,

                c.candidate_record_id,
                c.candidate_name,
                c.candidate_id,

                ac.id AS assignment_id,
                ac.status AS assignment_status,
                ac.access_code,
                ac.authorized_at,
                ac.started_at,
                ac.completed_at,
                ac.reviewer_decision,
                ac.reviewer_notes

            FROM assessment_candidates ac

            INNER JOIN assessments a

                ON a.assessment_id =
                   ac.assessment_id

            INNER JOIN candidates c

                ON c.candidate_record_id =
                   ac.candidate_record_id

            WHERE ac.access_code = ?

            LIMIT 1
            """,
            (
                access_code,
            )
        )

        row = cursor.fetchone()

        connection.close()

        if row is None:

            return None

        return dict(row)

    # ==========================================================
    # ASSESSMENT CANDIDATE COUNTS
    # ==========================================================

    def get_candidate_counts(
        self,
        assessment_id
    ):

        candidates = self.get_candidates(assessment_id)

        counts = {
            "total": len(candidates),
            "pending": 0,
            "accepted": 0,
            "rejected": 0,
            "active": 0,
            "completed": 0,
            "not_started": 0
        }

        for candidate in candidates:
            status = candidate.get("assignment_status")

            if status == "PENDING":
                counts["pending"] += 1
            elif status == "AUTHORIZED":
                counts["accepted"] += 1
                counts["not_started"] += 1
            elif status == "IN_PROGRESS":
                counts["active"] += 1
            elif status == "COMPLETED":
                counts["completed"] += 1
            elif status == "REJECTED":
                counts["rejected"] += 1

        return counts

    # ==========================================================
    # MARK ASSESSMENT IN PROGRESS
    # ==========================================================

    def mark_in_progress(
        self,
        assessment_id
    ):

        connection = self._connect()

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE assessments

            SET status = 'IN_PROGRESS'

            WHERE assessment_id = ?
            """,
            (
                assessment_id,
            )
        )

        connection.commit()

        connection.close()

    # ==========================================================
    # MARK ASSESSMENT COMPLETED
    # ==========================================================

    def mark_completed(
        self,
        assessment_id
    ):

        connection = self._connect()

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE assessments

            SET status = 'COMPLETED'

            WHERE assessment_id = ?
            """,
            (
                assessment_id,
            )
        )

        connection.commit()

        connection.close()

    # ==========================================================
    # MARK CANDIDATE STARTED
    # ==========================================================

    def mark_candidate_started(
        self,
        assessment_id,
        candidate_record_id
    ):

        connection = self._connect()

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE assessment_candidates

            SET
                status = 'IN_PROGRESS',
                started_at = ?

            WHERE assessment_id = ?
              AND candidate_record_id = ?
            """,
            (
                self._now(),
                assessment_id,
                candidate_record_id
            )
        )

        connection.commit()

        connection.close()

    # ==========================================================
    # MARK CANDIDATE COMPLETED
    # ==========================================================

    def mark_candidate_completed(
        self,
        assessment_id,
        candidate_record_id
    ):

        connection = self._connect()

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE assessment_candidates

            SET
                status = 'COMPLETED',
                completed_at = ?

            WHERE assessment_id = ?
              AND candidate_record_id = ?
            """,
            (
                self._now(),
                assessment_id,
                candidate_record_id
            )
        )

        connection.commit()

        connection.close()

    # ==========================================================
    # LINK SESSION
    # ==========================================================

    def link_session(
        self,
        assessment_id,
        session_id,
        candidate_record_id=None
    ):

        connection = self._connect()

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO assessment_sessions (

                assessment_id,
                candidate_record_id,
                session_id,
                created_at

            )
            VALUES (?, ?, ?, ?)
            """,
            (
                assessment_id,
                candidate_record_id,
                session_id,
                self._now()
            )
        )

        connection.commit()

        connection.close()

    # ==========================================================
    # GET SESSION
    # ==========================================================

    def get_session(
        self,
        session_id
    ):

        connection = self._connect()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM assessment_sessions
            WHERE session_id = ?
            """,
            (
                session_id,
            )
        )

        row = cursor.fetchone()

        connection.close()

        if row is None:

            return None

        return dict(row)
    
    # ==========================================================
    # GET EVENTS FOR SESSION
    # ==========================================================

    def get_events_for_session(
        self,
        session_id
    ):

        connection = self._connect()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                session_id,
                timestamp,
                event_type,
                direction,
                duration,
                evidence_path
            FROM events
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (
                session_id,
            )
        )

        rows = cursor.fetchall()

        connection.close()

        return [
            dict(row)
            for row in rows
        ]

    # ==========================================================
    # RESET ASSESSMENT
    # ==========================================================

    def reset_to_ready(
        self,
        assessment_id
    ):

        connection = self._connect()

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE assessments

            SET status = 'READY'

            WHERE assessment_id = ?
            """,
            (
                assessment_id,
            )
        )

        connection.commit()

        connection.close()

    # ==========================================================
    # REVIEW DECISION
    # ==========================================================

    def set_reviewer_decision(
        self,
        assessment_id,
        candidate_record_id,
        decision,
        notes=""
    ):

        allowed_decisions = {
            "CHEATING",
            "NOT_CHEATING",
            "NEEDS_REVIEW"
        }

        if decision not in allowed_decisions:

            raise ValueError(
                "Invalid reviewer decision."
            )

        connection = self._connect()

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE assessment_candidates

            SET
                reviewer_decision = ?,
                reviewer_notes = ?

            WHERE assessment_id = ?
              AND candidate_record_id = ?
            """,
            (
                decision,
                notes,
                assessment_id,
                candidate_record_id
            )
        )

        connection.commit()

        connection.close()