"""Executable local-only Phase 04 contract slice. No user data, no mock security claims."""
import json
import pathlib
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from abc_foundation.auth import AuthError, mint_test_token, verify_bearer
from abc_foundation.http_api import create_http_server
from abc_foundation.store import Store, DomainError

SECRET = "abc-phase04-test-key-only-do-not-reuse-" + "A" * 40
SCOPE = "IN_SALON_SHARED_SCREEN"
BODY = {"branch_id": "branch-1", "scope": SCOPE}
ACTOR = {"sub": "specialist-1", "tenant_id": "tenant-1", "branch_ids": ("branch-1",), "roles": ("SPECIALIST",)}


def key(label):
    return "test-key-" + label


class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = pathlib.Path(self.temp.name) / "runtime.sqlite"
        self.store = Store(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def create(self, label="one", body=None, actor=None):
        return self.store.create(actor or ACTOR, body or BODY, key(label))

    def assert_domain(self, status, call):
        with self.assertRaises(DomainError) as cm:
            call()
        self.assertEqual(cm.exception.status, status)

    def test_create_matches_canonical_public_fields(self):
        r = self.create()
        self.assertEqual(r["state"], "CREATED")
        self.assertEqual(r["state_version"], 0)
        self.assertEqual(r["tenant_id"], ACTOR["tenant_id"])
        self.assertEqual(r["specialist_id"], ACTOR["sub"])
        self.assertEqual(r["scope"], SCOPE)
        self.assertNotIn("checkpoint", r)

    def test_exact_create_replay_is_identical(self):
        a, b = self.create(), self.create()
        self.assertEqual(a, b)
        self.assertEqual(len(self.store.pending_outbox("worker-a")), 1)

    def test_create_rejects_changed_replay_payload(self):
        self.create()
        self.assert_domain(409, lambda: self.store.create(ACTOR, {**BODY, "client_id": "other"}, key("one")))

    def test_no_idempotency_key(self):
        self.assert_domain(400, lambda: self.store.create(ACTOR, BODY, None))

    def test_no_extra_fields_or_wrong_scope(self):
        for body in ({**BODY, "ignored": 42}, {**BODY, "scope": "AT_HOME"}, {"branch_id": "branch-1"}):
            self.assert_domain(400, lambda b=body: self.store.create(ACTOR, b, key("invalid"+str(len(b)))))

    def test_branch_outside_claims_forbidden(self):
        self.assert_domain(403, lambda: self.store.create(ACTOR, {"branch_id":"branch-2","scope":SCOPE}, key("outside")))

    def test_cross_tenant_read_hidden_like_missing(self):
        s = self.create()
        other = {**ACTOR, "tenant_id": "tenant-2"}
        self.assert_domain(404, lambda: self.store.get(other, s["session_id"]))
        self.assert_domain(404, lambda: self.store.get(ACTOR, "nonexistent"))

    def test_branch_isolation(self):
        s = self.create()
        other = {**ACTOR, "branch_ids": ("branch-2",)}
        self.assert_domain(404, lambda: self.store.get(other, s["session_id"]))

    def test_specialist_assignment_boundary(self):
        s = self.create()
        other = {**ACTOR, "sub": "specialist-2"}
        self.assert_domain(404, lambda: self.store.get(other, s["session_id"]))

    def test_pause_resume_persist_restart(self):
        s = self.create()
        p = self.store.checkpoint_command(ACTOR, s["session_id"], "pause", 0, key("pause"))
        self.assertEqual((p["state"], p["state_version"]), ("PAUSED", 1))
        restarted = Store(self.path)
        self.assertEqual(restarted.get(ACTOR, s["session_id"])["state"], "PAUSED")
        r = restarted.checkpoint_command(ACTOR, s["session_id"], "resume", 1, key("resume"))
        self.assertEqual((r["state"], r["state_version"]), ("CREATED", 2))
        self.assertEqual(Store(self.path).get(ACTOR, s["session_id"])["state_version"], 2)

    def test_pause_replay_is_identical_and_no_duplicate_version(self):
        sid = self.create()["session_id"]
        p1 = self.store.checkpoint_command(ACTOR, sid, "pause", 0, key("pause"))
        p2 = self.store.checkpoint_command(ACTOR, sid, "pause", 0, key("pause"))
        self.assertEqual(p1, p2)
        self.assertEqual(self.store.get(ACTOR, sid)["state_version"], 1)

    def test_stale_state_version_fails(self):
        sid = self.create()["session_id"]
        self.store.checkpoint_command(ACTOR, sid, "pause", 0, key("pause"))
        self.assert_domain(409, lambda: self.store.checkpoint_command(ACTOR, sid, "resume", 0, key("resume")))

    def test_resume_without_checkpoint_fails(self):
        sid = self.create()["session_id"]
        self.assert_domain(409, lambda: self.store.checkpoint_command(ACTOR, sid, "resume", 0, key("resume")))

    def test_reusing_same_checkpoint_key_with_new_version_fails(self):
        sid = self.create()["session_id"]
        self.store.checkpoint_command(ACTOR, sid, "pause", 0, key("pause"))
        self.assert_domain(409, lambda: self.store.checkpoint_command(ACTOR, sid, "pause", 1, key("pause")))

    def test_atomic_concurrent_CAS_only_one_winner(self):
        sid = self.create()["session_id"]
        def submit(i):
            try:
                self.store.checkpoint_command(ACTOR, sid, "pause", 0, key("race"+str(i)))
                return "ok"
            except DomainError as error:
                return error.status
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(submit, range(8)))
        self.assertEqual(results.count("ok"), 1)
        self.assertEqual(results.count(409), 7)

    def test_transactional_outbox_canonical_session_created_envelope(self):
        sid = self.create()["session_id"]
        events = self.store.pending_outbox("worker")
        self.assertEqual(len(events), 1)
        e = events[0]
        self.assertEqual(e["event_type"], "SESSION_CREATED")
        self.assertEqual(e["producer_engine_id"], "ENG-01")
        self.assertEqual(e["aggregate_id"], sid)
        self.assertEqual(e["aggregate_version"], 0)
        self.assertEqual(e["payload"], {"session_id":sid,"branch_id":"branch-1"})

    def test_consumer_ack_and_replay_dedupe(self):
        self.create()
        event_id = self.store.pending_outbox("consumer-a")[0]["event_id"]
        self.store.ack_outbox("consumer-a", event_id)
        self.store.ack_outbox("consumer-a", event_id)
        self.assertEqual(self.store.pending_outbox("consumer-a"), [])
        self.assertEqual(len(self.store.pending_outbox("consumer-b")), 1)
        self.assert_domain(404, lambda: self.store.ack_outbox("consumer-a", "fake-event"))

    def test_failed_transaction_keeps_outbox_consistent(self):
        self.assert_domain(400, lambda: self.store.create(ACTOR, {"branch_id":"branch-1"}, key("bad")))
        self.assertEqual(self.store.pending_outbox("worker"), [])

    def test_missing_token_and_wrong_signature_fail(self):
        with self.assertRaises(AuthError):
            verify_bearer(None, SECRET)
        token = mint_test_token(SECRET, "specialist-1", "tenant-1", ["branch-1"])
        with self.assertRaises(AuthError):
            verify_bearer("Bearer "+token, SECRET+"other")

    def test_expired_and_non_specialist_claims_fail(self):
        old = mint_test_token(SECRET,"s","t",["branch-1"],now=time.time()-800)
        with self.assertRaises(AuthError):
            verify_bearer("Bearer "+old, SECRET)
        client = mint_test_token(SECRET,"s","t",["branch-1"],roles=["CLIENT"])
        with self.assertRaises(AuthError):
            verify_bearer("Bearer "+client, SECRET)

    def test_local_server_refuses_public_bind(self):
        with self.assertRaises(ValueError):
            create_http_server(self.store, SECRET, host="0.0.0.0")


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(pathlib.Path(self.temp.name)/"http.db")
        self.http = create_http_server(self.store, SECRET, port=0)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.base = "http://127.0.0.1:"+str(self.http.server_port)
        self.token = mint_test_token(SECRET,"specialist-1","tenant-1",["branch-1"])

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(timeout=5)
        self.temp.cleanup()

    def call(self, method, path, data=None, token=None, headers=None):
        hdr = {"Authorization": "Bearer "+(token if token is not None else self.token)}
        hdr.update(headers or {})
        if data is not None:
            hdr["Content-Type"] = "application/json"
        body = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(self.base+path, data=body, headers=hdr, method=method)
        try:
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_http_create_get_and_checkpoint(self):
        status, r = self.call("POST","/v1/consultations",BODY,headers={"Idempotency-Key":key("http")})
        self.assertEqual(status,200)
        sid=r["session_id"]
        self.assertEqual(self.call("GET", "/v1/consultations/"+sid)[1]["state"], "CREATED")
        st, p = self.call("POST","/_foundation/v0/consultations/"+sid+"/pause",{},headers={
            "Idempotency-Key":key("pause"),"X-Expected-State-Version":"0"})
        self.assertEqual((st,p["state"]), (200,"PAUSED"))
        st, r2 = self.call("POST","/_foundation/v0/consultations/"+sid+"/resume",{},headers={
            "Idempotency-Key":key("resume"),"X-Expected-State-Version":"1"})
        self.assertEqual((st,r2["state"]), (200,"CREATED"))

    def test_http_denies_cross_tenant_without_leaking_resource(self):
        _, r = self.call("POST","/v1/consultations",BODY,headers={"Idempotency-Key":key("create")})
        other = mint_test_token(SECRET,"specialist-1","tenant-other",["branch-1"])
        st,_ = self.call("GET","/v1/consultations/"+r["session_id"],token=other)
        self.assertEqual(st,404)

    def test_http_unauthorized_request_no_fake_success(self):
        req=urllib.request.Request(self.base+"/v1/consultations",data=json.dumps(BODY).encode(),headers={
            "Content-Type":"application/json","Idempotency-Key":key("bad")},method="POST")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req,timeout=3)
        self.assertEqual(ctx.exception.code,401)

    def test_http_consents_and_images_fail_closed(self):
        _, r = self.call("POST","/v1/consultations",BODY,headers={"Idempotency-Key":key("s")})
        sid = r["session_id"]
        st, body = self.call("POST","/v1/consultations/"+sid+"/consents",
                            {"purpose":["AI_PROCESSING"]},headers={"Idempotency-Key":key("consent")})
        self.assertEqual(st,501)
        self.assertEqual(body["error"],"capability_not_implemented")
        st, _ = self.call("POST","/v1/consultations/"+sid+"/media-upload-intents",{},headers={"Idempotency-Key":key("media")})
        self.assertEqual(st,501)

    def test_healthz_local_status_only(self):
        with urllib.request.urlopen(self.base+"/healthz",timeout=3) as resp:
            self.assertEqual(json.loads(resp.read())["capability"],"LOCAL_INTEGRATION_ONLY")




class CanonicalAlignmentTests(unittest.TestCase):
    """Assert actual emitted DTO/event subsets against the frozen Phase-02 JSON definitions."""
    @classmethod
    def setUpClass(cls):
        cls.root = pathlib.Path(__file__).resolve().parents[3]
        cls.session = json.loads((cls.root/"contracts/v1/schemas/session.schema.json").read_text())
        cls.event = json.loads((cls.root/"contracts/v1/schemas/event.schema.json").read_text())
        cls.openapi = json.loads((cls.root/"contracts/v1/openapi.json").read_text())

    def test_live_projection_conforms_to_canonical_session_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            result=Store(pathlib.Path(folder)/"s.db").create(ACTOR,BODY,key("schema"))
        self.assertTrue(set(self.session["required"]).issubset(result))
        self.assertFalse(set(result)-set(self.session["properties"]))
        self.assertIn(result["state"],self.session["properties"]["state"]["enum"])
        self.assertEqual(result["scope"],self.session["properties"]["scope"]["const"])

    def test_emitted_session_event_conforms_to_canonical_envelope(self):
        with tempfile.TemporaryDirectory() as folder:
            db=Store(pathlib.Path(folder)/"s.db")
            db.create(ACTOR,BODY,key("event"))
            e=db.pending_outbox("validator")[0]
        self.assertTrue(set(self.event["required"]).issubset(e))
        self.assertFalse(set(e)-set(self.event["properties"]))
        self.assertIn(e["event_type"],self.event["properties"]["event_type"]["enum"])
        self.assertIn(e["producer_engine_id"],self.event["properties"]["producer_engine_id"]["enum"])
        self.assertEqual(e["actor"]["role"],"SPECIALIST")

    def test_only_actual_v1_implemented_operations_are_advertised(self):
        methods=self.openapi["paths"]
        self.assertEqual(methods["/v1/consultations"]["post"]["operationId"],"createConsultation")
        self.assertEqual(methods["/v1/consultations/{session_id}"]["get"]["operationId"],"getConsultation")
        self.assertEqual(methods["/v1/consultations"]["post"]["x-abc-roles"],["SPECIALIST"])
        self.assertIn("bearerAuth",methods["/v1/consultations"]["post"]["security"][0])

if __name__ == "__main__":
    unittest.main()
