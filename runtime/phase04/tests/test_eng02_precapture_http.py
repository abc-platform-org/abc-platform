"""ENG-02 pre-capture gate is deny-first; no photo upload is implemented.

Tests intentionally use fake clients and no real media, secrets or providers.
"""
import http.client
import json
import threading
import unittest
import uuid

from abc_foundation.http_api import create_oidc_pg_http_server
from abc_foundation.oidc import Principal, IdentityError
from abc_foundation.store import DomainError


class VerifiedIdentity:
    def verify(self, header):
        if header != "Bearer local-synthetic-verified":
            raise IdentityError("invalid_token")
        return Principal("specialist-ci", "https://test.invalid/identity")


class CaptureAuthority:
    def __init__(self):
        self.approved = True
        self.calls = []
        self.persisted_media = []

    def authorize_capture_preflight(self, principal, sid, state_version):
        self.calls.append((principal.subject, sid, state_version))
        if not self.approved:
            raise DomainError(403, "pre_capture_consent_or_session_denied")
        return {"consent_checked": True, "capture_authorized": False,
                "customer_media_accepted": False, "state_version": state_version}


class HttpPreCaptureTests(unittest.TestCase):
    def setUp(self):
        self.store=CaptureAuthority()
        self.server=create_oidc_pg_http_server(self.store,VerifiedIdentity())
        self.addCleanup(self.server.server_close)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.addCleanup(self.server.shutdown)
        self.sid=str(uuid.uuid4())
        self.path="/v1/consultations/"+self.sid+"/media"

    def send(self,path=None,headers=None,body=b"synthetic-bytes-never-retained"):
        conn=http.client.HTTPConnection("127.0.0.1",self.server.server_address[1],timeout=5)
        self.addCleanup(conn.close)
        h={"Authorization":"Bearer local-synthetic-verified",
           "X-Expected-State-Version":"2",
           "Content-Type":"application/octet-stream"}
        if headers: h.update(headers)
        conn.request("POST",path or self.path,body=body,headers=h)
        response=conn.getresponse()
        return response.status,json.loads(response.read())

    def test_verified_preflight_does_not_enable_capture(self):
        code,body=self.send()
        self.assertEqual(code,501)
        self.assertEqual(body["error"],"capability_not_implemented")
        self.assertEqual(self.store.calls,[("specialist-ci",self.sid,2)])
        self.assertEqual(self.store.persisted_media,[])

    def test_revoked_consent_denied_before_body_processing(self):
        self.store.approved=False
        code,body=self.send()
        self.assertEqual((code,body["error"]),(403,"pre_capture_consent_or_session_denied"))
        self.assertEqual(self.store.persisted_media,[])

    def test_missing_identity_denied_before_check(self):
        code,body=self.send(headers={"Authorization":""})
        self.assertEqual((code,body["error"]),(401,"unauthenticated"))
        self.assertEqual(self.store.calls,[])

    def test_missing_expected_version_denied(self):
        code,body=self.send(headers={"X-Expected-State-Version":""})
        self.assertEqual((code,body["error"]),(400,"expected_version_required"))
        self.assertEqual(self.store.calls,[])

    def test_no_preflight_capability_denies_closed(self):
        self.store.authorize_capture_preflight=None
        code,body=self.send()
        self.assertEqual((code,body["error"]),(403,"pre_capture_authority_unavailable"))

    def test_other_paths_never_return_capture_success(self):
        code,body=self.send(path="/v1/consultations/"+self.sid+"/capture")
        self.assertEqual((code,body["error"]),(501,"capability_not_implemented"))
        self.assertEqual(self.store.calls,[])


if __name__=="__main__":
    unittest.main()
