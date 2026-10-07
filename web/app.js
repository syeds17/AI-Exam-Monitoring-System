/* =========================================================
   MONITORAI FRONTEND
   CLEAN AUTHOR + CANDIDATE APPLICATION
   ========================================================= */

"use strict";


/* =========================================================
   GLOBAL STATE
   ========================================================= */

let assessments = [];

let selectedAssessment = null;
let selectedCandidate = null;

let candidateAssessment = null;
let candidateRecord = null;

let candidatePollingTimer = null;
let candidateCameraStream = null;

let currentAuthorPage = "dashboard";


/* =========================================================
   BASIC HELPERS
   ========================================================= */

function $(id) {
    return document.getElementById(id);
}


function escapeHtml(value) {
    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


function escapeJs(value) {
    return String(value ?? "")
        .replace(/\\/g, "\\\\")
        .replace(/'/g, "\\'");
}


function formatNumber(value) {
    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "0";
    }

    return number.toLocaleString();
}


function formatStatus(status) {
    if (!status) {
        return "UNKNOWN";
    }

    return String(status)
        .replace(/_/g, " ")
        .toLowerCase()
        .replace(/\b\w/g, letter => letter.toUpperCase());
}


function formatEventType(value) {
    if (!value) {
        return "Monitoring Event";
    }

    return String(value)
        .replace(/_/g, " ")
        .toLowerCase()
        .replace(/\b\w/g, letter => letter.toUpperCase());
}


function formatDateTime(value) {
    if (!value) {
        return "—";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return String(value);
    }

    return date.toLocaleString([], {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit"
    });
}


function formatDuration(minutes) {
    if (
        minutes === null ||
        minutes === undefined ||
        minutes === ""
    ) {
        return "—";
    }

    const value = Number(minutes);

    if (!Number.isFinite(value)) {
        return String(minutes);
    }

    if (value < 60) {
        return `${value} min`;
    }

    const hours = Math.floor(value / 60);
    const remaining = value % 60;

    if (!remaining) {
        return `${hours} hr`;
    }

    return `${hours} hr ${remaining} min`;
}


function getAssessmentStatus(assessment) {
    return String(
        assessment?.status ||
        "READY"
    ).toUpperCase();
}


function getCandidateStatus(candidate) {
    return String(
        candidate?.assignment_status ||
        candidate?.status ||
        "UNKNOWN"
    ).toUpperCase();
}


function isCandidateMonitoring(candidate) {
    return [
        "STARTED",
        "ACTIVE",
        "MONITORING",
        "IN_PROGRESS"
    ].includes(
        getCandidateStatus(candidate)
    );
}


function isCandidateCompleted(candidate) {
    return getCandidateStatus(candidate) === "COMPLETED";
}


/* =========================================================
   API
   ========================================================= */

async function apiRequest(
    url,
    options = {}
) {
    const config = {
        ...options,
        headers: {
            ...(options.body
                ? {
                    "Content-Type":
                        "application/json"
                }
                : {}),
            ...(options.headers || {})
        }
    };

    const response = await fetch(
        url,
        config
    );

    const contentType =
        response.headers.get("content-type") || "";

    let data;

    if (
        contentType.includes("application/json")
    ) {
        data = await response.json();
    } else {
        data = await response.text();
    }

    if (!response.ok) {
        let message =
            `Request failed (${response.status})`;

        if (
            data &&
            typeof data === "object" &&
            data.detail
        ) {
            message = data.detail;
        } else if (
            typeof data === "string" &&
            data.trim()
        ) {
            message = data;
        }

        throw new Error(message);
    }

    return data;
}


/* =========================================================
   TOAST
   ========================================================= */

function showToast(
    message,
    type = "success"
) {
    const container =
        $("toastContainer");

    if (!container) {
        return;
    }

    const toast =
        document.createElement("div");

    toast.className =
        `toast ${type}`;

    toast.textContent = message;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform =
            "translateY(8px)";

        setTimeout(() => {
            toast.remove();
        }, 200);
    }, 3000);
}


/* =========================================================
   MODALS
   ========================================================= */

function openModal(id) {
    const modal = $(id);

    if (!modal) {
        return;
    }

    modal.classList.add("open");
}


function closeModal(id) {
    const modal = $(id);

    if (!modal) {
        return;
    }

    modal.classList.remove("open");
}


/* =========================================================
   AUTHOR NAVIGATION
   ========================================================= */

function showAuthorPage(pageName) {

    const pages = [
        "dashboardPage",
        "assessmentsPage",
        "requestsPage"
    ];

    pages.forEach(id => {
        const page = $(id);

        if (!page) {
            return;
        }

        page.classList.toggle(
            "active-page",
            id === `${pageName}Page`
        );
    });


    document
        .querySelectorAll(".nav-item")
        .forEach(item => {

            item.classList.toggle(
                "active",
                item.dataset.page === pageName
            );

        });


    currentAuthorPage = pageName;


    const titleMap = {
        dashboard: [
            "Dashboard",
            "Manage assessments and candidates"
        ],

        assessments: [
            "Assessments",
            "Create and manage your assessment sessions"
        ],

        requests: [
            "Candidate Requests",
            "Review candidates requesting assessment access"
        ]
    };


    const info =
        titleMap[pageName] ||
        titleMap.dashboard;


    if ($("pageTitle")) {
        $("pageTitle").textContent =
            info[0];
    }


    if ($("pageSubtitle")) {
        $("pageSubtitle").textContent =
            info[1];
    }


    if (
        pageName === "dashboard"
    ) {
        loadDashboard();
    }


    if (
        pageName === "assessments"
    ) {
        loadAssessments();
    }


    if (
        pageName === "requests"
    ) {
        loadCandidateRequests();
    }
}


/* =========================================================
   LOAD ASSESSMENTS
   ========================================================= */

async function loadAssessments() {

    try {

        const result =
            await apiRequest(
                "/api/assessments"
            );

        assessments =
            Array.isArray(result)
                ? result
                : result.assessments || [];


        renderAssessmentStats();

        renderAssessmentCards(
            $("allAssessments"),
            assessments
        );

    } catch (error) {

        console.error(
            "Assessment loading failed:",
            error
        );

        showToast(
            error.message ||
            "Unable to load assessments.",
            "error"
        );

        renderEmptyState(
            $("allAssessments"),
            "Unable to load assessments",
            error.message ||
            "Please try again."
        );
    }
}


/* =========================================================
   ASSESSMENT STATS
   ========================================================= */

function renderAssessmentStats() {

    const total =
        assessments.length;

    const active =
        assessments.filter(
            assessment =>
                getAssessmentStatus(
                    assessment
                ) === "ACTIVE"
        ).length;

    const ready =
        assessments.filter(
            assessment =>
                getAssessmentStatus(
                    assessment
                ) === "READY"
        ).length;


    if ($("assessmentTotal")) {
        $("assessmentTotal").textContent =
            total;
    }


    if ($("assessmentActive")) {
        $("assessmentActive").textContent =
            active;
    }


    if ($("assessmentReady")) {
        $("assessmentReady").textContent =
            ready;
    }


    if ($("totalAssessments")) {
        $("totalAssessments").textContent =
            total;
    }


    if ($("activeAssessments")) {
        $("activeAssessments").textContent =
            active;
    }
}


/* =========================================================
   ASSESSMENT CARD
   ========================================================= */

function renderAssessmentCards(
    container,
    list
) {

    if (!container) {
        return;
    }


    if (!list.length) {

        renderEmptyState(
            container,
            "No assessments yet",
            "Create your first assessment to generate an assessment link."
        );

        return;
    }


    container.innerHTML =
        list.map(
            assessment =>
                createAssessmentCard(
                    assessment
                )
        ).join("");
}


function createAssessmentCard(
    assessment
) {

    const id =
        assessment.assessment_id ||
        "";


    const name =
        assessment.assessment_name ||
        "Untitled Assessment";


    const organization =
        assessment.organization ||
        "No organization";


    const type =
        assessment.assessment_type ||
        "Other";


    const duration =
        formatDuration(
            assessment.duration_minutes
        );


    const scheduled =
        assessment.scheduled_at
            ? formatDateTime(
                assessment.scheduled_at
            )
            : "Not scheduled";


    const limit =
        assessment.candidate_limit ??
        50;


    const status =
        getAssessmentStatus(
            assessment
        );


    const token =
        assessment.access_token ||
        "";


    return `
        <article class="assessment-card">

            <div class="assessment-card-top">

                <div class="assessment-card-icon">
                    ▣
                </div>

                <span
                    class="status-badge status-${status.toLowerCase()}"
                >
                    ${escapeHtml(status)}
                </span>

            </div>


            <div class="assessment-card-body">

                <h3>
                    ${escapeHtml(name)}
                </h3>

                <div class="organization">
                    ${escapeHtml(organization)}
                </div>


                <div class="assessment-meta">

                    <div class="assessment-meta-item">
                        <span>Type</span>
                        <strong>
                            ${escapeHtml(type)}
                        </strong>
                    </div>


                    <div class="assessment-meta-item">
                        <span>Duration</span>
                        <strong>
                            ${escapeHtml(duration)}
                        </strong>
                    </div>


                    <div class="assessment-meta-item">
                        <span>Candidate Limit</span>
                        <strong>
                            ${escapeHtml(limit)}
                        </strong>
                    </div>


                    <div class="assessment-meta-item">
                        <span>Scheduled</span>
                        <strong>
                            ${escapeHtml(scheduled)}
                        </strong>
                    </div>

                </div>

            </div>


            <div class="assessment-card-footer">

                <button
                    class="secondary-button"
                    onclick="openAssessmentDetails('${escapeJs(id)}')"
                >
                    Manage
                </button>

                ${
                    token
                        ? `
                            <button
                                class="secondary-button"
                                onclick="copyAssessmentToken('${escapeJs(token)}')"
                            >
                                Copy Link
                            </button>
                        `
                        : ""
                }

            </div>

        </article>
    `;
}


/* =========================================================
   EMPTY STATE
   ========================================================= */

function renderEmptyState(
    container,
    title,
    message
) {

    if (!container) {
        return;
    }


    container.innerHTML = `
        <div class="empty-state">

            <div class="empty-icon">
                ◌
            </div>

            <h3>
                ${escapeHtml(title)}
            </h3>

            <p>
                ${escapeHtml(message)}
            </p>

        </div>
    `;
}


/* =========================================================
   DASHBOARD
   ========================================================= */

async function loadDashboard() {

    try {

        const result =
            await apiRequest(
                "/api/assessments"
            );

        assessments =
            Array.isArray(result)
                ? result
                : result.assessments || [];


        renderAssessmentStats();


        const recent =
            assessments
                .slice()
                .sort(
                    (a, b) =>
                        new Date(
                            b.created_at || 0
                        ) -
                        new Date(
                            a.created_at || 0
                        )
                )
                .slice(0, 6);


        renderAssessmentCards(
            $("recentAssessments"),
            recent
        );


        await updateDashboardCandidateStats(
            assessments
        );

    } catch (error) {

        console.error(
            "Dashboard loading failed:",
            error
        );

        showToast(
            error.message ||
            "Unable to load dashboard.",
            "error"
        );
    }
}


/* =========================================================
   DASHBOARD CANDIDATE STATS
   ========================================================= */

async function updateDashboardCandidateStats(
    assessmentList
) {

    let authorized = 0;
    let completed = 0;


    for (
        const assessment of assessmentList
    ) {

        try {

            const result =
                await apiRequest(
                    `/api/assessments/${encodeURIComponent(
                        assessment.assessment_id
                    )}/candidates`
                );


            const candidates =
                Array.isArray(result)
                    ? result
                    : result.candidates || [];


            candidates.forEach(
                candidate => {

                    const status =
                        getCandidateStatus(
                            candidate
                        );


                    if (
                        [
                            "AUTHORIZED",
                            "STARTED",
                            "ACTIVE",
                            "MONITORING",
                            "IN_PROGRESS"
                        ].includes(status)
                    ) {
                        authorized++;
                    }


                    if (
                        status === "COMPLETED"
                    ) {
                        completed++;
                    }

                }
            );

        } catch (error) {

            console.warn(
                "Could not load candidate stats:",
                error
            );

        }

    }


    if ($("authorizedCandidates")) {
        $("authorizedCandidates").textContent =
            authorized;
    }


    if ($("completedCandidates")) {
        $("completedCandidates").textContent =
            completed;
    }
}


/* =========================================================
   CREATE ASSESSMENT
   ========================================================= */

async function submitAssessmentForm(
    event
) {

    event.preventDefault();


    const name =
        $("assessmentName")?.value.trim();


    const organization =
        $("organization")?.value.trim();


    const type =
        $("assessmentType")?.value ||
        "Other";


    const scheduledAt =
        $("scheduledAt")?.value ||
        null;


    const duration =
        Number(
            $("durationMinutes")?.value ||
            60
        );


    const candidateLimit =
        Number(
            $("candidateLimit")?.value ||
            50
        );


    if (!name) {

        showToast(
            "Enter an assessment name.",
            "warning"
        );

        return;
    }


    if (
        !Number.isFinite(duration) ||
        duration < 1
    ) {

        showToast(
            "Enter a valid duration.",
            "warning"
        );

        return;
    }


    if (
        !Number.isFinite(candidateLimit) ||
        candidateLimit < 1
    ) {

        showToast(
            "Enter a valid candidate limit.",
            "warning"
        );

        return;
    }


    try {

        const result =
            await apiRequest(
                "/api/assessments",
                {
                    method: "POST",

                    body: JSON.stringify({

                        assessment_name:
                            name,

                        organization:
                            organization,

                        assessment_type:
                            type,

                        scheduled_at:
                            scheduledAt,

                        duration_minutes:
                            duration,

                        candidate_limit:
                            candidateLimit

                    })
                }
            );


        closeModal(
            "assessmentModal"
        );


        event.target.reset();


        if ($("durationMinutes")) {
            $("durationMinutes").value =
                60;
        }


        if ($("candidateLimit")) {
            $("candidateLimit").value =
                50;
        }


        showToast(
            "Assessment created successfully.",
            "success"
        );


        await loadAssessments();


        const createdId =
            result.assessment_id ||
            result.id;


        if (createdId) {

            await openAssessmentDetails(
                createdId
            );

        }

    } catch (error) {

        console.error(
            "Assessment creation failed:",
            error
        );

        showToast(
            error.message ||
            "Unable to create assessment.",
            "error"
        );
    }
}


/* =========================================================
   ASSESSMENT DETAILS
   ========================================================= */

async function openAssessmentDetails(
    assessmentId
) {

    try {

        const result =
            await apiRequest(
                `/api/assessments/${encodeURIComponent(
                    assessmentId
                )}`
            );
        
        const assessment =
            result.assessment ||
            result;


        selectedAssessment =
            assessment;


        renderAssessmentDetails(
            assessment
        );


        await loadAssessmentCandidates(
            assessmentId
        );


        openModal(
            "detailsModal"
        );

    } catch (error) {

        console.error(
            "Assessment details failed:",
            error
        );

        showToast(
            error.message ||
            "Unable to load assessment.",
            "error"
        );
    }
}


/* =========================================================
   ASSESSMENT DETAILS UI
   ========================================================= */

function renderAssessmentDetails(
    assessment
) {

    const name =
        assessment.assessment_name ||
        "Assessment";


    if ($("detailsTitle")) {
        $("detailsTitle").textContent =
            name;
    }


    const details =
        $("assessmentDetails");


    if (details) {

        details.innerHTML = `

            <div class="detail-list">

                <div class="detail-row">
                    <span>Organization</span>
                    <strong>
                        ${escapeHtml(
                            assessment.organization ||
                            "—"
                        )}
                    </strong>
                </div>

                <div class="detail-row">
                    <span>Assessment Type</span>
                    <strong>
                        ${escapeHtml(
                            assessment.assessment_type ||
                            "—"
                        )}
                    </strong>
                </div>

                <div class="detail-row">
                    <span>Status</span>
                    <strong>
                        ${escapeHtml(
                            getAssessmentStatus(
                                assessment
                            )
                        )}
                    </strong>
                </div>

                <div class="detail-row">
                    <span>Duration</span>
                    <strong>
                        ${escapeHtml(
                            formatDuration(
                                assessment.duration_minutes
                            )
                        )}
                    </strong>
                </div>

                <div class="detail-row">
                    <span>Candidate Limit</span>
                    <strong>
                        ${escapeHtml(
                            assessment.candidate_limit ??
                            50
                        )}
                    </strong>
                </div>

                <div class="detail-row">
                    <span>Scheduled</span>
                    <strong>
                        ${escapeHtml(
                            assessment.scheduled_at
                                ? formatDateTime(
                                    assessment.scheduled_at
                                )
                                : "Not scheduled"
                        )}
                    </strong>
                </div>

            </div>
        `;
    }


    const token =
        assessment.access_token ||
        "";


    if ($("assessmentLink")) {

        if (token) {

            $("assessmentLink").value =
                buildAssessmentLink(
                    token
                );

        } else {

            $("assessmentLink").value =
                "Assessment link unavailable";

        }
    }


    const activateButton =
        $("activateAssessmentBtn");


    const deactivateButton =
        $("deactivateAssessmentBtn");


    const status =
        getAssessmentStatus(
            assessment
        );


    if (activateButton) {

        activateButton.style.display =
            status === "ACTIVE"
                ? "none"
                : "inline-flex";
    }


    if (deactivateButton) {

        deactivateButton.style.display =
            status === "ACTIVE"
                ? "inline-flex"
                : "none";
    }
}


/* =========================================================
   BUILD ASSESSMENT LINK
   ========================================================= */

function buildAssessmentLink(
    token
) {

    const base =
        window.location.origin;

    return `${base}/?assessment=${encodeURIComponent(token)}`;
}


function copyAssessmentToken(
    token
) {

    const link =
        buildAssessmentLink(
            token
        );


    copyText(
        link
    );
}


async function copyText(
    text
) {

    try {

        await navigator.clipboard.writeText(
            text
        );

        showToast(
            "Assessment link copied.",
            "success"
        );

    } catch (error) {

        const input =
            document.createElement("textarea");

        input.value =
            text;

        document.body.appendChild(
            input
        );

        input.select();

        document.execCommand(
            "copy"
        );

        input.remove();

        showToast(
            "Assessment link copied.",
            "success"
        );
    }
}


/* =========================================================
   ASSESSMENT CANDIDATES
   ========================================================= */

async function loadAssessmentCandidates(
    assessmentId
) {

    const container =
        $("assessmentCandidates");


    if (!container) {
        return;
    }


    try {

        const result =
            await apiRequest(
                `/api/assessments/${encodeURIComponent(
                    assessmentId
                )}/candidates`
            );


        const candidates =
            Array.isArray(result)
                ? result
                : result.candidates || [];


        renderCandidateRows(
            container,
            candidates,
            assessmentId
        );

    } catch (error) {

        console.error(
            "Candidate loading failed:",
            error
        );

        renderEmptyState(
            container,
            "Unable to load candidates",
            error.message ||
            "Please try again."
        );
    }
}


function renderCandidateRows(
    container,
    candidates,
    assessmentId
) {

    if (!candidates.length) {

        container.innerHTML = `
            <div class="empty-state">

                <div class="empty-icon">
                    ♙
                </div>

                <h3>
                    No candidates yet
                </h3>

                <p>
                    Candidates will appear here after requesting access.
                </p>

            </div>
        `;

        return;
    }


    container.innerHTML = `

        <div class="candidate-row header">

            <div>
                Candidate
            </div>

            <div>
                Candidate ID
            </div>

            <div>
                Status
            </div>

            <div>
                Final Review
            </div>

        </div>


        ${
            candidates.map(
                candidate => {

                    const recordId =
                        candidate.candidate_record_id ||
                        candidate.id ||
                        "";


                    const name =
                        candidate.candidate_name ||
                        candidate.name ||
                        "Unknown Candidate";


                    const candidateId =
                        candidate.candidate_id ||
                        "—";


                    const status =
                        getCandidateStatus(
                            candidate
                        );


                    /*
                     * Human reviewer decision.
                     *
                     * Possible values:
                     * CHEATING
                     * NOT_CHEATING
                     * NEEDS_REVIEW
                     */

                    const reviewerDecision =
                        candidate.reviewer_decision ||
                        "";


                    /*
                     * FINAL REVIEW DISPLAY
                     */

                    let reviewDisplay = `
                        <span class="status-badge status-pending">
                            NOT REVIEWED
                        </span>
                    `;


                    if (
                        reviewerDecision ===
                        "CHEATING"
                    ) {

                        reviewDisplay = `
                            <span class="status-badge status-rejected">
                                CHEATING
                            </span>
                        `;

                    }


                    else if (
                        reviewerDecision ===
                        "NOT_CHEATING"
                    ) {

                        reviewDisplay = `
                            <span class="status-badge status-completed">
                                NOT CHEATING
                            </span>
                        `;

                    }


                    else if (
                        reviewerDecision ===
                        "NEEDS_REVIEW"
                    ) {

                        reviewDisplay = `
                            <span class="status-badge status-warning">
                                NEEDS REVIEW
                            </span>
                        `;

                    }


                    /*
                     * Only candidates who have
                     * finished monitoring can be reviewed.
                     */

                    const canReview =
                        [

                            "COMPLETED",
                            "STARTED",
                            "ACTIVE",
                            "MONITORING",
                            "IN_PROGRESS"

                        ].includes(
                            status
                        );


                    /*
                     * IMPORTANT:
                     *
                     * Once a final decision exists,
                     * do NOT show the Review button again.
                     */

                    const showReviewButton =
                        canReview &&
                        !reviewerDecision;


                    return `

                        <div class="candidate-row">

                            <!-- CANDIDATE -->

                            <div class="candidate-name">

                                <strong>
                                    ${escapeHtml(name)}
                                </strong>

                                <span>
                                    ${
                                        candidate.access_code
                                            ? "Authorized"
                                            : "Candidate"
                                    }
                                </span>

                            </div>


                            <!-- CANDIDATE ID -->

                            <div>
                                ${escapeHtml(candidateId)}
                            </div>


                            <!-- STATUS -->

                            <div class="candidate-status">

                                <span
                                    class="status-badge status-${status.toLowerCase()}"
                                >
                                    ${escapeHtml(
                                        formatStatus(status)
                                    )}
                                </span>

                            </div>


                            <!-- FINAL REVIEW -->

                            <div class="candidate-review">

                                ${reviewDisplay}


                                ${
                                    showReviewButton
                                        ? `

                                            <button
                                                class="secondary-button"
                                                style="margin-top:6px;"
                                                onclick="openCandidateReview(
                                                    '${escapeJs(
                                                        assessmentId
                                                    )}',
                                                    '${escapeJs(
                                                        recordId
                                                    )}'
                                                )"
                                            >
                                                Review
                                            </button>

                                        `
                                        : ""
                                }

                            </div>

                        </div>

                    `;
                }
            ).join("")
        }

    `;
}

/* =========================================================
   ACTIVATE / DEACTIVATE
   ========================================================= */

async function activateAssessment() {

    if (!selectedAssessment) {
        return;
    }


    const id =
        selectedAssessment.assessment_id;


    try {

        await apiRequest(
            `/api/assessments/${encodeURIComponent(
                id
            )}/activate`,
            {
                method: "POST"
            }
        );


        showToast(
            "Assessment activated.",
            "success"
        );


        await openAssessmentDetails(
            id
        );


        await loadAssessments();

    } catch (error) {

        showToast(
            error.message ||
            "Unable to activate assessment.",
            "error"
        );
    }
}


async function deactivateAssessment() {

    if (!selectedAssessment) {
        return;
    }


    const id =
        selectedAssessment.assessment_id;


    try {

        await apiRequest(
            `/api/assessments/${encodeURIComponent(
                id
            )}/deactivate`,
            {
                method: "POST"
            }
        );


        showToast(
            "Assessment deactivated.",
            "success"
        );


        await openAssessmentDetails(
            id
        );


        await loadAssessments();

    } catch (error) {

        showToast(
            error.message ||
            "Unable to deactivate assessment.",
            "error"
        );
    }
}


/* =========================================================
   CANDIDATE REQUESTS
   ========================================================= */

async function loadCandidateRequests() {

    const container =
        $("candidateRequests");


    if (!container) {
        return;
    }


    try {

        const result =
            await apiRequest(
                "/api/assessments"
            );


        const list =
            Array.isArray(result)
                ? result
                : result.assessments || [];


        let requests = [];


        for (
            const assessment of list
        ) {

            try {

                const response =
                    await apiRequest(
                        `/api/assessments/${encodeURIComponent(
                            assessment.assessment_id
                        )}/candidates`
                    );


                const candidates =
                    Array.isArray(response)
                        ? response
                        : response.candidates || [];


                candidates
                    .filter(
                        candidate =>
                            getCandidateStatus(
                                candidate
                            ) === "PENDING"
                    )
                    .forEach(
                        candidate => {

                            requests.push({
                                ...candidate,
                                assessment_id:
                                    assessment.assessment_id,

                                assessment_name:
                                    assessment.assessment_name
                            });

                        }
                    );

            } catch (error) {

                console.warn(
                    "Could not load candidates:",
                    error
                );

            }
        }


        renderCandidateRequests(
            container,
            requests
        );

    } catch (error) {

        console.error(
            "Request loading failed:",
            error
        );

        renderEmptyState(
            container,
            "Unable to load requests",
            error.message ||
            "Please try again."
        );
    }
}


/* =========================================================
   REQUEST UI
   ========================================================= */

function renderCandidateRequests(
    container,
    requests
) {

    if (!requests.length) {

        renderEmptyState(
            container,
            "No pending requests",
            "Candidate access requests will appear here."
        );

        return;
    }


    container.innerHTML =
        requests.map(
            request => {

                const recordId =
                    request.candidate_record_id ||
                    request.id ||
                    "";


                const name =
                    request.candidate_name ||
                    request.name ||
                    "Unknown Candidate";


                const candidateId =
                    request.candidate_id ||
                    "—";


                return `

                    <article class="request-card">

                        <div class="request-main">

                            <h3>
                                ${escapeHtml(name)}
                            </h3>

                            <p>
                                Candidate ID:
                                ${escapeHtml(candidateId)}
                            </p>

                        </div>


                        <div class="request-assessment">

                            ${escapeHtml(
                                request.assessment_name ||
                                "Assessment"
                            )}

                        </div>


                        <div class="request-actions">

                            <button
                                class="secondary-button"
                                onclick="openCandidateRequest(
                                    '${escapeJs(
                                        request.assessment_id
                                    )}',
                                    '${escapeJs(
                                        recordId
                                    )}'
                                )"
                            >
                                Review
                            </button>

                        </div>

                    </article>
                `;
            }
        ).join("");
}


/* =========================================================
   REQUEST MODAL
   ========================================================= */

async function openCandidateRequest(
    assessmentId,
    candidateRecordId
) {

    try {

        const result =
            await apiRequest(
                `/api/assessments/${encodeURIComponent(
                    assessmentId
                )}/candidates/${encodeURIComponent(
                    candidateRecordId
                )}`
            );

        const candidate =
            result.candidate ||
            result;


        selectedCandidate = {
            ...candidate,
            assessment_id:
                assessmentId
        };


        const name =
            candidate.candidate_name ||
            candidate.name ||
            "Candidate";


        if ($("requestCandidateName")) {
            $("requestCandidateName").textContent =
                name;
        }


        if ($("requestDetails")) {

            $("requestDetails").innerHTML = `

                <div class="detail-row">
                    <span>Candidate ID</span>
                    <strong>
                        ${escapeHtml(
                            candidate.candidate_id ||
                            "—"
                        )}
                    </strong>
                </div>


                <div class="detail-row">
                    <span>Assessment</span>
                    <strong>
                        ${escapeHtml(
                            candidate.assessment_name ||
                            "Assessment"
                        )}
                    </strong>
                </div>


                <div class="detail-row">
                    <span>Status</span>
                    <strong>
                        ${escapeHtml(
                            formatStatus(
                                getCandidateStatus(
                                    candidate
                                )
                            )
                        )}
                    </strong>
                </div>


                <div class="detail-row">
                    <span>Requested</span>
                    <strong>
                        ${escapeHtml(
                            formatDateTime(
                                candidate.created_at
                            )
                        )}
                    </strong>
                </div>

            `;
        }


        openModal(
            "requestModal"
        );

    } catch (error) {

        showToast(
            error.message ||
            "Unable to load candidate request.",
            "error"
        );
    }
}


/* =========================================================
   APPROVE CANDIDATE
   ========================================================= */

async function approveCandidate() {

    if (!selectedCandidate) {
        return;
    }


    const assessmentId =
        selectedCandidate.assessment_id;


    const candidateRecordId =
        selectedCandidate.candidate_record_id ||
        selectedCandidate.id;


    try {

        const result =
            await apiRequest(
                `/api/assessments/${encodeURIComponent(
                    assessmentId
                )}/candidates/${encodeURIComponent(
                    candidateRecordId
                )}/approve`,
                {
                    method: "POST"
                }
            );


        closeModal(
            "requestModal"
        );


        showToast(
            result.access_code
                ? `Candidate approved. Access code: ${result.access_code}`
                : "Candidate approved.",
            "success"
        );


        await loadCandidateRequests();


    } catch (error) {

        showToast(
            error.message ||
            "Unable to approve candidate.",
            "error"
        );
    }
}


/* =========================================================
   REJECT CANDIDATE
   ========================================================= */

async function rejectCandidate() {

    if (!selectedCandidate) {
        return;
    }


    const assessmentId =
        selectedCandidate.assessment_id;


    const candidateRecordId =
        selectedCandidate.candidate_record_id ||
        selectedCandidate.id;


    try {

        await apiRequest(
            `/api/assessments/${encodeURIComponent(
                assessmentId
            )}/candidates/${encodeURIComponent(
                candidateRecordId
            )}/reject`,
            {
                method: "POST"
            }
        );


        closeModal(
            "requestModal"
        );


        showToast(
            "Candidate request rejected.",
            "success"
        );


        await loadCandidateRequests();

    } catch (error) {

        showToast(
            error.message ||
            "Unable to reject candidate.",
            "error"
        );
    }
}


/* =========================================================
   CANDIDATE REVIEW
   ========================================================= */

async function openCandidateReview(
    assessmentId,
    candidateRecordId
) {

    try {

        const result =
            await apiRequest(
                `/api/assessments/${encodeURIComponent(
                    assessmentId
                )}/candidates/${encodeURIComponent(
                    candidateRecordId
                )}/review`
            );


        selectedCandidate = {
            ...result.candidate,
            assessment_id:
                assessmentId,

            candidate_record_id:
                candidateRecordId
        };


        renderCandidateReview(
            result
        );


        openModal(
            "reviewModal"
        );

    } catch (error) {

        console.error(
            "Candidate review failed:",
            error
        );

        showToast(
            error.message ||
            "Unable to load candidate review.",
            "error"
        );
    }
}


/* =========================================================
   REVIEW UI
   ========================================================= */

function renderCandidateReview(
    result
) {

    const candidate =
        result.candidate ||
        {};


    const session =
        result.session ||
        {};


    const events =
        Array.isArray(result.events)
            ? result.events
            : [];


    if ($("reviewCandidateName")) {

        $("reviewCandidateName").textContent =
            candidate.candidate_name ||
            candidate.name ||
            "Candidate";
    }


    if ($("reviewAssessmentName")) {

        $("reviewAssessmentName").textContent =
            candidate.assessment_name ||
            "Assessment";
    }


    if ($("reviewSummary")) {

        $("reviewSummary").innerHTML = `

            <div class="review-summary-card">
                <span>Candidate ID</span>

                <strong>
                    ${escapeHtml(
                        candidate.candidate_id ||
                        "—"
                    )}
                </strong>
            </div>


            <div class="review-summary-card">
                <span>Session</span>

                <strong>
                    ${escapeHtml(
                        session.session_id ||
                        "—"
                    )}
                </strong>
            </div>


            <div class="review-summary-card">
                <span>Events</span>

                <strong>
                    ${events.length}
                </strong>
            </div>

        `;
    }


    renderReviewEvents(
        events
    );


    if ($("reviewDecision")) {

        $("reviewDecision").value =
            candidate.reviewer_decision ||
            "";
    }


    if ($("reviewNotes")) {

        $("reviewNotes").value =
            candidate.reviewer_notes ||
            "";
    }
}


/* =========================================================
   REVIEW EVENTS
   ========================================================= */

function renderReviewEvents(
    events
) {

    const container =
        $("reviewEvents");


    if (!container) {
        return;
    }


    if (!events.length) {

        container.innerHTML = `
            <div class="empty-state">

                <div class="empty-icon">
                    ✓
                </div>

                <h3>
                    No monitoring events
                </h3>

                <p>
                    No persisted monitoring events were recorded
                    for this session.
                </p>

            </div>
        `;

        return;
    }


    container.innerHTML =
        events.map(
            event => {

                const evidence =
                    event.evidence_path ||
                    "";


                return `

                    <div class="event-row">

                        <div>

                            <strong>
                                ${escapeHtml(
                                    formatEventType(
                                        event.event_type
                                    )
                                )}
                            </strong>

                            <span>
                                ${
                                    event.direction
                                        ? escapeHtml(
                                            event.direction
                                        )
                                        : "Monitoring event"
                                }
                            </span>

                        </div>


                        <div>

                            <time>
                                ${escapeHtml(
                                    formatDateTime(
                                        event.timestamp
                                    )
                                )}
                            </time>


                            ${
                                evidence
                                    ? `
                                        <button
                                            class="secondary-button"
                                            style="margin-top:6px;"
                                            onclick="openEvidence(
                                                '${escapeJs(
                                                    event.session_id
                                                )}',
                                                '${escapeJs(
                                                    evidence
                                                )}',
                                                '${escapeJs(
                                                    event.event_type
                                                )}'
                                            )"
                                        >
                                            Evidence
                                        </button>
                                    `
                                    : ""
                            }

                        </div>

                    </div>
                `;
            }
        ).join("");
}


/* =========================================================
   SAVE REVIEW
   ========================================================= */

async function saveReviewerDecision() {

    if (!selectedCandidate) {
        return;
    }


    const decision =
        $("reviewDecision")?.value ||
        "";


    const notes =
        $("reviewNotes")?.value ||
        "";


    if (!decision) {

        showToast(
            "Select a reviewer decision.",
            "warning"
        );

        return;
    }


    const assessmentId =
        selectedCandidate.assessment_id;


    const candidateRecordId =
        selectedCandidate.candidate_record_id ||
        selectedCandidate.id;


    try {

        await apiRequest(
            `/api/assessments/${encodeURIComponent(
                assessmentId
            )}/candidates/${encodeURIComponent(
                candidateRecordId
            )}/review`,
            {
                method: "POST",

                body: JSON.stringify({
                    decision,
                    notes
                })
            }
        );


        showToast(
            "Reviewer decision saved.",
            "success"
        );


        closeModal(
            "reviewModal"
        );

        await loadAssessmentCandidates(
            assessmentId
        );


        if (
            currentAuthorPage ===
            "dashboard"
        ) {
            await loadDashboard();
        }

    } catch (error) {

        showToast(
            error.message ||
            "Unable to save reviewer decision.",
            "error"
        );
    }
}


/* =========================================================
   EVIDENCE
   ========================================================= */

function openEvidence(
    sessionId,
    evidencePath,
    eventType
) {

    const filename =
        evidencePath
            .split(/[\\/]/)
            .pop();


    if (!filename) {

        showToast(
            "Evidence file unavailable.",
            "error"
        );

        return;
    }


    const image =
        $("evidenceImage");


    if (image) {

        image.src =
            `/api/evidence/${encodeURIComponent(
                sessionId
            )}/${encodeURIComponent(
                filename
            )}`;
    }


    if ($("evidenceTitle")) {

        $("evidenceTitle").textContent =
            formatEventType(
                eventType
            );
    }


    if ($("evidenceDetails")) {

        $("evidenceDetails").innerHTML = `

            <strong>
                ${escapeHtml(
                    formatEventType(
                        eventType
                    )
                )}
            </strong>

            <div style="margin-top:5px;">
                Session:
                ${escapeHtml(sessionId)}
            </div>

            <div style="margin-top:5px;">
                Evidence:
                ${escapeHtml(filename)}
            </div>

        `;
    }


    openModal(
        "evidenceModal"
    );
}

/* =========================================================
   CANDIDATE APPLICATION
   ========================================================= */


/* =========================================================
   SHOW CANDIDATE STEP
   ========================================================= */

function showCandidateStep(
    stepId
) {

    const steps = [
        "candidateAccessStep",
        "candidateRequestStep",
        "candidateWaitingStep",
        "candidateAuthorizedStep",
        "candidateReadinessStep",
        "candidateMonitoringStep",
        "candidateCompletedStep"
    ];


    steps.forEach(id => {

        const step = $(id);

        if (!step) {
            return;
        }

        step.classList.toggle(
            "active-step",
            id === stepId
        );

    });
}


/* =========================================================
   ENTER CANDIDATE APPLICATION
   ========================================================= */

function showCandidateApplication() {

    const authorApp =
        $("authorApp");

    const candidateApp =
        $("candidateApp");


    if (authorApp) {
        authorApp.style.display =
            "none";
    }


    if (candidateApp) {
        candidateApp.style.display =
            "block";
    }


    document.body.classList.add(
        "candidate-mode"
    );


    showCandidateStep(
        "candidateAccessStep"
    );
}


/* =========================================================
   ENTER AUTHOR APPLICATION
   ========================================================= */

function showAuthorApplication() {

    const authorApp =
        $("authorApp");

    const candidateApp =
        $("candidateApp");


    if (candidateApp) {
        candidateApp.style.display =
            "none";
    }


    if (authorApp) {
        authorApp.style.display =
            "flex";
    }


    document.body.classList.remove(
        "candidate-mode"
    );


    showAuthorPage(
        "dashboard"
    );
}


/* =========================================================
   LOAD CANDIDATE ASSESSMENT
   ========================================================= */

async function loadCandidateAssessment(
    accessToken
) {

    if (!accessToken) {

        showToast(
            "Assessment access token is missing.",
            "warning"
        );

        return;
    }


    try {

        const assessment =
            await apiRequest(
                `/api/assessments/link/${encodeURIComponent(
                    accessToken
                )}`
            );


        candidateAssessment =
            assessment.assessment || assessment;


        renderCandidateAssessment(
            candidateAssessment
        );


        showCandidateStep(
            "candidateRequestStep"
        );


        const headerStatus =
            $("candidateHeaderStatus");


        if (headerStatus) {

            headerStatus.textContent =
                "Assessment Found";
        }


    } catch (error) {

        console.error(
            "Candidate assessment loading failed:",
            error
        );


        const errorElement =
            $("candidateAccessError");


        if (errorElement) {

            errorElement.textContent =
                error.message ||
                "Assessment not found or unavailable.";
        }


        showToast(
            error.message ||
            "Unable to open assessment.",
            "error"
        );
    }
}


/* =========================================================
   RENDER CANDIDATE ASSESSMENT
   ========================================================= */

function renderCandidateAssessment(
    assessment
) {

    if ($("candidateAssessmentName")) {

        $("candidateAssessmentName").textContent =
            assessment.assessment_name ||
            "Assessment";
    }


    if ($("candidateOrganization")) {

        $("candidateOrganization").textContent =
            assessment.organization ||
            "—";
    }


    if ($("candidateAssessmentType")) {

        $("candidateAssessmentType").textContent =
            assessment.assessment_type ||
            "—";
    }


    if ($("candidateDuration")) {

        $("candidateDuration").textContent =
            formatDuration(
                assessment.duration_minutes
            );
    }


    if ($("candidateAssessmentInfo")) {

        $("candidateAssessmentInfo").textContent =
            "Enter your candidate details and request access to this assessment.";
    }
}


/* =========================================================
   CANDIDATE REQUEST ACCESS
   ========================================================= */

async function requestCandidateAccess() {

    if (!candidateAssessment) {

        showToast(
            "Assessment information is unavailable.",
            "error"
        );

        return;
    }


    const name =
        $("candidateName")?.value.trim() ||
        "";


    const candidateId =
        $("candidateId")?.value.trim() ||
        "";


    if (!name) {

        showToast(
            "Enter your full name.",
            "warning"
        );

        return;
    }


    if (!candidateId) {

        showToast(
            "Enter your candidate ID.",
            "warning"
        );

        return;
    }


    try {

        const result =
            await apiRequest(
                `/api/assessments/${encodeURIComponent(
                    candidateAssessment.assessment_id
                )}/access-request`,
                {
                    method: "POST",

                    body: JSON.stringify({

                        candidate_name:
                            name,

                        candidate_id:
                            candidateId

                    })
                }
            );


        candidateRecord =
            result.candidate ||
            result;


        showCandidateStep(
            "candidateWaitingStep"
        );


        const headerStatus =
            $("candidateHeaderStatus");


        if (headerStatus) {

            headerStatus.textContent =
                "Waiting for Approval";
        }


        showToast(
            "Access request submitted.",
            "success"
        );


        startCandidatePolling();

    } catch (error) {

        console.error(
            "Candidate access request failed:",
            error
        );


        showToast(
            error.message ||
            "Unable to submit access request.",
            "error"
        );
    }
}


/* =========================================================
   CANDIDATE AUTHORIZATION POLLING
   ========================================================= */

function startCandidatePolling() {

    stopCandidatePolling();


    candidatePollingTimer =
        setInterval(
            checkCandidateAuthorization,
            2500
        );


    checkCandidateAuthorization();
}


function stopCandidatePolling() {

    if (
        candidatePollingTimer
    ) {

        clearInterval(
            candidatePollingTimer
        );

        candidatePollingTimer =
            null;
    }
}


/* =========================================================
   CHECK CANDIDATE AUTHORIZATION
   ========================================================= */

async function checkCandidateAuthorization() {

    if (
        !candidateAssessment ||
        !candidateRecord
    ) {
        return;
    }


    const candidateRecordId =
        candidateRecord.candidate_record_id ||
        candidateRecord.id;


    if (!candidateRecordId) {
        return;
    }


    try {

        const result =
            await apiRequest(
                `/api/assessments/${encodeURIComponent(
                    candidateAssessment.assessment_id
                )}/candidates/${encodeURIComponent(
                    candidateRecordId
                )}`
            );

        const candidate =
            result.candidate ||
            result;


        candidateRecord =
            {
                ...candidateRecord,
                ...candidate
            };


        const status =
            getCandidateStatus(
                candidateRecord
            );


        if (
            [
                "AUTHORIZED",
                "APPROVED"
            ].includes(status)
        ) {

            stopCandidatePolling();

            showCandidateAuthorized();

            return;
        }


        if (
            [
                "REJECTED",
                "DENIED"
            ].includes(status)
        ) {

            stopCandidatePolling();

            showCandidateRejected();

            return;
        }


        if (
            [
                "STARTED",
                "ACTIVE",
                "MONITORING",
                "IN_PROGRESS"
            ].includes(status)
        ) {

            stopCandidatePolling();

            showCandidateMonitoringState();

            return;
        }


        if (
            status === "COMPLETED"
        ) {

            stopCandidatePolling();

            showCandidateCompleted();

        }

    } catch (error) {

        console.warn(
            "Authorization check failed:",
            error
        );
    }
}


/* =========================================================
   MANUAL CHECK STATUS
   ========================================================= */

async function manualCandidateStatusCheck() {

    await checkCandidateAuthorization();

    showToast(
        "Authorization status refreshed.",
        "success"
    );
}


/* =========================================================
   CANDIDATE AUTHORIZED
   ========================================================= */

function showCandidateAuthorized() {

    const accessCode =
        candidateRecord?.access_code ||
        candidateRecord?.candidate_access_code ||
        candidateRecord?.authorization_code ||
        "AUTHORIZED";


    if ($("candidateAccessCode")) {

        $("candidateAccessCode").textContent =
            accessCode;
    }


    const headerStatus =
        $("candidateHeaderStatus");


    if (headerStatus) {

        headerStatus.textContent =
            "Access Approved";
    }


    showCandidateStep(
        "candidateAuthorizedStep"
    );


    showToast(
        "Your assessment access has been approved.",
        "success"
    );
}


/* =========================================================
   CANDIDATE REJECTED
   ========================================================= */

function showCandidateRejected() {

    const waitingStep =
        $("candidateWaitingStep");


    if (waitingStep) {

        waitingStep.innerHTML = `

            <div class="candidate-card">

                <div
                    class="success-icon"
                    style="
                        color:#f87171;
                        background:rgba(239,68,68,.1);
                        border-color:rgba(239,68,68,.25);
                    "
                >
                    ×
                </div>

                <span class="eyebrow">
                    Access Request
                </span>

                <h1>
                    Access not approved
                </h1>

                <p>
                    Your request was not approved by the
                    assessment administrator.
                </p>

            </div>

        `;
    }


    showCandidateStep(
        "candidateWaitingStep"
    );


    const headerStatus =
        $("candidateHeaderStatus");


    if (headerStatus) {

        headerStatus.textContent =
            "Access Not Approved";
    }


    showToast(
        "Your assessment access was not approved.",
        "error"
    );
}


/* =========================================================
   ENTER CANDIDATE READINESS
   ========================================================= */

async function enterCandidateReadiness() {

    if (!candidateRecord) {

        showToast(
            "Candidate authorization information is missing.",
            "error"
        );

        return;
    }


    showCandidateStep(
        "candidateReadinessStep"
    );


    const headerStatus =
        $("candidateHeaderStatus");


    if (headerStatus) {

        headerStatus.textContent =
            "Camera Readiness";
    }


    await startCandidateCamera();
}


/* =========================================================
   CAMERA
   ========================================================= */

async function startCandidateCamera() {

    stopCandidateCamera();


    const video =
        $("candidateCamera");


    const readiness =
        $("cameraReadiness");


    if (!video) {
        return;
    }


    if (
        !navigator.mediaDevices ||
        !navigator.mediaDevices.getUserMedia
    ) {

        if (readiness) {

            readiness.textContent =
                "Camera access is not supported by this browser.";

            readiness.className =
                "readiness-status error";
        }

        return;
    }


    try {

        candidateCameraStream =
            await navigator.mediaDevices.getUserMedia({
                video: {
                    width: {
                        ideal: 1280
                    },

                    height: {
                        ideal: 720
                    },

                    facingMode: "user"
                },

                audio: false
            });


        video.srcObject =
            candidateCameraStream;


        await video.play();


        if (readiness) {

            readiness.textContent =
                "Camera ready. You can start monitoring.";

            readiness.className =
                "readiness-status ready";
        }


        const startButton =
            $("candidateStartBtn");


        if (startButton) {

            startButton.disabled =
                false;
        }


        const overlay =
            $("cameraOverlay");


        if (overlay) {

            overlay.textContent =
                "Camera Ready";
        }

    } catch (error) {

        console.error(
            "Camera access failed:",
            error
        );


        if (readiness) {

            readiness.textContent =
                "Camera permission is required.";

            readiness.className =
                "readiness-status error";
        }


        const startButton =
            $("candidateStartBtn");


        if (startButton) {

            startButton.disabled =
                true;
        }


        showToast(
            "Please allow camera access to continue.",
            "error"
        );
    }
}


/* =========================================================
   STOP CAMERA
   ========================================================= */

function stopCandidateCamera() {

    if (
        candidateCameraStream
    ) {

        candidateCameraStream
            .getTracks()
            .forEach(
                track =>
                    track.stop()
            );


        candidateCameraStream =
            null;
    }


    const video =
        $("candidateCamera");


    if (video) {

        video.pause();

        video.srcObject =
            null;
    }
}


/* =========================================================
   START MONITORING
   ========================================================= */

async function startCandidateMonitoring() {

    if (
        !candidateAssessment ||
        !candidateRecord
    ) {

        showToast(
            "Assessment or candidate information is missing.",
            "error"
        );

        return;
    }


    const candidateRecordId =
        candidateRecord.candidate_record_id ||
        candidateRecord.id;


    if (!candidateRecordId) {

        showToast(
            "Candidate record ID is missing.",
            "error"
        );

        return;
    }


    try {

        stopCandidateCamera();

        await new Promise(
            resolve => setTimeout(
                resolve,
                300
            )
        );

        await apiRequest(
            `/api/assessments/${encodeURIComponent(
                candidateAssessment.assessment_id
            )}/candidates/${encodeURIComponent(
                candidateRecordId
            )}/start`,
            {
                method: "POST"
            }
        );

        showCandidateMonitoringState();


        showToast(
            "Monitoring started.",
            "success"
        );


    } catch (error) {

        console.error(
            "Monitoring start failed:",
            error
        );


        showToast(
            error.message ||
            "Unable to start monitoring.",
            "error"
        );
    }
}


/* =========================================================
   SHOW LIVE MONITORING
   ========================================================= */

function showCandidateMonitoringState() {

    showCandidateStep(
        "candidateMonitoringStep"
    );


    const headerStatus =
        $("candidateHeaderStatus");


    if (headerStatus) {

        headerStatus.textContent =
            "Monitoring Active";
    }


    if ($("activeAssessmentName")) {

        $("activeAssessmentName").textContent =
            candidateAssessment?.assessment_name ||
            "Assessment";
    }


    const video =
        $("candidateMonitoringVideo");


    if (video) {

        video.src =
            `/api/video?t=${Date.now()}`;
    }


    startCandidateVideoRefresh();
}


/* =========================================================
   VIDEO REFRESH
   ========================================================= */

let candidateVideoTimer = null;


function startCandidateVideoRefresh() {

    stopCandidateVideoRefresh();


    refreshCandidateVideo();


    candidateVideoTimer =
        setInterval(
            refreshCandidateVideo,
            250
        );
}


function stopCandidateVideoRefresh() {

    if (
        candidateVideoTimer
    ) {

        clearInterval(
            candidateVideoTimer
        );

        candidateVideoTimer =
            null;
    }
}


function refreshCandidateVideo() {

    const video =
        $("candidateMonitoringVideo");


    if (!video) {
        return;
    }


    if (
        !candidateRecord
    ) {
        return;
    }


    /*
       The backend exposes /api/video as the monitoring stream.

       Do not continuously replace the src if the browser is
       already consuming the stream. This function mainly makes
       sure the source exists after navigation/reload.
    */

    if (
        !video.src ||
        !video.src.includes(
            "/api/video"
        )
    ) {

        video.src =
            `/api/video?t=${Date.now()}`;
    }
}


/* =========================================================
   COMPLETE ASSESSMENT
   ========================================================= */

async function completeCandidateAssessment() {

    if (
        !candidateAssessment ||
        !candidateRecord
    ) {

        showToast(
            "Candidate session information is missing.",
            "error"
        );

        return;
    }


    const candidateRecordId =
        candidateRecord.candidate_record_id ||
        candidateRecord.id;


    if (!candidateRecordId) {

        showToast(
            "Candidate record ID is missing.",
            "error"
        );

        return;
    }


    const confirmed =
        window.confirm(
            "Are you sure you want to complete the assessment?"
        );


    if (!confirmed) {
        return;
    }


    try {

        await apiRequest(
            `/api/assessments/${encodeURIComponent(
                candidateAssessment.assessment_id
            )}/candidates/${encodeURIComponent(
                candidateRecordId
            )}/complete`,
            {
                method: "POST"
            }
        );


        stopCandidateVideoRefresh();


        const video =
            $("candidateMonitoringVideo");


        if (video) {

            video.removeAttribute(
                "src"
            );
        }


        candidateRecord = {
            ...candidateRecord,

            status:
                "COMPLETED",

            assignment_status:
                "COMPLETED"
        };


        showCandidateCompleted();


        showToast(
            "Assessment completed successfully.",
            "success"
        );


    } catch (error) {

        console.error(
            "Assessment completion failed:",
            error
        );


        showToast(
            error.message ||
            "Unable to complete assessment.",
            "error"
        );
    }
}


/* =========================================================
   COMPLETED
   ========================================================= */

function showCandidateCompleted() {

    stopCandidatePolling();
    stopCandidateVideoRefresh();
    stopCandidateCamera();


    showCandidateStep(
        "candidateCompletedStep"
    );


    const headerStatus =
        $("candidateHeaderStatus");


    if (headerStatus) {

        headerStatus.textContent =
            "Assessment Completed";
    }
}


/* =========================================================
   CANDIDATE RESET
   ========================================================= */

function resetCandidateApplication() {

    stopCandidatePolling();

    stopCandidateVideoRefresh();

    stopCandidateCamera();


    candidateAssessment =
        null;

    candidateRecord =
        null;


    if ($("candidateAccessToken")) {

        $("candidateAccessToken").value =
            "";
    }


    if ($("candidateName")) {

        $("candidateName").value =
            "";
    }


    if ($("candidateId")) {

        $("candidateId").value =
            "";
    }


    if ($("candidateAccessError")) {

        $("candidateAccessError").textContent =
            "";
    }


    const startButton =
        $("candidateStartBtn");


    if (startButton) {

        startButton.disabled =
            true;
    }


    showCandidateStep(
        "candidateAccessStep"
    );


    if ($("candidateHeaderStatus")) {

        $("candidateHeaderStatus").textContent =
            "Secure Assessment";
    }
}


/* =========================================================
   URL / ACCESS TOKEN DETECTION
   ========================================================= */

function getAssessmentTokenFromUrl() {

    const params =
        new URLSearchParams(
            window.location.search
        );


    /*
       Primary format:

       /?assessment=TOKEN
    */

    const assessment =
        params.get(
            "assessment"
        );


    if (assessment) {
        return assessment.trim();
    }


    /*
       Also support:

       /?token=TOKEN
    */

    const token =
        params.get(
            "token"
        );


    if (token) {
        return token.trim();
    }


    return "";
}


/* =========================================================
   OPEN APPLICATION
   ========================================================= */

async function initializeApplication() {

    const token =
        getAssessmentTokenFromUrl();


    /*
       If the URL contains an assessment token,
       open the candidate portal.

       Otherwise show the author application.
    */

    if (token) {

        showCandidateApplication();

        if ($("candidateAccessToken")) {

            $("candidateAccessToken").value =
                token;
        }


        await loadCandidateAssessment(
            token
        );


        return;
    }


    showAuthorApplication();
}


/* =========================================================
   AUTHOR EVENTS
   ========================================================= */

function initializeAuthorEvents() {

    document
        .querySelectorAll(".nav-item")
        .forEach(
            item => {

                item.addEventListener(
                    "click",
                    () => {

                        const page =
                            item.dataset.page;

                        if (!page) {
                            return;
                        }

                        showAuthorPage(
                            page
                        );

                    }
                );

            }
        );


    const createButton =
        $("createAssessmentBtn");


    if (createButton) {

        createButton.addEventListener(
            "click",
            () => {

                openModal(
                    "assessmentModal"
                );

            }
        );
    }


    const assessmentCreateButton =
        $("assessmentCreateBtn");


    if (assessmentCreateButton) {

        assessmentCreateButton.addEventListener(
            "click",
            () => {

                openModal(
                    "assessmentModal"
                );

            }
        );
    }


    const viewAllButton =
        $("viewAllAssessmentsBtn");


    if (viewAllButton) {

        viewAllButton.addEventListener(
            "click",
            () => {

                showAuthorPage(
                    "assessments"
                );

            }
        );
    }


    const refreshButton =
        $("refreshBtn");


    if (refreshButton) {

        refreshButton.addEventListener(
            "click",
            () => {

                if (
                    currentAuthorPage ===
                    "dashboard"
                ) {

                    loadDashboard();

                } else if (
                    currentAuthorPage ===
                    "assessments"
                ) {

                    loadAssessments();

                } else if (
                    currentAuthorPage ===
                    "requests"
                ) {

                    loadCandidateRequests();

                }

            }
        );
    }


    const refreshRequests =
        $("refreshRequestsBtn");


    if (refreshRequests) {

        refreshRequests.addEventListener(
            "click",
            () => {

                loadCandidateRequests();

            }
        );
    }


    const assessmentForm =
        $("assessmentForm");


    if (assessmentForm) {

        assessmentForm.addEventListener(
            "submit",
            submitAssessmentForm
        );
    }


    const copyLinkButton =
        $("copyAssessmentLinkBtn");


    if (copyLinkButton) {

        copyLinkButton.addEventListener(
            "click",
            () => {

                const link =
                    $("assessmentLink")?.value;

                if (link) {
                    copyText(link);
                }

            }
        );
    }


    const activateButton =
        $("activateAssessmentBtn");


    if (activateButton) {

        activateButton.addEventListener(
            "click",
            activateAssessment
        );
    }


    const deactivateButton =
        $("deactivateAssessmentBtn");


    if (deactivateButton) {

        deactivateButton.addEventListener(
            "click",
            deactivateAssessment
        );
    }


    const approveButton =
        $("approveCandidateBtn");


    if (approveButton) {

        approveButton.addEventListener(
            "click",
            approveCandidate
        );
    }


    const rejectButton =
        $("rejectCandidateBtn");


    if (rejectButton) {

        rejectButton.addEventListener(
            "click",
            rejectCandidate
        );
    }


    const saveReviewButton =
        $("saveReviewBtn");


    if (saveReviewButton) {

        saveReviewButton.addEventListener(
            "click",
            saveReviewerDecision
        );
    }
}


/* =========================================================
   CANDIDATE EVENTS
   ========================================================= */

function initializeCandidateEvents() {

    const continueButton =
        $("candidateContinueBtn");


    if (continueButton) {

        continueButton.addEventListener(
            "click",
            async () => {

                const token =
                    $("candidateAccessToken")
                        ?.value
                        .trim();


                if (!token) {

                    if ($("candidateAccessError")) {

                        $("candidateAccessError")
                            .textContent =
                            "Enter an assessment access token.";

                    }

                    return;
                }


                if ($("candidateAccessError")) {

                    $("candidateAccessError")
                        .textContent =
                        "";
                }


                await loadCandidateAssessment(
                    token
                );

            }
        );
    }


    const requestButton =
        $("candidateRequestBtn");


    if (requestButton) {

        requestButton.addEventListener(
            "click",
            requestCandidateAccess
        );
    }


    const checkButton =
        $("candidateCheckBtn");


    if (checkButton) {

        checkButton.addEventListener(
            "click",
            manualCandidateStatusCheck
        );
    }


    const enterButton =
        $("candidateEnterBtn");


    if (enterButton) {

        enterButton.addEventListener(
            "click",
            enterCandidateReadiness
        );
    }


    const startButton =
        $("candidateStartBtn");


    if (startButton) {

        startButton.addEventListener(
            "click",
            startCandidateMonitoring
        );
    }


    const completeButton =
        $("candidateCompleteBtn");


    if (completeButton) {

        completeButton.addEventListener(
            "click",
            completeCandidateAssessment
        );
    }
}


/* =========================================================
   MODAL EVENTS
   ========================================================= */

function initializeModalEvents() {

    document
        .querySelectorAll(
            "[data-close-modal]"
        )
        .forEach(
            button => {

                button.addEventListener(
                    "click",
                    () => {

                        const modalId =
                            button.dataset.closeModal;

                        if (modalId) {

                            closeModal(
                                modalId
                            );

                        }

                    }
                );

            }
        );


    document
        .querySelectorAll(
            ".modal-overlay"
        )
        .forEach(
            overlay => {

                overlay.addEventListener(
                    "click",
                    event => {

                        if (
                            event.target ===
                            overlay
                        ) {

                            overlay.classList.remove(
                                "open"
                            );

                        }

                    }
                );

            }
        );


    document.addEventListener(
        "keydown",
        event => {

            if (
                event.key !==
                "Escape"
            ) {
                return;
            }


            document
                .querySelectorAll(
                    ".modal-overlay.open"
                )
                .forEach(
                    modal => {

                        modal.classList.remove(
                            "open"
                        );

                    }
                );

        }
    );
}


/* =========================================================
   GLOBAL FUNCTIONS
   ========================================================= */

window.openModal =
    openModal;

window.closeModal =
    closeModal;

window.showAuthorPage =
    showAuthorPage;

window.openAssessmentDetails =
    openAssessmentDetails;

window.copyAssessmentToken =
    copyAssessmentToken;

window.openCandidateRequest =
    openCandidateRequest;

window.approveCandidate =
    approveCandidate;

window.rejectCandidate =
    rejectCandidate;

window.openCandidateReview =
    openCandidateReview;

window.openEvidence =
    openEvidence;

window.saveReviewerDecision =
    saveReviewerDecision;

window.showCandidateApplication =
    showCandidateApplication;

window.showAuthorApplication =
    showAuthorApplication;

window.resetCandidateApplication =
    resetCandidateApplication;


/* =========================================================
   DOM READY
   ========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    async () => {

        initializeAuthorEvents();

        initializeCandidateEvents();

        initializeModalEvents();


        await initializeApplication();

    }
);


/* =========================================================
   CLEANUP
   ========================================================= */

window.addEventListener(
    "beforeunload",
    () => {

        stopCandidatePolling();

        stopCandidateVideoRefresh();

        stopCandidateCamera();

    }
);


console.log(
    "%cMonitorAI%c frontend initialized.",
    "font-weight:700;color:#60a5fa;",
    ""
);