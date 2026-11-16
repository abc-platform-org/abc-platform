"""Run with `python -m studio_preview.verify_browser` from runtime/phase04."""

import json
import os
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread

from jsonschema import Draft202012Validator
from playwright.sync_api import expect, sync_playwright

from abc_foundation.eng02_consultation import SYNTHETIC_SERVICE
from abc_foundation.store import Store
from .__main__ import BRANCH, SPECIALIST, TENANT, create_studio_server

STORAGE_KEY = "abc-studio-synthetic-consultation"
PATH = "/v1/consultations"


def verify(page, database, origin):
    schema_path = Path(__file__).resolve().parents[3] / "contracts/v1/schemas/session.schema.json"
    schema = Draft202012Validator(json.loads(schema_path.read_text()))
    store = Store(database)
    actor = {"tenant_id": TENANT, "sub": SPECIALIST, "branch_ids": [BRANCH]}
    request = {"branch_id": BRANCH, "scope": "IN_SALON_SHARED_SCREEN"}

    page.goto(origin)
    expect(page.frame_locator("iframe").get_by_text("جلسه حضوری مشترک")).to_be_visible()
    button = page.locator("#session-action")
    status = page.locator("#session-status")
    keys = []

    def lose_first_response(route):
        response = route.fetch()
        assert response.status == 200
        keys.append(route.request.headers["idempotency-key"])
        route.abort()

    # The server commits, then the response is lost. Refresh retains the key.
    page.route(origin + PATH, lose_first_response, times=1)
    button.click()
    expect(status).to_contain_text("ارتباط")
    page.reload()
    expect(button).to_have_text("تلاش دوباره")
    with page.expect_response(lambda r: r.url == origin + PATH) as retried:
        button.click()
    response = retried.value
    assert response.status == 200
    assert response.request.headers["idempotency-key"] == keys[0]
    session = response.json()
    schema.validate(session)
    sid = session["session_id"]
    assert len(store.pending_outbox("studio-browser")) == 1
    expect(page.locator("#session-id")).to_have_text(sid)
    expect(page.locator("#session-state")).to_have_text("CREATED · 0")

    # A server-side version change proves the refreshed page reads a live GET.
    store.checkpoint_command(actor, sid, "pause", 0, "studio-browser-checkpoint")
    with page.expect_response(lambda r: r.url == origin + PATH + "/" + sid) as recovered:
        page.reload()
    assert recovered.value.status == 200
    schema.validate(recovered.value.json())
    expect(page.locator("#session-id")).to_have_text(sid)
    expect(page.locator("#session-state")).to_have_text("PAUSED · 1")
    expect(status).to_have_text("جلسه از سرور بازیابی شد.")

    foreign = store.create({**actor, "tenant_id": "studio-foreign-tenant"}, request, "studio-browser-foreign")
    page.evaluate("([key, sid]) => sessionStorage.setItem(key, JSON.stringify({sessionId: sid}))",
                  [STORAGE_KEY, foreign["session_id"]])
    with page.expect_response(lambda r: r.url == origin + PATH + "/" + foreign["session_id"]) as denied:
        page.reload()
    assert denied.value.status == 404
    assert page.request.get(denied.value.url, headers={"X-ABC-Studio-Preview": "1"}).json()["error"] == "not_found"
    expect(page.locator("#session-details")).to_be_hidden()
    expect(status).to_have_text("جلسه یافت نشد یا دیگر در دسترس نیست.")

    conflict_key = "0b7107e0-5dda-41e0-96bf-42551cc842b4"
    store.create(actor, {**request, "service_id": "synthetic-different-service"}, conflict_key)
    page.evaluate("([key, pending]) => sessionStorage.setItem(key, JSON.stringify({key: pending}))",
                  [STORAGE_KEY, conflict_key])
    page.reload()
    with page.expect_response(lambda r: r.url == origin + PATH) as conflict:
        button.click()
    assert conflict.value.status == 409
    expect(status).to_contain_text("تعارض")

    headers = {"X-ABC-Studio-Preview": "1", "Idempotency-Key": "studio-browser-denied"}
    assert page.request.get(origin + PATH + "/" + sid).status == 401
    assert page.request.post(origin + PATH, headers=headers, data=request).status == 403
    assert page.request.post(origin + PATH, headers={**headers, "Origin": "https://untrusted.invalid"},
                             data=request).status == 403
    assert page.request.post(origin + PATH, headers={**headers, "Origin": origin}, data=request).status == 400
    assert page.request.post(origin + PATH + "/" + sid + "/media", headers=headers).status == 404
    print("PASS: refresh re-read persisted session, retry created once, foreign tenant denied; "
          "401, 409, cross-origin and synthetic input gates verified.")


def verify_questions(page, database, origin):
    page.goto(origin)
    with page.expect_response(lambda r: r.url == origin + PATH and r.request.method == "POST") as created:
        page.locator("#session-action").click()
    created_response = created.value
    assert created_response.status == 200
    session = created_response.json()
    assert session["service_id"] == SYNTHETIC_SERVICE
    sid = session["session_id"]
    root = f"{origin}/_studio/consultations/{sid}"
    answers_url = root + "/answers"
    browser_prompt = page.locator("#next-question")
    answer_button = page.locator("#answer-action")
    answer_status = page.locator("#question-status")
    headers = {"X-ABC-Studio-Preview": "1", "Origin": origin, "X-Expected-State-Version": "0"}
    first = {"question_id": "synthetic:prior-treatment", "value": "NO"}
    expect(browser_prompt).to_contain_text("previous chemical hair treatment")
    page.locator("#question-catalog summary").click()
    expect(page.locator("#question-list li")).to_have_count(4)
    assert page.request.get(root + "/questions").status == 401
    assert page.request.post(answers_url, headers={**headers, "Idempotency-Key": "invalid-version",
                                                   "X-Expected-State-Version": "9"}, data=first).status == 409
    assert page.request.post(answers_url, headers={**headers, "Idempotency-Key": "wrong-order"},
                             data={"question_id": "synthetic:sensitivity", "value": "NO"}).json()["error"] == "eng14_policy_blocked"
    assert page.request.post(answers_url, headers={**headers, "Idempotency-Key": "foreign-origin",
                                                   "Origin": "https://untrusted.invalid"}, data=first).status == 403

    committed = {}

    def lose_recorded_response(route):
        response = route.fetch()
        assert response.status == 200
        committed.update(key=route.request.headers["idempotency-key"], receipt=response.json())
        route.abort()

    page.route(answers_url, lose_recorded_response, times=1)
    page.locator("#answer-value").select_option("NO")
    answer_button.click()
    expect(answer_status).to_contain_text("تأیید پاسخ دریافت نشد")
    page.reload()
    expect(answer_button).to_have_text("تلاش دوباره برای ثبت پاسخ")
    with page.expect_response(lambda r: r.url == answers_url) as retry:
        answer_button.click()
    replay = retry.value
    assert replay.status == 200
    assert replay.request.headers["idempotency-key"] == committed["key"]
    assert replay.json() == committed["receipt"]
    expect(browser_prompt).to_contain_text("reported sensitivity")
    page.reload()
    expect(browser_prompt).to_contain_text("reported sensitivity")

    store = Store(database)
    actor = {"tenant_id": TENANT, "sub": SPECIALIST, "branch_ids": [BRANCH]}
    request = {"branch_id": BRANCH, "scope": "IN_SALON_SHARED_SCREEN", "service_id": SYNTHETIC_SERVICE}
    foreign = store.create({**actor, "tenant_id": "studio-foreign-tenant"}, request, "foreign-tenant-questions")
    other_branch = "studio-other-branch"
    other = store.create({**actor, "branch_ids": [other_branch]}, {**request, "branch_id": other_branch}, "foreign-branch-questions")
    for out_of_scope in (foreign, other):
        other_root = f"{origin}/_studio/consultations/{out_of_scope['session_id']}"
        assert page.request.get(other_root + "/next-question", headers=headers).status == 404
        assert page.request.post(other_root + "/answers", headers={**headers, "Idempotency-Key": "unscoped-answer"},
                                 data=first).status == 404

    page.locator("#answer-value").select_option("YES")
    answer_button.click()
    expect(answer_status).to_contain_text("به بررسی متخصص نیاز دارد")
    expect(answer_button).to_be_hidden()
    assert page.request.post(answers_url, headers={**headers, "Idempotency-Key": "safety-stop"},
                             data={"question_id": "synthetic:desired-goal", "value": "SUBTLE"}).json()["error"] == "eng14_policy_blocked"

    with closing(store.connect()) as connection:
        assert connection.execute("SELECT COUNT(*) FROM eng02_answers WHERE session_id=?", (sid,)).fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM eng02_receipts WHERE session_id=?", (sid,)).fetchone()[0] == 2
        # Remove the existing specialist's branch scope before retrying a committed operation.
        connection.execute("UPDATE sessions SET branch_id=? WHERE session_id=?", (other_branch, sid))
    assert page.request.post(answers_url, headers={**headers, "Idempotency-Key": committed["key"]},
                             data=first).status == 404
    print("PASS: ENG-02 question catalog/next/answer, ENG-14 safety stop, refresh/replay, stale version, revoked scope")


def main():
    with TemporaryDirectory(prefix="abc-studio-browser-") as directory:
        database = Path(directory) / "session.sqlite"
        with create_studio_server(database) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(
                        executable_path=os.environ.get("ABC_STUDIO_CHROMIUM") or None,
                        args=os.environ.get("ABC_STUDIO_CHROMIUM_ARGS", "").split(),
                    )
                    with browser:
                        origin = f"http://127.0.0.1:{server.server_port}"
                        verify(browser.new_page(), database, origin)
                        verify_questions(browser.new_page(), database, origin)
            finally:
                server.shutdown()
                thread.join()


if __name__ == "__main__":
    main()
