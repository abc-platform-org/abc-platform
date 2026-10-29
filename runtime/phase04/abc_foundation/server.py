"""Run: ABC_LOCAL_TEST_SECRET=<32+ random bytes> python -m abc_foundation.server
Never expose this test harness to real clients.
"""
import os
from .http_api import create_http_server
from .store import Store


def main():
    if os.environ.get("ABC_ENV") != "LOCAL_INTEGRATION_ONLY":
        raise SystemExit("ABC_ENV=LOCAL_INTEGRATION_ONLY required; no production identity provider")
    database = os.environ.get("ABC_DB_PATH")
    secret = os.environ.get("ABC_LOCAL_TEST_SECRET")
    if not database or not secret:
        raise SystemExit("ABC_DB_PATH and ABC_LOCAL_TEST_SECRET required")
    host = os.environ.get("ABC_LISTEN_HOST", "127.0.0.1")
    port = int(os.environ.get("ABC_LISTEN_PORT", "8766"))
    http = create_http_server(Store(database), secret, host, port)
    try:
        print("ABC local-only foundation listening on loopback; no real clients permitted.", flush=True)
        http.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        http.server_close()


if __name__ == "__main__":
    main()
