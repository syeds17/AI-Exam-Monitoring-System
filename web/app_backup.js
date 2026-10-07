/* ============================================================
   MonitorAI - Assessment Monitoring Frontend
   ============================================================ */

"use strict";

/* ============================================================
   GLOBAL STATE
   ============================================================ */

const state = {
    assessments: [],
    selectedAssessment: null,

    selectedCandidate: null,
    selectedCandidateAssessment: null,

    reviewData: null,

    candidateSession: {
        assessmentId: null,
        candidateRecordId: null,
        accessCode: null,
        accessToken: null,
        candidateName: null,
        candidateId: null
    },

    currentPage: "dashboard",

    refreshTimer: null,
    candidateTimer: null,
    liveTimer: null
};


/* ============================================================
   API HELPER
   ============================================================ */

async function api(url, options = {}) {
    const config = {
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {})
        },
        ...options
    };

    try {
        const response = await fetch(url, config);

        let data = null;

        const contentType = response.headers.get("content-type") || "";

        if (contentType.includes("application/json")) {
            data = await response.json();
        } else {
            const text = await response.text();

            try {
                data = JSON.parse(text);
            } catch {
                data = text;
            }
        }

        if (!response.ok) {
            let message = "Request failed.";

            if (data && typeof data === "object") {
                message =
                    data.detail ||
                    data.message ||
                    data.error ||
                    message;
            } else if (typeof data === "string" && data.trim()) {
                message = data;
            }

            throw new Error(message);
        }

        return data;

    } catch (error) {

        console.error("API Error:", url, error);

        throw error;
    }
}


/* ============================================================
   DOM HELPERS
   ============================================================ */

function $(id) {
    return document.getElementById(id);
}


function show(element) {
    if (!element) return;

    element.classList.remove("hidden");
}


function hide(element) {
    if (!element) return;

    element.classList.add("hidden");
}


function setText(element, value) {
    if (!element) return;

    element.textContent =
        value === null ||
        value === undefined ||
        value === ""
            ? "—"
            : String(value);
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


function formatDate(value) {
    if (!value) return "—";

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return date.toLocaleString();
}


function formatDateShort(value) {
    if (!value) return "—";

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return date.toLocaleDateString();
}


function formatDuration(seconds) {
    if (
        seconds === null ||
        seconds === undefined ||
        Number.isNaN(Number(seconds))
    ) {
        return "—";
    }

    const total = Math.round(Number(seconds));

    const minutes = Math.floor(total / 60);
    const remaining = total % 60;

    if (minutes <= 0) {
        return `${remaining}s`;
    }

    return `${minutes}m ${remaining}s`;
}


function normalizeStatus(status) {
    if (!status) return "UNKNOWN";

    return String(status)
        .trim()
        .toUpperCase()
        .replace(/\s+/g, "_");
}


function statusClass(status) {
    const normalized = normalizeStatus(status);

    if (
        normalized === "ACTIVE" ||
        normalized === "AUTHORIZED" ||
        normalized === "COMPLETED" ||
        normalized === "APPROVED" ||
        normalized === "NOT_CHEATING"
    ) {
        return "success";
    }

    if (
        normalized === "READY" ||
        normalized === "PENDING" ||
        normalized === "NEEDS_REVIEW" ||
        normalized === "IN_PROGRESS" ||
        normalized === "REQUESTED"
    ) {
        return "warning";
    }

    if (
        normalized === "REJECTED" ||
        normalized === "DEACTIVATED" ||
        normalized === "CHEATING"
    ) {
        return "danger";
    }

    return "neutral";
}


function statusPill(status) {
    const normalized = normalizeStatus(status);

    return `
        <span class="status-pill ${statusClass(normalized)}">
            ${escapeHtml(normalized.replace(/_/g, " "))}
        </span>
    `;
}


/* ============================================================
   TOAST
   ============================================================ */

function toast(message, type = "info") {
    const container = $("toast");
    const messageElement = $("toastMessage");

    if (!container || !messageElement) {
        console.log(`[${type}] ${message}`);
        return;
    }

    messageElement.textContent = message;

    container.classList.remove(
        "success",
        "error",
        "warning",
        "info"
    );

    container.classList.add(type);

    show(container);

    window.clearTimeout(toast._timer);

    toast._timer = window.setTimeout(() => {
        hide(container);
    }, 3500);
}


/* ============================================================
   PAGE NAVIGATION
   ============================================================ */

function navigate(page) {
    const pages = document.querySelectorAll(".page");

    pages.forEach(pageElement => {
        pageElement.classList.remove("active-page");
    });

    const target = $(`${page}Page`);

    if (target) {
        target.classList.add("active-page");
    }

    document.querySelectorAll(".nav-item").forEach(item => {
        item.classList.remove("active");

        if (item.dataset.page === page) {
            item.classList.add("active");
        }
    });

    state.currentPage = page;

    updatePageHeader(page);

    if (page === "dashboard") {
        loadDashboard();
    }

    if (page === "assessments") {
        loadAssessments();
    }

    if (page === "requests") {
        loadRequests();
    }

    if (page === "live") {
        loadLiveMonitoring();
    }
}


function updatePageHeader(page) {
    const title = $("pageTitle");
    const subtitle = $("pageSubtitle");

    const content = {
        dashboard: {
            title: "Dashboard",
            subtitle: "Overview of your monitored assessments."
        },

        assessments: {
            title: "Assessments",
            subtitle: "Create and manage assessment monitoring sessions."
        },

        requests: {
            title: "Candidate Requests",
            subtitle: "Review candidates requesting assessment access."
        },

        live: {
            title: "Live Monitoring",
            subtitle: "Monitor candidates currently taking assessments."
        },

        candidate: {
            title: "Candidate Portal",
            subtitle: "Assessment access and monitoring."
        }
    };

    const data = content[page] || content.dashboard;

    setText(title, data.title);
    setText(subtitle, data.subtitle);
}


/* ============================================================
   MODAL HELPERS
   ============================================================ */

function openModal(id) {
    const modal = $(id);

    if (!modal) return;

    show(modal);

    document.body.classList.add("modal-open");
}


function closeModal(id) {
    const modal = $(id);

    if (!modal) return;

    hide(modal);

    document.body.classList.remove("modal-open");
}


/* ============================================================
   CREATE ASSESSMENT
   ============================================================ */

function openCreateAssessmentModal() {
    const form = $("createAssessmentForm");

    if (form) {
        form.reset();

        if ($("candidateLimit")) {
            $("candidateLimit").value = 50;
        }

        if ($("durationMinutes")) {
            $("durationMinutes").value = 60;
        }
    }

    hide($("createAssessmentMessage"));

    openModal("createAssessmentModal");
}


function closeCreateAssessmentModal() {
    closeModal("createAssessmentModal");
}


async function createAssessment(event) {
    event.preventDefault();

    const name = $("assessmentName")?.value.trim();

    if (!name) {
        showFormMessage(
            "createAssessmentMessage",
            "Assessment name is required.",
            "error"
        );

        return;
    }

    const payload = {
        assessment_name: name,

        organization:
            $("organization")?.value.trim() || "",

        assessment_type:
            $("assessmentType")?.value || "Other",

        scheduled_at:
            $("scheduledAt")?.value || null,

        duration_minutes:
            Number($("durationMinutes")?.value || 60),

        candidate_limit:
            Number($("candidateLimit")?.value || 50)
    };

    try {

        const submitButton =
            document.querySelector(
                "#createAssessmentForm button[type='submit']"
            );

        if (submitButton) {
            submitButton.disabled = true;
            submitButton.textContent = "Creating...";
        }

        const response = await api(
            "/api/assessments",
            {
                method: "POST",
                body: JSON.stringify(payload)
            }
        );

        console.log("Assessment created:", response);

        closeCreateAssessmentModal();

        toast(
            "Assessment created successfully.",
            "success"
        );

        await loadAssessments();

        navigate("assessments");

    } catch (error) {

        showFormMessage(
            "createAssessmentMessage",
            error.message,
            "error"
        );

    } finally {

        const submitButton =
            document.querySelector(
                "#createAssessmentForm button[type='submit']"
            );

        if (submitButton) {
            submitButton.disabled = false;
            submitButton.textContent = "Create Assessment";
        }
    }
}


/* ============================================================
   LOAD ASSESSMENTS
   ============================================================ */

async function loadAssessments() {
    const container = $("assessmentsList");

    if (container) {
        container.innerHTML = `
            <div class="loading-state">
                Loading assessments...
            </div>
        `;
    }

    try {

        const response = await api(
            "/api/assessments"
        );

        const assessments =
            extractArray(response, [
                "assessments",
                "data",
                "items"
            ]);

        state.assessments = assessments;

        renderAssessments(assessments);

        renderRecentAssessments(assessments);

        updateDashboardStats(assessments);

        await updateRequestBadge();

    } catch (error) {

        console.error(error);

        if (container) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">!</div>

                    <h3>
                        Unable to load assessments
                    </h3>

                    <p>
                        ${escapeHtml(error.message)}
                    </p>

                    <button
                        class="primary-btn"
                        onclick="loadAssessments()"
                    >
                        Retry
                    </button>
                </div>
            `;
        }
    }
}


/* ============================================================
   ARRAY EXTRACTION
   ============================================================ */

function extractArray(response, possibleKeys = []) {

    if (Array.isArray(response)) {
        return response;
    }

    if (!response || typeof response !== "object") {
        return [];
    }

    for (const key of possibleKeys) {

        if (Array.isArray(response[key])) {
            return response[key];
        }
    }

    return [];
}


/* ============================================================
   DASHBOARD
   ============================================================ */

async function loadDashboard() {
    await loadAssessments();
}


function updateDashboardStats(assessments) {

    const total = assessments.length;

    const active = assessments.filter(
        assessment =>
            normalizeStatus(assessment.status) === "ACTIVE"
    ).length;

    let authorized = 0;
    let monitoring = 0;

    assessments.forEach(assessment => {

        const counts =
            assessment.candidate_counts ||
            assessment.counts ||
            {};

        authorized += Number(
            counts.authorized ||
            counts.accepted ||
            assessment.authorized_candidates ||
            0
        );

        monitoring += Number(
            counts.active ||
            counts.in_progress ||
            assessment.active_candidates ||
            0
        );
    });

    setText(
        $("statTotalAssessments"),
        total
    );

    setText(
        $("statActiveAssessments"),
        active
    );

    setText(
        $("statAuthorizedCandidates"),
        authorized
    );

    setText(
        $("statMonitoringCandidates"),
        monitoring
    );
}


/* ============================================================
   ASSESSMENT CARD
   ============================================================ */

function renderRecentAssessments(assessments) {

    const container = $("recentAssessments");

    if (!container) return;

    if (!assessments.length) {

        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">▣</div>

                <h3>
                    No assessments yet
                </h3>

                <p>
                    Create your first assessment to get started.
                </p>

                <button
                    class="primary-btn"
                    onclick="openCreateAssessmentModal()"
                >
                    Create Assessment
                </button>
            </div>
        `;

        return;
    }

    const recent = assessments.slice(0, 6);

    container.innerHTML =
        recent.map(createAssessmentCard).join("");
}


function createAssessmentCard(assessment) {

    const id =
        assessment.assessment_id ||
        assessment.id ||
        "";

    const name =
        assessment.assessment_name ||
        assessment.name ||
        "Untitled Assessment";

    const organization =
        assessment.organization ||
        "—";

    const type =
        assessment.assessment_type ||
        "Other";

    const status =
        normalizeStatus(assessment.status || "READY");

    const limit =
        assessment.candidate_limit ||
        50;

    return `
        <div class="assessment-card">

            <div class="assessment-card-top">

                <div class="assessment-type-icon">
                    ▣
                </div>

                ${statusPill(status)}

            </div>


            <h3>
                ${escapeHtml(name)}
            </h3>


            <p class="assessment-organization">
                ${escapeHtml(organization)}
            </p>


            <div class="assessment-meta">

                <span>
                    ${escapeHtml(type)}
                </span>

                <span>
                    ${limit} candidates
                </span>

            </div>


            <div class="assessment-card-footer">

                <button
                    class="secondary-btn"
                    onclick="openAssessmentDetails('${escapeHtml(id)}')"
                >
                    Manage
                </button>


                <button
                    class="primary-btn"
                    onclick="openAssessmentCandidates('${escapeHtml(id)}')"
                >
                    Candidates
                </button>

            </div>

        </div>
    `;
}


/* ============================================================
   ASSESSMENTS LIST
   ============================================================ */

function renderAssessments(assessments) {

    const container = $("assessmentsList");

    if (!container) return;

    if (!assessments.length) {

        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">▣</div>

                <h3>
                    No assessments found
                </h3>

                <p>
                    Create an assessment to begin.
                </p>

                <button
                    class="primary-btn"
                    onclick="openCreateAssessmentModal()"
                >
                    + Create Assessment
                </button>
            </div>
        `;

        return;
    }

    container.innerHTML = assessments.map(
        assessment => {

            const id =
                assessment.assessment_id ||
                assessment.id;

            const name =
                assessment.assessment_name ||
                assessment.name ||
                "Untitled Assessment";

            const status =
                normalizeStatus(
                    assessment.status || "READY"
                );

            const organization =
                assessment.organization ||
                "—";

            const scheduled =
                assessment.scheduled_at;

            const duration =
                assessment.duration_minutes ||
                "—";

            const limit =
                assessment.candidate_limit ||
                50;

            return `
                <div class="assessment-row">

                    <div class="assessment-row-main">

                        <div class="assessment-type-icon">
                            ▣
                        </div>

                        <div>

                            <h3>
                                ${escapeHtml(name)}
                            </h3>

                            <p>
                                ${escapeHtml(organization)}
                            </p>

                        </div>

                    </div>


                    <div class="assessment-row-info">

                        <div>
                            <span>Status</span>
                            ${statusPill(status)}
                        </div>

                        <div>
                            <span>Schedule</span>
                            <strong>
                                ${escapeHtml(
                                    formatDate(scheduled)
                                )}
                            </strong>
                        </div>

                        <div>
                            <span>Duration</span>
                            <strong>
                                ${escapeHtml(
                                    duration
                                )} min
                            </strong>
                        </div>

                        <div>
                            <span>Candidate Limit</span>
                            <strong>
                                ${escapeHtml(
                                    limit
                                )}
                            </strong>
                        </div>

                    </div>


                    <div class="assessment-row-actions">

                        <button
                            class="secondary-btn"
                            onclick="openAssessmentDetails('${escapeHtml(id)}')"
                        >
                            Details
                        </button>

                        <button
                            class="secondary-btn"
                            onclick="openAssessmentCandidates('${escapeHtml(id)}')"
                        >
                            Candidates
                        </button>

                    </div>

                </div>
            `;
        }
    ).join("");
}


/* ============================================================
   ASSESSMENT DETAILS
   ============================================================ */

async function openAssessmentDetails(assessmentId) {

    openModal("assessmentDetailsModal");

    const content = $("assessmentDetailsContent");

    if (content) {
        content.innerHTML = `
            <div class="loading-state">
                Loading assessment...
            </div>
        `;
    }

    try {

        const response = await api(
            `/api/assessments/${encodeURIComponent(assessmentId)}`
        );

        const assessment =
            response.assessment ||
            response.data ||
            response;

        state.selectedAssessment = assessment;

        renderAssessmentDetails(assessment);

    } catch (error) {

        if (content) {
            content.innerHTML = `
                <div class="empty-state compact">
                    <h3>
                        Unable to load assessment
                    </h3>

                    <p>
                        ${escapeHtml(error.message)}
                    </p>
                </div>
            `;
        }
    }
}


function renderAssessmentDetails(assessment) {

    const content = $("assessmentDetailsContent");

    if (!content) return;

    const id =
        assessment.assessment_id ||
        assessment.id ||
        "—";

    const name =
        assessment.assessment_name ||
        assessment.name ||
        "Untitled";

    const status =
        normalizeStatus(
            assessment.status || "READY"
        );

    const token =
        assessment.access_token ||
        assessment.token ||
        "";

    const organization =
        assessment.organization ||
        "—";

    const type =
        assessment.assessment_type ||
        "Other";

    const duration =
        assessment.duration_minutes ||
        "—";

    const limit =
        assessment.candidate_limit ||
        50;

    const scheduled =
        assessment.scheduled_at;

    content.innerHTML = `
        <div class="detail-grid">

            <div class="detail-item">
                <span>Assessment ID</span>
                <strong>
                    ${escapeHtml(id)}
                </strong>
            </div>

            <div class="detail-item">
                <span>Status</span>
                <strong>
                    ${statusPill(status)}
                </strong>
            </div>

            <div class="detail-item">
                <span>Assessment Name</span>
                <strong>
                    ${escapeHtml(name)}
                </strong>
            </div>

            <div class="detail-item">
                <span>Organization</span>
                <strong>
                    ${escapeHtml(organization)}
                </strong>
            </div>

            <div class="detail-item">
                <span>Assessment Type</span>
                <strong>
                    ${escapeHtml(type)}
                </strong>
            </div>

            <div class="detail-item">
                <span>Scheduled</span>
                <strong>
                    ${escapeHtml(
                        formatDate(scheduled)
                    )}
                </strong>
            </div>

            <div class="detail-item">
                <span>Duration</span>
                <strong>
                    ${escapeHtml(duration)} minutes
                </strong>
            </div>

            <div class="detail-item">
                <span>Candidate Limit</span>
                <strong>
                    ${escapeHtml(limit)}
                </strong>
            </div>

        </div>


        ${
            token
                ? `
                    <div class="access-link-box">

                        <span>
                            Candidate Assessment Token
                        </span>

                        <code>
                            ${escapeHtml(token)}
                        </code>

                        <button
                            class="secondary-btn"
                            onclick="copyText('${escapeHtml(token)}')"
                        >
                            Copy
                        </button>

                    </div>
                `
                : ""
        }


        <div class="detail-actions">

            <button
                class="secondary-btn"
                onclick="openAssessmentCandidates('${escapeHtml(id)}')"
            >
                Manage Candidates
            </button>

            ${
                status === "ACTIVE"
                    ? `
                        <button
                            class="danger-outline-btn"
                            onclick="deactivateAssessment('${escapeHtml(id)}')"
                        >
                            Deactivate
                        </button>
                    `
                    : `
                        <button
                            class="primary-btn"
                            onclick="activateAssessment('${escapeHtml(id)}')"
                        >
                            Activate Assessment
                        </button>
                    `
            }

        </div>
    `;

    const footerButton = $("detailsActivateBtn");

    if (footerButton) {

        if (status === "ACTIVE") {

            footerButton.textContent =
                "Deactivate Assessment";

            footerButton.className =
                "danger-outline-btn";

            footerButton.onclick = () =>
                deactivateAssessment(id);

        } else {

            footerButton.textContent =
                "Activate Assessment";

            footerButton.className =
                "primary-btn";

            footerButton.onclick = () =>
                activateAssessment(id);
        }
    }
}


/* ============================================================
   ACTIVATE / DEACTIVATE
   ============================================================ */

async function activateAssessment(assessmentId) {

    try {

        await api(
            `/api/assessments/${encodeURIComponent(assessmentId)}/activate`,
            {
                method: "POST"
            }
        );

        toast(
            "Assessment activated.",
            "success"
        );

        closeModal("assessmentDetailsModal");

        await loadAssessments();

    } catch (error) {

        toast(
            error.message,
            "error"
        );
    }
}


async function deactivateAssessment(assessmentId) {

    const confirmed =
        window.confirm(
            "Deactivate this assessment?"
        );

    if (!confirmed) return;

    try {

        await api(
            `/api/assessments/${encodeURIComponent(assessmentId)}/deactivate`,
            {
                method: "POST"
            }
        );

        toast(
            "Assessment deactivated.",
            "success"
        );

        closeModal("assessmentDetailsModal");

        await loadAssessments();

    } catch (error) {

        toast(
            error.message,
            "error"
        );
    }
}


/* ============================================================
   CANDIDATES
   ============================================================ */

async function openAssessmentCandidates(assessmentId) {

    state.selectedCandidateAssessment =
        assessmentId;

    navigate("requests");

    await loadCandidatesForAssessment(
        assessmentId
    );
}


async function loadCandidatesForAssessment(
    assessmentId
) {

    const container = $("requestsList");

    if (!container) return;

    container.innerHTML = `
        <div class="loading-state">
            Loading candidates...
        </div>
    `;

    try {

        const response = await api(
            `/api/assessments/${encodeURIComponent(assessmentId)}/candidates`
        );

        const candidates =
            extractArray(response, [
                "candidates",
                "data",
                "items"
            ]);

        renderCandidateRequests(
            candidates,
            assessmentId
        );

    } catch (error) {

        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">!</div>

                <h3>
                    Unable to load candidates
                </h3>

                <p>
                    ${escapeHtml(error.message)}
                </p>
            </div>
        `;
    }
}


async function loadRequests() {

    if (
        state.selectedCandidateAssessment
    ) {

        await loadCandidatesForAssessment(
            state.selectedCandidateAssessment
        );

        return;
    }

    const container = $("requestsList");

    if (!container) return;

    container.innerHTML = `
        <div class="loading-state">
            Loading candidate requests...
        </div>
    `;

    try {

        await loadAssessments();

        const allCandidates = [];

        for (const assessment of state.assessments) {

            const assessmentId =
                assessment.assessment_id ||
                assessment.id;

            if (!assessmentId) continue;

            try {

                const response = await api(
                    `/api/assessments/${encodeURIComponent(assessmentId)}/candidates`
                );

                const candidates =
                    extractArray(response, [
                        "candidates",
                        "data",
                        "items"
                    ]);

                candidates.forEach(candidate => {

                    allCandidates.push({
                        ...candidate,
                        assessment_id:
                            assessmentId,
                        assessment_name:
                            assessment.assessment_name ||
                            assessment.name ||
                            "Assessment"
                    });

                });

            } catch (error) {

                console.warn(
                    "Unable to load candidates for",
                    assessmentId,
                    error
                );
            }
        }

        renderCandidateRequests(
            allCandidates,
            null
        );

        updateRequestBadgeFromCandidates(
            allCandidates
        );

    } catch (error) {

        container.innerHTML = `
            <div class="empty-state">
                <h3>
                    Unable to load requests
                </h3>

                <p>
                    ${escapeHtml(error.message)}
                </p>
            </div>
        `;
    }
}


/* ============================================================
   RENDER CANDIDATE REQUESTS
   ============================================================ */

function renderCandidateRequests(
    candidates,
    assessmentId
) {

    const container = $("requestsList");

    if (!container) return;

    if (!candidates.length) {

        container.innerHTML = `
            <div class="empty-state compact">

                <div class="empty-icon">
                    ♙
                </div>

                <h3>
                    No candidate requests
                </h3>

                <p>
                    Candidate access requests will appear here.
                </p>

            </div>
        `;

        return;
    }

    const pending = candidates.filter(
        candidate => {

            const status =
                normalizeStatus(
                    candidate.assignment_status ||
                    candidate.status ||
                    "PENDING"
                );

            return (
                status === "PENDING" ||
                status === "REQUESTED"
            );
        }
    );

    const others = candidates.filter(
        candidate => !pending.includes(candidate)
    );

    container.innerHTML = `

        ${
            pending.length
                ? `
                    <div class="requests-section">

                        <div class="section-header">
                            <div>
                                <h3>
                                    Pending Requests
                                </h3>

                                <p>
                                    Candidates waiting for authorization.
                                </p>
                            </div>
                        </div>

                        <div class="candidate-request-grid">

                            ${pending.map(
                                candidate =>
                                    createCandidateRequestCard(
                                        candidate,
                                        assessmentId
                                    )
                            ).join("")}

                        </div>

                    </div>
                `
                : ""
        }


        ${
            others.length
                ? `
                    <div class="requests-section">

                        <div class="section-header">
                            <div>
                                <h3>
                                    Candidate Status
                                </h3>

                                <p>
                                    Previously processed candidates.
                                </p>
                            </div>
                        </div>

                        <div class="candidate-request-grid">

                            ${others.map(
                                candidate =>
                                    createCandidateRequestCard(
                                        candidate,
                                        assessmentId
                                    )
                            ).join("")}

                        </div>

                    </div>
                `
                : ""
        }
    `;
}


function createCandidateRequestCard(
    candidate,
    assessmentId
) {

    const candidateRecordId =
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
        normalizeStatus(
            candidate.assignment_status ||
            candidate.status ||
            "PENDING"
        );

    const assessmentName =
        candidate.assessment_name ||
        "";

    const effectiveAssessmentId =
        assessmentId ||
        candidate.assessment_id ||
        "";

    const accessCode =
        candidate.access_code ||
        "";

    const isPending =
        status === "PENDING" ||
        status === "REQUESTED";

    return `
        <div class="candidate-card-row">

            <div class="candidate-avatar">
                ${escapeHtml(
                    name.charAt(0).toUpperCase()
                )}
            </div>


            <div class="candidate-info">

                <h3>
                    ${escapeHtml(name)}
                </h3>

                <p>
                    Candidate ID:
                    ${escapeHtml(candidateId)}
                </p>

                ${
                    assessmentName
                        ? `
                            <small>
                                ${escapeHtml(
                                    assessmentName
                                )}
                            </small>
                        `
                        : ""
                }

            </div>


            <div class="candidate-status">

                ${statusPill(status)}

                ${
                    accessCode
                        ? `
                            <small>
                                Code:
                                ${escapeHtml(accessCode)}
                            </small>
                        `
                        : ""
                }

            </div>


            <div class="candidate-actions">

                ${
                    isPending
                        ? `
                            <button
                                class="primary-btn"
                                onclick="openCandidateRequest(
                                    '${escapeHtml(effectiveAssessmentId)}',
                                    '${escapeHtml(candidateRecordId)}'
                                )"
                            >
                                Review Request
                            </button>
                        `
                        : `
                            <button
                                class="secondary-btn"
                                onclick="openCandidateReview(
                                    '${escapeHtml(effectiveAssessmentId)}',
                                    '${escapeHtml(candidateRecordId)}'
                                )"
                            >
                                Review
                            </button>
                        `
                }

            </div>

        </div>
    `;
}


/* ============================================================
   REQUEST BADGE
   ============================================================ */

async function updateRequestBadge() {

    try {

        const allCandidates = [];

        for (const assessment of state.assessments) {

            const assessmentId =
                assessment.assessment_id ||
                assessment.id;

            if (!assessmentId) continue;

            try {

                const response = await api(
                    `/api/assessments/${encodeURIComponent(assessmentId)}/candidates`
                );

                const candidates =
                    extractArray(response, [
                        "candidates",
                        "data",
                        "items"
                    ]);

                candidates.forEach(candidate => {
                    allCandidates.push(candidate);
                });

            } catch {
                // Ignore individual assessment failure.
            }
        }

        updateRequestBadgeFromCandidates(
            allCandidates
        );

    } catch (error) {

        console.warn(
            "Request badge error:",
            error
        );
    }
}


function updateRequestBadgeFromCandidates(
    candidates
) {

    const pending = candidates.filter(
        candidate => {

            const status =
                normalizeStatus(
                    candidate.assignment_status ||
                    candidate.status ||
                    ""
                );

            return (
                status === "PENDING" ||
                status === "REQUESTED"
            );
        }
    ).length;

    const badge = $("requestBadge");

    if (!badge) return;

    if (pending > 0) {
        badge.textContent = pending;
        show(badge);
    } else {
        hide(badge);
    }
}


/* ============================================================
   CANDIDATE REQUEST DETAILS
   ============================================================ */

async function openCandidateRequest(
    assessmentId,
    candidateRecordId
) {

    state.selectedCandidate = {
        assessmentId,
        candidateRecordId
    };

    openModal(
        "candidateRequestModal"
    );

    const content =
        $("candidateRequestContent");

    if (content) {
        content.innerHTML = `
            <div class="loading-state">
                Loading candidate...
            </div>
        `;
    }

    try {

        const response = await api(
            `/api/assessments/${encodeURIComponent(assessmentId)}/candidates`
        );

        const candidates =
            extractArray(response, [
                "candidates",
                "data",
                "items"
            ]);

        const candidate =
            candidates.find(
                item =>
                    String(
                        item.candidate_record_id ||
                        item.id
                    ) === String(candidateRecordId)
            );

        if (!candidate) {
            throw new Error(
                "Candidate record not found."
            );
        }

        state.selectedCandidate.data =
            candidate;

        renderCandidateRequestDetails(
            candidate,
            assessmentId,
            candidateRecordId
        );

    } catch (error) {

        if (content) {
            content.innerHTML = `
                <div class="empty-state compact">
                    <h3>
                        Unable to load candidate
                    </h3>

                    <p>
                        ${escapeHtml(error.message)}
                    </p>
                </div>
            `;
        }
    }
}


function renderCandidateRequestDetails(
    candidate,
    assessmentId,
    candidateRecordId
) {

    const content =
        $("candidateRequestContent");

    if (!content) return;

    const name =
        candidate.candidate_name ||
        candidate.name ||
        "Unknown";

    const candidateId =
        candidate.candidate_id ||
        "—";

    const status =
        normalizeStatus(
            candidate.assignment_status ||
            candidate.status ||
            "PENDING"
        );

    content.innerHTML = `
        <div class="detail-grid">

            <div class="detail-item">
                <span>Candidate Name</span>

                <strong>
                    ${escapeHtml(name)}
                </strong>
            </div>


            <div class="detail-item">
                <span>Candidate ID</span>

                <strong>
                    ${escapeHtml(candidateId)}
                </strong>
            </div>


            <div class="detail-item">
                <span>Assignment Status</span>

                <strong>
                    ${statusPill(status)}
                </strong>
            </div>


            <div class="detail-item">
                <span>Requested</span>

                <strong>
                    ${escapeHtml(
                        formatDate(
                            candidate.created_at ||
                            candidate.requested_at
                        )
                    )}
                </strong>
            </div>

        </div>
    `;

    const approve =
        $("approveCandidateBtn");

    const reject =
        $("rejectCandidateBtn");

    const isPending =
        status === "PENDING" ||
        status === "REQUESTED";

    if (approve) {
        approve.disabled = !isPending;

        approve.onclick = () =>
            approveCandidate(
                assessmentId,
                candidateRecordId
            );
    }

    if (reject) {
        reject.disabled = !isPending;

        reject.onclick = () =>
            rejectCandidate(
                assessmentId,
                candidateRecordId
            );
    }
}


/* ============================================================
   APPROVE / REJECT
   ============================================================ */

async function approveCandidate(
    assessmentId,
    candidateRecordId
) {

    try {

        const response = await api(
            `/api/assessments/${encodeURIComponent(assessmentId)}/candidates/${encodeURIComponent(candidateRecordId)}/approve`,
            {
                method: "POST"
            }
        );

        const accessCode =
            response.access_code ||
            response.data?.access_code ||
            response.candidate?.access_code ||
            "";

        closeModal(
            "candidateRequestModal"
        );

        toast(
            accessCode
                ? `Candidate approved. Access code: ${accessCode}`
                : "Candidate approved successfully.",
            "success"
        );

        await loadCandidatesForAssessment(
            assessmentId
        );

    } catch (error) {

        toast(
            error.message,
            "error"
        );
    }
}


async function rejectCandidate(
    assessmentId,
    candidateRecordId
) {

    const confirmed =
        window.confirm(
            "Reject this candidate's access request?"
        );

    if (!confirmed) return;

    try {

        await api(
            `/api/assessments/${encodeURIComponent(assessmentId)}/candidates/${encodeURIComponent(candidateRecordId)}/reject`,
            {
                method: "POST"
            }
        );

        closeModal(
            "candidateRequestModal"
        );

        toast(
            "Candidate request rejected.",
            "success"
        );

        await loadCandidatesForAssessment(
            assessmentId
        );

    } catch (error) {

        toast(
            error.message,
            "error"
        );
    }
}


/* ============================================================
   CANDIDATE REVIEW
   ============================================================ */

async function openCandidateReview(
    assessmentId,
    candidateRecordId
) {

    state.selectedCandidate = {
        assessmentId,
        candidateRecordId
    };

    openModal(
        "candidateReviewModal"
    );

    const content =
        $("candidateReviewContent");

    if (content) {
        content.innerHTML = `
            <div class="loading-state">
                Loading monitoring review...
            </div>
        `;
    }

    try {

        const response = await api(
            `/api/assessments/${encodeURIComponent(assessmentId)}/candidates/${encodeURIComponent(candidateRecordId)}/review`
        );

        state.reviewData =
            response.data ||
            response;

        renderCandidateReview(
            state.reviewData
        );

    } catch (error) {

        if (content) {
            content.innerHTML = `
                <div class="empty-state compact">

                    <h3>
                        Unable to load review
                    </h3>

                    <p>
                        ${escapeHtml(error.message)}
                    </p>

                </div>
            `;
        }
    }
}


function renderCandidateReview(data) {

    const content =
        $("candidateReviewContent");

    if (!content) return;

    const candidate =
        data.candidate ||
        {};

    const session =
        data.session ||
        null;

    const events =
        Array.isArray(data.events)
            ? data.events
            : [];

    const name =
        candidate.candidate_name ||
        candidate.name ||
        "Unknown Candidate";

    const candidateId =
        candidate.candidate_id ||
        "—";

    const decision =
        candidate.reviewer_decision ||
        "";

    const notes =
        candidate.reviewer_notes ||
        "";

    if ($("reviewDecision")) {
        $("reviewDecision").value =
            decision;
    }

    if ($("reviewNotes")) {
        $("reviewNotes").value =
            notes;
    }

    const sessionId =
        session?.session_id ||
        "—";

    content.innerHTML = `

        <div class="review-summary">

            <div class="review-candidate">

                <div class="candidate-avatar large">
                    ${escapeHtml(
                        name.charAt(0).toUpperCase()
                    )}
                </div>

                <div>

                    <h3>
                        ${escapeHtml(name)}
                    </h3>

                    <p>
                        Candidate ID:
                        ${escapeHtml(candidateId)}
                    </p>

                </div>

            </div>


            <div class="review-session">

                <span>Session</span>

                <strong>
                    ${escapeHtml(sessionId)}
                </strong>

            </div>

        </div>


        <div class="review-event-summary">

            <div>
                <span>Total Events</span>
                <strong>
                    ${events.length}
                </strong>
            </div>

            <div>
                <span>Session Started</span>
                <strong>
                    ${escapeHtml(
                        formatDate(
                            session?.created_at
                        )
                    )}
                </strong>
            </div>

            <div>
                <span>Current Decision</span>
                <strong>
                    ${
                        decision
                            ? statusPill(decision)
                            : "Not reviewed"
                    }
                </strong>
            </div>

        </div>


        <div class="review-events">

            <div class="section-header">

                <div>

                    <h3>
                        Monitoring Events
                    </h3>

                    <p>
                        AI-detected observable monitoring events.
                    </p>

                </div>

            </div>


            ${
                events.length
                    ? `
                        <div class="event-list">

                            ${events.map(
                                event =>
                                    createReviewEvent(
                                        event
                                    )
                            ).join("")}

                        </div>
                    `
                    : `
                        <div class="empty-state compact">

                            <div class="empty-icon">
                                ✓
                            </div>

                            <h3>
                                No monitoring events
                            </h3>

                            <p>
                                No persisted monitoring events were
                                recorded for this session.
                            </p>

                        </div>
                    `
            }

        </div>
    `;
}


function createReviewEvent(event) {

    const eventId =
        event.id ||
        "";

    const eventType =
        event.event_type ||
        "UNKNOWN_EVENT";

    const direction =
        event.direction ||
        "";

    const timestamp =
        event.timestamp ||
        "";

    const duration =
        event.duration;

    const evidence =
        event.evidence_path ||
        "";

    let evidenceButton = "";

    if (
        evidence &&
        event.session_id
    ) {

        const filename =
            evidence.split(/[\\/]/).pop();

        evidenceButton = `
            <button
                class="secondary-btn small-btn"
                onclick="openEvidence(
                    '${escapeHtml(
                        event.session_id
                    )}',
                    '${escapeHtml(
                        filename
                    )}',
                    '${escapeHtml(
                        eventType
                    )}',
                    '${escapeHtml(
                        direction
                    )}',
                    '${escapeHtml(
                        timestamp
                    )}'
                )"
            >
                View Evidence
            </button>
        `;
    }

    return `
        <div class="event-row">

            <div class="event-indicator">
                !
            </div>


            <div class="event-main">

                <strong>
                    ${escapeHtml(
                        eventType.replace(
                            /_/g,
                            " "
                        )
                    )}
                </strong>

                <span>
                    ${escapeHtml(
                        formatDate(timestamp)
                    )}
                </span>

            </div>


            <div class="event-details">

                ${
                    direction
                        ? `
                            <span>
                                Direction:
                                ${escapeHtml(
                                    direction
                                )}
                            </span>
                        `
                        : ""
                }

                ${
                    duration !== null &&
                    duration !== undefined
                        ? `
                            <span>
                                Duration:
                                ${escapeHtml(
                                    formatDuration(
                                        duration
                                    )
                                )}
                            </span>
                        `
                        : ""
                }

            </div>


            <div class="event-actions">

                ${evidenceButton}

            </div>

        </div>
    `;
}


/* ============================================================
   SAVE REVIEW
   ============================================================ */

async function saveCandidateReview() {

    const selected =
        state.selectedCandidate;

    if (!selected) {
        toast(
            "No candidate selected.",
            "error"
        );

        return;
    }

    const decision =
        $("reviewDecision")?.value || "";

    const notes =
        $("reviewNotes")?.value.trim() || "";

    if (!decision) {

        toast(
            "Please select a reviewer decision.",
            "warning"
        );

        return;
    }

    try {

        const button =
            $("saveCandidateReviewBtn");

        if (button) {
            button.disabled = true;
            button.textContent = "Saving...";
        }

        await api(
            `/api/assessments/${encodeURIComponent(selected.assessmentId)}/candidates/${encodeURIComponent(selected.candidateRecordId)}/review`,
            {
                method: "POST",
                body: JSON.stringify({
                    decision,
                    notes
                })
            }
        );

        toast(
            "Review decision saved.",
            "success"
        );

        await openCandidateReview(
            selected.assessmentId,
            selected.candidateRecordId
        );

    } catch (error) {

        toast(
            error.message,
            "error"
        );

    } finally {

        const button =
            $("saveCandidateReviewBtn");

        if (button) {
            button.disabled = false;
            button.textContent =
                "Save Review Decision";
        }
    }
}


/* ============================================================
   EVIDENCE
   ============================================================ */

function openEvidence(
    sessionId,
    filename,
    eventType,
    direction,
    timestamp
) {

    const image =
        $("evidenceImage");

    const details =
        $("evidenceDetails");

    if (!image) return;

    image.src =
        `/api/evidence/${encodeURIComponent(sessionId)}/${encodeURIComponent(filename)}`;

    if (details) {

        details.innerHTML = `

            <div class="detail-grid">

                <div class="detail-item">

                    <span>
                        Event
                    </span>

                    <strong>
                        ${escapeHtml(
                            eventType
                        )}
                    </strong>

                </div>


                <div class="detail-item">

                    <span>
                        Direction
                    </span>

                    <strong>
                        ${escapeHtml(
                            direction || "—"
                        )}
                    </strong>

                </div>


                <div class="detail-item">

                    <span>
                        Timestamp
                    </span>

                    <strong>
                        ${escapeHtml(
                            formatDate(timestamp)
                        )}
                    </strong>

                </div>

            </div>

            <p class="evidence-disclaimer">
                This image is monitoring evidence associated with
                an AI-detected event. It should be reviewed by a
                human and should not be treated as an automatic
                cheating verdict.
            </p>
        `;
    }

    openModal("evidenceModal");
}


/* ============================================================
   LIVE MONITORING
   ============================================================ */

async function loadLiveMonitoring() {

    const container =
        $("liveMonitoringGrid");

    if (!container) return;

    try {

        /*
         * The current backend exposes one active monitoring
         * session through /api/session/status.
         *
         * The UI is therefore prepared for the current
         * single-worker monitoring architecture.
         */

        const response =
            await api(
                "/api/session/status"
            );

        const status =
            response.status ||
            response.data ||
            response;

        if (
            !status ||
            !status.running
        ) {

            renderNoLiveMonitoring();

            return;
        }

        renderLiveMonitoring(
            status
        );

    } catch (error) {

        console.warn(
            "Live monitoring:",
            error
        );

        renderNoLiveMonitoring();
    }
}


function renderNoLiveMonitoring() {

    const container =
        $("liveMonitoringGrid");

    if (!container) return;

    container.innerHTML = `
        <div class="empty-state">

            <div class="empty-icon">
                ●
            </div>

            <h3>
                No active candidates
            </h3>

            <p>
                Candidates currently being monitored will appear here.
            </p>

        </div>
    `;
}


function renderLiveMonitoring(status) {

    const container =
        $("liveMonitoringGrid");

    if (!container) return;

    const sessionId =
        status.session_id ||
        "—";

    const fps =
        status.fps ??
        status.monitoring_fps ??
        "—";

    const faceCount =
        status.face_count ??
        "—";

    const personCount =
        status.person_count ??
        "—";

    const direction =
        status.direction ||
        "CENTER";

    const eye =
        status.eye ||
        "OPEN";

    const events =
        Array.isArray(status.events)
            ? status.events
            : [];

    container.innerHTML = `

        <div class="live-monitor-card">

            <div class="live-card-header">

                <div>

                    <span class="eyebrow">
                        LIVE SESSION
                    </span>

                    <h3>
                        Candidate Monitoring
                    </h3>

                </div>

                <span class="status-pill active">
                    ● LIVE
                </span>

            </div>


            <div class="live-video-wrapper">

                <img
                    src="/api/video"
                    alt="Live candidate monitoring"
                >

                <span class="monitoring-live-badge">
                    ● LIVE
                </span>

            </div>


            <div class="live-metrics">

                <div>
                    <span>Session</span>
                    <strong>
                        ${escapeHtml(sessionId)}
                    </strong>
                </div>

                <div>
                    <span>FPS</span>
                    <strong>
                        ${escapeHtml(fps)}
                    </strong>
                </div>

                <div>
                    <span>Faces</span>
                    <strong>
                        ${escapeHtml(faceCount)}
                    </strong>
                </div>

                <div>
                    <span>Persons</span>
                    <strong>
                        ${escapeHtml(personCount)}
                    </strong>
                </div>

                <div>
                    <span>Direction</span>
                    <strong>
                        ${escapeHtml(direction)}
                    </strong>
                </div>

                <div>
                    <span>Eyes</span>
                    <strong>
                        ${escapeHtml(eye)}
                    </strong>
                </div>

            </div>


            <div class="live-events-preview">

                <h4>
                    Recent Events
                </h4>

                ${
                    events.length
                        ? events.slice(-5).reverse().map(
                            event =>
                                `
                                    <div class="mini-event">

                                        <span>
                                            !
                                        </span>

                                        <strong>
                                            ${escapeHtml(
                                                event.event_type ||
                                                "EVENT"
                                            )}
                                        </strong>

                                        <small>
                                            ${escapeHtml(
                                                formatDate(
                                                    event.timestamp
                                                )
                                            )}
                                        </small>

                                    </div>
                                `
                        ).join("")
                        : `
                            <p>
                                No recent monitoring events.
                            </p>
                        `
                }

            </div>

        </div>
    `;
}


/* ============================================================
   CANDIDATE PORTAL
   ============================================================ */

function openCandidatePortal() {

    navigate("candidate");

    hideCandidateViews();

    show(
        $("candidateAccessView")
    );

    loadCandidateFromStorage();
}


function hideCandidateViews() {

    [
        "candidateAccessView",
        "candidateWaitingView",
        "candidateAuthorizedView",
        "candidateReadyView",
        "candidateMonitoringView",
        "candidateCompletedView"
    ].forEach(id => {
        hide($(id));
    });
}


function loadCandidateFromStorage() {

    try {

        const stored =
            localStorage.getItem(
                "monitorai_candidate_session"
            );

        if (!stored) return;

        const data =
            JSON.parse(stored);

        if (!data) return;

        state.candidateSession = {
            ...state.candidateSession,
            ...data
        };

    } catch (error) {

        console.warn(
            "Unable to load candidate state:",
            error
        );
    }
}


function saveCandidateState() {

    localStorage.setItem(
        "monitorai_candidate_session",
        JSON.stringify(
            state.candidateSession
        )
    );
}


function clearCandidateState() {

    state.candidateSession = {
        assessmentId: null,
        candidateRecordId: null,
        accessCode: null,
        accessToken: null,
        candidateName: null,
        candidateId: null
    };

    localStorage.removeItem(
        "monitorai_candidate_session"
    );
}


/* ============================================================
   CANDIDATE REQUEST ACCESS
   ============================================================ */

async function requestCandidateAccess() {

    const token =
        $("candidateAssessmentToken")
            ?.value
            .trim();

    const candidateName =
        $("candidateName")
            ?.value
            .trim();

    const candidateId =
        $("candidateId")
            ?.value
            .trim();

    if (!token) {

        showFormMessage(
            "candidateAccessMessage",
            "Assessment access token is required.",
            "error"
        );

        return;
    }

    if (!candidateName) {

        showFormMessage(
            "candidateAccessMessage",
            "Candidate name is required.",
            "error"
        );

        return;
    }

    if (!candidateId) {

        showFormMessage(
            "candidateAccessMessage",
            "Candidate ID is required.",
            "error"
        );

        return;
    }

    try {

        const assessmentResponse =
            await api(
                `/api/assessments/link/${encodeURIComponent(token)}`
            );

        const assessment =
            assessmentResponse.assessment ||
            assessmentResponse.data ||
            assessmentResponse;

        const assessmentId =
            assessment.assessment_id ||
            assessment.id;

        if (!assessmentId) {
            throw new Error(
                "Invalid assessment access token."
            );
        }

        const payload = {
            candidate_name: candidateName,
            candidate_id: candidateId
        };

        const response =
            await api(
                `/api/assessments/${encodeURIComponent(assessmentId)}/access-request`,
                {
                    method: "POST",
                    body: JSON.stringify(payload)
                }
            );

        const candidate =
            response.candidate ||
            response.data ||
            response;

        state.candidateSession = {
            ...state.candidateSession,

            assessmentId,

            candidateRecordId:
                candidate.candidate_record_id ||
                candidate.id ||
                response.candidate_record_id ||
                null,

            accessToken: token,

            candidateName,
            candidateId,

            accessCode:
                candidate.access_code ||
                response.access_code ||
                null
        };

        saveCandidateState();

        if (
            state.candidateSession.accessCode
        ) {

            showCandidateAuthorized(
                state.candidateSession.accessCode
            );

        } else {

            showCandidateWaiting(
                assessment
            );

            startCandidateStatusPolling();
        }

        toast(
            "Access request submitted.",
            "success"
        );

    } catch (error) {

        showFormMessage(
            "candidateAccessMessage",
            error.message,
            "error"
        );
    }
}


/* ============================================================
   CANDIDATE WAITING
   ============================================================ */

function showCandidateWaiting(
    assessment = null
) {

    hideCandidateViews();

    show(
        $("candidateWaitingView")
    );

    const details =
        $("candidateWaitingDetails");

    if (!details) return;

    const name =
        state.candidateSession.candidateName ||
        "Candidate";

    const candidateId =
        state.candidateSession.candidateId ||
        "—";

    const assessmentName =
        assessment?.assessment_name ||
        assessment?.name ||
        "Assessment";

    details.innerHTML = `
        <strong>
            ${escapeHtml(name)}
        </strong>

        <span>
            Candidate ID:
            ${escapeHtml(candidateId)}
        </span>

        <span>
            Assessment:
            ${escapeHtml(assessmentName)}
        </span>

        <small>
            Your request is waiting for author approval.
        </small>
    `;
}


function startCandidateStatusPolling() {

    window.clearInterval(
        state.candidateTimer
    );

    state.candidateTimer =
        window.setInterval(
            checkCandidateAccess,
            5000
        );
}


async function checkCandidateAccess() {

    const session =
        state.candidateSession;

    if (
        !session.assessmentId ||
        !session.candidateRecordId
    ) {
        return;
    }

    try {

        const response =
            await api(
                `/api/assessments/${encodeURIComponent(session.assessmentId)}/candidates`
            );

        const candidates =
            extractArray(response, [
                "candidates",
                "data",
                "items"
            ]);

        const candidate =
            candidates.find(
                item =>
                    String(
                        item.candidate_record_id ||
                        item.id
                    ) ===
                    String(
                        session.candidateRecordId
                    )
            );

        if (!candidate) return;

        const status =
            normalizeStatus(
                candidate.assignment_status ||
                candidate.status ||
                ""
            );

        if (
            status === "AUTHORIZED" ||
            status === "APPROVED"
        ) {

            window.clearInterval(
                state.candidateTimer
            );

            const accessCode =
                candidate.access_code ||
                "";

            state.candidateSession.accessCode =
                accessCode;

            saveCandidateState();

            showCandidateAuthorized(
                accessCode
            );

            toast(
                "Your assessment access has been approved.",
                "success"
            );
        }

        if (status === "REJECTED") {

            window.clearInterval(
                state.candidateTimer
            );

            showCandidateRejected();
        }

    } catch (error) {

        console.warn(
            "Candidate access polling:",
            error
        );
    }
}


function showCandidateRejected() {

    hideCandidateViews();

    const view =
        $("candidateWaitingView");

    show(view);

    const details =
        $("candidateWaitingDetails");

    if (details) {

        details.innerHTML = `
            <strong>
                Access Request Rejected
            </strong>

            <span>
                The assessment author has rejected your
                access request.
            </span>
        `;
    }
}


/* ============================================================
   CANDIDATE AUTHORIZED
   ============================================================ */

function showCandidateAuthorized(
    accessCode
) {

    hideCandidateViews();

    show(
        $("candidateAuthorizedView")
    );

    setText(
        $("candidateAccessCode"),
        accessCode || "Pending"
    );
}


/* ============================================================
   ENTER ASSESSMENT
   ============================================================ */

async function enterCandidateAssessment() {

    const accessCode =
        state.candidateSession.accessCode;

    if (!accessCode) {

        toast(
            "Access code is not available yet.",
            "warning"
        );

        return;
    }

    try {

        const response =
            await api(
                `/api/candidates/access/${encodeURIComponent(accessCode)}`
            );

        const candidate =
            response.candidate ||
            response.data ||
            response;

        state.candidateSession = {
            ...state.candidateSession,

            assessmentId:
                candidate.assessment_id ||
                state.candidateSession.assessmentId,

            candidateRecordId:
                candidate.candidate_record_id ||
                state.candidateSession.candidateRecordId,

            accessCode,

            candidateName:
                candidate.candidate_name ||
                state.candidateSession.candidateName,

            candidateId:
                candidate.candidate_id ||
                state.candidateSession.candidateId
        };

        saveCandidateState();

        showCandidateReady();

    } catch (error) {

        toast(
            error.message,
            "error"
        );
    }
}


/* ============================================================
   CANDIDATE READY
   ============================================================ */

function showCandidateReady() {

    hideCandidateViews();

    show(
        $("candidateReadyView")
    );

    setText(
        $("candidateReadyTitle"),
        state.candidateSession.candidateName
            ? `Ready, ${state.candidateSession.candidateName}`
            : "Ready to Begin"
    );

    startCameraReadinessPolling();
}


function startCameraReadinessPolling() {

    updateCandidateReadiness();

    window.clearInterval(
        startCameraReadinessPolling._timer
    );

    startCameraReadinessPolling._timer =
        window.setInterval(
            updateCandidateReadiness,
            2000
        );
}


async function updateCandidateReadiness() {

    try {

        const response =
            await api(
                "/api/session/status"
            );

        const status =
            response.status ||
            response.data ||
            response;

        const running =
            Boolean(
                status.running
            );

        setReadiness(
            "cameraReadiness",
            running
                ? "Camera active"
                : "Camera ready"
        );

        setReadiness(
            "faceReadiness",
            status.face_count > 0
                ? "Face detected"
                : "Waiting for face"
        );

        setReadiness(
            "environmentReadiness",
            status.person_count !== undefined
                ? `${status.person_count} person detected`
                : "Ready"
        );

    } catch {

        setReadiness(
            "cameraReadiness",
            "Ready"
        );

        setReadiness(
            "faceReadiness",
            "Position yourself in camera"
        );

        setReadiness(
            "environmentReadiness",
            "Ready"
        );
    }
}


function setReadiness(
    id,
    text
) {

    const element = $(id);

    if (!element) return;

    element.textContent = text;
}


/* ============================================================
   START CANDIDATE MONITORING
   ============================================================ */

async function startCandidateMonitoring() {

    const session =
        state.candidateSession;

    if (
        !session.assessmentId ||
        !session.candidateRecordId
    ) {

        toast(
            "Candidate session information is missing.",
            "error"
        );

        return;
    }

    try {

        const button =
            $("candidateStartMonitoringBtn");

        if (button) {

            button.disabled = true;
            button.textContent =
                "Starting Monitoring...";
        }

        const response =
            await api(
                `/api/assessments/${encodeURIComponent(session.assessmentId)}/candidates/${encodeURIComponent(session.candidateRecordId)}/start`,
                {
                    method: "POST"
                }
            );

        const returnedSession =
            response.session ||
            response.data ||
            response;

        if (
            returnedSession.session_id
        ) {

            state.candidateSession.sessionId =
                returnedSession.session_id;

            saveCandidateState();
        }

        hideCandidateViews();

        show(
            $("candidateMonitoringView")
        );

        setText(
            $("candidateMonitoringTitle"),
            session.candidateName
                ? `${session.candidateName} — Monitoring Active`
                : "Assessment in Progress"
        );

        toast(
            "Monitoring started.",
            "success"
        );

        startCandidateMonitoringPolling();

    } catch (error) {

        toast(
            error.message,
            "error"
        );

    } finally {

        const button =
            $("candidateStartMonitoringBtn");

        if (button) {

            button.disabled = false;
            button.textContent =
                "Start Monitoring";
        }
    }
}


function startCandidateMonitoringPolling() {

    window.clearInterval(
        state.candidateTimer
    );

    state.candidateTimer =
        window.setInterval(
            refreshCandidateMonitoring,
            2000
        );
}


async function refreshCandidateMonitoring() {

    try {

        const response =
            await api(
                "/api/session/status"
            );

        const status =
            response.status ||
            response.data ||
            response;

        if (
            status.running === false &&
            state.candidateSession.sessionId
        ) {

            /*
             * The monitoring session may have been stopped
             * externally. Do not automatically mark completed.
             */
            console.warn(
                "Monitoring session is no longer running."
            );
        }

    } catch (error) {

        console.warn(
            "Monitoring status:",
            error
        );
    }
}


/* ============================================================
   COMPLETE ASSESSMENT
   ============================================================ */

async function completeCandidateAssessment() {

    const session =
        state.candidateSession;

    if (
        !session.assessmentId ||
        !session.candidateRecordId
    ) {

        toast(
            "Candidate session information is missing.",
            "error"
        );

        return;
    }

    const confirmed =
        window.confirm(
            "Are you sure you have completed the assessment?"
        );

    if (!confirmed) return;

    try {

        const button =
            $("candidateCompleteBtn");

        if (button) {

            button.disabled = true;
            button.textContent =
                "Completing...";
        }

        await api(
            `/api/assessments/${encodeURIComponent(session.assessmentId)}/candidates/${encodeURIComponent(session.candidateRecordId)}/complete`,
            {
                method: "POST"
            }
        );

        window.clearInterval(
            state.candidateTimer
        );

        hideCandidateViews();

        show(
            $("candidateCompletedView")
        );

        toast(
            "Assessment completed successfully.",
            "success"
        );

    } catch (error) {

        toast(
            error.message,
            "error"
        );

    } finally {

        const button =
            $("candidateCompleteBtn");

        if (button) {

            button.disabled = false;
            button.textContent =
                "Assessment Completed";
        }
    }
}


/* ============================================================
   CAMERA PREVIEW
   ============================================================ */

function refreshCameraImages() {

    const images = [
        $("candidateCameraPreview"),
        $("candidateLiveVideo")
    ];

    const timestamp =
        Date.now();

    images.forEach(image => {

        if (!image) return;

        const base =
            "/api/video";

        image.src =
            `${base}?t=${timestamp}`;
    });
}


/* ============================================================
   COPY
   ============================================================ */

async function copyText(value) {

    try {

        await navigator.clipboard.writeText(
            value
        );

        toast(
            "Copied to clipboard.",
            "success"
        );

    } catch {

        toast(
            "Unable to copy.",
            "error"
        );
    }
}


/* ============================================================
   FORM MESSAGE
   ============================================================ */

function showFormMessage(
    id,
    message,
    type = "info"
) {

    const element = $(id);

    if (!element) return;

    element.textContent = message;

    element.classList.remove(
        "success",
        "error",
        "warning",
        "info"
    );

    element.classList.add(type);

    show(element);
}


/* ============================================================
   CANDIDATE PORTAL URL HANDLING
   ============================================================ */

function detectCandidateMode() {

    const params =
        new URLSearchParams(
            window.location.search
        );

    const mode =
        params.get("mode");

    if (
        mode === "candidate" ||
        mode === "portal"
    ) {

        openCandidatePortal();

        return true;
    }

    return false;
}


/* ============================================================
   EVENT BINDINGS
   ============================================================ */

function bindNavigation() {

    document.querySelectorAll(
        ".nav-item"
    ).forEach(button => {

        button.addEventListener(
            "click",
            () => {

                const page =
                    button.dataset.page;

                if (page) {
                    navigate(page);
                }
            }
        );
    });


    document.querySelectorAll(
        "[data-page]"
    ).forEach(button => {

        if (
            button.classList.contains(
                "nav-item"
            )
        ) {
            return;
        }

        button.addEventListener(
            "click",
            () => {

                const page =
                    button.dataset.page;

                if (page) {
                    navigate(page);
                }
            }
        );
    });
}


function bindCreateAssessmentButtons() {

    [
        "createAssessmentTopBtn",
        "dashboardCreateBtn",
        "assessmentsCreateBtn",
        "emptyCreateBtn"
    ].forEach(id => {

        const button = $(id);

        if (!button) return;

        button.addEventListener(
            "click",
            openCreateAssessmentModal
        );
    });
}


function bindModalButtons() {

    const closeCreate =
        $("closeCreateModalBtn");

    const cancelCreate =
        $("cancelCreateAssessmentBtn");

    if (closeCreate) {
        closeCreate.addEventListener(
            "click",
            closeCreateAssessmentModal
        );
    }

    if (cancelCreate) {
        cancelCreate.addEventListener(
            "click",
            closeCreateAssessmentModal
        );
    }


    const closeDetails =
        $("closeDetailsModalBtn");

    const detailsClose =
        $("detailsCloseBtn");

    if (closeDetails) {
        closeDetails.addEventListener(
            "click",
            () =>
                closeModal(
                    "assessmentDetailsModal"
                )
        );
    }

    if (detailsClose) {
        detailsClose.addEventListener(
            "click",
            () =>
                closeModal(
                    "assessmentDetailsModal"
                )
        );
    }


    const closeRequest =
        $("closeCandidateRequestModalBtn");

    if (closeRequest) {
        closeRequest.addEventListener(
            "click",
            () =>
                closeModal(
                    "candidateRequestModal"
                )
        );
    }


    const closeReview =
        $("closeCandidateReviewModalBtn");

    const closeReviewBottom =
        $("closeCandidateReviewBtn");

    if (closeReview) {
        closeReview.addEventListener(
            "click",
            () =>
                closeModal(
                    "candidateReviewModal"
                )
        );
    }

    if (closeReviewBottom) {
        closeReviewBottom.addEventListener(
            "click",
            () =>
                closeModal(
                    "candidateReviewModal"
                )
        );
    }


    const closeEvidence =
        $("closeEvidenceModalBtn");

    if (closeEvidence) {
        closeEvidence.addEventListener(
            "click",
            () =>
                closeModal(
                    "evidenceModal"
                )
        );
    }


    document.querySelectorAll(
        ".modal-overlay"
    ).forEach(overlay => {

        overlay.addEventListener(
            "click",
            () => {

                const modal =
                    overlay.closest(".modal");

                if (modal) {
                    hide(modal);
                }

                document.body.classList.remove(
                    "modal-open"
                );
            }
        );
    });
}


function bindForms() {

    const createForm =
        $("createAssessmentForm");

    if (createForm) {

        createForm.addEventListener(
            "submit",
            createAssessment
        );
    }


    const candidateRequest =
        $("candidateRequestBtn");

    if (candidateRequest) {

        candidateRequest.addEventListener(
            "click",
            requestCandidateAccess
        );
    }


    const candidateCheck =
        $("candidateCheckAccessBtn");

    if (candidateCheck) {

        candidateCheck.addEventListener(
            "click",
            async () => {

                await checkCandidateAccess();

                toast(
                    "Access status checked.",
                    "info"
                );
            }
        );
    }


    const candidateEnter =
        $("candidateEnterAssessmentBtn");

    if (candidateEnter) {

        candidateEnter.addEventListener(
            "click",
            enterCandidateAssessment
        );
    }


    const candidateStart =
        $("candidateStartMonitoringBtn");

    if (candidateStart) {

        candidateStart.addEventListener(
            "click",
            startCandidateMonitoring
        );
    }


    const candidateComplete =
        $("candidateCompleteBtn");

    if (candidateComplete) {

        candidateComplete.addEventListener(
            "click",
            completeCandidateAssessment
        );
    }


    const saveReview =
        $("saveCandidateReviewBtn");

    if (saveReview) {

        saveReview.addEventListener(
            "click",
            saveCandidateReview
        );
    }
}


function bindUtilityButtons() {

    const refresh =
        $("refreshBtn");

    if (refresh) {

        refresh.addEventListener(
            "click",
            async () => {

                await loadDashboard();

                if (
                    state.currentPage ===
                    "assessments"
                ) {
                    await loadAssessments();
                }

                if (
                    state.currentPage ===
                    "requests"
                ) {
                    await loadRequests();
                }

                if (
                    state.currentPage ===
                    "live"
                ) {
                    await loadLiveMonitoring();
                }

                toast(
                    "Dashboard refreshed.",
                    "success"
                );
            }
        );
    }
}


/* ============================================================
   BACKGROUND REFRESH
   ============================================================ */

function startBackgroundRefresh() {

    window.clearInterval(
        state.refreshTimer
    );

    state.refreshTimer =
        window.setInterval(
            async () => {

                if (
                    state.currentPage ===
                    "dashboard"
                ) {
                    await loadDashboard();
                }

                if (
                    state.currentPage ===
                    "live"
                ) {
                    await loadLiveMonitoring();
                }

            },
            10000
        );
}


/* ============================================================
   KEYBOARD SHORTCUTS
   ============================================================ */

function bindKeyboardShortcuts() {

    document.addEventListener(
        "keydown",
        event => {

            if (
                event.key === "Escape"
            ) {

                document.querySelectorAll(
                    ".modal"
                ).forEach(modal => {
                    hide(modal);
                });

                document.body.classList.remove(
                    "modal-open"
                );
            }
        }
    );
}


/* ============================================================
   INITIALIZATION
   ============================================================ */

async function initializeApp() {

    console.log(
        "MonitorAI frontend initializing..."
    );

    bindNavigation();

    bindCreateAssessmentButtons();

    bindModalButtons();

    bindForms();

    bindUtilityButtons();

    bindKeyboardShortcuts();

    updatePageHeader("dashboard");

    const candidateMode =
        detectCandidateMode();

    if (!candidateMode) {

        await loadDashboard();

        startBackgroundRefresh();
    }

    console.log(
        "MonitorAI frontend initialized."
    );
}


/* ============================================================
   GLOBAL EXPORTS
   ============================================================ */

window.openCreateAssessmentModal =
    openCreateAssessmentModal;

window.closeCreateAssessmentModal =
    closeCreateAssessmentModal;

window.openAssessmentDetails =
    openAssessmentDetails;

window.activateAssessment =
    activateAssessment;

window.deactivateAssessment =
    deactivateAssessment;

window.openAssessmentCandidates =
    openAssessmentCandidates;

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

window.copyText =
    copyText;

window.loadAssessments =
    loadAssessments;

window.loadRequests =
    loadRequests;

window.loadLiveMonitoring =
    loadLiveMonitoring;


/* ============================================================
   START
   ============================================================ */

document.addEventListener(
    "DOMContentLoaded",
    initializeApp
);