"use strict";

const storageKey = "abc-studio-synthetic-consultation";
const consultations = "/v1/consultations";
const uuid = /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/;
const action = document.querySelector("#session-action");
const statusLine = document.querySelector("#session-status");
const details = document.querySelector("#session-details");
let reference;
let busy = false;

function save(value) {
  sessionStorage.setItem(storageKey, JSON.stringify(value));
  reference = value;
}

function showSession(data, recovered) {
  document.querySelector("#session-id").textContent = data.session_id;
  document.querySelector("#session-state").textContent = `${data.state} · ${data.state_version}`;
  details.hidden = false;
  document.dispatchEvent(new CustomEvent("studio:session", {detail: data}));
  statusLine.textContent = recovered ? "جلسه از سرور بازیابی شد." : "جلسه در سرور ایجاد شد.";
}

async function submit() {
  if (busy) return;
  busy = true;
  action.disabled = true;
  details.hidden = true;
  document.dispatchEvent(new CustomEvent("studio:session", {detail: null}));
  const recovering = Boolean(reference.sessionId);
  statusLine.textContent = recovering ? "در حال بازیابی جلسه…" : "در حال ایجاد جلسه…";
  try {
    if (!recovering && !reference.key) save({key: crypto.randomUUID()});
    const headers = {"X-ABC-Studio-Preview": "1"};
    if (!recovering) {
      headers["Content-Type"] = "application/json";
      headers["Idempotency-Key"] = reference.key;
    }
    const response = await fetch(recovering ? `${consultations}/${reference.sessionId}` : consultations, {
      method: recovering ? "GET" : "POST",
      headers,
      body: recovering ? undefined : JSON.stringify({scope: "IN_SALON_SHARED_SCREEN"}),
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });
    if (!response.ok) {
      if (response.status === 404 && recovering) {
        save({});
        statusLine.textContent = "جلسه یافت نشد یا دیگر در دسترس نیست.";
      } else if (response.status === 401 || response.status === 403) {
        statusLine.textContent = "دسترسی به محیط آزمایشی تأیید نشد.";
      } else if (response.status === 409) {
        if (!recovering) save({});
        statusLine.textContent = "تعارض در درخواست جلسه. دوباره درخواست دهید.";
      } else {
        statusLine.textContent = "سرور نتوانست درخواست جلسه را انجام دهد. دوباره امتحان کنید.";
      }
      return;
    }
    const data = await response.json();
    if (!uuid.test(data?.session_id ?? "") || (recovering && data.session_id !== reference.sessionId)
        || !Number.isInteger(data.state_version) || data.state_version < 0
        || typeof data.state !== "string" || !data.state) {
      throw new Error("invalid consultation response");
    }
    save({sessionId: data.session_id});
    showSession(data, recovering);
  } catch {
    statusLine.textContent = "ارتباط یا ذخیرهٔ شناسهٔ جلسه انجام نشد. دوباره امتحان کنید.";
  } finally {
    busy = false;
    action.disabled = false;
    action.textContent = reference.sessionId ? "بازیابی جلسه" : reference.key ? "تلاش دوباره" : "ایجاد جلسه";
  }
}

action.addEventListener("click", submit);
try {
  const saved = JSON.parse(sessionStorage.getItem(storageKey) ?? "null");
  reference = uuid.test(saved?.sessionId ?? "") ? {sessionId: saved.sessionId}
    : uuid.test(saved?.key ?? "") ? {key: saved.key} : {};
  if (reference.sessionId) {
    void submit();
  } else {
    action.disabled = false;
    action.textContent = reference.key ? "تلاش دوباره" : "ایجاد جلسه";
    statusLine.textContent = reference.key ? "درخواست قبلی را دوباره امتحان کنید." : "هنوز جلسه‌ای ایجاد نشده است.";
  }
} catch {
  statusLine.textContent = "فضای ذخیره‌سازی این تب در دسترس نیست.";
}
