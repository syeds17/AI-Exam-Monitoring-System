let statusInterval = null;


// ============================================================
// START EXAM
// ============================================================

async function startExam() {

    try {

        const response = await fetch(
            "/api/session/start",
            {
                method: "POST"
            }
        );

        const data = await response.json();

        if (!data.success) {
            throw new Error(
                "Failed to start session."
            );
        }

        // Session information
        document.getElementById(
            "sessionId"
        ).textContent = data.session_id;

        document.getElementById(
            "status"
        ).textContent = "RUNNING";

        // Buttons
        document.getElementById(
            "startBtn"
        ).disabled = true;

        document.getElementById(
            "stopBtn"
        ).disabled = false;

        // Start video stream
        const video =
            document.getElementById("video");

        video.src =
            "/api/video?t=" + Date.now();

        // Start status polling
        if (statusInterval !== null) {

            clearInterval(
                statusInterval
            );
        }

        statusInterval = setInterval(
            updateStatus,
            250
        );

        await updateStatus();

    } catch (error) {

        console.error(
            "Start error:",
            error
        );

        alert(
            "Failed to start monitoring: "
            + error.message
        );
    }
}


// ============================================================
// STOP EXAM
// ============================================================

async function stopExam() {

    try {

        const response = await fetch(
            "/api/session/stop",
            {
                method: "POST"
            }
        );

        const data = await response.json();

        // Stop polling
        if (statusInterval !== null) {

            clearInterval(
                statusInterval
            );

            statusInterval = null;
        }

        // Stop video
        const video =
            document.getElementById("video");

        video.src = "";

        // Update status
        document.getElementById(
            "status"
        ).textContent = "STOPPED";

        document.getElementById(
            "sessionId"
        ).textContent =
            data.session_id || "-";

        // Buttons
        document.getElementById(
            "startBtn"
        ).disabled = false;

        document.getElementById(
            "stopBtn"
        ).disabled = true;

    } catch (error) {

        console.error(
            "Stop error:",
            error
        );

        alert(
            "Failed to stop monitoring: "
            + error.message
        );
    }
}


// ============================================================
// UPDATE STATUS
// ============================================================

async function updateStatus() {

    try {

        const response = await fetch(
            "/api/session/status"
        );

        const data = await response.json();

        if (!data) {
            return;
        }


        // ----------------------------------------------------
        // SESSION
        // ----------------------------------------------------

        if (data.session_id) {

            document.getElementById(
                "sessionId"
            ).textContent =
                data.session_id;
        }


        document.getElementById(
            "status"
        ).textContent =
            data.running
                ? "RUNNING"
                : "STOPPED";


        // ----------------------------------------------------
        // CURRENT STATE
        // ----------------------------------------------------

        const state = data.state;

        if (state) {

            updateMetrics(state);

            updateCurrentEvent(state);
        }


        // ----------------------------------------------------
        // PERSISTENT EVENT HISTORY
        // ----------------------------------------------------

        renderEventHistory(
            data.events || []
        );


        // ----------------------------------------------------
        // ERROR
        // ----------------------------------------------------

        if (data.error) {

            console.error(
                "Monitoring error:",
                data.error
            );
        }

    } catch (error) {

        console.error(
            "Status update error:",
            error
        );
    }
}


// ============================================================
// UPDATE METRICS
// ============================================================

function updateMetrics(state) {

    const faces =
        state.face_count ??
        state.faces ??
        0;

    const direction =
        state.direction ??
        "UNKNOWN";

    const eyes =
        state.eye_status ??
        "UNKNOWN";

    const fps =
        state.fps ??
        state.capture_fps ??
        0;


    const facesElement =
        document.getElementById("faces");

    if (facesElement) {

        facesElement.textContent =
            faces;
    }


    const directionElement =
        document.getElementById(
            "direction"
        );

    if (directionElement) {

        directionElement.textContent =
            direction;
    }


    const eyesElement =
        document.getElementById("eyes");

    if (eyesElement) {

        eyesElement.textContent =
            eyes;
    }


    const fpsElement =
        document.getElementById("fps");

    if (fpsElement) {

        fpsElement.textContent =
            Number(fps).toFixed(1);
    }
}


// ============================================================
// CURRENT EVENT
// ============================================================

function updateCurrentEvent(state) {

    const event =
        state.event ||
        state.new_event ||
        state.alert ||
        state.last_event ||
        null;

    const eventBox =
        document.getElementById("event");

    if (!eventBox) {
        return;
    }


    if (!event) {

        eventBox.innerHTML = `
            <div class="normal-event">
                ✓ No active monitoring alert
            </div>
        `;

        return;
    }


    const type =
        event.type ||
        event.event_type ||
        "UNKNOWN EVENT";

    const direction =
        event.direction || "";

    const duration =
        event.duration != null
            ? Number(
                event.duration
            ).toFixed(2)
            : null;


    let details = "";


    if (direction) {

        details += `
            <div>
                Direction: ${direction}
            </div>
        `;
    }


    if (duration !== null) {

        details += `
            <div>
                Duration: ${duration} sec
            </div>
        `;
    }


    eventBox.innerHTML = `
        <div class="active-event">

            <div class="event-title">
                🚨 ${formatEventType(type)}
            </div>

            ${details}

        </div>
    `;
}


// ============================================================
// EVENT HISTORY
// ============================================================

function renderEventHistory(events) {

    const container =
        document.getElementById(
            "eventHistory"
        );

    if (!container) {
        return;
    }


    if (!events || events.length === 0) {

        container.innerHTML = `
            <div class="no-events">
                No monitoring events yet.
            </div>
        `;

        return;
    }


    // Newest event first
    const orderedEvents =
        [...events].reverse();


    container.innerHTML =
        orderedEvents.map(
            event => {

                const type =
                    event.type ||
                    event.event_type ||
                    "UNKNOWN EVENT";

                const direction =
                    event.direction;

                const duration =
                    event.duration != null
                        ? Number(
                            event.duration
                        ).toFixed(2)
                        : null;

                const timestamp =
                    event.timestamp ||
                    "--:--:--";


                return `
                    <div class="event-item">

                        <div class="event-header">

                            <span class="event-title">
                                🚨
                                ${formatEventType(type)}
                            </span>

                            <span class="event-time">
                                ${timestamp}
                            </span>

                        </div>


                        ${
                            direction
                            ? `
                                <div class="event-detail">
                                    Direction:
                                    ${direction}
                                </div>
                            `
                            : ""
                        }


                        ${
                            duration !== null
                            ? `
                                <div class="event-detail">
                                    Duration:
                                    ${duration} sec
                                </div>
                            `
                            : ""
                        }

                    </div>
                `;
            }
        ).join("");
}


// ============================================================
// FORMAT EVENT NAME
// ============================================================

function formatEventType(type) {

    const names = {

        "LOOKING_AWAY":
            "LOOKING AWAY",

        "EYES_CLOSED":
            "EYES CLOSED",

        "FACE_NOT_DETECTED":
            "FACE NOT DETECTED",

        "MULTIPLE_FACES":
            "MULTIPLE FACES DETECTED",

        "PHONE_DETECTED":
            "PHONE DETECTED",

        "EARPHONES_DETECTED":
            "EARPHONES DETECTED",

        "SMARTWATCH_DETECTED":
            "SMARTWATCH DETECTED",

        "BOOK_DETECTED":
            "BOOK DETECTED",

        "PAPER_DETECTED":
            "PAPER / NOTES DETECTED",

        "LAPTOP_DETECTED":
            "LAPTOP DETECTED",

        "TABLET_DETECTED":
            "TABLET DETECTED"
    };


    return names[type] || type;
}


// ============================================================
// INITIALIZATION
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    () => {

        const startButton =
            document.getElementById(
                "startBtn"
            );

        const stopButton =
            document.getElementById(
                "stopBtn"
            );


        if (startButton) {

            startButton.addEventListener(
                "click",
                startExam
            );
        }


        if (stopButton) {

            stopButton.addEventListener(
                "click",
                stopExam
            );

            stopButton.disabled = true;
        }


        updateStatus();
    }
);