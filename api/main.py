from pathlib import Path
import re
import hashlib
import hmac
import secrets

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import (
    FileResponse,
    StreamingResponse,
    JSONResponse,
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from api.monitoring_service import monitoring_service
from api.auth_service import (
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_SECURE,
    SESSION_TTL_HOURS,
    authenticate_author,
    create_author,
    list_authors,
    create_session,
    get_session_author,
    revoke_session,
    validate_session,
)

ACTIVE_CANDIDATE_VIDEO_TOKEN_HASH: str | None = None

class LoginRequest(BaseModel):
    username: str
    password: str


class CreateAuthorRequest(BaseModel):
    username: str
    password: str


# ==========================================================
# APPLICATION
# ==========================================================

app = FastAPI(
    title="AI Online Assessment Monitoring System",
    version="1.0.0",
)

# ==========================================================
# AUTHOR AUTHENTICATION
# ==========================================================


@app.post("/api/auth/login")
def author_login(request: LoginRequest):
    author = authenticate_author(
        request.username,
        request.password
    )

    if not author:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password."
        )

    token, expires_at = create_session(author["author_id"])

    response = JSONResponse({
        "success": True,
        "username": author["username"],
        "role": author["role"],
        "expires_at": expires_at.isoformat(),
    })

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="strict",
        max_age=SESSION_TTL_HOURS * 60 * 60,
        path="/",
    )

    return response




@app.get("/api/auth/me")
def author_me(request: Request):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    author = get_session_author(token)

    if not author:
        raise HTTPException(
            status_code=401,
            detail="Authentication required."
        )

    return {
        "authenticated": True,
        "author_id": author["author_id"],
        "username": author["username"],
        "role": author["role"],
        "expires_at": author["expires_at"],
    }

@app.post("/api/auth/logout")
def author_logout(request: Request):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    revoke_session(token)

    response = JSONResponse({
        "success": True,
        "message": "Logged out successfully.",
    })

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="strict",
    )

    return response



def require_author(request: Request):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    author = get_session_author(token)

    if not author:
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

    return author


def require_admin(request: Request):
    author = require_author(request)

    if author.get("role") != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Administrator access required.",
        )

    return author


def get_owned_assessment(
    assessment_id: str,
    current_author: dict,
):
    assessment = monitoring_service.get_assessment(assessment_id)

    if (
        assessment is None
        or assessment.get("created_by_author_id")
        != current_author["author_id"]
    ):
        raise HTTPException(
            status_code=404,
            detail="Assessment not found.",
        )

    return assessment


def get_owned_monitoring_session(
    session_id: str,
    current_author: dict,
):
    connection = monitoring_service.assessment_manager._connect()

    try:
        cursor = connection.cursor()

        row = cursor.execute(
            """
            SELECT a.*
            FROM assessment_sessions AS s
            JOIN assessments AS a
                ON a.assessment_id = s.assessment_id
            WHERE s.session_id = ?
              AND a.created_by_author_id = ?
            """,
            (
                session_id,
                current_author["author_id"],
            ),
        ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Monitoring session not found.",
            )

        return dict(row)

    finally:
        connection.close()


@app.post("/api/auth/authors", status_code=201)
def create_author_account(
    request: CreateAuthorRequest,
    current_author: dict = Depends(require_admin),
):
    username = request.username.strip()

    try:
        create_author(
            username=username,
            password=request.password,
            role="AUTHOR",
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    return {
        "success": True,
        "message": "Author account created successfully.",
        "username": username,
        "role": "AUTHOR",
    }
    
@app.get("/api/auth/authors")
def get_author_accounts(
    current_author: dict = Depends(require_admin),
):
    return {
        "success": True,
        "authors": list_authors(),
    }



def get_authenticated_candidate(request: Request):
    token = request.cookies.get("monitorai_candidate")

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Candidate authentication required.",
        )

    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    candidate = monitoring_service.get_candidate_by_token_hash(
        token_hash
    )

    if candidate is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid candidate credential.",
        )

    return candidate




# ==========================================================
# DIRECTORIES
# ==========================================================

WEB_DIR = Path("web")

EVIDENCE_DIR = Path(
    "data/evidence"
)

EVIDENCE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ==========================================================
# STATIC FILES
# ==========================================================

app.mount(
    "/static",
    StaticFiles(
        directory=str(WEB_DIR)
    ),
    name="static",
)

# ==========================================================
# REQUEST MODELS
# ==========================================================

class AssessmentCreateRequest(BaseModel):

    assessment_name: str

    organization: str = ""

    assessment_type: str

    scheduled_at: str | None = None

    duration_minutes: int = 60

    candidate_limit: int = 50


class CandidateAccessRequest(BaseModel):

    candidate_name: str

    candidate_id: str = ""
    
# ==========================================================
# HOME
# ==========================================================

@app.get("/")
def home():

    return FileResponse(
        WEB_DIR / "index.html"
    )


# ==========================================================
# CREATE ASSESSMENT
# ==========================================================


@app.post("/api/assessments")
def create_assessment(
    request: AssessmentCreateRequest,
    current_author: dict = Depends(require_author),
):
    try:
        assessment_id = monitoring_service.create_assessment(
            assessment_name=request.assessment_name,
            organization=request.organization,
            assessment_type=request.assessment_type,
            scheduled_at=request.scheduled_at,
            duration_minutes=request.duration_minutes,
            candidate_limit=request.candidate_limit,
            created_by_author_id=current_author["author_id"],
        )

        assessment = monitoring_service.get_assessment(
            assessment_id
        )

        return {
            "success": True,
            "assessment": assessment,
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to create assessment.",
        )


# ==========================================================
# GET ALL ASSESSMENTS
# ==========================================================


@app.get("/api/assessments")
def get_assessments(
    current_author: dict = Depends(require_author),
):
    try:
        assessments = monitoring_service.get_assessments(
            created_by_author_id=current_author["author_id"]
        )

        return {
            "assessments": assessments
        }

    except Exception:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve assessments."
        )


# ==========================================================
# GET SINGLE ASSESSMENT
# ==========================================================


@app.get("/api/assessments/{assessment_id}")
def get_assessment(
    assessment_id: str,
    current_author: dict = Depends(require_author),
):
    try:
        assessment = monitoring_service.get_assessment(
            assessment_id
        )

        if (
            assessment is None
            or assessment.get("created_by_author_id")
            != current_author["author_id"]
        ):
            raise HTTPException(
                status_code=404,
                detail="Assessment not found.",
            )

        return {
            "success": True,
            "assessment": assessment,
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve assessment.",
        )



# ==========================================================
# GET ASSESSMENT BY PUBLIC ACCESS TOKEN
# ==========================================================

@app.get(
    "/api/assessments/link/{access_token}",
    dependencies=[Depends(require_author)],
)
def get_assessment_by_access_token(
    access_token: str
):

    try:

        assessment = (
            monitoring_service
            .get_assessment_by_access_token(
                access_token
            )
        )

        if assessment is None:

            raise HTTPException(
                status_code=404,
                detail="Invalid assessment link.",
            )

        return {
            "success": True,
            "assessment": assessment,
        }

    except HTTPException:

        raise

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# ==========================================================
# ACTIVATE ASSESSMENT
# ==========================================================


@app.post("/api/assessments/{assessment_id}/activate")
def activate_assessment(
    assessment_id: str,
    current_author: dict = Depends(require_author),
):
    try:
        assessment = monitoring_service.get_assessment(
            assessment_id
        )

        if (
            assessment is None
            or assessment.get("created_by_author_id")
            != current_author["author_id"]
        ):
            raise HTTPException(
                status_code=404,
                detail="Assessment not found.",
            )

        updated_assessment = monitoring_service.activate_assessment(
            assessment_id
        )

        return {
            "success": True,
            "assessment": updated_assessment,
        }

    except HTTPException:
        raise

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to activate assessment.",
        )


# ==========================================================
# DEACTIVATE ASSESSMENT
# ==========================================================


@app.post("/api/assessments/{assessment_id}/deactivate")
def deactivate_assessment(
    assessment_id: str,
    current_author: dict = Depends(require_author),
):
    try:
        assessment = monitoring_service.get_assessment(
            assessment_id
        )

        if (
            assessment is None
            or assessment.get("created_by_author_id")
            != current_author["author_id"]
        ):
            raise HTTPException(
                status_code=404,
                detail="Assessment not found.",
            )

        updated_assessment = monitoring_service.deactivate_assessment(
            assessment_id
        )

        return {
            "success": True,
            "assessment": updated_assessment,
        }

    except HTTPException:
        raise

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to deactivate assessment.",
        )


# ==========================================================
# REQUEST CANDIDATE ACCESS
# ==========================================================



@app.post("/api/assessments/{assessment_id}/access-request")
def request_candidate_access(
    assessment_id: str,
    request: CandidateAccessRequest,
):
    try:
        # Verify the assessment exists.
        assessment = monitoring_service.get_assessment(
            assessment_id
        )

        if assessment is None:
            raise HTTPException(
                status_code=404,
                detail="Assessment not found.",
            )

        # Keep the candidate-facing route public.
        # Do not require an author session here.
        candidate = monitoring_service.request_candidate_access(
            assessment_id=assessment_id,
            candidate_name=request.candidate_name,
            candidate_id=request.candidate_id,
        )

        candidate_token = candidate.pop("candidate_token")
        candidate.pop("candidate_token_hash", None)

        result = JSONResponse({
            "success": True,
            "candidate": candidate,
        })

        result.set_cookie(
            key="monitorai_candidate",
            value=candidate_token,
            httponly=True,
            secure=SESSION_COOKIE_SECURE,
            samesite="strict",
            path="/api",
        )

        return result

    except HTTPException:
        raise

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to submit candidate access request.",
        )


# ==========================================================
# GET CANDIDATES
# ==========================================================


@app.get("/api/assessments/{assessment_id}/candidates")
def get_candidates(
    assessment_id: str,
    current_author: dict = Depends(require_author),
):
    try:
        assessment = monitoring_service.get_assessment(
            assessment_id
        )

        if (
            assessment is None
            or assessment.get("created_by_author_id")
            != current_author["author_id"]
        ):
            raise HTTPException(
                status_code=404,
                detail="Assessment not found.",
            )

        candidates = monitoring_service.get_candidates(
            assessment_id
        )

        return {
            "success": True,
            "assessment_id": assessment_id,
            "candidates": candidates,
            "candidate_count": len(candidates),
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve candidates.",
        )


# ==========================================================
# GET ONE CANDIDATE
# ==========================================================


@app.get("/api/assessments/{assessment_id}/candidates/{candidate_record_id}")
def get_candidate(
    assessment_id: str,
    candidate_record_id: str,
    current_author: dict = Depends(require_author),
):
    try:
        assessment = monitoring_service.get_assessment(assessment_id)

        if (
            assessment is None
            or assessment.get("created_by_author_id")
            != current_author["author_id"]
        ):
            raise HTTPException(
                status_code=404,
                detail="Assessment not found.",
            )

        candidate = monitoring_service.get_candidate(
            assessment_id=assessment_id,
            candidate_record_id=candidate_record_id,
        )

        if candidate is None:
            raise HTTPException(
                status_code=404,
                detail="Candidate not found.",
            )

        return {"success": True, "candidate": candidate}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve candidate.",
        )



@app.get("/api/candidate/status")
def get_candidate_status(request: Request):
    token = request.cookies.get("monitorai_candidate")

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Candidate authentication required.",
        )

    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    candidate = monitoring_service.get_candidate_by_token_hash(
        token_hash
    )

    if candidate is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid candidate credential.",
        )

    return {
        "success": True,
        "candidate": candidate,
    }


# ==========================================================
# APPROVE CANDIDATE
# ==========================================================


@app.post(
    "/api/assessments/{assessment_id}/candidates/{candidate_record_id}/approve"
)
def approve_candidate(
    assessment_id: str,
    candidate_record_id: str,
    current_author: dict = Depends(require_author),
):
    try:
        assessment = monitoring_service.get_assessment(assessment_id)

        if (
            assessment is None
            or assessment.get("created_by_author_id")
            != current_author["author_id"]
        ):
            raise HTTPException(
                status_code=404,
                detail="Assessment not found.",
            )

        candidate = monitoring_service.get_candidate(
            assessment_id=assessment_id,
            candidate_record_id=candidate_record_id,
        )

        if candidate is None:
            raise HTTPException(
                status_code=404,
                detail="Candidate not found.",
            )

        approved = monitoring_service.approve_candidate(
            assessment_id=assessment_id,
            candidate_record_id=candidate_record_id,
        )

        return {"success": True, "candidate": approved}

    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to approve candidate.",
        )


# ==========================================================
# REJECT CANDIDATE
# ==========================================================


@app.post(
    "/api/assessments/{assessment_id}/candidates/{candidate_record_id}/reject"
)
def reject_candidate(
    assessment_id: str,
    candidate_record_id: str,
    current_author: dict = Depends(require_author),
):
    try:
        assessment = monitoring_service.get_assessment(assessment_id)

        if (
            assessment is None
            or assessment.get("created_by_author_id")
            != current_author["author_id"]
        ):
            raise HTTPException(
                status_code=404,
                detail="Assessment not found.",
            )

        candidate = monitoring_service.get_candidate(
            assessment_id=assessment_id,
            candidate_record_id=candidate_record_id,
        )

        if candidate is None:
            raise HTTPException(
                status_code=404,
                detail="Candidate not found.",
            )

        rejected = monitoring_service.reject_candidate(
            assessment_id=assessment_id,
            candidate_record_id=candidate_record_id,
        )

        return {"success": True, "candidate": rejected}

    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to reject candidate.",
        )


# ==========================================================
# GET CANDIDATE BY ACCESS CODE
# ==========================================================

@app.get(
    "/api/candidates/access/{access_code}"
)
def get_candidate_by_access_code(
    access_code: str
):

    try:

        candidate = (
            monitoring_service
            .get_candidate_by_access_code(
                access_code
            )
        )

        if candidate is None:

            raise HTTPException(
                status_code=404,
                detail="Invalid candidate access code.",
            )

        return {
            "success": True,
            "candidate": candidate,
        }

    except HTTPException:

        raise

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# ==========================================================
# START CANDIDATE MONITORING
# ==========================================================


@app.post(
    "/api/assessments/{assessment_id}/candidates/{candidate_record_id}/start"
)
def start_candidate_monitoring(
    assessment_id: str,
    candidate_record_id: str,
    request: Request,
):
    global ACTIVE_CANDIDATE_VIDEO_TOKEN_HASH

    try:
        candidate = get_authenticated_candidate(request)

        if (
            candidate["assessment_id"] != assessment_id
            or candidate["candidate_record_id"] != candidate_record_id
        ):
            raise HTTPException(
                status_code=403,
                detail="Candidate session mismatch.",
            )

        if candidate["assessment_status"] != "ACTIVE":
            raise HTTPException(
                status_code=400,
                detail="Assessment is not active.",
            )

        if candidate["assignment_status"] != "AUTHORIZED":
            raise HTTPException(
                status_code=403,
                detail="Candidate is not authorized to start.",
            )

        session_id = monitoring_service.start(
            assessment_id=assessment_id,
            candidate_record_id=candidate_record_id,
        )

        video_token = secrets.token_urlsafe(32)

        ACTIVE_CANDIDATE_VIDEO_TOKEN_HASH = hashlib.sha256(
            video_token.encode("utf-8")
        ).hexdigest()

        response = JSONResponse({
            "success": True,
            "assessment_id": assessment_id,
            "candidate_record_id": candidate_record_id,
            "session_id": session_id,
        })

        response.set_cookie(
            key="monitorai_candidate_video",
            value=video_token,
            httponly=True,
            secure=SESSION_COOKIE_SECURE,
            samesite="strict",
            path="/api/video",
        )

        return response

    except HTTPException:
        raise

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to start candidate monitoring.",
        )

# ==========================================================
# COMPLETE CANDIDATE MONITORING
# ==========================================================


@app.post(
    "/api/assessments/{assessment_id}/candidates/{candidate_record_id}/complete"
)
def complete_candidate_monitoring(
    assessment_id: str,
    candidate_record_id: str,
    request: Request,
):
    global ACTIVE_CANDIDATE_VIDEO_TOKEN_HASH

    try:
        candidate = get_authenticated_candidate(request)

        if (
            candidate["assessment_id"] != assessment_id
            or candidate["candidate_record_id"] != candidate_record_id
        ):
            raise HTTPException(
                status_code=403,
                detail="Candidate session mismatch.",
            )

        if (
            monitoring_service.assessment_id != assessment_id
            or monitoring_service.candidate_record_id != candidate_record_id
            or not monitoring_service.running
        ):
            raise HTTPException(
                status_code=400,
                detail="Candidate is not the active monitoring session.",
            )

        session_id = monitoring_service.stop()

        ACTIVE_CANDIDATE_VIDEO_TOKEN_HASH = None

        response = JSONResponse({
            "success": True,
            "assessment_id": assessment_id,
            "candidate_record_id": candidate_record_id,
            "session_id": session_id,
            "status": "COMPLETED",
        })

        # Clear the video-stream cookie.
        response.delete_cookie(
            key="monitorai_candidate_video",
            path="/api/video",
            secure=SESSION_COOKIE_SECURE,
            httponly=True,
            samesite="strict",
        )

        return response

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to complete candidate monitoring.",
        )


# ==========================================================
# SESSION STATUS
# ==========================================================


@app.get("/api/session/status")
def session_status(
    current_author: dict = Depends(require_author),
):
    status = monitoring_service.get_status()

    assessment_id = status.get("assessment_id")

    # No monitoring session is associated with this status.
    if not assessment_id:
        return {
            "running": False,
            "session_id": None,
            "assessment_id": None,
            "candidate_record_id": None,
            "state": None,
            "events": [],
            "error": None,
        }

    # Verify that this author owns the assessment.
    get_owned_assessment(
        assessment_id,
        current_author,
    )

    return status


# ==========================================================
# EVENTS
# ==========================================================


@app.get("/api/events")
def get_events(
    current_author: dict = Depends(require_author),
):
    status = monitoring_service.get_status()
    assessment_id = status.get("assessment_id")

    if not assessment_id:
        return {"events": []}

    get_owned_assessment(
        assessment_id,
        current_author,
    )

    return {
        "events": status.get("events", [])
    }


# ==========================================================
# CANDIDATE REVIEW
# ==========================================================


@app.get(
    "/api/assessments/{assessment_id}/candidates/{candidate_record_id}/review"
)
def get_candidate_review(
    assessment_id: str,
    candidate_record_id: str,
    current_author: dict = Depends(require_author),
):
    try:
        get_owned_assessment(assessment_id, current_author)

        return {
            "success": True,
            **monitoring_service.get_candidate_review(
                assessment_id,
                candidate_record_id,
            ),
        }

    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve candidate review.",
        )

# ==========================================================
# REVIEWER DECISION
# ==========================================================

class ReviewerDecisionRequest(BaseModel):

    decision: str
    notes: str = ""



@app.post(
    "/api/assessments/{assessment_id}/candidates/{candidate_record_id}/review"
)
def submit_reviewer_decision(
    assessment_id: str,
    candidate_record_id: str,
    request: ReviewerDecisionRequest,
    current_author: dict = Depends(require_author),
):
    try:
        get_owned_assessment(assessment_id, current_author)

        result = (
            monitoring_service.assessment_manager
            .set_reviewer_decision(
                assessment_id,
                candidate_record_id,
                request.decision,
                request.notes,
            )
        )

        return {
            "success": True,
            "assessment_id": assessment_id,
            "candidate_record_id": candidate_record_id,
            "decision": request.decision,
            "notes": request.notes,
        }

    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to submit reviewer decision.",
        )

        
# ==========================================================
# EVIDENCE IMAGE
# ==========================================================


@app.get("/api/evidence/{session_id}/{filename}")
def get_evidence(
    session_id: str,
    filename: str,
    current_author: dict = Depends(require_author),
):
    # Confirm the session belongs to this author's assessment.
    get_owned_monitoring_session(
        session_id,
        current_author,
    )

    # Allow only a filename, not a directory path.
    if (
        not filename
        or filename in {".", ".."}
        or Path(filename).name != filename
        or "/" in filename
        or "\\" in filename
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid evidence path.",
        )

    evidence_root = (
        Path("data").resolve()
        / "evidence"
    ).resolve()

    evidence_dir = (
        evidence_root / session_id
    ).resolve()

    file_path = (
        evidence_dir / filename
    ).resolve()

    # Verify the resolved file remains inside this session's folder.
    if (
        evidence_dir.parent != evidence_root
        or file_path.parent != evidence_dir
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid evidence path.",
        )

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Evidence image not found.",
        )

    return FileResponse(
        path=file_path,
        media_type="image/jpeg",
    )


# ==========================================================
# VIDEO STREAM
# ==========================================================

def frame_generator():

    last_sequence = -1

    while monitoring_service.running:

        frame, sequence = (
            monitoring_service.wait_for_frame(
                last_sequence,
                timeout=1.0,
            )
        )

        if frame is None:

            continue

        last_sequence = sequence

        yield (

            b"--frame\r\n"

            b"Content-Type: image/jpeg\r\n"

            b"Content-Length: "

            + str(
                len(frame)
            ).encode()

            + b"\r\n\r\n"

            + frame

            + b"\r\n"
        )




@app.get("/api/video")
def video_stream(request: Request):
    global ACTIVE_CANDIDATE_VIDEO_TOKEN_HASH

    token = request.cookies.get("monitorai_candidate_video")

    if not monitoring_service.running:
        ACTIVE_CANDIDATE_VIDEO_TOKEN_HASH = None
        raise HTTPException(
            status_code=401,
            detail="No active candidate monitoring session.",
        )

    if (
        not token
        or ACTIVE_CANDIDATE_VIDEO_TOKEN_HASH is None
    ):
        raise HTTPException(
            status_code=401,
            detail="Valid candidate monitoring session required.",
        )

    supplied_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    if not hmac.compare_digest(
        supplied_hash,
        ACTIVE_CANDIDATE_VIDEO_TOKEN_HASH,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid candidate video credential.",
        )

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )
