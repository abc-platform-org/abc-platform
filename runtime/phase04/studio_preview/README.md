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
