"use strict";

const panel = document.querySelector("#consultation-questions");
const message = document.querySelector("#question-status");
const catalog = document.querySelector("#question-catalog");
const list = document.querySelector("#question-list");
const form = document.querySelector("#answer-form");
const promptText = document.querySelector("#next-question");
const select = document.querySelector("#answer-value");
const submitAnswer = document.querySelector("#answer-action");
const pendingKey = "abc-studio-synthetic-answer";
const labels = {
  YES: "بله", NO: "خیر", UNKNOWN: "نامشخص", SUBTLE: "ملایم", BOLD: "چشمگیر",
  UNSURE: "مطمئن نیستم", LOW: "کم", FLEXIBLE: "انعطاف‌پذیر",
};

let current;
let nextQuestion;
let pending;
let loading = false;
let submitting = false;

async function requestQuestion(sessionId, operation, answer) {
  const headers = {"X-ABC-Studio-Preview": "1"};
  if (answer) {
    headers["Content-Type"] = "application/json";
    headers["Idempotency-Key"] = answer.key;
    headers["X-Expected-State-Version"] = String(answer.version);
  }
  const response = await fetch(`/_studio/consultations/${sessionId}/${operation}`, {
    method: answer ? "POST" : "GET",
    headers,
    body: answer ? JSON.stringify({question_id: answer.questionId, value: answer.value}) : undefined,
    cache: "no-store",
    signal: AbortSignal.timeout(10000),
  });
  if (!response.ok) {
    const payload = await response.json();
    throw Object.assign(new Error(payload.error), {status: response.status});
  }
  return response.json();
}

function loadPending(session) {
  const saved = JSON.parse(sessionStorage.getItem(pendingKey) ?? "null");
  if (saved?.sessionId === session.session_id && saved.version === session.state_version) return saved;
  sessionStorage.removeItem(pendingKey);
  return null;
}

function renderQuestion(question) {
  nextQuestion = question;
  form.hidden = !question && !pending;
  if (pending) {
    promptText.textContent = "";
    select.replaceChildren(new Option(labels[pending.value] ?? pending.value, pending.value));
  } else if (question) {
    promptText.textContent = question.text;
    select.replaceChildren(new Option("انتخاب پاسخ", ""),
      ...question.allowed_values.map(value => new Option(labels[value] ?? value, value)));
  }
  select.disabled = Boolean(pending);
  submitAnswer.textContent = pending ? "تلاش دوباره برای ثبت پاسخ" : "ثبت پاسخ";
  submitAnswer.disabled = false;
}

async function loadQuestions(session, notice = "") {
  loading = true;
  form.hidden = true;
  message.textContent = "در حال دریافت سؤال‌ها…";
  try {
    const [questions, progress] = await Promise.all([
      requestQuestion(session.session_id, "questions"),
      requestQuestion(session.session_id, "next-question"),
    ]);
    if (current !== session) return;
    list.replaceChildren(...questions.questions.map(question => {
      const item = document.createElement("li");
      item.textContent = question.text;
      return item;
    }));
    catalog.hidden = false;
    renderQuestion(progress.next_question);
    if (pending) message.textContent = "ثبت پاسخ قبلی را دوباره امتحان کنید.";
    else if (progress.stop_reason === "SPECIALIST_REVIEW_REQUIRED") {
      message.textContent = "پرسش‌وپاسخ متوقف شد و به بررسی متخصص نیاز دارد.";
    } else if (!progress.next_question) {
      message.textContent = "پرسش‌وپاسخ آزمایشی کامل شد.";
    } else {
      message.textContent = notice || "سؤال بعدی از ENG‑02 دریافت شد.";
    }
  } catch (error) {
    if (current === session) {
      if (pending && !error.status) renderQuestion(null);
      message.textContent = error.status === 404 ? "جلسه در دسترس نیست."
        : error.status === 409 ? "نسخه یا وضعیت جلسه تغییر کرده است. جلسه را بازیابی کنید."
        : "دریافت سؤال‌ها ممکن نشد. جلسه را دوباره بازیابی کنید.";
    }
  } finally {
    if (current === session) loading = false;
  }
}

document.addEventListener("studio:session", ({detail}) => {
  current = detail;
  pending = null;
  loading = false;
  form.hidden = true;
  catalog.hidden = true;
  panel.hidden = !detail;
  if (!detail) return;
  if (detail.state !== "CREATED") {
    message.textContent = "پرسش‌وپاسخ برای جلسهٔ غیرفعال در دسترس نیست.";
    return;
  }
  try {
    pending = loadPending(detail);
  } catch {
    message.textContent = "فضای ذخیره‌سازی تلاش مجدد در دسترس نیست.";
    return;
  }
  void loadQuestions(detail);
});

form.addEventListener("submit", async event => {
  event.preventDefault();
  if (!current || loading || submitting || (!pending && !select.value)) {
    if (!pending && !select.value) select.reportValidity();
    return;
  }
  const session = current;
  submitting = true;
  submitAnswer.disabled = true;
  select.disabled = true;
  const operation = pending ?? {
    key: crypto.randomUUID(), sessionId: session.session_id, version: session.state_version,
    questionId: nextQuestion.question_id, value: select.value,
  };
  try {
    sessionStorage.setItem(pendingKey, JSON.stringify(operation));
    pending = operation;
    message.textContent = "در حال ثبت پاسخ…";
    await requestQuestion(session.session_id, "answers", operation);
    sessionStorage.removeItem(pendingKey);
    if (current === session) {
      pending = null;
      await loadQuestions(session, "پاسخ ثبت شد. سؤال بعدی آماده است.");
    }
  } catch (error) {
    if (current !== session) return;
    if (error.status >= 400 && error.status < 500) {
      sessionStorage.removeItem(pendingKey);
      pending = null;
      form.hidden = true;
      message.textContent = error.status === 409
        ? "پاسخ رد شد. نسخه، ترتیب سؤال یا مجوز را با بازیابی جلسه بررسی کنید."
        : "پاسخ مجاز نیست. جلسه را دوباره بازیابی کنید.";
    } else {
      renderQuestion(nextQuestion);
      message.textContent = "تأیید پاسخ دریافت نشد. دوباره تلاش کنید.";
    }
  } finally {
    submitting = false;
  }
});
