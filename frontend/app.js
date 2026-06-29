const API_BASE = "https://legal-outreach-system-production.up.railway.app";
window.API_BASE = API_BASE;
console.log("Using LOCAL API_BASE:", API_BASE);

const DEMO_MODE = false;
const AUTH_TOKEN_KEY = "greenLightAuthToken";
const BUSINESS_PROFILE_ID_KEY = "greenLightBusinessProfileId";

const DEMO_ONLY_MESSAGE = "Demo only. Live sending is disabled.";
const SIGNATURE_IMAGE_PLACEHOLDER = "{{signature_image}}";
const SIGNATURE_IMAGE_HTML = '<img src="cid:signature_image" alt="Signature" style="width:140px; max-width:140px; display:block; margin:8px 0 4px 0;">';
const MANUAL_CRM_COUNTS_KEY = "greenLightManualCrmCounts";
const CRM_STATUSES = [
  "Not Contacted",
  "Email Sent",
  "Replied",
  "Interested",
  "Meeting Scheduled",
  "Partner",
  "Not Interested",
  "Do Not Contact"
];
const CONTACTED_STATUSES = new Set(CRM_STATUSES.filter((status) => status !== "Not Contacted"));

const OFFICIAL_TEMPLATE_BODY = `Dear {firm_name} Team,

We are reaching out to professional firms in the {city} area to introduce Green Light Drivers Ed & DUI School LLC and the services we provide.

Greetings from Green Light Drivers Ed & DUI School LLC, a Bilingual Driving School at www.greenlightdrivers.com.

We write to introduce our organization and the services we provide as a Georgia DDS-Certified Driving and DUI/Risk reduction School serving teens and adults throughout the State and other States in the United States.

This letter does not serve as a Direct Solicitation or engage in any activity that could be interpreted as Direct Soliciting. Our goal is to network with Great professionals like your firm and introduce our professional services to your firm as a Licensed, Successful Driving School with over 200 5-star Google Ratings, offering Driving Education, Defensive Driving/Driver Improvement, DUI/Risk Reduction programs, and Georgia-approved third-party road tests. We are also providing Clinical evaluations/ASAM thought by Certified Instructors at our Location as professional Resources available to you, as needed or required by your clients in Georgia.

Services We Provide

• DDS-Approved Defensive Driving Courses (In-Class & Virtual through Zoom)
• DUI / Risk Reduction Programs (In-Class & Virtual through Zoom)
• Joshua’s Law Driver Education Courses
• Behind-The-Wheel Driving Lessons (Cars equipped with Cameras and Instructor driving pedals)
• Road Test Preparation
• DDS-Approved On-Site Road Testing
• English and Spanish Programs
• Flexible Scheduling Including Weekends

How Our Services May Help Your Clients

Many drivers require educational or compliance-related services connected to:

• License point reduction
• Court requirements
• Fine reduction eligibility
• License reinstatement processes
• Driving evaluations
• Safe-driving education

Our school focuses on safe driving compliance, driver education, road safety, and professional support for students’ safe driving.

Certified instructors conduct all courses, and we offer both virtual and in-person options to help students meet the Department of Driver Services (DDS) and the Court requirements efficiently and professionally.

Contact Information

Green Light Drivers Ed & DUI School LLC
6110 McFarland Station Drive, Suite 703
Alpharetta, GA 30004

Phone: (770) 685-1600
Email: info@greenlightdrivers.com
Website: https://greenlightdrivers.com

Thank you for your time and consideration. We appreciate the opportunity to introduce our school and would be happy to provide additional information or informational materials for your office at any time.

Sincerely,

{{signature_image}}

Manager
Green Light Drivers Ed & DUI School LLC`;

const demoFirms = [
  {
    id: 1,
    firm_name: "Peachtree DUI Defense Group",
    practice_area: "DUI lawyer",
    city: "Atlanta",
    phone: "(404) 555-0184",
    website: "https://example.com/peachtree-dui",
    email: "intake@peachtreeduidemo.com",
    status: "Not Contacted"
  },
  {
    id: 2,
    firm_name: "Midtown Criminal Law",
    practice_area: "DUI lawyer",
    city: "Atlanta",
    phone: "(404) 555-0129",
    website: "https://example.com/midtown-law",
    email: "hello@midtowndemo.com",
    status: "Email Sent"
  },
  {
    id: 3,
    firm_name: "Northside Legal Advocates",
    practice_area: "DUI lawyer",
    city: "Atlanta",
    phone: "(678) 555-0197",
    website: "https://example.com/northside-legal",
    email: null,
    status: "Not Contacted"
  }
];

const demoLogs = [
  {
    firm_name: "Midtown Criminal Law",
    email: "hello@midtowndemo.com",
    subject: "Professional Introduction - Green Light Drivers Ed & DUI School LLC",
    status: "Sent",
    sent_at: new Date(Date.now() - 86400000).toISOString()
  },
  {
    firm_name: "Sample Prospect",
    email: "sample@example.com",
    subject: "Green Light Drivers Ed & DUI School LLC Outreach",
    status: "Failed",
    sent_at: new Date(Date.now() - 43200000).toISOString()
  }
];

const demoFollowUps = {
  eligible_count: 0,
  follow_ups_sent: 0,
  reply_rate: "0.0%",
  prospects: []
};

const demoAutoFollowUpSettings = {
  enabled: false,
  daily_limit: 5,
  delay_seconds: 10
};

const demoNewsletterStats = {
  total_newsletter_contacts: 2,
  newsletters_sent: 0,
  last_newsletter_sent: null,
  unsubscribed_do_not_contact: 0
};

const demoTemplate = {
  id: 1,
  name: "Demo outreach letter",
  subject: "Professional Introduction - Green Light Drivers Ed & DUI School LLC",
  body_text: OFFICIAL_TEMPLATE_BODY,
  is_active: true
};

let firmsCache = [];
let logsCache = [];
let activeTemplate = null;
let selectedPreviewFirmId = null;
let backendConnected = false;
let logsNewestFirst = true;
let replyReportCache = [];
let followUpsCache = [];
let autoFollowUpSettingsCache = demoAutoFollowUpSettings;
let manualCrmCountsCache = loadManualCrmCounts();
let newsletterContactsCache = [];
let selectedNewsletterContactIds = new Set();
let authToken = localStorage.getItem(AUTH_TOKEN_KEY) || "";
let currentUser = null;
let usersCache = [];
let auditLogsCache = [];
let businessProfilesCache = [];
let businessProfileOptionsCache = [];
let selectedBusinessProfileId = Number(localStorage.getItem(BUSINESS_PROFILE_ID_KEY) || 0);

const MAIN_PAGE_SELECTORS = [
  "#dashboard",
  ".stats-grid",
  ".analytics-panel",
  ".reply-tracking-panel",
  "#campaign",
  "#follow-ups",
  ".content-grid",
  ".owner-tools-grid",
  "#email-template",
  "#firms",
  "#logs",
  "#settings",
  "#users"
];
const NEWSLETTER_SECTION_ID = "newsletters";

function getElement(id) {
  return document.getElementById(id);
}

function setText(id, value) {
  const element = getElement(id);
  if (element) {
    element.textContent = value;
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatLocalTimestamp(value) {
  if (!value) return "Not recorded";

  const normalizedValue =
    typeof value === "string" && /^\d{4}-\d{2}-\d{2}T/.test(value) && !/[zZ]|[+-]\d{2}:\d{2}$/.test(value)
      ? `${value}Z`
      : value;
  const date = new Date(normalizedValue);

  if (Number.isNaN(date.getTime())) {
    return "Not recorded";
  }

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit"
  }).format(date);
}

function writeFrame(frameId, html) {
  const frame = getElement(frameId);
  if (!frame) return;

  const documentRef = frame.contentDocument || frame.contentWindow.document;
  documentRef.open();
  documentRef.write(html);
  documentRef.close();
}

function emailHtmlFromText(bodyText) {
  const escapedBody = escapeHtml(bodyText)
    .replaceAll(SIGNATURE_IMAGE_PLACEHOLDER, SIGNATURE_IMAGE_HTML)
    .replaceAll("\n", "<br>");

  return `
    <!DOCTYPE html>
    <html>
      <head>
        <style>
          body {
            color: #1f2937;
            font-family: Arial, sans-serif;
            font-size: 15px;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
          }
        </style>
      </head>
      <body>${escapedBody}</body>
    </html>
  `;
}

function calculateStats(firms, logs) {
  return {
    total_firms: firms.length,
    firms_with_emails: firms.filter((firm) => Boolean(firm.email)).length,
    emails_sent: logs.filter((log) => log.status === "Sent").length,
    not_contacted: firms.filter((firm) => firm.status !== "Email Sent").length
  };
}

function calculateAnalytics(firms, logs) {
  const sentFirmIds = new Set(
    logs
      .filter((log) => log.status === "Sent" && log.firm_id)
      .map((log) => log.firm_id)
  );
  const emailsSent = firms.filter((firm) => sentFirmIds.has(firm.id) || CONTACTED_STATUSES.has(firm.status)).length;
  const replies = firms.filter((firm) => ["Replied", "Interested", "Meeting Scheduled", "Partner", "Not Interested"].includes(firm.status)).length;
  const interested = firms.filter((firm) => ["Interested", "Meeting Scheduled", "Partner"].includes(firm.status)).length;
  const meetingsScheduled = firms.filter((firm) => ["Meeting Scheduled", "Partner"].includes(firm.status)).length;
  const partners = firms.filter((firm) => firm.status === "Partner").length;
  const notInterested = firms.filter((firm) => firm.status === "Not Interested").length;

  return {
    total_prospects: firms.length,
    emails_sent: emailsSent,
    replies,
    interested,
    meetings_scheduled: meetingsScheduled,
    partners,
    not_interested: notInterested,
    reply_rate: emailsSent === 0 ? 0 : (replies / emailsSent) * 100,
    interested_rate: replies === 0 ? 0 : (interested / replies) * 100,
    partner_conversion_rate: emailsSent === 0 ? 0 : (partners / emailsSent) * 100
  };
}

function normalizeManualCrmCounts(counts = {}) {
  return {
    interested: Math.max(0, Number.parseInt(counts.interested, 10) || 0),
    meetings_scheduled: Math.max(0, Number.parseInt(counts.meetings_scheduled, 10) || 0),
    partners: Math.max(0, Number.parseInt(counts.partners, 10) || 0),
    not_interested: Math.max(0, Number.parseInt(counts.not_interested, 10) || 0)
  };
}

function loadManualCrmCounts() {
  try {
    return normalizeManualCrmCounts(JSON.parse(localStorage.getItem(MANUAL_CRM_COUNTS_KEY) || "{}"));
  } catch (error) {
    return normalizeManualCrmCounts();
  }
}

function saveManualCrmCounts(counts) {
  manualCrmCountsCache = normalizeManualCrmCounts(counts);
  localStorage.setItem(MANUAL_CRM_COUNTS_KEY, JSON.stringify(manualCrmCountsCache));
  return manualCrmCountsCache;
}

function applyManualCrmCounts(analytics) {
  const displayAnalytics = {
    ...analytics,
    interested: manualCrmCountsCache.interested,
    meetings_scheduled: manualCrmCountsCache.meetings_scheduled,
    partners: manualCrmCountsCache.partners,
    not_interested: manualCrmCountsCache.not_interested
  };
  const replies = Number(displayAnalytics.replies || 0);
  const emailsSent = Number(displayAnalytics.emails_sent || 0);

  displayAnalytics.interested_rate = replies === 0 ? 0 : (displayAnalytics.interested / replies) * 100;
  displayAnalytics.partner_conversion_rate = emailsSent === 0 ? 0 : (displayAnalytics.partners / emailsSent) * 100;

  return displayAnalytics;
}

function setSystemStatus(mode, detail) {
  const status = getElement("systemStatus");
  if (status) {
    status.classList.toggle("online", mode.toLowerCase().includes("connected") || mode.toLowerCase().includes("demo"));
    status.classList.toggle("offline", mode.toLowerCase().includes("unavailable"));
    status.dataset.mode = mode;
    status.innerHTML = `
      <span class="status-dot"></span>
      <div>
        <strong>${escapeHtml(mode)}</strong>
        <small>${escapeHtml(detail)}</small>
      </div>
    `;
  }

  if (DEMO_MODE) {
    setText("apiEndpoint", "GitHub Pages demo data");
  } else {
    setText("apiEndpoint", API_BASE);
  }
}

function getBackendUnavailableMessage() {
  return "Start FastAPI at http://127.0.0.1:8000 and refresh.";
}

function setBackendUnavailableStatus() {
  setSystemStatus("Backend Unavailable", getBackendUnavailableMessage());
}

function hasRole(role) {
  const levels = { staff: 1, manager: 2, admin: 3 };
  return (levels[currentUser?.role] || 0) >= (levels[role] || 0);
}

function clearAuth() {
  authToken = "";
  currentUser = null;
  localStorage.removeItem(AUTH_TOKEN_KEY);
}

function getSelectedBusinessProfileId() {
  return Number(selectedBusinessProfileId || localStorage.getItem(BUSINESS_PROFILE_ID_KEY) || 0) || null;
}

function getSelectedBusinessProfile() {
  const selectedId = getSelectedBusinessProfileId();
  return businessProfileOptionsCache.find((profile) => profile.id === selectedId)
    || businessProfileOptionsCache.find((profile) => profile.is_default)
    || businessProfileOptionsCache[0]
    || null;
}

function setSelectedBusinessProfile(profileId, shouldPersist = true) {
  selectedBusinessProfileId = Number(profileId || 0);
  const profile = getSelectedBusinessProfile();
  if (profile) selectedBusinessProfileId = profile.id;

  if (shouldPersist && selectedBusinessProfileId) {
    localStorage.setItem(BUSINESS_PROFILE_ID_KEY, String(selectedBusinessProfileId));
  }

  renderBusinessProfileSelector();
}

function shouldAttachBusinessProfile(path) {
  return [
    "/templates",
    "/firms/check-replies",
    "/firms/run-auto-follow-ups",
    "/firms/run-campaign",
    "/firms/send-batch-outreach",
    "/firms/",
    "/newsletters"
  ].some((prefix) => path.startsWith(prefix));
}

function withBusinessProfileRequest(path, options = {}) {
  const profileId = getSelectedBusinessProfileId();
  if (!profileId || !shouldAttachBusinessProfile(path)) {
    return { path, options };
  }

  const updatedOptions = { ...options };
  const body = updatedOptions.body;

  if (body instanceof FormData) {
    body.set("business_profile_id", String(profileId));
    return { path, options: updatedOptions };
  }

  const contentType = new Headers(updatedOptions.headers || {}).get("Content-Type") || "";
  if (body && contentType.includes("application/json")) {
    try {
      updatedOptions.body = JSON.stringify({
        ...JSON.parse(body),
        business_profile_id: profileId
      });
      return { path, options: updatedOptions };
    } catch (error) {
      // Fall through to query-string attachment if the JSON body cannot be parsed.
    }
  }

  const separator = path.includes("?") ? "&" : "?";
  return {
    path: `${path}${separator}business_profile_id=${encodeURIComponent(profileId)}`,
    options: updatedOptions
  };
}

function showLoginGate(message = "") {
  document.body.classList.add("auth-locked");
  getElement("loginScreen")?.classList.remove("section-hidden");
  getElement("appShell")?.classList.add("section-hidden");
  setText("loginMessage", message);
}

function showApplication() {
  document.body.classList.remove("auth-locked");
  getElement("loginScreen")?.classList.add("section-hidden");
  getElement("appShell")?.classList.remove("section-hidden");
  setText("currentUserEmail", currentUser?.email || "");
  setText("currentUserRole", currentUser?.role || "");
  applyRoleVisibility();
}

async function loadBusinessProfileOptions() {
  if (DEMO_MODE) {
    return [
      { id: 1, name: "Green Light Drivers Ed & DUI School LLC", is_default: true },
      { id: 2, name: "Greenlight Hope Foundation", is_default: false }
    ];
  }

  return fetchJson("/business-profiles/active-options/");
}

async function initializeBusinessProfiles() {
  businessProfileOptionsCache = await loadBusinessProfileOptions();
  const storedId = getSelectedBusinessProfileId();
  const selectedExists = businessProfileOptionsCache.some((profile) => profile.id === storedId);
  const defaultProfile = businessProfileOptionsCache.find((profile) => profile.is_default) || businessProfileOptionsCache[0];

  setSelectedBusinessProfile(selectedExists ? storedId : defaultProfile?.id, true);
}

function renderBusinessProfileSelector() {
  const selector = getElement("businessProfileSelector");
  const selectedProfile = getSelectedBusinessProfile();
  const selectedName = selectedProfile?.name || "Green Light Drivers Ed & DUI School LLC";

  if (selector) {
    selector.innerHTML = businessProfileOptionsCache.length
      ? businessProfileOptionsCache.map((profile) => `
          <option value="${escapeHtml(profile.id)}" ${profile.id === selectedProfile?.id ? "selected" : ""}>${escapeHtml(profile.name)}</option>
        `).join("")
      : `<option value="">Green Light Drivers Ed & DUI School LLC</option>`;
  }

  setText("selectedBusinessName", selectedName);
  setText("settingsBusinessName", selectedName);
  const headerEyebrow = document.querySelector(".top-header .header-copy .eyebrow");
  if (headerEyebrow) headerEyebrow.textContent = selectedName;
}

function applyRoleVisibility() {
  const isAdmin = hasRole("admin");
  const isManager = hasRole("manager");

  document.querySelectorAll("[data-min-role]").forEach((element) => {
    element.hidden = !hasRole(element.dataset.minRole);
  });

  [
    "campaignButton",
    "importExcelButton",
    "batchButton",
    "previewSendButton",
    "newsletterDraftButton",
    "newsletterSendButton",
    "runAutoFollowUpsButton"
  ].forEach((id) => {
    const button = getElement(id);
    if (button && !isManager) button.disabled = true;
  });

  [
    "templateSaveButton",
    "templateActivateButton",
    "saveAutoFollowUpSettingsButton",
    "resetCampaignButton"
  ].forEach((id) => {
    const button = getElement(id);
    if (button && !isAdmin) button.disabled = true;
  });
}

async function login(event) {
  event.preventDefault();
  const email = getElement("loginEmail")?.value.trim();
  const password = getElement("loginPassword")?.value || "";
  const message = getElement("loginMessage");

  if (message) message.textContent = "Signing in...";

  try {
    const data = await fetchJson("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    authToken = data.access_token;
    currentUser = data.user;
    localStorage.setItem(AUTH_TOKEN_KEY, authToken);
    showApplication();
    await initializeBusinessProfiles();
    await loadDashboard();
  } catch (error) {
    if (message) message.textContent = error.message || "Login failed.";
  }
}

async function logout() {
  clearAuth();
  showLoginGate("Signed out.");
}

async function initializeAuth() {
  if (!authToken) {
    showLoginGate();
    return;
  }

  try {
    currentUser = await fetchJson("/auth/me");
    showApplication();
    await initializeBusinessProfiles();
    await loadDashboard();
  } catch (error) {
    showLoginGate("Please sign in.");
  }
}

function getTemplateBody(template) {
  return template?.body_text || template?.body_html || "";
}

function statusBadge(status) {
  const value = status || "Not Contacted";
  const normalized = value.toLowerCase();
  let className = "status-neutral";

  if (normalized.includes("sent")) className = "status-sent";
  if (normalized.includes("fail") || normalized.includes("error")) className = "status-failed";
  if (normalized.includes("not") || normalized.includes("pending")) className = "status-pending";

  return `<span class="status-badge ${className}">${escapeHtml(value)}</span>`;
}

function normalizeUrl(url) {
  if (!url) return "";
  const trimmed = String(url).trim();
  if (!trimmed) return "";
  return /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
}

function setActionButtonsForMode() {
  const postButtons = [
    "searchButton",
    "campaignButton",
    "manualAddButton",
    "importExcelButton",
    "batchButton",
    "templateSaveButton",
    "templateActivateButton",
    "previewSendButton",
    "newsletterDraftButton",
    "newsletterSendButton",
    "resetCampaignButton"
  ];

  postButtons.forEach((id) => {
    const button = getElement(id);
    if (!button) return;

    if (DEMO_MODE) {
      button.textContent = DEMO_ONLY_MESSAGE;
      button.disabled = true;
      button.classList.add("disabled");
    } else {
      button.disabled = false;
      button.classList.remove("disabled");
    }
  });

  applyRoleVisibility();
}

function buildApiUrl(path) {
  return path.startsWith("http") ? path : `${API_BASE}${path}`;
}

function formatApiErrorBody(body) {
  if (!body) return "";

  if (typeof body === "string") {
    return body;
  }

  const detail = body.detail || body.message || body.error;

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const location = Array.isArray(item.loc) ? item.loc.join(".") : "";
        const message = item.msg || JSON.stringify(item);
        return location ? `${location}: ${message}` : message;
      })
      .join("; ");
  }

  if (detail && typeof detail === "object") {
    return JSON.stringify(detail);
  }

  return detail || JSON.stringify(body);
}

function getApiErrorMessage(error, fallback = "Request failed.") {
  return error?.message || fallback;
}

async function apiFetch(path, options = {}) {
  const profiledRequest = withBusinessProfileRequest(path, options);
  path = profiledRequest.path;
  options = profiledRequest.options;

  const headers = new Headers(options.headers || {});
  const body = options.body;

  if (authToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${authToken}`);
  }

  if (body && !(body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const url = buildApiUrl(path);
  console.log("API request URL:", url);

  let response;
  try {
    response = await fetch(url, {
      ...options,
      headers
    });
  } catch (error) {
    console.error("API fetch failed:", error);
    throw new Error(error.message || "Network request failed.");
  }

  console.log("API response status:", response.status);

  const responseText = await response.text();
  console.log("API response body:", responseText);

  let responseBody = null;
  if (responseText) {
    try {
      responseBody = JSON.parse(responseText);
    } catch (error) {
      responseBody = responseText;
    }
  }

  if (response.status === 401) {
    clearAuth();
    showLoginGate("Please sign in again.");
  }

  if (!response.ok) {
    const backendMessage = formatApiErrorBody(responseBody);
    const fallbackMessage = `API request failed: ${response.status}`;
    const error = new Error(backendMessage || fallbackMessage);
    error.status = response.status;
    error.body = responseBody;
    throw error;
  }

  return responseBody;
}

async function fetchJson(path, options = {}) {
  return apiFetch(path, options);
}

function getDemoGeneratedEmail(firm) {
  const subject = demoTemplate.subject;
  const body = getTemplateBody(demoTemplate)
    .replaceAll("{firm_name}", firm?.firm_name || "your firm")
    .replaceAll("{city}", firm?.city || "your area")
    .replaceAll("{practice_area}", firm?.practice_area || "legal");

  return { subject, body };
}

function renderStats(stats, logs = logsCache) {
  setText("totalFirms", stats.total_firms ?? 0);
  setText("firmsWithEmails", stats.firms_with_emails ?? 0);
  setText("emailsSent", stats.emails_sent ?? 0);
  setText("notContacted", stats.not_contacted ?? 0);

  const sent = logs.filter((log) => log.status === "Sent").length;
  const failed = logs.filter((log) => log.status === "Failed").length;
  const total = sent + failed;
  const successRate = total === 0 ? 0 : Math.round((sent / total) * 100);
  setText("successRate", `${successRate}%`);
}

function formatPercent(value) {
  const number = Number(value || 0);
  return `${number.toFixed(1)}%`;
}

function renderAnalytics(analytics) {
  const displayAnalytics = applyManualCrmCounts(analytics);

  setText("analyticsTotalProspects", displayAnalytics.total_prospects ?? 0);
  setText("analyticsEmailsSent", displayAnalytics.emails_sent ?? 0);
  setText("analyticsReplies", displayAnalytics.replies ?? 0);
  setText("analyticsInterested", displayAnalytics.interested ?? 0);
  setText("analyticsMeetingsScheduled", displayAnalytics.meetings_scheduled ?? 0);
  setText("analyticsPartners", displayAnalytics.partners ?? 0);
  setText("analyticsNotInterested", displayAnalytics.not_interested ?? 0);
  setText("analyticsReplyRate", formatPercent(displayAnalytics.reply_rate));
  setText("analyticsInterestedRate", formatPercent(displayAnalytics.interested_rate));
  setText("analyticsPartnerConversionRate", formatPercent(displayAnalytics.partner_conversion_rate));
  renderManualCrmCountInputs();
}

function showCrmStatusMessage(message, type = "success") {
  const element = getElement("crmStatusMessage");
  if (!element) return;

  element.textContent = message;
  element.className = `crm-status-message ${type}`;
}

function renderManualCrmCountInputs() {
  const counts = manualCrmCountsCache;
  const interested = getElement("manualInterestedCount");
  const meetings = getElement("manualMeetingsCount");
  const partners = getElement("manualPartnersCount");
  const notInterested = getElement("manualNotInterestedCount");

  if (interested) interested.value = counts.interested;
  if (meetings) meetings.value = counts.meetings_scheduled;
  if (partners) partners.value = counts.partners;
  if (notInterested) notInterested.value = counts.not_interested;
}

function renderFirms(firms) {
  const table = getElement("firmsTable");
  if (!table) return;

  table.innerHTML = "";

  if (!firms.length) {
    table.innerHTML = `<tr><td colspan="6"><div class="table-state">No firms saved yet.</div></td></tr>`;
    return;
  }

  firms.forEach((firm) => {
    const hasEmail = Boolean(firm.email && firm.email !== "null");
    const website = normalizeUrl(firm.website);
    const sendButton =
      DEMO_MODE
        ? `<button class="button button-ghost" type="button" disabled>${DEMO_ONLY_MESSAGE}</button>`
        : hasEmail && firm.status === "Not Contacted" && hasRole("manager")
          ? `<button class="button button-ghost" type="button" onclick="sendOutreach(${firm.id})">Send Outreach</button>`
          : `<button class="button button-ghost" type="button" disabled>Unavailable</button>`;

    table.innerHTML += `
      <tr>
        <td>
          <div class="firm-cell">
            <strong>${escapeHtml(firm.firm_name || "Unknown Firm")}</strong>
            <span>${escapeHtml(firm.city || firm.practice_area || "No location saved")}</span>
          </div>
        </td>
        <td>${firm.email ? `<a href="mailto:${escapeHtml(firm.email)}">${escapeHtml(firm.email)}</a>` : `<span class="muted-cell">No email</span>`}</td>
        <td>${firm.phone ? `<a href="tel:${escapeHtml(firm.phone)}">${escapeHtml(firm.phone)}</a>` : `<span class="muted-cell">No phone</span>`}</td>
        <td>${website ? `<a href="${escapeHtml(website)}" target="_blank" rel="noopener">Open site</a>` : `<span class="muted-cell">No website</span>`}</td>
        <td>${statusBadge(firm.status)}</td>
        <td>
          <div class="actions">
            <button class="button button-ghost" type="button" onclick="previewLetter(${firm.id})">Preview Letter</button>
            ${sendButton}
          </div>
        </td>
      </tr>
    `;
  });
}

function renderLogs(logs) {
  const table = getElement("logsTable");
  if (!table) return;

  table.innerHTML = "";

  if (!logs.length) {
    table.innerHTML = `<tr><td colspan="5"><div class="table-state">No email logs yet.</div></td></tr>`;
    return;
  }

  const orderedLogs = logsNewestFirst ? logs.slice().reverse() : logs.slice();

  orderedLogs.forEach((log) => {
    const statusClass = log.status === "Sent" ? "sent" : "failed";
    const failureReason = log.failure_reason || log.error_message || "";

    table.innerHTML += `
      <tr>
        <td>${escapeHtml(log.firm_name || "Unknown")}</td>
        <td>${escapeHtml(log.email || "N/A")}</td>
        <td>
          <span class="status ${statusClass}">${escapeHtml(log.status || "N/A")}</span>
          ${failureReason ? `<div class="muted-cell">Failure Reason: ${escapeHtml(failureReason)}</div>` : ""}
        </td>
        <td>${escapeHtml(log.subject || "N/A")}</td>
        <td>${escapeHtml(formatLocalTimestamp(log.sent_at))}</td>
      </tr>
    `;
  });
}

function renderCampaignReport(data) {
  const report = getElement("campaignReport");
  if (!report) return;

  const metrics = [
    ["Firms Found From Search", data.searched_count],
    ["New Firms Saved", data.saved_count],
    ["Firms With Emails", data.eligible_count],
    ["Emails Sent", data.sent_count],
    ["Failed Sends", data.failed_count],
    ["Skipped No Email", data.skipped_no_email],
    ["Skipped Already Contacted", data.skipped_already_contacted],
    ["Skipped Other", data.skipped_other]
  ];
  const details = Array.isArray(data.details) ? data.details.slice(0, 12) : [];
  const hasNoSearchResults = Number(data.searched_count || 0) === 0;
  const failedCount = Number(data.failed_count || 0);
  const message = hasNoSearchResults
    ? "No firms were found for this search. Check the keyword, location, and Google Maps configuration, then try again."
    : failedCount > 0
      ? "Campaign finished with failed sends. Review the details below and the Email Logs table."
      : "Campaign finished. Counts below reflect search, save, eligibility, sending, and skipped outcomes.";

  report.innerHTML = `
    <div class="campaign-report-card">
      <div class="report-message ${hasNoSearchResults ? "warning" : failedCount > 0 ? "error" : "success"}">${escapeHtml(message)}</div>
      <div class="report-summary-grid campaign-summary-grid">
        ${metrics.map(([label, value]) => `
          <div class="report-metric">
            <span>${escapeHtml(label)}</span>
            <strong>${escapeHtml(value ?? 0)}</strong>
          </div>
        `).join("")}
      </div>
      ${details.length ? `
        <div class="campaign-detail-table">
          <table>
            <thead>
              <tr>
                <th>Prospect</th>
                <th>Email</th>
                <th>Outcome</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              ${details.map((item) => `
                <tr>
                  <td>${escapeHtml(item.firm || item.firm_name || "Unknown firm")}</td>
                  <td>${escapeHtml(item.email || "No email")}</td>
                  <td>${escapeHtml((item.outcome || "recorded").replaceAll("_", " "))}</td>
                  <td>${escapeHtml(item.error || item.reason || "Recorded")}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      ` : ""}
    </div>
  `;
}

function renderImportResults(data) {
  const results = getElement("importExcelResults");
  if (!results) return;

  const skippedRows = [...(data.duplicates || []), ...(data.missing_email || [])].slice(0, 12);

  results.innerHTML = `
    <div class="import-summary-grid">
      <div class="import-summary-card">
        <span>Imported</span>
        <strong>${data.imported_count ?? 0}</strong>
      </div>
      <div class="import-summary-card">
        <span>Duplicates</span>
        <strong>${data.duplicate_count ?? 0}</strong>
      </div>
      <div class="import-summary-card">
        <span>Missing Emails</span>
        <strong>${data.missing_email_count ?? 0}</strong>
      </div>
      <div class="import-summary-card">
        <span>Skipped</span>
        <strong>${data.skipped_count ?? 0}</strong>
      </div>
    </div>
    ${
      skippedRows.length
        ? `<span class="import-list-title">Skipped rows</span>
          <div class="import-detail-list">
            ${skippedRows.map((row) => `
              <div class="import-detail-row">
                <strong>Row ${escapeHtml(row.row || "")}</strong>
                <span>${escapeHtml(row.email || "No email")}</span>
                <span>${escapeHtml(row.reason || "Skipped")}</span>
              </div>
            `).join("")}
          </div>`
        : ""
    }
  `;
}

function normalizeUpdatedFirmCount(value) {
  if (Array.isArray(value)) return value.length;
  return Number(value || 0);
}

function renderReplyReport(data) {
  const message = getElement("replyTrackingMessage");
  const results = getElement("replyResults");
  const replies = Array.isArray(data?.replies) ? data.replies : [];
  replyReportCache = replies;

  setText("replyMessagesChecked", data?.checked_messages ?? 0);
  setText("replyRepliesFound", data?.replies_found ?? replies.length);
  setText("replyUpdatedFirms", normalizeUpdatedFirmCount(data?.updated_firms));
  setText("replyReplyRate", data?.reply_rate || "0.0%");

  if (message) {
    const statusMessage = data?.message || "Reply tracking check complete.";
    const searchHelper = data?.gmail_search_query
      ? `<small style="display:block;margin-top:4px;">Checked Gmail messages related to the outreach campaign.</small>`
      : "";
    message.innerHTML = `${escapeHtml(statusMessage)}${searchHelper}`;
    message.className = data?.success ? "reply-status success" : "reply-status error";
  }

  if (!results) return;

  if (!replies.length) {
    results.innerHTML = `<div class="reply-empty-state">No matching replies found yet.</div>`;
    return;
  }

  results.innerHTML = `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Firm</th>
            <th>From</th>
            <th>Subject</th>
            <th>Reply Date</th>
            <th>Snippet</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          ${replies.map((reply, index) => `
            <tr>
              <td>
                <div class="firm-cell">
                  <strong>${escapeHtml(reply.firm_name || "Unknown Firm")}</strong>
                  <span>${escapeHtml(reply.email || "No prospect email")}</span>
                </div>
              </td>
              <td>
                <div class="reply-from-cell">
                  <strong>${escapeHtml(reply.from_name || "Unknown sender")}</strong>
                  <span>${escapeHtml(reply.from_email || "No sender email")}</span>
                </div>
              </td>
              <td>
                <div class="reply-subject-cell">
                  <strong>${escapeHtml(reply.subject || "No subject")}</strong>
                  <button class="button button-ghost" type="button" onclick="openReplyDetails(${index})">View Reply Details</button>
                </div>
              </td>
              <td>${escapeHtml(reply.reply_date || "N/A")}</td>
              <td>
                <div class="reply-snippet-cell">
                  <span>${escapeHtml(reply.snippet || "No snippet available.")}</span>
                </div>
              </td>
              <td>${statusBadge(reply.status || "Replied")}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function formatDisplayDate(value) {
  return formatLocalTimestamp(value);
}

function renderFollowUps(data) {
  const prospects = Array.isArray(data?.prospects) ? data.prospects : [];
  const results = getElement("followUpResults");
  followUpsCache = prospects;

  setText("eligibleFollowUps", data?.eligible_count ?? prospects.length);
  setText("followUpsSent", data?.follow_ups_sent ?? 0);
  setText("followUpReplyRate", data?.reply_rate || "0.0%");

  if (!results) return;

  if (!prospects.length) {
    results.innerHTML = `<div class="follow-up-empty-state">No prospects are ready for follow-up yet.</div>`;
    return;
  }

  results.innerHTML = `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Firm</th>
            <th>Email</th>
            <th>Status</th>
            <th>Last Contacted</th>
            <th>Follow-Up Count</th>
            <th>Days Since Contact</th>
            <th>Next Follow-Up</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${prospects.map((prospect) => `
            <tr>
              <td>
                <div class="firm-cell">
                  <strong>${escapeHtml(prospect.firm_name || "Unknown Firm")}</strong>
                  <span>${escapeHtml(prospect.next_follow_up_type || "Follow-Up")}</span>
                </div>
              </td>
              <td>${prospect.email ? `<a href="mailto:${escapeHtml(prospect.email)}">${escapeHtml(prospect.email)}</a>` : `<span class="muted-cell">No email</span>`}</td>
              <td>${statusBadge(prospect.status)}</td>
              <td>${escapeHtml(formatDisplayDate(prospect.last_contacted))}</td>
              <td><span class="follow-up-count">${escapeHtml(prospect.follow_up_count ?? 0)}</span></td>
              <td>${escapeHtml(prospect.days_since_contact ?? "N/A")}</td>
              <td>${escapeHtml(prospect.next_follow_up_type || "N/A")}</td>
              <td>
                <button class="button button-ghost" type="button" onclick="sendFollowUp(${prospect.id})">
                  Send ${escapeHtml(prospect.next_follow_up_type || "Follow-Up")}
                </button>
              </td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function formatNewsletterDate(value) {
  return formatLocalTimestamp(value);
}

function renderNewsletterStats(stats) {
  setText("newsletterTotalContacts", stats?.total_newsletter_contacts ?? 0);
  setText("newsletterSentCount", stats?.newsletters_sent ?? 0);
  setText("newsletterLastSent", formatNewsletterDate(stats?.last_newsletter_sent));
  setText("newsletterBlockedCount", stats?.unsubscribed_do_not_contact ?? 0);
}

function newsletterEligibilityBadge(contact) {
  return contact.newsletter_eligible
    ? `<span class="status-badge status-sent">Eligible</span>`
    : `<span class="status-badge status-failed">Blocked</span>`;
}

function updateNewsletterSelectedCount() {
  setText("newsletterSelectedCount", `${selectedNewsletterContactIds.size} selected`);
}

function renderNewsletterContacts(contacts = newsletterContactsCache) {
  const table = getElement("newsletterContactsTable");
  if (!table) return;

  table.innerHTML = "";

  if (!contacts.length) {
    table.innerHTML = `<tr><td colspan="7"><div class="table-state">No newsletter contacts found.</div></td></tr>`;
    updateNewsletterSelectedCount();
    return;
  }

  contacts.forEach((contact) => {
    const checked = selectedNewsletterContactIds.has(contact.id) ? "checked" : "";
    const disabled = contact.newsletter_eligible ? "" : "disabled";

    table.innerHTML += `
      <tr>
        <td>
          <input class="newsletter-contact-checkbox" type="checkbox" value="${escapeHtml(contact.id)}" ${checked} ${disabled} aria-label="Select ${escapeHtml(contact.firm_name || "contact")}" />
        </td>
        <td>
          <div class="firm-cell">
            <strong>${escapeHtml(contact.firm_name || "Unknown")}</strong>
            <span>${escapeHtml(contact.source || "Contact")}</span>
          </div>
        </td>
        <td>${contact.email ? `<a href="mailto:${escapeHtml(contact.email)}">${escapeHtml(contact.email)}</a>` : `<span class="muted-cell">No email</span>`}</td>
        <td>${escapeHtml(contact.city || "N/A")}</td>
        <td>${escapeHtml(contact.type_category || "Contact")}</td>
        <td>${statusBadge(contact.status)}</td>
        <td>${newsletterEligibilityBadge(contact)}</td>
      </tr>
    `;
  });

  updateNewsletterSelectedCount();
}

function filterNewsletterContacts() {
  const query = getElement("newsletterContactFilter")?.value.trim().toLowerCase();

  if (!query) {
    renderNewsletterContacts(newsletterContactsCache);
    return;
  }

  renderNewsletterContacts(
    newsletterContactsCache.filter((contact) => {
      return [
        contact.firm_name,
        contact.email,
        contact.city,
        contact.type_category,
        contact.status,
        contact.source
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(query));
    })
  );
}

function getSelectedNewsletterAudience() {
  return document.querySelector('input[name="newsletterAudience"]:checked')?.value || "all";
}

function getNewsletterPayload() {
  return {
    title: getElement("newsletterTitle")?.value.trim() || "",
    subject: getElement("newsletterSubject")?.value.trim() || "",
    body_text: getElement("newsletterBody")?.value.trim() || "",
    call_to_action: getElement("newsletterCta")?.value.trim() || "",
    audience: getSelectedNewsletterAudience(),
    statuses: Array.from(document.querySelectorAll(".newsletter-status-checkbox:checked")).map((input) => input.value),
    contact_ids: Array.from(selectedNewsletterContactIds),
    send_limit: Number(getElement("newsletterSendLimit")?.value || 25),
    delay_seconds: Number(getElement("newsletterDelaySeconds")?.value || 10),
    confirmed: getElement("newsletterConfirmSend")?.checked ?? false
  };
}

function validateNewsletterFields(payload, requireConfirmation = false) {
  if (!payload.title || !payload.subject || !payload.body_text) {
    return "Please enter a newsletter title, subject line, and message body.";
  }

  if (payload.audience === "status" && !payload.statuses.length) {
    return "Choose at least one prospect status for the newsletter audience.";
  }

  if (payload.audience === "selected" && !payload.contact_ids.length) {
    return "Select at least one eligible contact from the table.";
  }

  if (requireConfirmation && !payload.confirmed) {
    return "Check the confirmation box before sending this newsletter.";
  }

  return "";
}

function showNewsletterMessage(message, type = "") {
  const element = getElement("newsletterMessage");
  if (!element) return;

  element.textContent = message;
  element.className = `inline-feedback ${type}`.trim();
}

function renderNewsletterReport(data) {
  const report = getElement("newsletterReport");
  if (!report) return;

  const list = (items, emptyText) => items?.length
    ? items.slice(0, 12).map((item) => `
      <div class="report-item">
        <div>
          <strong>${escapeHtml(item.firm_name || "Unknown")}</strong>
          <span>${escapeHtml(item.email || "No email")}</span>
        </div>
        <span class="report-reason">${escapeHtml(item.reason || item.error || item.status || "")}</span>
      </div>
    `).join("")
    : `<div class="report-item"><span>${escapeHtml(emptyText)}</span></div>`;

  report.innerHTML = `
    <div class="report-summary-grid">
      <div class="report-metric"><span>Sent</span><strong>${data.sent_count ?? 0}</strong></div>
      <div class="report-metric"><span>Failed</span><strong>${data.failed_count ?? 0}</strong></div>
      <div class="report-metric"><span>Skipped</span><strong>${data.skipped_count ?? 0}</strong></div>
    </div>
    <div class="report-message">${escapeHtml(data.message || "Newsletter report ready.")}</div>
    <div class="report-lists">
      <div class="report-list">
        <div class="report-list-title"><strong>Sent</strong><span>${data.sent_count ?? 0}</span></div>
        <div class="report-items">${list(data.sent || [], "No sent contacts.")}</div>
      </div>
      <div class="report-list">
        <div class="report-list-title"><strong>Failed</strong><span>${data.failed_count ?? 0}</span></div>
        <div class="report-items">${list(data.failed || [], "No failed contacts.")}</div>
      </div>
      <div class="report-list">
        <div class="report-list-title"><strong>Skipped</strong><span>${data.skipped_count ?? 0}</span></div>
        <div class="report-items">${list(data.skipped || [], "No skipped contacts.")}</div>
      </div>
    </div>
  `;
}

function selectEligibleNewsletterContacts() {
  newsletterContactsCache.forEach((contact) => {
    if (contact.newsletter_eligible) {
      selectedNewsletterContactIds.add(contact.id);
    }
  });
  renderNewsletterContacts();
}

function clearNewsletterSelection() {
  selectedNewsletterContactIds.clear();
  renderNewsletterContacts();
}

function renderAutoFollowUpSettings(settings, followUps = null) {
  const normalized = {
    enabled: Boolean(settings?.enabled),
    daily_limit: settings?.daily_limit ?? 5,
    delay_seconds: settings?.delay_seconds ?? 10
  };
  autoFollowUpSettingsCache = normalized;

  const enabledInput = getElement("autoFollowUpEnabled");
  const limitInput = getElement("autoFollowUpLimit");
  const delayInput = getElement("autoFollowUpDelaySeconds");
  const badge = getElement("autoFollowUpStatusBadge");

  if (enabledInput) enabledInput.checked = normalized.enabled;
  if (limitInput) limitInput.value = normalized.daily_limit;
  if (delayInput) delayInput.value = normalized.delay_seconds;

  setText("autoFollowUpStatus", normalized.enabled ? "Enabled" : "Disabled");
  setText("autoFollowUpDailyLimit", normalized.daily_limit);
  setText("autoFollowUpDelay", `${normalized.delay_seconds}s`);
  setText("autoEligibleFollowUps", followUps?.eligible_count ?? followUpsCache.length ?? 0);

  if (badge) {
    badge.textContent = normalized.enabled ? "Enabled" : "Disabled";
    badge.classList.toggle("status-sent", normalized.enabled);
    badge.classList.toggle("status-pending", !normalized.enabled);
  }
}

function renderTemplate(template) {
  activeTemplate = template || demoTemplate;
  setText("templateId", activeTemplate.id || "");

  const templateId = getElement("templateId");
  const templateName = getElement("templateName");
  const templateSubject = getElement("templateSubject");
  const templateBodyField = getElement("templateBody");

  if (templateId) templateId.value = activeTemplate.id || "";
  if (templateName) templateName.value = activeTemplate.name || "";
  if (templateSubject) templateSubject.value = activeTemplate.subject || "";
  if (templateBodyField) templateBodyField.value = getTemplateBody(activeTemplate);
}

function showBackendUnavailable(error) {
  backendConnected = false;
  setBackendUnavailableStatus();

  const errorMessage = getBackendUnavailableMessage();
  const details = error?.message ? ` (${error.message})` : "";

  const firmsTable = getElement("firmsTable");
  const logsTable = getElement("logsTable");
  const newsletterTable = getElement("newsletterContactsTable");

  if (firmsTable) {
    firmsTable.innerHTML = `<tr><td colspan="6"><div class="table-state">${escapeHtml(errorMessage + details)}</div></td></tr>`;
  }

  if (logsTable) {
    logsTable.innerHTML = `<tr><td colspan="5"><div class="table-state">${escapeHtml(errorMessage + details)}</div></td></tr>`;
  }

  if (newsletterTable) {
    newsletterTable.innerHTML = `<tr><td colspan="7"><div class="table-state">${escapeHtml(errorMessage + details)}</div></td></tr>`;
  }

  setText("searchMessage", errorMessage);
  setText("batchMessage", errorMessage);
  setText("followUpMessage", errorMessage);
  showNewsletterMessage(errorMessage, "error");
  renderFollowUps(demoFollowUps);
  renderAutoFollowUpSettings(demoAutoFollowUpSettings, demoFollowUps);
  renderNewsletterStats({ total_newsletter_contacts: 0, newsletters_sent: 0, last_newsletter_sent: null, unsubscribed_do_not_contact: 0 });
  const autoResult = getElement("autoFollowUpResult");
  if (autoResult) {
    autoResult.textContent = errorMessage;
    autoResult.className = "auto-follow-up-result error";
  }
  renderStats({ total_firms: 0, firms_with_emails: 0, emails_sent: 0, not_contacted: 0 }, []);
  renderAnalytics({
    total_prospects: 0,
    emails_sent: 0,
    replies: 0,
    interested: 0,
    meetings_scheduled: 0,
    partners: 0,
    not_interested: 0,
    reply_rate: 0,
    interested_rate: 0,
    partner_conversion_rate: 0
  });
}

async function loadStats() {
  if (DEMO_MODE) {
    return calculateStats(demoFirms, demoLogs);
  }

  return fetchJson("/firms/stats/");
}

async function loadAnalytics() {
  if (DEMO_MODE) {
    return calculateAnalytics(demoFirms, demoLogs);
  }

  return fetchJson("/firms/analytics/");
}

async function loadFirms() {
  if (DEMO_MODE) {
    return demoFirms;
  }

  return fetchJson("/firms/");
}

async function loadLogs() {
  if (DEMO_MODE) {
    return demoLogs;
  }

  if (!hasRole("manager")) {
    return [];
  }

  return fetchJson("/firms/email-logs/");
}

async function loadFollowUps() {
  if (DEMO_MODE) {
    return demoFollowUps;
  }

  return fetchJson("/firms/follow-ups/");
}

async function loadAutoFollowUpSettings() {
  if (DEMO_MODE) {
    return demoAutoFollowUpSettings;
  }

  return fetchJson("/firms/auto-follow-up-settings/");
}

async function loadNewsletterStats() {
  if (DEMO_MODE) {
    return demoNewsletterStats;
  }

  return fetchJson("/newsletters/stats/");
}

async function loadNewsletterContacts() {
  if (DEMO_MODE) {
    return demoFirms.map((firm) => ({
      id: firm.id,
      firm_name: firm.firm_name,
      email: firm.email,
      city: firm.city,
      type_category: firm.practice_area || "Prospect",
      status: firm.status,
      newsletter_eligible: Boolean(firm.email) && !["Not Interested", "Do Not Contact"].includes(firm.status),
      source: firm.practice_area === "Imported Contact" ? "Imported" : "Prospect"
    }));
  }

  return fetchJson("/newsletters/contacts/");
}

async function loadUsers() {
  if (!hasRole("admin")) return [];
  return fetchJson("/users/");
}

async function loadBusinessProfiles() {
  if (!hasRole("admin")) return [];
  return fetchJson("/business-profiles/");
}

async function loadAuditLogs() {
  if (!hasRole("admin")) return [];
  return fetchJson("/audit-logs/?limit=100");
}

function renderBusinessProfiles(profiles) {
  const table = getElement("businessProfilesTable");
  if (!table) return;

  if (!profiles.length) {
    table.innerHTML = `<tr><td colspan="5"><div class="table-state">No business profiles found.</div></td></tr>`;
    return;
  }

  table.innerHTML = profiles.map((profile) => `
    <tr>
      <td>${escapeHtml(profile.name)}</td>
      <td>${escapeHtml(profile.sender_email || "Not set")}</td>
      <td>
        <div class="firm-cell">
          <strong>${escapeHtml(profile.gmail_credentials_env_key || "Not set")}</strong>
          <span>${escapeHtml(profile.gmail_token_env_key || "Not set")}</span>
        </div>
      </td>
      <td>${statusBadge(profile.is_active ? "Active" : "Disabled")}</td>
      <td>
        <button class="button button-ghost business-profile-edit-button" type="button" data-profile-id="${profile.id}">Edit</button>
        <button class="button button-danger business-profile-disable-button" type="button" data-profile-id="${profile.id}" ${profile.name === "Green Light Drivers Ed & DUI School LLC" ? "disabled" : ""}>Disable</button>
      </td>
    </tr>
  `).join("");
}

function clearBusinessProfileForm() {
  getElement("businessProfileForm")?.reset();
  const id = getElement("businessProfileId");
  const active = getElement("businessProfileActive");
  if (id) id.value = "";
  if (active) active.checked = true;
}

function editBusinessProfile(profileId) {
  const profile = businessProfilesCache.find((item) => item.id === Number(profileId));
  if (!profile) return;

  const fields = {
    businessProfileId: profile.id,
    businessProfileName: profile.name || "",
    businessProfileSenderEmail: profile.sender_email || "",
    businessProfilePhone: profile.phone || "",
    businessProfileWebsite: profile.website || "",
    businessProfileCredentialsEnv: profile.gmail_credentials_env_key || "",
    businessProfileTokenEnv: profile.gmail_token_env_key || "",
    businessProfileAddress: profile.address || "",
    businessProfileDefaultSubject: profile.default_template_subject || "",
    businessProfileDefaultBody: profile.default_template_body || ""
  };

  Object.entries(fields).forEach(([id, value]) => {
    const element = getElement(id);
    if (element) element.value = value;
  });

  const active = getElement("businessProfileActive");
  if (active) active.checked = Boolean(profile.is_active);
}

function getBusinessProfilePayloadFromForm() {
  return {
    name: getElement("businessProfileName")?.value.trim() || "",
    sender_email: getElement("businessProfileSenderEmail")?.value.trim() || null,
    phone: getElement("businessProfilePhone")?.value.trim() || null,
    website: getElement("businessProfileWebsite")?.value.trim() || null,
    address: getElement("businessProfileAddress")?.value.trim() || null,
    default_template_subject: getElement("businessProfileDefaultSubject")?.value.trim() || null,
    default_template_body: getElement("businessProfileDefaultBody")?.value.trim() || null,
    gmail_credentials_env_key: getElement("businessProfileCredentialsEnv")?.value.trim() || null,
    gmail_token_env_key: getElement("businessProfileTokenEnv")?.value.trim() || null,
    is_active: getElement("businessProfileActive")?.checked ?? true
  };
}

async function saveBusinessProfile(event) {
  event.preventDefault();
  const message = getElement("businessProfileMessage");
  const profileId = getElement("businessProfileId")?.value;
  const payload = getBusinessProfilePayloadFromForm();

  if (!payload.name) {
    if (message) message.textContent = "Business profile name is required.";
    return;
  }

  try {
    await fetchJson(profileId ? `/business-profiles/${profileId}` : "/business-profiles/", {
      method: profileId ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (message) message.textContent = "Business profile saved.";
    clearBusinessProfileForm();
    await initializeBusinessProfiles();
    await refreshAdminData();
  } catch (error) {
    if (message) message.textContent = error.message || "Unable to save business profile.";
  }
}

async function disableBusinessProfile(profileId) {
  const message = getElement("businessProfileMessage");
  const confirmed = confirm("Disable this business profile?");
  if (!confirmed) return;

  try {
    await fetchJson(`/business-profiles/${profileId}`, { method: "DELETE" });
    if (message) message.textContent = "Business profile disabled.";
    await initializeBusinessProfiles();
    await refreshAdminData();
  } catch (error) {
    if (message) message.textContent = error.message || "Unable to disable business profile.";
  }
}

function renderUsers(users) {
  const table = getElement("usersTable");
  if (!table) return;

  if (!users.length) {
    table.innerHTML = `<tr><td colspan="6"><div class="table-state">No users found.</div></td></tr>`;
    return;
  }

  table.innerHTML = users.map((user) => `
    <tr>
      <td>${escapeHtml(user.email)}</td>
      <td>
        <input class="user-name-input" data-user-id="${user.id}" type="text" value="${escapeHtml(user.full_name || "")}" placeholder="Full name" />
      </td>
      <td>
        <select class="role-select" data-user-id="${user.id}" ${user.id === currentUser?.id ? "disabled" : ""}>
          ${["admin", "manager", "staff"].map((role) => `<option value="${role}" ${user.role === role ? "selected" : ""}>${role}</option>`).join("")}
        </select>
      </td>
      <td>${statusBadge(user.is_active ? "Active" : "Disabled")}</td>
      <td>${escapeHtml(formatLocalTimestamp(user.last_login_at))}</td>
      <td>
        <button class="button button-ghost user-toggle-button" type="button" data-user-id="${user.id}" data-active="${user.is_active}" ${user.id === currentUser?.id ? "disabled" : ""}>
          ${user.is_active ? "Disable" : "Enable"}
        </button>
        <button class="button button-ghost user-reset-password-button" type="button" data-user-id="${user.id}">
          Reset Password
        </button>
        <button class="button button-danger user-delete-button" type="button" data-user-id="${user.id}" ${user.id === currentUser?.id ? "disabled" : ""}>
          Delete
        </button>
      </td>
    </tr>
  `).join("");
}

function renderAuditLogs(logs) {
  const table = getElement("auditLogsTable");
  if (!table) return;

  if (!logs.length) {
    table.innerHTML = `<tr><td colspan="5"><div class="table-state">No audit events yet.</div></td></tr>`;
    return;
  }

  table.innerHTML = logs.map((log) => `
    <tr>
      <td>${escapeHtml(formatLocalTimestamp(log.created_at))}</td>
      <td>${escapeHtml(log.event_type)}</td>
      <td>${escapeHtml(log.actor_email || "System")}</td>
      <td>${escapeHtml([log.target_type, log.target_id].filter(Boolean).join(" #") || "N/A")}</td>
      <td>${escapeHtml(log.ip_address || "N/A")}</td>
    </tr>
  `).join("");
}

function generateClientPassword(length = 18) {
  const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%^&*";
  const cryptoRef = window.crypto || window.msCrypto;
  const values = new Uint32Array(length);
  cryptoRef.getRandomValues(values);
  return Array.from(values, (value) => alphabet[value % alphabet.length]).join("");
}

function accountDetailsText(account) {
  return `Green Light Outreach Login Details

Name: ${account.full_name || ""}
Email: ${account.email || ""}
Role: ${account.role || ""}
Temporary Password: ${account.temporary_password || ""}
Login URL: ${window.location.href.split("#")[0]}

Please log in and change your password after first access.`;
}

function showAccountDetails(user, temporaryPassword) {
  const card = getElement("accountDetailsCard");
  const details = getElement("accountDetailsText");
  if (!card || !details) return;

  const account = { ...user, temporary_password: temporaryPassword };
  details.textContent = accountDetailsText(account);
  card.hidden = false;
}

async function copyAccountDetails() {
  const details = getElement("accountDetailsText")?.textContent || "";
  const message = getElement("userManagementMessage");
  if (!details) return;

  try {
    await navigator.clipboard.writeText(details);
    if (message) message.textContent = "Account details copied.";
  } catch (error) {
    if (message) message.textContent = "Unable to copy automatically. Select and copy the details manually.";
  }
}

async function createUser(event) {
  event.preventDefault();
  const message = getElement("userManagementMessage");
  const payload = {
    email: getElement("newUserEmail")?.value.trim(),
    full_name: getElement("newUserName")?.value.trim() || null,
    role: getElement("newUserRole")?.value || "staff",
    password: getElement("newUserPassword")?.value || ""
  };

  try {
    const data = await fetchJson("/users/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    getElement("userCreateForm")?.reset();
    showAccountDetails(data.user, data.temporary_password);
    if (message) message.textContent = "User created. Temporary password is shown once.";
    await refreshAdminData();
  } catch (error) {
    if (message) message.textContent = error.message || "Unable to create user.";
  }
}

async function updateUser(userId, updates) {
  const message = getElement("userManagementMessage");
  try {
    await fetchJson(`/users/${userId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates)
    });
    if (message) message.textContent = "User updated.";
    await refreshAdminData();
  } catch (error) {
    if (message) message.textContent = error.message || "Unable to update user.";
  }
}

async function resetUserPassword(userId) {
  const message = getElement("userManagementMessage");
  try {
    const data = await fetchJson(`/users/${userId}/reset-password`, { method: "POST" });
    showAccountDetails(data.user, data.temporary_password);
    if (message) message.textContent = "Password reset. Temporary password is shown once.";
    await refreshAdminData();
  } catch (error) {
    if (message) message.textContent = error.message || "Unable to reset password.";
  }
}

async function deleteUser(userId) {
  const message = getElement("userManagementMessage");
  const confirmed = confirm("Delete this user account?");
  if (!confirmed) return;

  try {
    await fetchJson(`/users/${userId}`, { method: "DELETE" });
    if (message) message.textContent = "User deleted.";
    await refreshAdminData();
  } catch (error) {
    if (message) message.textContent = error.message || "Unable to delete user.";
  }
}

async function refreshAdminData() {
  if (!hasRole("admin")) return;
  const [users, auditLogs, businessProfiles] = await Promise.all([loadUsers(), loadAuditLogs(), loadBusinessProfiles()]);
  usersCache = users;
  auditLogsCache = auditLogs;
  businessProfilesCache = businessProfiles;
  renderUsers(usersCache);
  renderAuditLogs(auditLogsCache);
  renderBusinessProfiles(businessProfilesCache);
}

async function updateFirmStatus(firmId, status) {
  if (DEMO_MODE) {
    showCrmStatusMessage(DEMO_ONLY_MESSAGE, "error");
    return;
  }

  if (!CRM_STATUSES.includes(status)) {
    showCrmStatusMessage("Invalid prospect status.", "error");
    await loadDashboard();
    return;
  }

  try {
    await fetchJson(`/firms/${firmId}/status`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status })
    });
    await loadDashboard();
    showCrmStatusMessage("Status updated.", "success");
  } catch (error) {
    showCrmStatusMessage(getApiErrorMessage(error, "Unable to update status. Please refresh and try again."), "error");
    setBackendUnavailableStatus();
    await loadDashboard();
  }
}

async function saveManualCrmCountsFromForm() {
  saveManualCrmCounts({
    interested: getElement("manualInterestedCount")?.value,
    meetings_scheduled: getElement("manualMeetingsCount")?.value,
    partners: getElement("manualPartnersCount")?.value,
    not_interested: getElement("manualNotInterestedCount")?.value
  });

  showCrmStatusMessage("CRM counts saved.", "success");
  await loadDashboard();
  showCrmStatusMessage("CRM counts saved.", "success");
}

async function saveAutoFollowUpSettings() {
  const result = getElement("autoFollowUpResult");

  if (DEMO_MODE) {
    if (result) {
      result.textContent = DEMO_ONLY_MESSAGE;
      result.className = "auto-follow-up-result error";
    }
    return;
  }

  const settings = {
    enabled: getElement("autoFollowUpEnabled")?.checked ?? false,
    daily_limit: Number(getElement("autoFollowUpLimit")?.value || 5),
    delay_seconds: Number(getElement("autoFollowUpDelaySeconds")?.value || 10)
  };

  if (result) {
    result.textContent = "Saving automatic follow-up settings...";
    result.className = "auto-follow-up-result";
  }

  try {
    const savedSettings = await fetchJson("/firms/auto-follow-up-settings/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings)
    });

    renderAutoFollowUpSettings(savedSettings, {
      eligible_count: followUpsCache.length
    });

    if (result) {
      result.textContent = "Automatic follow-up settings saved.";
      result.className = "auto-follow-up-result success";
    }
  } catch (error) {
    if (result) {
      result.textContent = getApiErrorMessage(error, "Unable to save automatic follow-up settings.");
      result.className = "auto-follow-up-result error";
    }
  }
}

async function runAutoFollowUps() {
  const result = getElement("autoFollowUpResult");

  if (DEMO_MODE) {
    if (result) {
      result.textContent = DEMO_ONLY_MESSAGE;
      result.className = "auto-follow-up-result error";
    }
    return;
  }

  const confirmed = confirm("Run automatic follow-ups now for eligible prospects?");
  if (!confirmed) return;

  if (result) {
    result.textContent = "Running automatic follow-ups...";
    result.className = "auto-follow-up-result";
  }

  try {
    const data = await fetchJson("/firms/run-auto-follow-ups/", { method: "POST" });

    if (result) {
      result.textContent = `${data.message || "Automatic follow-up run complete."} Sent: ${data.sent_count ?? 0}, Failed: ${data.failed_count ?? 0}, Skipped: ${data.skipped_count ?? 0}.`;
      result.className = data.success ? "auto-follow-up-result success" : "auto-follow-up-result error";
    }

    await loadDashboard();
  } catch (error) {
    if (result) {
      result.textContent = getApiErrorMessage(error, "Automatic follow-up run failed. Make sure backend is running.");
      result.className = "auto-follow-up-result error";
    }
    setBackendUnavailableStatus();
  }
}

async function checkReplies() {
  const button = getElement("checkRepliesButton");
  const message = getElement("replyTrackingMessage");

  if (DEMO_MODE) {
    renderReplyReport({
      success: true,
      checked_messages: 0,
      replies_found: 0,
      updated_firms: 0,
      reply_rate: "0.0%",
      replies: [],
      message: "Reply tracking is available in live mode only."
    });
    return;
  }

  if (message) {
    message.textContent = "Checking reply tracking configuration...";
    message.className = "reply-status";
  }

  if (button) {
    button.disabled = true;
    button.classList.add("is-loading");
  }

  try {
    const data = await fetchJson("/firms/check-replies/");
    renderReplyReport(data);

    if (data.success) {
      await loadDashboard();
    }
  } catch (error) {
    if (message) {
      message.textContent = getApiErrorMessage(error, `Unable to check reply tracking. ${getBackendUnavailableMessage()}`);
      message.className = "reply-status error";
    }
    setBackendUnavailableStatus();
  } finally {
    if (button) {
      button.disabled = false;
      button.classList.remove("is-loading");
    }
  }
}

function openReplyDetails(index) {
  const reply = replyReportCache[index];
  const modal = getElement("replyDetailsModal");

  if (!reply || !modal) return;

  setText("replyDetailFirm", `${reply.firm_name || "Unknown Firm"} (${reply.email || "No prospect email"})`);
  setText("replyDetailFrom", `${reply.from_name || "Unknown sender"} <${reply.from_email || "No sender email"}>`);
  setText("replyDetailSubject", reply.subject || "No subject");
  setText("replyDetailDate", reply.reply_date || "N/A");
  setText("replyDetailSnippet", reply.snippet || "No snippet available.");

  modal.classList.add("is-open");
  modal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
}

function closeReplyDetailsModal() {
  const modal = getElement("replyDetailsModal");
  if (!modal) return;

  modal.classList.remove("is-open");
  modal.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
}

async function loadTemplate() {
  if (DEMO_MODE) {
    return demoTemplate;
  }

  try {
    const template = await fetchJson("/templates/active/");
    return template || demoTemplate;
  } catch (error) {
    return demoTemplate;
  }
}

async function loadDashboard() {
  setActionButtonsForMode();

  if (DEMO_MODE) {
    backendConnected = false;
    firmsCache = demoFirms;
    logsCache = demoLogs;
    renderStats(calculateStats(firmsCache, logsCache), logsCache);
    renderAnalytics(calculateAnalytics(firmsCache, logsCache));
    renderFirms(firmsCache);
    renderLogs(logsCache);
    renderFollowUps(demoFollowUps);
    renderAutoFollowUpSettings(demoAutoFollowUpSettings, demoFollowUps);
    newsletterContactsCache = await loadNewsletterContacts();
    renderNewsletterStats(demoNewsletterStats);
    renderNewsletterContacts(newsletterContactsCache);
    renderTemplate(demoTemplate);
    setSystemStatus("Demo Mode", "GitHub Pages sample data. Live sending is disabled.");
    return;
  }

  setSystemStatus("Checking API", `Connecting to ${API_BASE}`);

  try {
    const [stats, analytics, firms, logs, template, followUps, autoFollowUpSettings, newsletterStats, newsletterContacts] = await Promise.all([
      loadStats(),
      loadAnalytics(),
      loadFirms(),
      loadLogs(),
      loadTemplate(),
      loadFollowUps(),
      loadAutoFollowUpSettings(),
      loadNewsletterStats(),
      loadNewsletterContacts()
    ]);

    backendConnected = true;
    firmsCache = firms;
    logsCache = logs;
    renderStats(stats, logsCache);
    renderAnalytics(analytics);
    renderFirms(firmsCache);
    renderLogs(logsCache);
    renderFollowUps(followUps);
    renderAutoFollowUpSettings(autoFollowUpSettings, followUps);
    newsletterContactsCache = newsletterContacts;
    renderNewsletterStats(newsletterStats);
    renderNewsletterContacts(newsletterContactsCache);
    renderTemplate(template);
    await refreshAdminData();
    setSystemStatus("Local Backend Connected", `Using FastAPI data from ${API_BASE}`);
    setText("searchMessage", "");
    setText("batchMessage", "Ready to send controlled outreach to eligible prospects.");
  } catch (error) {
    showBackendUnavailable(error);
  }
}

async function searchAndSaveFirms() {
  const keyword = getElement("keywordInput")?.value.trim();
  const city = getElement("cityInput")?.value.trim();
  const state = getElement("stateInput")?.value.trim();
  const message = getElement("searchMessage");

  if (DEMO_MODE) {
    if (message) message.textContent = DEMO_ONLY_MESSAGE;
    return;
  }

  if (!keyword || !city || !state) {
    if (message) message.textContent = "Please fill in keyword, city, and state.";
    return;
  }

  if (message) message.textContent = "Searching and saving firms...";

  try {
    const data = await fetchJson(
      `/firms/search-and-save/?keyword=${encodeURIComponent(keyword)}&city=${encodeURIComponent(city)}&state=${encodeURIComponent(state)}`,
      { method: "POST" }
    );

    if (message) message.textContent = `Saved/loaded ${data.length} firms.`;
    await loadDashboard();
  } catch (error) {
    if (message) message.textContent = getApiErrorMessage(error, "Search failed. Make sure backend is running.");
    setBackendUnavailableStatus();
  }
}

async function runCampaign() {
  const report = getElement("campaignReport");

  if (DEMO_MODE) {
    if (report) report.textContent = DEMO_ONLY_MESSAGE;
    return;
  }

  const keyword = getElement("campaignKeyword")?.value.trim();
  const city = getElement("campaignCity")?.value.trim();
  const state = getElement("campaignState")?.value.trim();
  const limit = getElement("campaignLimit")?.value || 3;
  const delaySeconds = getElement("campaignDelay")?.value || 10;
  const sendImmediately = getElement("campaignSendImmediately")?.checked ?? true;

  if (!keyword || !city || !state) {
    if (report) report.textContent = "Please fill in keyword, city, and state.";
    return;
  }

  if (report) {
    report.innerHTML = `
      <div class="report-empty">
        <strong>Running campaign</strong>
        <span>Searching, saving prospects, checking eligibility, and preparing outreach counts...</span>
      </div>
    `;
  }

  try {
    const data = await fetchJson(
      `/firms/run-campaign/?keyword=${encodeURIComponent(keyword)}&city=${encodeURIComponent(city)}&state=${encodeURIComponent(state)}&limit=${encodeURIComponent(limit)}&delay_seconds=${encodeURIComponent(delaySeconds)}&send_immediately=${sendImmediately}`,
      { method: "POST" }
    );

    renderCampaignReport(data);
    await loadDashboard();
  } catch (error) {
    if (report) {
      report.innerHTML = `
        <div class="report-empty report-error">
          <strong>Campaign failed</strong>
          <span>${escapeHtml(error.message || "Campaign failed. Make sure backend is running and Google Maps search is configured.")}</span>
        </div>
      `;
    }
    setBackendUnavailableStatus();
  }
}

async function previewNewsletter() {
  const payload = getNewsletterPayload();
  const errorMessage = validateNewsletterFields(payload);
  const preview = getElement("newsletterPreview");

  if (errorMessage) {
    showNewsletterMessage(errorMessage, "error");
    return;
  }

  if (DEMO_MODE) {
    setText("newsletterPreviewSubject", payload.subject);
    writeFrame("newsletterPreviewFrame", emailHtmlFromText(`${payload.title}\n\n${payload.body_text}\n\n${payload.call_to_action}`));
    if (preview) preview.hidden = false;
    showNewsletterMessage(DEMO_ONLY_MESSAGE, "error");
    return;
  }

  showNewsletterMessage("Generating newsletter preview...");

  try {
    const data = await fetchJson("/newsletters/preview/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    setText("newsletterPreviewSubject", data.subject || payload.subject);
    writeFrame("newsletterPreviewFrame", data.html || "");
    if (preview) preview.hidden = false;
    showNewsletterMessage("Newsletter preview ready.", "success");
  } catch (error) {
    showNewsletterMessage(getApiErrorMessage(error, "Unable to preview newsletter. Make sure backend is running."), "error");
    setBackendUnavailableStatus();
  }
}

async function saveNewsletterDraft() {
  const payload = getNewsletterPayload();
  const errorMessage = validateNewsletterFields(payload);

  if (DEMO_MODE) {
    showNewsletterMessage(DEMO_ONLY_MESSAGE, "error");
    return;
  }

  if (errorMessage) {
    showNewsletterMessage(errorMessage, "error");
    return;
  }

  showNewsletterMessage("Saving newsletter draft...");

  try {
    const data = await fetchJson("/newsletters/draft/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    showNewsletterMessage(data.message || "Newsletter draft saved.", "success");
  } catch (error) {
    showNewsletterMessage(getApiErrorMessage(error, "Unable to save newsletter draft. Make sure backend is running."), "error");
    setBackendUnavailableStatus();
  }
}

async function sendNewsletter() {
  const payload = getNewsletterPayload();
  const errorMessage = validateNewsletterFields(payload, true);
  const button = getElement("newsletterSendButton");

  if (DEMO_MODE) {
    showNewsletterMessage(DEMO_ONLY_MESSAGE, "error");
    return;
  }

  if (errorMessage) {
    showNewsletterMessage(errorMessage, "error");
    return;
  }

  const confirmed = confirm(`Send newsletter to the selected audience? Limit: ${payload.send_limit}, Delay: ${payload.delay_seconds}s`);
  if (!confirmed) return;

  showNewsletterMessage("Sending newsletter...");
  if (button) {
    button.disabled = true;
    button.classList.add("is-loading");
  }

  try {
    const data = await fetchJson("/newsletters/send/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    renderNewsletterReport(data);
    showNewsletterMessage(data.message || "Newsletter send complete.", data.failed_count ? "error" : "success");
    await loadDashboard();
  } catch (error) {
    showNewsletterMessage(getApiErrorMessage(error, "Newsletter send failed. Make sure backend is running and Gmail settings are configured."), "error");
    setBackendUnavailableStatus();
  } finally {
    if (button) {
      button.disabled = false;
      button.classList.remove("is-loading");
    }
  }
}

async function addManualProspect() {
  const form = getElement("manualAddForm");
  const message = getElement("manualAddMessage");
  const button = getElement("manualAddButton");
  const firmName = getElement("manualFirmName")?.value.trim();
  const email = getElement("manualEmail")?.value.trim();
  const phone = getElement("manualPhone")?.value.trim();
  const website = getElement("manualWebsite")?.value.trim();
  const city = getElement("manualCity")?.value.trim();
  const prospectType = getElement("manualProspectType")?.value.trim();

  if (DEMO_MODE) {
    if (message) message.textContent = DEMO_ONLY_MESSAGE;
    return;
  }

  if (!firmName || !email) {
    if (message) {
      message.textContent = "Please enter a company name and email address.";
      message.className = "inline-feedback error";
    }
    return;
  }

  if (message) {
    message.textContent = "Adding prospect...";
    message.className = "inline-feedback";
  }

  if (button) {
    button.disabled = true;
    button.classList.add("is-loading");
  }

  try {
    await fetchJson("/firms/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        firm_name: firmName,
        email,
        phone: phone || null,
        website: website || null,
        city: city || null,
        practice_area: prospectType || null,
        status: "Not Contacted"
      })
    });

    if (form) form.reset();
    if (message) {
      message.textContent = "Prospect added successfully.";
      message.className = "inline-feedback success";
    }
    await loadDashboard();
  } catch (error) {
    if (message) {
      message.textContent = getApiErrorMessage(error, "Unable to add prospect. Please try again.");
      message.className = "inline-feedback error";
    }
  } finally {
    if (button) {
      button.disabled = false;
      button.classList.remove("is-loading");
    }
  }
}

async function importExcelDatabase() {
  const fileInput = getElement("excelFileInput");
  const message = getElement("importExcelMessage");
  const button = getElement("importExcelButton");
  const results = getElement("importExcelResults");
  const file = fileInput?.files?.[0];

  if (DEMO_MODE) {
    if (message) message.textContent = DEMO_ONLY_MESSAGE;
    return;
  }

  if (!file) {
    if (message) {
      message.textContent = "Please choose a .xlsx file.";
      message.className = "inline-feedback error";
    }
    return;
  }

  if (!file.name.toLowerCase().endsWith(".xlsx")) {
    if (message) {
      message.textContent = "Please choose a .xlsx Excel file.";
      message.className = "inline-feedback error";
    }
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  if (message) {
    message.textContent = "Importing Excel contact list...";
    message.className = "inline-feedback";
  }

  if (results) results.innerHTML = "";
  if (button) {
    button.disabled = true;
    button.classList.add("is-loading");
  }

  try {
    const data = await fetchJson("/firms/import-excel/", {
      method: "POST",
      body: formData
    });

    renderImportResults(data);
    if (message) {
      message.textContent = `Imported ${data.imported_count ?? 0} prospects. Skipped ${data.skipped_count ?? 0}.`;
      message.className = "inline-feedback success";
    }
    if (fileInput) fileInput.value = "";
    setText("excelSelectedFile", "No file selected");
    await loadDashboard();
  } catch (error) {
    if (message) {
      message.textContent = getApiErrorMessage(error, "Import failed. Please check the file and try again.");
      message.className = "inline-feedback error";
    }
  } finally {
    if (button) {
      button.disabled = false;
      button.classList.remove("is-loading");
    }
  }
}

async function sendOutreach(firmId) {
  if (DEMO_MODE) {
    alert(DEMO_ONLY_MESSAGE);
    return;
  }

  const confirmed = confirm("Send outreach email to this firm?");
  if (!confirmed) return;

  try {
    const data = await fetchJson(`/firms/${firmId}/send-outreach/`, { method: "POST" });

    alert(data.message || data.error || "Request complete.");
    await loadDashboard();
  } catch (error) {
    alert(getApiErrorMessage(error, "Failed to send email. Check backend."));
    setBackendUnavailableStatus();
  }
}

async function sendBatchOutreach() {
  const limit = getElement("batchLimit")?.value || 3;
  const delaySeconds = getElement("delaySeconds")?.value || 10;
  const message = getElement("batchMessage");

  if (DEMO_MODE) {
    if (message) message.textContent = DEMO_ONLY_MESSAGE;
    return;
  }

  const confirmed = confirm(`Send batch outreach? Limit: ${limit}, Delay: ${delaySeconds}s`);
  if (!confirmed) return;

  if (message) message.textContent = "Sending batch outreach...";

  try {
    const data = await fetchJson(
      `/firms/send-batch-outreach/?limit=${encodeURIComponent(limit)}&delay_seconds=${encodeURIComponent(delaySeconds)}`,
      { method: "POST" }
    );

    if (message) message.textContent = `Sent: ${data.sent_count}, Failed: ${data.failed_count}`;
    await loadDashboard();
  } catch (error) {
    if (message) message.textContent = getApiErrorMessage(error, "Batch sending failed. Check backend.");
    setBackendUnavailableStatus();
  }
}

async function resetCampaignData() {
  const result = getElement("resetCampaignResult");
  const button = getElement("resetCampaignButton");

  if (DEMO_MODE) {
    if (result) {
      result.textContent = DEMO_ONLY_MESSAGE;
      result.className = "reset-campaign-result error";
    }
    return;
  }

  const typedConfirmation = prompt("Type RESET to clear campaign data after an automatic backup is created.");
  if (typedConfirmation !== "RESET") {
    if (result) {
      result.textContent = "Reset cancelled. Confirmation text did not match RESET.";
      result.className = "reset-campaign-result error";
    }
    return;
  }

  if (result) {
    result.textContent = "Creating backup and clearing campaign data...";
    result.className = "reset-campaign-result";
  }

  if (button) {
    button.disabled = true;
    button.classList.add("is-loading");
  }

  try {
    const data = await fetchJson("/admin/reset-campaign-data", { method: "POST" });
    const backupFile = data.backup_file || "backup file not reported";

    if (result) {
      result.textContent = `${data.message || "Campaign data cleared successfully."} Backup: ${backupFile}`;
      result.className = "reset-campaign-result success";
    }

    await loadDashboard();
  } catch (error) {
    if (result) {
      result.textContent = error.message || "Reset failed. Campaign data was not cleared.";
      result.className = "reset-campaign-result error";
    }
    setBackendUnavailableStatus();
  } finally {
    if (button) {
      button.disabled = false;
      button.classList.remove("is-loading");
    }
  }
}

async function sendFollowUp(firmId) {
  const prospect = followUpsCache.find((item) => item.id === firmId);
  const message = getElement("followUpMessage");
  const label = prospect?.next_follow_up_type || "follow-up";
  const firmName = prospect?.firm_name || "this prospect";

  if (DEMO_MODE) {
    if (message) {
      message.textContent = DEMO_ONLY_MESSAGE;
      message.className = "inline-feedback error";
    }
    return;
  }

  const confirmed = confirm(`Send ${label} to ${firmName}?`);
  if (!confirmed) return;

  if (message) {
    message.textContent = `Sending ${label}...`;
    message.className = "inline-feedback";
  }

  try {
    const data = await fetchJson(`/firms/${firmId}/send-follow-up/`, { method: "POST" });

    if (data.success) {
      if (message) {
        message.textContent = data.message || `${label} sent.`;
        message.className = "inline-feedback success";
      }
      await loadDashboard();
    } else if (message) {
      message.textContent = data.detail || data.error || "Unable to send follow-up.";
      message.className = "inline-feedback error";
    }
  } catch (error) {
    if (message) {
      message.textContent = getApiErrorMessage(error, "Follow-up failed. Make sure backend is running.");
      message.className = "inline-feedback error";
    }
    setBackendUnavailableStatus();
  }
}

async function previewLetter(firmId) {
  selectedPreviewFirmId = firmId;
  const firm = firmsCache.find((item) => item.id === firmId);
  const modal = getElement("emailPreviewModal");
  const previewMessage = getElement("previewMessage");

  if (!firm) return;

  setText("previewFirmName", firm.firm_name || "Unknown firm");
  setText("previewSubject", "Loading...");
  if (previewMessage) previewMessage.textContent = "";

  if (modal) {
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("modal-open");
  }

  try {
    const generated = DEMO_MODE
      ? getDemoGeneratedEmail(firm)
      : await fetchJson(`/firms/${firmId}/generate-email/`);

    setText("previewSubject", generated.subject || "Outreach email");
    writeFrame("previewBodyFrame", DEMO_MODE ? emailHtmlFromText(generated.body || "") : generated.body || "");

    if (DEMO_MODE && previewMessage) {
      previewMessage.textContent = DEMO_ONLY_MESSAGE;
    }
  } catch (error) {
    setText("previewSubject", "Preview unavailable");
    writeFrame("previewBodyFrame", emailHtmlFromText(getApiErrorMessage(error, "Unable to generate preview. Make sure backend is running.")));
    if (previewMessage) previewMessage.textContent = getApiErrorMessage(error, "Preview failed. Check backend.");
    setBackendUnavailableStatus();
  }
}

function closePreviewModal() {
  const modal = getElement("emailPreviewModal");
  if (modal) {
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("modal-open");
  }
  selectedPreviewFirmId = null;
}

async function saveTemplate() {
  const message = getElement("templateMessage");

  if (DEMO_MODE) {
    if (message) message.textContent = DEMO_ONLY_MESSAGE;
    return;
  }

  const templateId = getElement("templateId")?.value;
  const name = getElement("templateName")?.value.trim();
  const subject = getElement("templateSubject")?.value.trim();
  const bodyText = getElement("templateBody")?.value.trim();

  if (!name || !subject || !bodyText) {
    if (message) message.textContent = "Please fill in template name, subject, and body.";
    return;
  }

  const method = templateId ? "PUT" : "POST";
  const path = templateId ? `/templates/${templateId}/` : "/templates/";

  try {
    const template = await fetchJson(path, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        subject,
        body_text: bodyText,
        is_active: true
      })
    });

    renderTemplate(template);
    if (message) message.textContent = "Template saved.";
  } catch (error) {
    if (message) message.textContent = getApiErrorMessage(error, "Template save failed. Check backend.");
    setBackendUnavailableStatus();
  }
}

async function activateTemplate() {
  const message = getElement("templateMessage");

  if (DEMO_MODE) {
    if (message) message.textContent = DEMO_ONLY_MESSAGE;
    return;
  }

  const templateId = getElement("templateId")?.value;

  if (!templateId) {
    if (message) message.textContent = "Save a template before activating it.";
    return;
  }

  try {
    const template = await fetchJson(`/templates/${templateId}/activate/`, { method: "POST" });
    renderTemplate(template);
    if (message) message.textContent = "Template activated.";
  } catch (error) {
    if (message) message.textContent = getApiErrorMessage(error, "Template activation failed. Check backend.");
    setBackendUnavailableStatus();
  }
}

function previewTemplate() {
  const subject = getElement("templateSubject")?.value || demoTemplate.subject;
  const body = getElement("templateBody")?.value || getTemplateBody(demoTemplate);
  const preview = getElement("templatePreview");

  setText("templatePreviewSubject", subject);
  writeFrame("templatePreviewFrame", emailHtmlFromText(body));

  if (preview) {
    preview.hidden = false;
  }
}

function filterFirms() {
  const query = getElement("firmFilterInput")?.value.trim().toLowerCase();

  if (!query) {
    renderFirms(firmsCache);
    return;
  }

  renderFirms(
    firmsCache.filter((firm) => {
      return [
        firm.firm_name,
        firm.email,
        firm.city,
        firm.status,
        firm.website,
        firm.phone
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(query));
    })
  );
}

function getSectionFromHash() {
  const sectionId = (window.location.hash || "#dashboard").replace("#", "");
  return sectionId || "dashboard";
}

function setActiveNav(sectionId) {
  document.querySelectorAll(".nav-link").forEach((link) => {
    const isActive = link.dataset.section === sectionId;
    link.classList.toggle("active", isActive);

    if (isActive) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  });
}

function setNewsletterPageMode(sectionId = getSectionFromHash(), shouldScroll = false) {
  const activeSection = sectionId === NEWSLETTER_SECTION_ID ? NEWSLETTER_SECTION_ID : sectionId;
  const isNewsletterPage = activeSection === NEWSLETTER_SECTION_ID;
  const newsletterSection = getElement(NEWSLETTER_SECTION_ID);

  MAIN_PAGE_SELECTORS.forEach((selector) => {
    document.querySelectorAll(selector).forEach((section) => {
      section.classList.toggle("section-hidden", isNewsletterPage);
    });
  });

  if (newsletterSection) {
    newsletterSection.classList.toggle("section-hidden", !isNewsletterPage);
  }

  setActiveNav(activeSection);

  if (shouldScroll) {
    const target = getElement(activeSection);
    if (target) {
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    } else {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }
}

function setupEventListeners() {
  getElement("loginForm")?.addEventListener("submit", login);
  getElement("logoutButton")?.addEventListener("click", logout);
  getElement("businessProfileSelector")?.addEventListener("change", async (event) => {
    setSelectedBusinessProfile(event.target.value, true);
    await loadDashboard();
  });
  getElement("businessProfileForm")?.addEventListener("submit", saveBusinessProfile);
  getElement("businessProfileNewButton")?.addEventListener("click", clearBusinessProfileForm);
  getElement("businessProfilesTable")?.addEventListener("click", (event) => {
    if (event.target.classList.contains("business-profile-edit-button")) {
      editBusinessProfile(event.target.dataset.profileId);
    }

    if (event.target.classList.contains("business-profile-disable-button")) {
      disableBusinessProfile(Number(event.target.dataset.profileId));
    }
  });
  getElement("userCreateForm")?.addEventListener("submit", createUser);
  getElement("generatePasswordButton")?.addEventListener("click", () => {
    const input = getElement("newUserPassword");
    if (input) input.value = generateClientPassword();
  });
  getElement("copyAccountDetailsButton")?.addEventListener("click", copyAccountDetails);
  getElement("usersTable")?.addEventListener("change", (event) => {
    if (event.target.classList.contains("role-select")) {
      updateUser(Number(event.target.dataset.userId), { role: event.target.value });
    }

    if (event.target.classList.contains("user-name-input")) {
      updateUser(Number(event.target.dataset.userId), { full_name: event.target.value.trim() || null });
    }
  });
  getElement("usersTable")?.addEventListener("click", (event) => {
    if (event.target.classList.contains("user-toggle-button")) {
      const userId = Number(event.target.dataset.userId);
      const isActive = event.target.dataset.active === "true";
      updateUser(userId, { is_active: !isActive });
    }

    if (event.target.classList.contains("user-reset-password-button")) {
      resetUserPassword(Number(event.target.dataset.userId));
    }

    if (event.target.classList.contains("user-delete-button")) {
      deleteUser(Number(event.target.dataset.userId));
    }
  });

  document.querySelectorAll(".nav-link").forEach((link) => {
    link.addEventListener("click", (event) => {
      const sectionId = link.dataset.section || "dashboard";

      event.preventDefault();
      history.pushState(null, "", `#${sectionId}`);
      setNewsletterPageMode(sectionId, true);
    });
  });

  window.addEventListener("hashchange", () => {
    setNewsletterPageMode(getSectionFromHash(), true);
  });
  window.addEventListener("popstate", () => {
    setNewsletterPageMode(getSectionFromHash(), true);
  });

  getElement("refreshButton")?.addEventListener("click", loadDashboard);
  getElement("refreshFollowUpsButton")?.addEventListener("click", loadDashboard);
  getElement("refreshNewslettersButton")?.addEventListener("click", loadDashboard);
  getElement("checkRepliesButton")?.addEventListener("click", checkReplies);
  getElement("autoFollowUpSettingsForm")?.addEventListener("submit", (event) => {
    event.preventDefault();
    saveAutoFollowUpSettings();
  });
  getElement("manualCrmCountsForm")?.addEventListener("submit", (event) => {
    event.preventDefault();
    saveManualCrmCountsFromForm();
  });
  getElement("runAutoFollowUpsButton")?.addEventListener("click", runAutoFollowUps);
  getElement("manualAddForm")?.addEventListener("submit", (event) => {
    event.preventDefault();
    addManualProspect();
  });
  getElement("searchForm")?.addEventListener("submit", (event) => {
    event.preventDefault();
    searchAndSaveFirms();
  });
  getElement("campaignForm")?.addEventListener("submit", (event) => {
    event.preventDefault();
    runCampaign();
  });
  getElement("newsletterPreviewButton")?.addEventListener("click", previewNewsletter);
  getElement("newsletterDraftButton")?.addEventListener("click", saveNewsletterDraft);
  getElement("newsletterSendButton")?.addEventListener("click", sendNewsletter);
  getElement("resetCampaignButton")?.addEventListener("click", resetCampaignData);
  getElement("newsletterContactFilter")?.addEventListener("input", filterNewsletterContacts);
  getElement("newsletterSelectEligibleButton")?.addEventListener("click", selectEligibleNewsletterContacts);
  getElement("newsletterClearSelectionButton")?.addEventListener("click", clearNewsletterSelection);
  getElement("newsletterContactsTable")?.addEventListener("change", (event) => {
    if (!event.target.classList.contains("newsletter-contact-checkbox")) return;

    const contactId = Number(event.target.value);
    if (event.target.checked) {
      selectedNewsletterContactIds.add(contactId);
    } else {
      selectedNewsletterContactIds.delete(contactId);
    }
    updateNewsletterSelectedCount();
  });
  getElement("importExcelForm")?.addEventListener("submit", (event) => {
    event.preventDefault();
    importExcelDatabase();
  });
  getElement("excelFileInput")?.addEventListener("change", (event) => {
    const fileName = event.target.files?.[0]?.name || "No file selected";
    setText("excelSelectedFile", fileName);
  });
  getElement("batchForm")?.addEventListener("submit", (event) => {
    event.preventDefault();
    sendBatchOutreach();
  });
  getElement("templateForm")?.addEventListener("submit", (event) => {
    event.preventDefault();
    saveTemplate();
  });
  getElement("templateActivateButton")?.addEventListener("click", activateTemplate);
  getElement("templatePreviewButton")?.addEventListener("click", previewTemplate);
  getElement("firmFilterInput")?.addEventListener("input", filterFirms);
  getElement("sortLogsButton")?.addEventListener("click", () => {
    logsNewestFirst = !logsNewestFirst;
    setText("sortLogsButton", logsNewestFirst ? "Newest First" : "Oldest First");
    renderLogs(logsCache);
  });
  getElement("previewCloseButton")?.addEventListener("click", closePreviewModal);
  getElement("previewCancelButton")?.addEventListener("click", closePreviewModal);
  getElement("previewSendButton")?.addEventListener("click", () => {
    if (!selectedPreviewFirmId) return;
    sendOutreach(selectedPreviewFirmId);
  });
  getElement("replyDetailsCloseButton")?.addEventListener("click", closeReplyDetailsModal);
  getElement("replyDetailsDoneButton")?.addEventListener("click", closeReplyDetailsModal);
}

document.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
  setNewsletterPageMode(getSectionFromHash(), false);
  initializeAuth();
});
