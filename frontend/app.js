const currentOrigin = window.location.origin || "";
const API_BASE =
  window.API_BASE_URL ||
  (currentOrigin.includes(":8000") ? currentOrigin : "http://127.0.0.1:8000");

const state = {
  firms: [],
  logs: [],
  logsNewestFirst: true,
  firmFilter: "",
  previewFirmId: null,
  isRefreshing: false
};

const els = {};

document.addEventListener("DOMContentLoaded", () => {
  cacheElements();
  bindEvents();
  document.getElementById("apiEndpoint").textContent = API_BASE;
  loadDashboard();
});

function cacheElements() {
  els.totalFirms = document.getElementById("totalFirms");
  els.firmsWithEmails = document.getElementById("firmsWithEmails");
  els.emailsSent = document.getElementById("emailsSent");
  els.notContacted = document.getElementById("notContacted");
  els.successRate = document.getElementById("successRate");
  els.firmsTable = document.getElementById("firmsTable");
  els.logsTable = document.getElementById("logsTable");
  els.searchForm = document.getElementById("searchForm");
  els.campaignForm = document.getElementById("campaignForm");
  els.batchForm = document.getElementById("batchForm");
  els.searchButton = document.getElementById("searchButton");
  els.campaignButton = document.getElementById("campaignButton");
  els.batchButton = document.getElementById("batchButton");
  els.refreshButton = document.getElementById("refreshButton");
  els.searchMessage = document.getElementById("searchMessage");
  els.campaignReport = document.getElementById("campaignReport");
  els.batchMessage = document.getElementById("batchMessage");
  els.batchProgress = document.getElementById("batchProgress");
  els.systemStatus = document.getElementById("systemStatus");
  els.firmFilterInput = document.getElementById("firmFilterInput");
  els.sortLogsButton = document.getElementById("sortLogsButton");
  els.toastRegion = document.getElementById("toastRegion");
  els.emailPreviewModal = document.getElementById("emailPreviewModal");
  els.previewCloseButton = document.getElementById("previewCloseButton");
  els.previewCancelButton = document.getElementById("previewCancelButton");
  els.previewSendButton = document.getElementById("previewSendButton");
  els.previewFirmName = document.getElementById("previewFirmName");
  els.previewSubject = document.getElementById("previewSubject");
  els.previewBodyFrame = document.getElementById("previewBodyFrame");
  els.previewMessage = document.getElementById("previewMessage");
}

function bindEvents() {
  els.refreshButton.addEventListener("click", loadDashboard);
  els.searchForm.addEventListener("submit", event => {
    event.preventDefault();
    searchAndSaveFirms();
  });
  els.campaignForm.addEventListener("submit", event => {
    event.preventDefault();
    runCampaign();
  });
  els.batchForm.addEventListener("submit", event => {
    event.preventDefault();
    sendBatchOutreach();
  });
  els.firmFilterInput.addEventListener("input", event => {
    state.firmFilter = event.target.value.trim().toLowerCase();
    renderFirms();
  });
  els.sortLogsButton.addEventListener("click", () => {
    state.logsNewestFirst = !state.logsNewestFirst;
    els.sortLogsButton.textContent = state.logsNewestFirst ? "Newest First" : "Oldest First";
    renderLogs();
  });
  els.previewCloseButton.addEventListener("click", closeEmailPreview);
  els.previewCancelButton.addEventListener("click", closeEmailPreview);
  els.previewSendButton.addEventListener("click", sendPreviewOutreach);
  els.emailPreviewModal.addEventListener("click", event => {
    if (event.target === els.emailPreviewModal) closeEmailPreview();
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && els.emailPreviewModal.classList.contains("is-open")) {
      closeEmailPreview();
    }
  });

  document.querySelectorAll(".nav-link").forEach(link => {
    link.addEventListener("click", () => {
      document.querySelectorAll(".nav-link").forEach(item => item.classList.remove("active"));
      link.classList.add("active");
    });
  });
}

async function apiFetch(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.headers || {})
    }
  });

  let data = null;
  const text = await response.text();

  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!response.ok) {
    const detail = typeof data === "object" && data && data.detail ? data.detail : response.statusText;
    throw new Error(Array.isArray(detail) ? detail.map(item => item.msg).join(", ") : detail);
  }

  return data;
}

async function loadDashboard() {
  if (state.isRefreshing) return;

  state.isRefreshing = true;
  setButtonLoading(els.refreshButton, true, "Refreshing");
  setStatus("checking", "Checking API", "Syncing dashboard data");
  renderLoadingRows();

  try {
    const [stats, firms, logs] = await Promise.all([
      apiFetch("/firms/stats/"),
      apiFetch("/firms/"),
      apiFetch("/firms/email-logs/")
    ]);

    state.firms = Array.isArray(firms) ? firms : [];
    state.logs = Array.isArray(logs) ? logs : [];

    renderStats(stats || {});
    renderFirms();
    renderLogs();
    setStatus("online", "Prospective Client Outreach System online", `${state.firms.length} prospects loaded`);
  } catch (error) {
    renderStats({});
    renderErrorRows(error.message);
    setStatus("offline", "API unavailable", "Start FastAPI or check the endpoint");
    toast("Connection issue", error.message, "error");
  } finally {
    state.isRefreshing = false;
    setButtonLoading(els.refreshButton, false, "Refresh");
  }
}

function renderStats(stats) {
  const totalFirms = toNumber(stats.total_firms);
  const firmsWithEmails = toNumber(stats.firms_with_emails);
  const emailsSent = toNumber(stats.emails_sent);
  const notContacted = toNumber(stats.not_contacted);
  const sentLogs = toNumber(stats.sent_logs);
  const failedLogs = toNumber(stats.failed_logs);
  const successRate = sentLogs + failedLogs > 0 ? Math.round((sentLogs / (sentLogs + failedLogs)) * 100) : 0;

  els.totalFirms.textContent = formatNumber(totalFirms);
  els.firmsWithEmails.textContent = formatNumber(firmsWithEmails);
  els.emailsSent.textContent = formatNumber(emailsSent);
  els.notContacted.textContent = formatNumber(notContacted);
  els.successRate.textContent = `${successRate}%`;
}

function renderFirms() {
  const firms = state.firms.filter(firm => {
    if (!state.firmFilter) return true;
    return [
      firm.firm_name,
      firm.email,
      firm.phone,
      firm.website,
      firm.city,
      firm.status,
      firm.practice_area
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase()
      .includes(state.firmFilter);
  });

  if (!firms.length) {
    els.firmsTable.innerHTML = emptyRow(
      6,
      state.firms.length ? "No prospects match the current filter." : "No prospects saved yet. Run a search to build the database."
    );
    return;
  }

  els.firmsTable.innerHTML = firms
    .map(firm => {
      const email = firm.email || "";
      const website = normalizeUrl(firm.website);
      const canSend = Boolean(email) && firm.status !== "Email Sent";

      return `
        <tr>
          <td>
            <div class="firm-cell">
              <strong>${escapeHtml(firm.firm_name || "Unnamed prospect")}</strong>
              <span>${escapeHtml(firm.city || firm.practice_area || "No location saved")}</span>
            </div>
          </td>
          <td>${email ? `<a href="mailto:${escapeAttr(email)}">${escapeHtml(email)}</a>` : `<span class="muted-cell">No email</span>`}</td>
          <td>${firm.phone ? `<a href="tel:${escapeAttr(firm.phone)}">${escapeHtml(firm.phone)}</a>` : `<span class="muted-cell">Not listed</span>`}</td>
          <td>${website ? `<a href="${escapeAttr(website)}" target="_blank" rel="noopener">Open site</a>` : `<span class="muted-cell">No website</span>`}</td>
          <td>${statusBadge(firm.status)}</td>
          <td>
            <div class="actions">
              <button class="button button-ghost" type="button" data-action="preview" data-id="${firm.id}">Preview Letter</button>
              <button class="button button-ghost" type="button" data-action="send" data-id="${firm.id}" ${canSend ? "" : "disabled"}>Send Outreach</button>
              <button class="button button-ghost" type="button" data-action="website" data-url="${escapeAttr(website)}" ${website ? "" : "disabled"}>Open Website</button>
            </div>
          </td>
        </tr>
      `;
    })
    .join("");

  els.firmsTable.querySelectorAll("[data-action='preview']").forEach(button => {
    button.addEventListener("click", () => previewEmail(button.dataset.id, button));
  });
  els.firmsTable.querySelectorAll("[data-action='send']").forEach(button => {
    button.addEventListener("click", () => sendSingleOutreach(button.dataset.id, button));
  });
  els.firmsTable.querySelectorAll("[data-action='website']").forEach(button => {
    button.addEventListener("click", () => {
      if (button.dataset.url) window.open(button.dataset.url, "_blank", "noopener");
    });
  });
}

function renderLogs() {
  if (!state.logs.length) {
    els.logsTable.innerHTML = emptyRow(5, "No email logs yet. Completed outreach attempts will appear here.");
    return;
  }

  const logs = [...state.logs].sort((a, b) => {
    const first = new Date(a.sent_at || 0).getTime();
    const second = new Date(b.sent_at || 0).getTime();
    return state.logsNewestFirst ? second - first : first - second;
  });

  els.logsTable.innerHTML = logs
    .map(log => `
      <tr>
        <td>
          <div class="firm-cell">
            <strong>${escapeHtml(log.firm_name || "Unknown prospect")}</strong>
            <span>Log #${escapeHtml(log.id || "")}</span>
          </div>
        </td>
        <td>${log.email ? `<a href="mailto:${escapeAttr(log.email)}">${escapeHtml(log.email)}</a>` : `<span class="muted-cell">No email</span>`}</td>
        <td>${statusBadge(log.status)}</td>
        <td>${escapeHtml(log.subject || log.error_message || "No subject recorded")}</td>
        <td>${formatDate(log.sent_at)}</td>
      </tr>
    `)
    .join("");
}

async function searchAndSaveFirms() {
  const keyword = document.getElementById("keywordInput").value.trim();
  const city = document.getElementById("cityInput").value.trim();
  const stateValue = document.getElementById("stateInput").value.trim().toUpperCase();

  if (!keyword || !city || !stateValue) {
    setInlineMessage(els.searchMessage, "Enter a keyword, city, and state before searching.", "error");
    return;
  }

  setButtonLoading(els.searchButton, true, "Searching");
  setInlineMessage(els.searchMessage, `Searching ${city}, ${stateValue} for ${keyword}...`, "");

  try {
    const params = new URLSearchParams({ keyword, city, state: stateValue });
    const saved = await apiFetch(`/firms/search-and-save/?${params.toString()}`, { method: "POST" });
    const count = Array.isArray(saved) ? saved.length : 0;

    setInlineMessage(els.searchMessage, `${count} prospects saved from ${city}, ${stateValue}.`, "success");
    toast("Search complete", `${count} prospects were added to the database.`);
    await loadDashboard();
  } catch (error) {
    setInlineMessage(els.searchMessage, error.message, "error");
    toast("Search failed", error.message, "error");
  } finally {
    setButtonLoading(els.searchButton, false, "Search");
  }
}

async function runCampaign() {
  const keyword = document.getElementById("campaignKeyword").value.trim();
  const city = document.getElementById("campaignCity").value.trim();
  const stateValue = document.getElementById("campaignState").value.trim().toUpperCase();
  const limit = Math.max(1, Number(document.getElementById("campaignLimit").value || 1));
  const delaySeconds = Math.max(0, Number(document.getElementById("campaignDelay").value || 0));
  const sendImmediately = document.getElementById("campaignSendImmediately").checked;

  if (!keyword || !city || !stateValue) {
    renderCampaignError("Enter a keyword, city, and state before running a campaign.");
    return;
  }

  setButtonLoading(els.campaignButton, true, sendImmediately ? "Running" : "Previewing");
  renderCampaignLoading(keyword, city, stateValue, sendImmediately);

  try {
    const params = new URLSearchParams({
      keyword,
      city,
      state: stateValue,
      limit: String(limit),
      delay_seconds: String(delaySeconds),
      send_immediately: String(sendImmediately)
    });
    const report = await apiFetch(`/firms/run-campaign/?${params.toString()}`, { method: "POST" });

    renderCampaignReport(report);
    const sent = toNumber(report.sent_count);
    const failed = toNumber(report.failed_count);
    const eligible = toNumber(report.eligible_count);
    const message = sendImmediately
      ? `Campaign complete: ${sent} sent, ${failed} failed, ${eligible} eligible.`
      : `Campaign preview ready: ${eligible} eligible prospects found.`;

    toast(sendImmediately ? "Campaign complete" : "Campaign preview ready", message, failed ? "error" : "success");
    await loadDashboard();
  } catch (error) {
    renderCampaignError(error.message);
    toast("Campaign failed", error.message, "error");
  } finally {
    setButtonLoading(els.campaignButton, false, "Run Campaign");
  }
}

function renderCampaignLoading(keyword, city, stateValue, sendImmediately) {
  els.campaignReport.innerHTML = `
    <div class="report-empty loading-shimmer">
      <strong>${sendImmediately ? "Running campaign" : "Building campaign preview"}</strong>
      <span>${escapeHtml(keyword)} in ${escapeHtml(city)}, ${escapeHtml(stateValue)}</span>
    </div>
  `;
}

function renderCampaignError(message) {
  els.campaignReport.innerHTML = `
    <div class="report-message">${escapeHtml(message)}</div>
    <div class="report-empty">
      <strong>Campaign did not complete</strong>
      <span>Check the API response and try again when the campaign service is ready.</span>
    </div>
  `;
}

function renderCampaignReport(report = {}) {
  const sendImmediately = report.send_immediately !== false;
  const metrics = [
    ["Searched", report.searched_count],
    ["Saved", report.saved_count],
    ["Eligible", report.eligible_count],
    ["Sent", report.sent_count],
    ["Failed", report.failed_count],
    ["Skipped", report.skipped_count]
  ];
  const summary = sendImmediately
    ? "Campaign run finished. Successful and failed send attempts were written to Email Logs."
    : "Preview complete. No emails were sent because Send immediately is off.";

  els.campaignReport.innerHTML = `
    <div class="report-summary-grid">
      ${metrics
        .map(([label, value]) => `
          <div class="report-metric">
            <span>${escapeHtml(label)}</span>
            <strong>${formatNumber(value)}</strong>
          </div>
        `)
        .join("")}
    </div>
    <div class="report-message">${escapeHtml(summary)}</div>
    <div class="report-lists">
      ${reportList("Sent", report.sent || [], "status")}
      ${reportList("Failed", report.failed || [], "error")}
      ${reportList(sendImmediately ? "Skipped" : "Skipped / Not eligible", report.skipped || [], "reason")}
      ${reportList("Eligible", report.eligible || [], "status")}
    </div>
  `;
}

function reportList(title, items, detailKey) {
  const safeItems = Array.isArray(items) ? items : [];
  const body = safeItems.length
    ? safeItems
        .map(item => {
          const detail = item[detailKey] || item.reason || item.error || item.status || "";
          return `
            <div class="report-item">
              <div>
                <strong>${escapeHtml(item.firm || "Unknown prospect")}</strong>
                <span>${item.email ? escapeHtml(item.email) : "No email"}</span>
              </div>
              <span class="report-reason">${escapeHtml(detail)}</span>
            </div>
          `;
        })
        .join("")
    : `
      <div class="report-item">
        <div>
          <strong>No records</strong>
          <span>Nothing to show in this category.</span>
        </div>
      </div>
    `;

  return `
    <div class="report-list">
      <div class="report-list-title">
        <strong>${escapeHtml(title)}</strong>
        <span>${formatNumber(safeItems.length)}</span>
      </div>
      <div class="report-items">${body}</div>
    </div>
  `;
}

async function sendSingleOutreach(firmId, button) {
  if (!firmId) return;

  setButtonLoading(button, true, "Sending");

  try {
    const result = await apiFetch(`/firms/${firmId}/send-outreach/`, { method: "POST" });

    if (result && result.success === false) {
      throw new Error(result.error || "Outreach was not sent.");
    }

    toast("Outreach sent", result.message || "Email sent successfully.");
    await loadDashboard();
  } catch (error) {
    toast("Outreach failed", error.message, "error");
  } finally {
    setButtonLoading(button, false, "Send Outreach");
  }
}

async function previewEmail(firmId, button) {
  if (!firmId) return;

  const firm = state.firms.find(item => String(item.id) === String(firmId));

  state.previewFirmId = firmId;
  openEmailPreview();
  setPreviewMessage("Generating email preview...", "");
  els.previewFirmName.textContent = firm?.firm_name || "Selected prospect";
  els.previewSubject.textContent = "Loading...";
  setPreviewBody("<html><body><p>Loading email preview...</p></body></html>");
  setButtonLoading(button, true, "Previewing");

  try {
    const preview = await apiFetch(`/firms/${firmId}/generate-email/`);

    if (preview && preview.success === false) {
      throw new Error(preview.error || "Email preview could not be generated.");
    }

    els.previewFirmName.textContent = firm?.firm_name || preview.firm_name || "Selected prospect";
    els.previewSubject.textContent = preview.subject || "No subject returned";
    setPreviewBody(preview.body || "<html><body><p>No email body returned.</p></body></html>");
    setPreviewMessage("Review the letter below before sending outreach.", "");
    els.previewSendButton.disabled = false;
  } catch (error) {
    els.previewSubject.textContent = "Preview unavailable";
    setPreviewBody(`<html><body><p>${escapeHtml(error.message)}</p></body></html>`);
    setPreviewMessage(error.message, "error");
    els.previewSendButton.disabled = true;
    toast("Preview failed", error.message, "error");
  } finally {
    setButtonLoading(button, false, "Preview Letter");
  }
}

async function sendPreviewOutreach() {
  if (!state.previewFirmId) return;

  setButtonLoading(els.previewSendButton, true, "Sending");
  setPreviewMessage("Sending outreach email...", "");

  try {
    const result = await apiFetch(`/firms/${state.previewFirmId}/send-outreach/`, { method: "POST" });

    if (result && result.success === false) {
      throw new Error(result.error || "Outreach was not sent.");
    }

    setPreviewMessage(result.message || "Email sent successfully.", "success");
    toast("Outreach sent", result.message || "Email sent successfully.");
    await loadDashboard();
    closeEmailPreview();
  } catch (error) {
    setPreviewMessage(error.message, "error");
    toast("Outreach failed", error.message, "error");
  } finally {
    setButtonLoading(els.previewSendButton, false, "Send Outreach");
  }
}

function openEmailPreview() {
  els.emailPreviewModal.classList.add("is-open");
  els.emailPreviewModal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
  els.previewSendButton.disabled = true;
}

function closeEmailPreview() {
  els.emailPreviewModal.classList.remove("is-open");
  els.emailPreviewModal.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
  state.previewFirmId = null;
  els.previewFirmName.textContent = "Loading...";
  els.previewSubject.textContent = "Loading...";
  setPreviewBody("");
  setPreviewMessage("", "");
  setButtonLoading(els.previewSendButton, false, "Send Outreach");
}

function setPreviewBody(html) {
  els.previewBodyFrame.srcdoc = html || "";
}

function setPreviewMessage(message, type) {
  els.previewMessage.textContent = message;
  els.previewMessage.className = `modal-message ${type || ""}`.trim();
}

async function sendBatchOutreach() {
  const limit = Math.max(1, Number(document.getElementById("batchLimit").value || 1));
  const delaySeconds = Math.max(0, Number(document.getElementById("delaySeconds").value || 0));

  setButtonLoading(els.batchButton, true, "Sending");
  els.batchProgress.classList.add("active");
  setBatchMessage(`Sending up to ${limit} outreach emails with a ${delaySeconds}s delay...`, "");

  try {
    const params = new URLSearchParams({
      limit: String(limit),
      delay_seconds: String(delaySeconds)
    });
    const result = await apiFetch(`/firms/send-batch-outreach/?${params.toString()}`, { method: "POST" });
    const sent = toNumber(result.sent_count);
    const failed = toNumber(result.failed_count);
    const message = `Batch complete: ${sent} sent, ${failed} failed.`;

    setBatchMessage(message, failed ? "error" : "success");
    toast("Batch outreach complete", message, failed ? "error" : "success");
    await loadDashboard();
  } catch (error) {
    setBatchMessage(error.message, "error");
    toast("Batch outreach failed", error.message, "error");
  } finally {
    els.batchProgress.classList.remove("active");
    els.batchProgress.style.width = "100%";
    setTimeout(() => {
      els.batchProgress.style.width = "0";
    }, 600);
    setButtonLoading(els.batchButton, false, "Send Batch");
  }
}

function renderLoadingRows() {
  els.firmsTable.innerHTML = emptyRow(6, "Loading prospects...");
  els.logsTable.innerHTML = emptyRow(5, "Loading logs...");
}

function renderErrorRows(message) {
  els.firmsTable.innerHTML = emptyRow(6, `Unable to load prospects. ${message}`);
  els.logsTable.innerHTML = emptyRow(5, `Unable to load logs. ${message}`);
}

function emptyRow(colspan, message) {
  return `
    <tr>
      <td colspan="${colspan}">
        <div class="table-state">${escapeHtml(message)}</div>
      </td>
    </tr>
  `;
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

function setStatus(mode, title, detail) {
  els.systemStatus.classList.remove("online", "offline");
  if (mode === "online") els.systemStatus.classList.add("online");
  if (mode === "offline") els.systemStatus.classList.add("offline");

  els.systemStatus.querySelector("strong").textContent = title;
  els.systemStatus.querySelector("small").textContent = detail;
}

function setButtonLoading(button, loading, label) {
  button.disabled = loading;
  button.classList.toggle("is-loading", loading);

  const icon = button.querySelector(".button-icon");
  if (icon) {
    button.childNodes.forEach(node => {
      if (node.nodeType === Node.TEXT_NODE) node.textContent = "";
    });
    button.lastChild.textContent = ` ${label}`;
  } else {
    button.textContent = label;
  }
}

function setInlineMessage(element, message, type) {
  element.textContent = message;
  element.className = `inline-feedback ${type || ""}`.trim();
}

function setBatchMessage(message, type) {
  els.batchMessage.textContent = message;
  els.batchMessage.className = `result-summary ${type || ""}`.trim();
}

function toast(title, message, type = "success") {
  const item = document.createElement("div");
  item.className = `toast ${type === "error" ? "error" : ""}`.trim();
  item.innerHTML = `
    <strong>${escapeHtml(title)}</strong>
    <span>${escapeHtml(message)}</span>
  `;

  els.toastRegion.appendChild(item);

  setTimeout(() => {
    item.style.opacity = "0";
    item.style.transform = "translateY(8px)";
    item.addEventListener("transitionend", () => item.remove(), { once: true });
  }, 4200);
}

function normalizeUrl(url) {
  if (!url) return "";
  const trimmed = String(url).trim();
  if (!trimmed) return "";
  return /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
}

function formatDate(value) {
  if (!value) return "Not recorded";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Not recorded";

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(date);
}

function formatNumber(value) {
  return new Intl.NumberFormat().format(toNumber(value));
}

function toNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function escapeAttr(value) {
  return escapeHtml(value).replace(/`/g, "&#096;");
}

window.loadDashboard = loadDashboard;
window.searchAndSaveFirms = searchAndSaveFirms;
window.runCampaign = runCampaign;
window.sendBatchOutreach = sendBatchOutreach;
