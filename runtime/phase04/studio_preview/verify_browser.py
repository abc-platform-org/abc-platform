"""Run with `python -m studio_preview.verify_browser` from runtime/phase04."""

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread

from jsonschema import Draft202012Validator
from playwright.sync_api import expect, sync_playwright

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
                        verify(browser.new_page(), database, f"http://127.0.0.1:{server.server_port}")
            finally:
                server.shutdown()
                thread.join()


if __name__ == "__main__":
    main()
