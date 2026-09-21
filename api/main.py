from fastapi import FastAPI
from fastapi.responses import (
    FileResponse,
    StreamingResponse
)
from fastapi.staticfiles import StaticFiles

from api.monitoring_service import monitoring_service


app = FastAPI(
    title="AI Exam Monitoring System",
    version="1.0.0"
)


app.mount(
    "/static",
    StaticFiles(directory="web"),
    name="static"
)


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.get("/")
def home():

    return FileResponse(
        "web/index.html"
    )


# --------------------------------------------------
# START SESSION
# --------------------------------------------------

@app.post("/api/session/start")
def start_session():

    session_id = (
        monitoring_service.start()
    )

    return {
        "success": True,
        "session_id": session_id
    }


# --------------------------------------------------
# STOP SESSION
# --------------------------------------------------

@app.post("/api/session/stop")
def stop_session():

    session_id = (
        monitoring_service.stop()
    )

    return {
        "success": True,
        "session_id": session_id
    }


# --------------------------------------------------
# SESSION STATUS
# --------------------------------------------------

@app.get("/api/session/status")
def session_status():

    return (
        monitoring_service.get_status()
    )


# --------------------------------------------------
# EVENT HISTORY
# --------------------------------------------------

@app.get("/api/events")
def get_events():

    return {
        "events":
            monitoring_service.get_events()
    }


# --------------------------------------------------
# VIDEO STREAM
# --------------------------------------------------

def frame_generator():

    last_sequence = -1

    while monitoring_service.running:

        frame, sequence = (
            monitoring_service.wait_for_frame(
                last_sequence,
                timeout=1.0
            )
        )

        if frame is None:

            continue

        last_sequence = sequence

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n"
            b"Content-Length: "
            + str(len(frame)).encode()
            + b"\r\n\r\n"
            + frame
            + b"\r\n"
        )


@app.get("/api/video")
def video_stream():

    return StreamingResponse(
        frame_generator(),
        media_type=(
            "multipart/x-mixed-replace;"
            " boundary=frame"
        ),
        headers={
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }
    )