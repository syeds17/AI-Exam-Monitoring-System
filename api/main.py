from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import (
    FileResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from api.monitoring_service import (
    monitoring_service,
)


# ==========================================================
# APPLICATION
# ==========================================================

app = FastAPI(
    title="AI Online Assessment Monitoring System",
    version="1.0.0",
)


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

app.mount(
    "/evidence",
    StaticFiles(
        directory=str(EVIDENCE_DIR)
    ),
    name="evidence",
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

@app.post(
    "/api/assessments"
)
def create_assessment(
    request: AssessmentCreateRequest
):

    try:

        assessment_id = (
            monitoring_service.create_assessment(
                assessment_name=request.assessment_name,
                organization=request.organization,
                assessment_type=request.assessment_type,
                scheduled_at=request.scheduled_at,
                duration_minutes=request.duration_minutes,
                candidate_limit=request.candidate_limit,
            )
        )

        assessment = (
            monitoring_service.get_assessment(
                assessment_id
            )
        )

        return {
            "success": True,
            "assessment": assessment,
        }

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# ==========================================================
# GET ALL ASSESSMENTS
# ==========================================================

@app.get(
    "/api/assessments"
)
def get_assessments():

    try:

        return {
            "assessments":
                monitoring_service.get_assessments()
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# ==========================================================
# GET SINGLE ASSESSMENT
# ==========================================================

@app.get(
    "/api/assessments/{assessment_id}"
)
def get_assessment(
    assessment_id: str
):

    try:

        assessment = (
            monitoring_service.get_assessment(
                assessment_id
            )
        )

        if assessment is None:

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

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# ==========================================================
# GET ASSESSMENT BY PUBLIC ACCESS TOKEN
# ==========================================================

@app.get(
    "/api/assessments/link/{access_token}"
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

@app.post(
    "/api/assessments/{assessment_id}/activate"
)
def activate_assessment(
    assessment_id: str
):

    try:

        assessment = (
            monitoring_service
            .activate_assessment(
                assessment_id
            )
        )

        return {
            "success": True,
            "assessment": assessment,
        }

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# ==========================================================
# DEACTIVATE ASSESSMENT
# ==========================================================

@app.post(
    "/api/assessments/{assessment_id}/deactivate"
)
def deactivate_assessment(
    assessment_id: str
):

    try:

        assessment = (
            monitoring_service
            .deactivate_assessment(
                assessment_id
            )
        )

        return {
            "success": True,
            "assessment": assessment,
        }

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# ==========================================================
# REQUEST CANDIDATE ACCESS
# ==========================================================

@app.post(
    "/api/assessments/{assessment_id}/access-request"
)
def request_candidate_access(
    assessment_id: str,
    request: CandidateAccessRequest,
):

    try:

        candidate = (
            monitoring_service
            .request_candidate_access(
                assessment_id=assessment_id,
                candidate_name=request.candidate_name,
                candidate_id=request.candidate_id,
            )
        )

        return {
            "success": True,
            "candidate": candidate,
        }

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# ==========================================================
# GET CANDIDATES
# ==========================================================

@app.get(
    "/api/assessments/{assessment_id}/candidates"
)
def get_candidates(
    assessment_id: str
):

    try:

        assessment = (
            monitoring_service.get_assessment(
                assessment_id
            )
        )

        if assessment is None:

            raise HTTPException(
                status_code=404,
                detail="Assessment not found.",
            )

        candidates = (
            monitoring_service.get_candidates(
                assessment_id
            )
        )

        return {
            "success": True,
            "assessment_id": assessment_id,
            "candidates": candidates,
            "candidate_count": len(candidates),
        }

    except HTTPException:

        raise

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# ==========================================================
# GET ONE CANDIDATE
# ==========================================================

@app.get(
    "/api/assessments/{assessment_id}/candidates/{candidate_record_id}"
)
def get_candidate(
    assessment_id: str,
    candidate_record_id: str,
):

    try:

        candidate = (
            monitoring_service.get_candidate(
                assessment_id=assessment_id,
                candidate_record_id=candidate_record_id,
            )
        )

        if candidate is None:

            raise HTTPException(
                status_code=404,
                detail="Candidate not found.",
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
# APPROVE CANDIDATE
# ==========================================================

@app.post(
    "/api/assessments/{assessment_id}/candidates/{candidate_record_id}/approve"
)
def approve_candidate(
    assessment_id: str,
    candidate_record_id: str,
):

    try:

        candidate = (
            monitoring_service.get_candidate(
                assessment_id=assessment_id,
                candidate_record_id=candidate_record_id,
            )
        )

        if candidate is None:

            raise HTTPException(
                status_code=404,
                detail="Candidate not found.",
            )

        approved = (
            monitoring_service.approve_candidate(
                assessment_id=assessment_id,
                candidate_record_id=candidate_record_id,
            )
        )

        return {
            "success": True,
            "candidate": approved,
        }

    except HTTPException:

        raise

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
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
):

    try:

        candidate = (
            monitoring_service.get_candidate(
                assessment_id=assessment_id,
                candidate_record_id=candidate_record_id,
            )
        )

        if candidate is None:

            raise HTTPException(
                status_code=404,
                detail="Candidate not found.",
            )

        rejected = (
            monitoring_service.reject_candidate(
                assessment_id=assessment_id,
                candidate_record_id=candidate_record_id,
            )
        )

        return {
            "success": True,
            "candidate": rejected,
        }

    except HTTPException:

        raise

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
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
):

    try:

        candidate = (
            monitoring_service.get_candidate(
                assessment_id=assessment_id,
                candidate_record_id=candidate_record_id,
            )
        )

        if candidate is None:

            raise HTTPException(
                status_code=404,
                detail="Candidate not found.",
            )

        session_id = (
            monitoring_service.start(
                assessment_id=assessment_id,
                candidate_record_id=candidate_record_id,
            )
        )

        return {
            "success": True,
            "assessment_id": assessment_id,
            "candidate_record_id":
                candidate_record_id,
            "session_id": session_id,
        }

    except HTTPException:

        raise

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
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
):

    try:

        if (
            monitoring_service.assessment_id
            != assessment_id
            or
            monitoring_service.candidate_record_id
            != candidate_record_id
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "Candidate is not the active "
                    "monitoring session."
                ),
            )

        session_id = (
            monitoring_service.stop()
        )

        return {
            "success": True,
            "assessment_id": assessment_id,
            "candidate_record_id":
                candidate_record_id,
            "session_id": session_id,
            "status": "COMPLETED",
        }

    except HTTPException:

        raise

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# ==========================================================
# SESSION STATUS
# ==========================================================

@app.get(
    "/api/session/status"
)
def session_status():

    return (
        monitoring_service.get_status()
    )


# ==========================================================
# EVENTS
# ==========================================================

@app.get(
    "/api/events"
)
def get_events():

    return {
        "events":
            monitoring_service.get_events()
    }
    
# ==========================================================
# CANDIDATE REVIEW
# ==========================================================

@app.get(
    "/api/assessments/{assessment_id}/candidates/{candidate_record_id}/review"
)
def get_candidate_review(
    assessment_id: str,
    candidate_record_id: str
):

    try:

        return {
            "success": True,
            **monitoring_service.get_candidate_review(
                assessment_id,
                candidate_record_id
            )
        }

    except ValueError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error)
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
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
    request: ReviewerDecisionRequest
):

    try:

        result = (
            monitoring_service.assessment_manager
            .set_reviewer_decision(
                assessment_id,
                candidate_record_id,
                request.decision,
                request.notes
            )
        )

        return {
            "success": True,
            "assessment_id": assessment_id,
            "candidate_record_id": candidate_record_id,
            "decision": request.decision,
            "notes": request.notes,
        }

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )
        
# ==========================================================
# EVIDENCE IMAGE
# ==========================================================

@app.get(
    "/api/evidence/{session_id}/{filename}"
)
def get_evidence(
    session_id: str,
    filename: str
):

    try:

        evidence_dir = (
            Path("data")
            / "evidence"
            / session_id
        )

        file_path = (
            evidence_dir
            / filename
        )

        # Prevent path traversal
        if (
            file_path.parent.resolve()
            != evidence_dir.resolve()
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid evidence path"
            )

        if not file_path.is_file():
            raise HTTPException(
                status_code=404,
                detail="Evidence image not found"
            )

        return FileResponse(
            path=file_path,
            media_type="image/jpeg"
        )

    except HTTPException:
        raise

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
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


@app.get(
    "/api/video"
)
def video_stream():

    return StreamingResponse(

        frame_generator(),

        media_type=(
            "multipart/x-mixed-replace;"
            " boundary=frame"
        ),

        headers={

            "Cache-Control":
                "no-cache, no-store, must-revalidate",

            "Pragma":
                "no-cache",

            "Expires":
                "0",
        },
    )