// ==========================================================
// AI ONLINE ASSESSMENT MONITORING SYSTEM
// AUTHOR DASHBOARD
// ==========================================================


// ==========================================================
// GLOBAL STATE
// ==========================================================

let assessments = [];

let selectedAssessment = null;

let monitoringInterval = null;

let eventInterval = null;

let monitoringActive = false;


// ==========================================================
// DOM HELPERS
// ==========================================================

function getElement(id) {

    return document.getElementById(id);

}


// ==========================================================
// INITIALIZATION
// ==========================================================

document.addEventListener(
    "DOMContentLoaded",
    () => {

        initializeNavigation();

        initializeAssessmentButtons();

        initializeModalButtons();

        initializeAssessmentForm();

        initializeMonitoringButtons();

        loadAssessments();

        updateSystemStatus(
            "System Ready",
            true
        );

    }
);


// ==========================================================
// NAVIGATION
// ==========================================================

function initializeNavigation() {

    const navItems = document.querySelectorAll(
        ".nav-item"
    );


    navItems.forEach(
        (item) => {

            item.addEventListener(
                "click",
                () => {

                    const page =
                        item.dataset.page;

                    showPage(page);

                }
            );

        }
    );

}


// ==========================================================
// SHOW PAGE
// ==========================================================

function showPage(page) {

    const pages = document.querySelectorAll(
        ".page"
    );

    const navItems = document.querySelectorAll(
        ".nav-item"
    );


    pages.forEach(
        (pageElement) => {

            pageElement.classList.remove(
                "active-page"
            );

        }
    );


    navItems.forEach(
        (item) => {

            item.classList.remove(
                "active"
            );

        }
    );


    const targetPage =
        getElement(
            `${page}Page`
        );


    if (targetPage) {

        targetPage.classList.add(
            "active-page"
        );

    }


    const activeNav =
        document.querySelector(
            `.nav-item[data-page="${page}"]`
        );


    if (activeNav) {

        activeNav.classList.add(
            "active"
        );

    }


    updatePageHeader(
        page
    );


    if (page === "dashboard") {

        loadAssessments();

    }


    if (page === "assessments") {

        loadAssessments();

    }

}


// ==========================================================
// PAGE HEADER
// ==========================================================

function updatePageHeader(page) {

    const title =
        getElement(
            "pageTitle"
        );

    const subtitle =
        getElement(
            "pageSubtitle"
        );


    if (page === "dashboard") {

        title.textContent =
            "Dashboard";

        subtitle.textContent =
            "Manage your online assessments";

    }


    else if (page === "assessments") {

        title.textContent =
            "Assessments";

        subtitle.textContent =
            "Create and manage assessment sessions";

    }


    else if (page === "monitoring") {

        title.textContent =
            "Live Monitoring";

        subtitle.textContent =
            "Real-time AI assessment monitoring";

    }

}


// ==========================================================
// ASSESSMENT BUTTONS
// ==========================================================

function initializeAssessmentButtons() {

    const createButton =
        getElement(
            "createAssessmentBtn"
        );

    const emptyCreateButton =
        getElement(
            "emptyCreateBtn"
        );

    const assessmentCreateButton =
        getElement(
            "assessmentCreateBtn"
        );

    const viewAllButton =
        getElement(
            "viewAllAssessmentsBtn"
        );


    if (createButton) {

        createButton.addEventListener(
            "click",
            openAssessmentModal
        );

    }


    if (emptyCreateButton) {

        emptyCreateButton.addEventListener(
            "click",
            openAssessmentModal
        );

    }


    if (assessmentCreateButton) {

        assessmentCreateButton.addEventListener(
            "click",
            openAssessmentModal
        );

    }


    if (viewAllButton) {

        viewAllButton.addEventListener(
            "click",
            () => {

                showPage(
                    "assessments"
                );

            }
        );

    }

}


// ==========================================================
// LOAD ASSESSMENTS
// ==========================================================

async function loadAssessments() {

    try {

        const response =
            await fetch(
                "/api/assessments"
            );


        if (!response.ok) {

            throw new Error(
                "Failed to load assessments."
            );

        }


        const data =
            await response.json();


        if (Array.isArray(data)) {

            assessments = data;

        }

        else {

            assessments =
                data.assessments || [];

        }


        updateDashboardStats();

        renderRecentAssessments();

        renderAllAssessments();

        updateSystemStatus(
            "System Ready",
            true
        );

    }

    catch (error) {

        console.error(
            "Assessment loading error:",
            error
        );


        updateSystemStatus(
            "API Connection Error",
            false
        );


        showToast(
            "Unable to load assessments.",
            "error"
        );

    }

}


// ==========================================================
// DASHBOARD STATISTICS
// ==========================================================

function updateDashboardStats() {

    const total =
        assessments.length;


    const ready =
        assessments.filter(
            (assessment) =>
                assessment.status === "READY"
        ).length;


    const active =
        assessments.filter(
            (assessment) =>
                assessment.status === "IN_PROGRESS"
        ).length;


    const completed =
        assessments.filter(
            (assessment) =>
                assessment.status === "COMPLETED"
        ).length;


    setText(
        "totalAssessments",
        total
    );

    setText(
        "readyAssessments",
        ready
    );

    setText(
        "activeAssessments",
        active
    );

    setText(
        "completedAssessments",
        completed
    );

}


// ==========================================================
// RENDER RECENT ASSESSMENTS
// ==========================================================

function renderRecentAssessments() {

    const container =
        getElement(
            "recentAssessments"
        );


    if (!container) {

        return;

    }


    const recent =
        assessments.slice(
            0,
            6
        );


    if (recent.length === 0) {

        container.innerHTML = `

            <div class="empty-state">

                <div class="empty-icon">
                    📋
                </div>

                <h3>
                    No assessments yet
                </h3>

                <p>
                    Create your first assessment to get started.
                </p>

                <button
                    class="primary-btn"
                    onclick="openAssessmentModal()"
                >
                    Create Assessment
                </button>

            </div>

        `;

        return;

    }


    container.innerHTML =
        recent
            .map(
                createAssessmentCard
            )
            .join("");

}


// ==========================================================
// RENDER ALL ASSESSMENTS
// ==========================================================

function renderAllAssessments() {

    const container =
        getElement(
            "allAssessments"
        );


    if (!container) {

        return;

    }


    if (assessments.length === 0) {

        container.innerHTML = `

            <div class="empty-state">

                <div class="empty-icon">
                    📋
                </div>

                <h3>
                    No assessments found
                </h3>

                <p>
                    Create an assessment to begin monitoring candidates.
                </p>

            </div>

        `;

        return;

    }


    container.innerHTML =
        assessments
            .map(
                createAssessmentCard
            )
            .join("");

}


// ==========================================================
// CREATE ASSESSMENT CARD
// ==========================================================

function createAssessmentCard(
    assessment
) {

    const status =
        assessment.status ||
        "READY";


    const statusClass =
        status
            .toLowerCase()
            .replace(
                "_",
                "-"
            );


    const assessmentId =
        escapeHtml(
            assessment.assessment_id ||
            "-"
        );


    const name =
        escapeHtml(
            assessment.assessment_name ||
            "Untitled Assessment"
        );


    const organization =
        escapeHtml(
            assessment.organization ||
            "No organization"
        );


    const candidate =
        escapeHtml(
            assessment.candidate_name ||
            "Unknown candidate"
        );


    const candidateId =
        escapeHtml(
            assessment.candidate_id ||
            "-"
        );


    const type =
        escapeHtml(
            assessment.assessment_type ||
            "Assessment"
        );


    const duration =
        assessment.duration_minutes ||
        "-";


    const scheduled =
        formatDateTime(
            assessment.scheduled_at
        );


    return `

        <div
            class="assessment-card"
            data-assessment-id="${assessmentId}"
        >

            <div class="assessment-card-header">

                <div class="assessment-card-icon">
                    📋
                </div>

                <span
                    class="status-badge ${statusClass}"
                >
                    ${formatStatus(status)}
                </span>

            </div>


            <div class="assessment-card-body">

                <h3>
                    ${name}
                </h3>

                <p class="organization">
                    ${organization}
                </p>


                <div class="assessment-info">

                    <div>

                        <span>
                            Candidate
                        </span>

                        <strong>
                            ${candidate}
                        </strong>

                    </div>


                    <div>

                        <span>
                            Candidate ID
                        </span>

                        <strong>
                            ${candidateId}
                        </strong>

                    </div>


                    <div>

                        <span>
                            Type
                        </span>

                        <strong>
                            ${type}
                        </strong>

                    </div>


                    <div>

                        <span>
                            Duration
                        </span>

                        <strong>
                            ${duration} min
                        </strong>

                    </div>


                    <div>

                        <span>
                            Scheduled
                        </span>

                        <strong>
                            ${scheduled}
                        </strong>

                    </div>

                </div>

            </div>


            <div class="assessment-card-footer">

                <button
                    class="secondary-btn"
                    onclick="openAssessmentDetails('${assessmentId}')"
                >
                    View Details
                </button>


                ${
                    status === "READY"
                        ? `
                            <button
                                class="primary-btn"
                                onclick="startAssessment('${assessmentId}')"
                            >
                                ▶ Start
                            </button>
                        `
                        : ""
                }


                ${
                    status === "IN_PROGRESS"
                        ? `
                            <button
                                class="primary-btn"
                                onclick="openMonitoring('${assessmentId}')"
                            >
                                🎥 Monitor
                            </button>
                        `
                        : ""
                }

            </div>

        </div>

    `;

}


// ==========================================================
// CREATE ASSESSMENT FORM
// ==========================================================

function initializeAssessmentForm() {

    const form =
        getElement(
            "assessmentForm"
        );


    if (!form) {

        return;

    }


    form.addEventListener(
        "submit",
        async (event) => {

            event.preventDefault();

            await createAssessment();

        }
    );

}


// ==========================================================
// CREATE ASSESSMENT
// ==========================================================

async function createAssessment() {

    const assessmentName =
        getElement(
            "assessmentName"
        ).value.trim();


    const organization =
        getElement(
            "organization"
        ).value.trim();


    const assessmentType =
        getElement(
            "assessmentType"
        ).value;


    const candidateName =
        getElement(
            "candidateName"
        ).value.trim();


    const candidateId =
        getElement(
            "candidateId"
        ).value.trim();


    const scheduledAt =
        getElement(
            "scheduledAt"
        ).value;


    const durationMinutes =
        Number(
            getElement(
                "durationMinutes"
            ).value
        );


    if (!assessmentName) {

        showToast(
            "Assessment name is required.",
            "error"
        );

        return;

    }


    if (!assessmentType) {

        showToast(
            "Select an assessment type.",
            "error"
        );

        return;

    }


    if (!candidateName) {

        showToast(
            "Candidate name is required.",
            "error"
        );

        return;

    }


    if (
        !durationMinutes ||
        durationMinutes < 1
    ) {

        showToast(
            "Enter a valid duration.",
            "error"
        );

        return;

    }


    const payload = {

        assessment_name:
            assessmentName,

        organization:
            organization,

        assessment_type:
            assessmentType,

        candidate_name:
            candidateName,

        candidate_id:
            candidateId,

        scheduled_at:
            scheduledAt
                ? new Date(
                    scheduledAt
                ).toISOString()
                : null,

        duration_minutes:
            durationMinutes

    };


    try {

        const response =
            await fetch(
                "/api/assessments",
                {

                    method:
                        "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body:
                        JSON.stringify(
                            payload
                        )

                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                data.message ||
                "Failed to create assessment."
            );

        }


        closeAssessmentModal();


        getElement(
            "assessmentForm"
        ).reset();


        getElement(
            "durationMinutes"
        ).value = 60;


        showToast(
            "Assessment created successfully.",
            "success"
        );


        await loadAssessments();


        showPage(
            "assessments"
        );

    }

    catch (error) {

        console.error(
            "Create assessment error:",
            error
        );


        showToast(
            error.message,
            "error"
        );

    }

}


// ==========================================================
// ASSESSMENT DETAILS
// ==========================================================

async function openAssessmentDetails(
    assessmentId
) {

    try {

        const response =
            await fetch(
                `/api/assessments/${encodeURIComponent(
                    assessmentId
                )}`
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Unable to load assessment."
            );

        }


        selectedAssessment =
            data.assessment ||
            data;


        renderAssessmentDetails(
            selectedAssessment
        );


        openDetailsModal();

    }

    catch (error) {

        console.error(
            "Assessment details error:",
            error
        );


        showToast(
            error.message,
            "error"
        );

    }

}


// ==========================================================
// RENDER ASSESSMENT DETAILS
// ==========================================================

function renderAssessmentDetails(
    assessment
) {

    const container =
        getElement(
            "assessmentDetailsContent"
        );


    if (!container) {

        return;

    }


    const status =
        assessment.status ||
        "READY";


    container.innerHTML = `

        <div class="detail-row">

            <span>
                Assessment ID
            </span>

            <strong>
                ${escapeHtml(
                    assessment.assessment_id ||
                    "-"
                )}
            </strong>

        </div>


        <div class="detail-row">

            <span>
                Assessment Name
            </span>

            <strong>
                ${escapeHtml(
                    assessment.assessment_name ||
                    "-"
                )}
            </strong>

        </div>


        <div class="detail-row">

            <span>
                Organization
            </span>

            <strong>
                ${escapeHtml(
                    assessment.organization ||
                    "-"
                )}
            </strong>

        </div>


        <div class="detail-row">

            <span>
                Assessment Type
            </span>

            <strong>
                ${escapeHtml(
                    assessment.assessment_type ||
                    "-"
                )}
            </strong>

        </div>


        <div class="detail-row">

            <span>
                Candidate
            </span>

            <strong>
                ${escapeHtml(
                    assessment.candidate_name ||
                    "-"
                )}
            </strong>

        </div>


        <div class="detail-row">

            <span>
                Candidate ID
            </span>

            <strong>
                ${escapeHtml(
                    assessment.candidate_id ||
                    "-"
                )}
            </strong>

        </div>


        <div class="detail-row">

            <span>
                Duration
            </span>

            <strong>
                ${
                    assessment.duration_minutes ||
                    "-"
                }
                minutes
            </strong>

        </div>


        <div class="detail-row">

            <span>
                Scheduled At
            </span>

            <strong>
                ${formatDateTime(
                    assessment.scheduled_at
                )}
            </strong>

        </div>


        <div class="detail-row">

            <span>
                Status
            </span>

            <span
                class="status-badge ${status
                    .toLowerCase()
                    .replace(
                        "_",
                        "-"
                    )}"
            >
                ${formatStatus(status)}
            </span>

        </div>

    `;


    const startButton =
        getElement(
            "detailsStartBtn"
        );


    if (startButton) {

        if (status === "READY") {

            startButton.style.display =
                "inline-flex";

            startButton.textContent =
                "▶ Start Monitoring";

        }

        else if (
            status === "IN_PROGRESS"
        ) {

            startButton.style.display =
                "inline-flex";

            startButton.textContent =
                "🎥 Open Monitoring";

        }

        else {

            startButton.style.display =
                "none";

        }

    }

}


// ==========================================================
// START ASSESSMENT
// ==========================================================

async function startAssessment(
    assessmentId
) {

    try {

        const response =
            await fetch(
                `/api/assessments/${encodeURIComponent(
                    assessmentId
                )}/start`,
                {

                    method:
                        "POST"

                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Unable to start assessment."
            );

        }


        showToast(
            "Assessment monitoring started.",
            "success"
        );


        await loadAssessments();


        openMonitoring(
            assessmentId,
            data.session_id
        );

    }

    catch (error) {

        console.error(
            "Start assessment error:",
            error
        );


        showToast(
            error.message,
            "error"
        );

    }

}


// ==========================================================
// OPEN MONITORING
// ==========================================================

async function openMonitoring(
    assessmentId,
    sessionId = null
) {

    const assessment =
        assessments.find(
            (item) =>
                item.assessment_id ===
                assessmentId
        );


    if (assessment) {

        selectedAssessment =
            assessment;

    }


    if (
        !selectedAssessment ||
        selectedAssessment.assessment_id !==
            assessmentId
    ) {

        try {

            const response =
                await fetch(
                    `/api/assessments/${encodeURIComponent(
                        assessmentId
                    )}`
                );


            const data =
                await response.json();


            if (response.ok) {

                selectedAssessment =
                    data.assessment ||
                    data;

            }

        }

        catch (error) {

            console.error(
                error
            );

        }

    }


    updateMonitoringDetails();

    showPage(
        "monitoring"
    );


    startMonitoringPolling();


    if (
        sessionId ||
        selectedAssessment?.status ===
            "IN_PROGRESS"
    ) {

        monitoringActive =
            true;

        startVideoFeed();

        updateMonitoringButtons();

    }

}


// ==========================================================
// UPDATE MONITORING DETAILS
// ==========================================================

function updateMonitoringDetails() {

    if (!selectedAssessment) {

        return;

    }


    setText(
        "monitoringAssessmentName",
        selectedAssessment.assessment_name ||
            "Assessment"
    );


    setText(
        "monitoringCandidate",
        selectedAssessment.candidate_name ||
            "-"
    );


    setText(
        "monitoringCandidateId",
        selectedAssessment.candidate_id ||
            "-"
    );


    setText(
        "monitoringOrganization",
        selectedAssessment.organization ||
            "-"
    );


    setText(
        "monitoringType",
        selectedAssessment.assessment_type ||
            "-"
    );


    const status =
        selectedAssessment.status ||
        "READY";


    setText(
        "monitoringStatus",
        formatStatus(status)
    );

}


// ==========================================================
// MONITORING BUTTONS
// ==========================================================

function initializeMonitoringButtons() {

    const stopButton =
        getElement(
            "monitoringStopBtn"
        );


    if (stopButton) {

        stopButton.addEventListener(
            "click",
            stopMonitoring
        );

    }


    const detailsStartButton =
        getElement(
            "detailsStartBtn"
        );


    if (detailsStartButton) {

        detailsStartButton.addEventListener(
            "click",
            async () => {

                if (
                    !selectedAssessment
                ) {

                    return;

                }


                closeDetailsModal();


                if (
                    selectedAssessment.status ===
                    "READY"
                ) {

                    await startAssessment(
                        selectedAssessment.assessment_id
                    );

                }

                else if (
                    selectedAssessment.status ===
                    "IN_PROGRESS"
                ) {

                    openMonitoring(
                        selectedAssessment.assessment_id
                    );

                }

            }
        );

    }

}


// ==========================================================
// START VIDEO FEED
// ==========================================================

function startVideoFeed() {

    const video =
        getElement(
            "video"
        );


    const placeholder =
        getElement(
            "videoPlaceholder"
        );


    if (!video) {

        return;

    }


    video.src =
        `/api/video?t=${Date.now()}`;


    video.style.display =
        "block";


    if (placeholder) {

        placeholder.style.display =
            "none";

    }

}


// ==========================================================
// STOP VIDEO FEED
// ==========================================================

function stopVideoFeed() {

    const video =
        getElement(
            "video"
        );


    const placeholder =
        getElement(
            "videoPlaceholder"
        );


    if (video) {

        video.src = "";

        video.style.display =
            "none";

    }


    if (placeholder) {

        placeholder.style.display =
            "flex";

    }

}


// ==========================================================
// MONITORING POLLING
// ==========================================================

function startMonitoringPolling() {

    stopMonitoringPolling();


    monitoringInterval =
        setInterval(
            updateMonitoringStatus,
            1000
        );


    eventInterval =
        setInterval(
            updateEventHistory,
            1000
        );


    updateMonitoringStatus();

    updateEventHistory();

}


// ==========================================================
// STOP MONITORING POLLING
// ==========================================================

function stopMonitoringPolling() {

    if (
        monitoringInterval !== null
    ) {

        clearInterval(
            monitoringInterval
        );

        monitoringInterval =
            null;

    }


    if (
        eventInterval !== null
    ) {

        clearInterval(
            eventInterval
        );

        eventInterval =
            null;

    }

}


// ==========================================================
// UPDATE MONITORING STATUS
// ==========================================================

async function updateMonitoringStatus() {

    try {

        const response =
            await fetch(
                "/api/session/status"
            );


        if (!response.ok) {

            return;

        }


        const data =
            await response.json();


        const state =
            data.state;


        if (state) {

            updateMonitoringMetrics(
                state
            );

        }


        if (data.running) {

            monitoringActive =
                true;

            startVideoFeed();

        }

        else {

            monitoringActive =
                false;

        }


        updateMonitoringButtons();


        if (
            data.error
        ) {

            updateSystemStatus(
                "Monitoring Error",
                false
            );

        }

    }

    catch (error) {

        console.error(
            "Monitoring status error:",
            error
        );

    }

}


// ==========================================================
// UPDATE MONITORING METRICS
// ==========================================================

function updateMonitoringMetrics(
    state
) {

    setText(
        "faces",
        state.face_count ??
            "-"
    );


    setText(
        "direction",
        state.direction ??
            "-"
    );


    setText(
        "eyes",
        state.eye_status ??
            "-"
    );


    setText(
        "fps",
        formatNumber(
            state.fps
        )
    );


    setText(
        "persons",
        state.person_count ??
            "-"
    );


    setText(
        "objects",
        state.object_count ??
            "-"
    );


    const currentEvent =
        state.last_event;


    if (currentEvent) {

        displayCurrentEvent(
            currentEvent
        );

    }

}


// ==========================================================
// UPDATE MONITORING BUTTONS
// ==========================================================

function updateMonitoringButtons() {

    const stopButton =
        getElement(
            "monitoringStopBtn"
        );


    if (stopButton) {

        stopButton.disabled =
            !monitoringActive;

    }


    const statusElement =
        getElement(
            "monitoringStatus"
        );


    if (statusElement) {

        if (monitoringActive) {

            statusElement.textContent =
                "IN PROGRESS";

            statusElement.className =
                "status-badge in-progress";

        }

        else if (
            selectedAssessment &&
            selectedAssessment.status ===
                "COMPLETED"
        ) {

            statusElement.textContent =
                "COMPLETED";

            statusElement.className =
                "status-badge completed";

        }

        else {

            statusElement.textContent =
                "NOT RUNNING";

            statusElement.className =
                "status-badge ready";

        }

    }

}


// ==========================================================
// STOP MONITORING
// ==========================================================

async function stopMonitoring() {

    if (!monitoringActive) {

        return;

    }


    try {

        const response =
            await fetch(
                "/api/session/stop",
                {

                    method:
                        "POST"

                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Unable to stop monitoring."
            );

        }


        monitoringActive =
            false;


        stopVideoFeed();

        stopMonitoringPolling();

        updateMonitoringButtons();


        showToast(
            "Monitoring session completed.",
            "success"
        );


        await loadAssessments();


        if (
            selectedAssessment
        ) {

            const updated =
                assessments.find(
                    (assessment) =>
                        assessment.assessment_id ===
                        selectedAssessment.assessment_id
                );


            if (updated) {

                selectedAssessment =
                    updated;

            }

        }


        updateMonitoringDetails();

    }

    catch (error) {

        console.error(
            "Stop monitoring error:",
            error
        );


        showToast(
            error.message,
            "error"
        );

    }

}


// ==========================================================
// EVENT HISTORY
// ==========================================================

async function updateEventHistory() {

    try {

        const response =
            await fetch(
                "/api/events"
            );


        if (!response.ok) {

            return;

        }


        const data =
            await response.json();


        const events =
            data.events || [];


        renderEventHistory(
            events
        );

    }

    catch (error) {

        console.error(
            "Event history error:",
            error
        );

    }

}


// ==========================================================
// RENDER EVENT HISTORY
// ==========================================================

function renderEventHistory(
    events
) {

    const container =
        getElement(
            "eventHistory"
        );


    const count =
        getElement(
            "eventCount"
        );


    if (!container) {

        return;

    }


    if (count) {

        count.textContent =
            `${events.length} ${
                events.length === 1
                    ? "event"
                    : "events"
            }`;

    }


    if (events.length === 0) {

        container.innerHTML = `

            <div class="no-events">
                No monitoring events yet.
            </div>

        `;

        return;

    }


    const reversedEvents =
        [...events].reverse();


    container.innerHTML =
        reversedEvents
            .map(
                createEventItem
            )
            .join("");

}


// ==========================================================
// CREATE EVENT ITEM
// ==========================================================

function createEventItem(
    event
) {

    const type =
        event.type ||
        event.event_type ||
        "UNKNOWN";


    const direction =
        event.direction ||
        "";


    const duration =
        event.duration;


    const timestamp =
        event.timestamp ||
        "--:--:--";


    const evidencePath =
        event.evidence_path;


    let description =
        formatEventType(
            type
        );


    if (direction) {

        description +=
            ` · ${formatDirection(
                direction
            )}`;

    }


    if (
        duration !== null &&
        duration !== undefined
    ) {

        description +=
            ` · ${formatNumber(
                duration
            )} sec`;

    }


    return `

        <div class="event-item">

            <div class="event-icon">
                ⚠
            </div>


            <div class="event-content">

                <strong>
                    ${escapeHtml(
                        description
                    )}
                </strong>

                <span>
                    ${escapeHtml(
                        timestamp
                    )}
                </span>

            </div>


            ${
                evidencePath
                    ? `
                        <button
                            class="evidence-btn"
                            onclick="openEvidence(
                                '${escapeHtml(
                                    evidencePath
                                )}',
                                '${escapeHtml(
                                    type
                                )}',
                                '${escapeHtml(
                                    timestamp
                                )}'
                            )"
                        >
                            📷 Evidence
                        </button>
                    `
                    : ""
            }

        </div>

    `;

}


// ==========================================================
// CURRENT EVENT
// ==========================================================

function displayCurrentEvent(
    event
) {

    const eventElement =
        getElement(
            "event"
        );


    if (!eventElement) {

        return;

    }


    const type =
        event.type ||
        event.event_type ||
        "UNKNOWN";


    const direction =
        event.direction;


    const duration =
        event.duration;


    let message =
        formatEventType(
            type
        );


    if (direction) {

        message +=
            ` · ${formatDirection(
                direction
            )}`;

    }


    if (
        duration !== null &&
        duration !== undefined
    ) {

        message +=
            ` · ${formatNumber(
                duration
            )} sec`;

    }


    eventElement.textContent =
        message;


    eventElement.className =
        "event alert";

}


// ==========================================================
// EVIDENCE
// ==========================================================

function openEvidence(
    evidencePath,
    eventType,
    timestamp
) {

    const modal =
        getElement(
            "evidenceModal"
        );


    const image =
        getElement(
            "evidenceImage"
        );


    const details =
        getElement(
            "evidenceDetails"
        );


    if (!modal || !image) {

        return;

    }


    const url =
        normalizeEvidencePath(
            evidencePath
        );


    image.src =
        `${url}?t=${Date.now()}`;


    if (details) {

        details.innerHTML = `

            <div>

                <span>
                    Event
                </span>

                <strong>
                    ${escapeHtml(
                        formatEventType(
                            eventType
                        )
                    )}
                </strong>

            </div>


            <div>

                <span>
                    Time
                </span>

                <strong>
                    ${escapeHtml(
                        timestamp
                    )}
                </strong>

            </div>

        `;

    }


    modal.classList.remove(
        "hidden"
    );

}


// ==========================================================
// NORMALIZE EVIDENCE PATH
// ==========================================================

function normalizeEvidencePath(
    path
) {

    if (!path) {

        return "";

    }


    if (
        path.startsWith(
            "/evidence/"
        )
    ) {

        return path;

    }


    if (
        path.startsWith(
            "data/evidence/"
        )
    ) {

        return (
            "/evidence/" +
            path.substring(
                "data/evidence/".length
            )
        );

    }


    if (
        path.startsWith(
            "/data/evidence/"
        )
    ) {

        return (
            "/evidence/" +
            path.substring(
                "/data/evidence/".length
            )
        );

    }


    return path;

}


// ==========================================================
// MODAL BUTTONS
// ==========================================================

function initializeModalButtons() {

    const closeModalButton =
        getElement(
            "closeModalBtn"
        );

    const cancelModalButton =
        getElement(
            "cancelModalBtn"
        );

    const closeDetailsButton =
        getElement(
            "closeDetailsModalBtn"
        );

    const detailsCloseButton =
        getElement(
            "detailsCloseBtn"
        );

    const closeEvidenceButton =
        getElement(
            "closeEvidenceModalBtn"
        );


    if (closeModalButton) {

        closeModalButton.addEventListener(
            "click",
            closeAssessmentModal
        );

    }


    if (cancelModalButton) {

        cancelModalButton.addEventListener(
            "click",
            closeAssessmentModal
        );

    }


    if (closeDetailsButton) {

        closeDetailsButton.addEventListener(
            "click",
            closeDetailsModal
        );

    }


    if (detailsCloseButton) {

        detailsCloseButton.addEventListener(
            "click",
            closeDetailsModal
        );

    }


    if (closeEvidenceButton) {

        closeEvidenceButton.addEventListener(
            "click",
            closeEvidenceModal
        );

    }


    document.querySelectorAll(
        ".modal-overlay"
    ).forEach(
        (overlay) => {

            overlay.addEventListener(
                "click",
                () => {

                    const modal =
                        overlay.closest(
                            ".modal"
                        );


                    if (modal) {

                        modal.classList.add(
                            "hidden"
                        );

                    }

                }
            );

        }
    );


    document.addEventListener(
        "keydown",
        (event) => {

            if (
                event.key ===
                "Escape"
            ) {

                closeAssessmentModal();

                closeDetailsModal();

                closeEvidenceModal();

            }

        }
    );

}


// ==========================================================
// ASSESSMENT MODAL
// ==========================================================

function openAssessmentModal() {

    const modal =
        getElement(
            "assessmentModal"
        );


    if (!modal) {

        return;

    }


    modal.classList.remove(
        "hidden"
    );

}


function closeAssessmentModal() {

    const modal =
        getElement(
            "assessmentModal"
        );


    if (modal) {

        modal.classList.add(
            "hidden"
        );

    }

}


// ==========================================================
// DETAILS MODAL
// ==========================================================

function openDetailsModal() {

    const modal =
        getElement(
            "detailsModal"
        );


    if (modal) {

        modal.classList.remove(
            "hidden"
        );

    }

}


function closeDetailsModal() {

    const modal =
        getElement(
            "detailsModal"
        );


    if (modal) {

        modal.classList.add(
            "hidden"
        );

    }

}


// ==========================================================
// EVIDENCE MODAL
// ==========================================================

function closeEvidenceModal() {

    const modal =
        getElement(
            "evidenceModal"
        );


    const image =
        getElement(
            "evidenceImage"
        );


    if (modal) {

        modal.classList.add(
            "hidden"
        );

    }


    if (image) {

        image.src = "";

    }

}


// ==========================================================
// SYSTEM STATUS
// ==========================================================

function updateSystemStatus(
    message,
    online
) {

    setText(
        "systemStatus",
        message
    );


    const dot =
        getElement(
            "systemStatusDot"
        );


    if (!dot) {

        return;

    }


    if (online) {

        dot.classList.add(
            "online"
        );

        dot.classList.remove(
            "offline"
        );

    }

    else {

        dot.classList.add(
            "offline"
        );

        dot.classList.remove(
            "online"
        );

    }

}


// ==========================================================
// TOAST
// ==========================================================

let toastTimeout = null;


function showToast(
    message,
    type = "info"
) {

    const toast =
        getElement(
            "toast"
        );


    const toastMessage =
        getElement(
            "toastMessage"
        );


    if (!toast || !toastMessage) {

        return;

    }


    toastMessage.textContent =
        message;


    toast.className =
        `toast ${type}`;


    toast.classList.remove(
        "hidden"
    );


    if (toastTimeout) {

        clearTimeout(
            toastTimeout
        );

    }


    toastTimeout =
        setTimeout(
            () => {

                toast.classList.add(
                    "hidden"
                );

            },
            3500
        );

}


// ==========================================================
// TEXT HELPER
// ==========================================================

function setText(
    id,
    value
) {

    const element =
        getElement(
            id
        );


    if (element) {

        element.textContent =
            value;

    }

}


// ==========================================================
// FORMAT STATUS
// ==========================================================

function formatStatus(
    status
) {

    if (!status) {

        return "READY";

    }


    return status
        .replace(
            /_/g,
            " "
        );

}


// ==========================================================
// FORMAT EVENT TYPE
// ==========================================================

function formatEventType(
    type
) {

    if (!type) {

        return "Unknown Event";

    }


    const names = {

        LOOKING_AWAY:
            "Looking Away",

        FACE_NOT_DETECTED:
            "Face Not Detected",

        MULTIPLE_FACES:
            "Multiple Faces",

        EYES_CLOSED:
            "Eyes Closed",

        ADDITIONAL_PERSON:
            "Additional Person",

        MOBILE_PHONE:
            "Mobile Phone Detected",

        EARPHONES:
            "Earphones Detected",

        SMARTWATCH:
            "Smartwatch Detected",

        BOOK:
            "Book Detected",

        PAPER_NOTES:
            "Paper / Notes Detected",

        LAPTOP:
            "Laptop Detected",

        TABLET:
            "Tablet Detected"

    };


    return (
        names[type] ||
        type
            .replace(
                /_/g,
                " "
            )
            .replace(
                /\b\w/g,
                (character) =>
                    character.toUpperCase()
            )
    );

}


// ==========================================================
// FORMAT DIRECTION
// ==========================================================

function formatDirection(
    direction
) {

    if (!direction) {

        return "";

    }


    return direction
        .toString()
        .replace(
            /_/g,
            " "
        )
        .replace(
            /\b\w/g,
            (character) =>
                character.toUpperCase()
        );

}


// ==========================================================
// FORMAT DATE/TIME
// ==========================================================

function formatDateTime(
    value
) {

    if (!value) {

        return "Not scheduled";

    }


    try {

        const date =
            new Date(
                value
            );


        if (
            Number.isNaN(
                date.getTime()
            )
        ) {

            return value;

        }


        return date.toLocaleString(
            [],
            {

                dateStyle:
                    "medium",

                timeStyle:
                    "short"

            }
        );

    }

    catch (error) {

        return value;

    }

}


// ==========================================================
// FORMAT NUMBER
// ==========================================================

function formatNumber(
    value
) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {

        return "-";

    }


    const number =
        Number(
            value
        );


    if (
        Number.isNaN(
            number
        )
    ) {

        return value;

    }


    return number.toFixed(
        1
    );

}


// ==========================================================
// HTML ESCAPE
// ==========================================================

function escapeHtml(
    value
) {

    if (
        value === null ||
        value === undefined
    ) {

        return "";

    }


    return String(
        value
    )
        .replace(
            /&/g,
            "&amp;"
        )
        .replace(
            /</g,
            "&lt;"
        )
        .replace(
            />/g,
            "&gt;"
        )
        .replace(
            /"/g,
            "&quot;"
        )
        .replace(
            /'/g,
            "&#039;"
        );

}