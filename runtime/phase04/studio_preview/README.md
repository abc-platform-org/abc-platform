# ABC AI Studio consultation preview

From the repository root, start a synthetic loopback-only preview:

```bash
cd runtime/phase04
ABC_ENV=LOCAL_INTEGRATION_ONLY python -m studio_preview
```

Open the printed loopback URL. Create a consultation and refresh the same tab to
retrieve the same session from the backend. The preview keeps a synthetic
SQLite database for the life of the process and stores the session reference
or pending idempotency key in the current tab. A new preview process starts
with an empty database. This development entry point accepts synthetic inputs
only and binds to 127.0.0.1.

Run the browser verification from the same directory:

```bash
python -m pip install -r requirements.txt playwright==1.56.0
python -m playwright install chromium
ABC_ENV=LOCAL_INTEGRATION_ONLY python -m studio_preview.verify_browser
```

## ENG-02 question flow

The synthetic `hair-color` session shows the catalog and the next question from
ENG-02. The preview exposes the local-only `/_studio/consultations/{session_id}/`
routes `questions`, `next-question`, and `answers`. The answer route requires an
idempotency key and the current session version. Scoped authorization and
version validation run inside the SQLite answer transaction, then ENG-14
checks order and safety before a new answer is recorded. An exact replay
reuses its receipt after the current authorization and version checks.

Answer progress lives in the same disposable database as the session. The tab
keeps a pending synthetic selection and key until a definitive response, so a
lost response can be retried after refresh. The browser check also covers a
specialist-review stop, stale version, foreign tenant/branch and loss of scope.
No paid provider or media is used. The Foundation v1 contract and consultation
lifecycle transitions are unchanged.
