"""ENG-02 actual disposable PG16 pre-capture gate with HTTP and revocation races.

No media writer exists: a successful consent check STILL returns HTTP 501
and no media bytes, object or inference are persisted. Operator-admin seeded
"verified" status is strictly a synthetic CI fixture, not a client signature.
"""
import http.client
import json
import os
import threading
import time
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone,timedelta

import psycopg
from abc_foundation.http_api import create_oidc_pg_http_server
from abc_foundation.oidc import Principal, IdentityError
from abc_foundation.pg_store import PostgresStore
from abc_foundation.store import DomainError

ADMIN=os.getenv("ABC_TEST_PG_ADMIN_DSN")
APP=os.getenv("ABC_TEST_PG_DSN")
ISSUER="https://ci-eng02-identity.invalid/qualified"


class StaticCIIdentity:
    def __init__(self,sub):self.sub=sub
    def verify(self,header):
        if header!="Bearer synthetic-oidc-test-token":
            raise IdentityError("invalid_ci_identity")
        return Principal(self.sub,ISSUER)


@unittest.skipUnless(ADMIN and APP and os.getenv("ABC_ENV")=="LOCAL_INTEGRATION_ONLY",
                     "disposable PostgreSQL16 required")
class ENG02CapturePostgresGate(unittest.TestCase):
    def setUp(self):
        suffix=uuid.uuid4().hex[:12]
        self.tenant="capture-tenant-"+suffix
        self.branch="capture-branch-"+suffix
        self.subject="qualified-specialist-"+suffix
        self.client="synthetic-client-"+suffix
        self.principal=Principal(self.subject,ISSUER)
        self.store=PostgresStore(APP)
        with psycopg.connect(ADMIN) as con:
            con.execute("INSERT INTO abc.tenants(tenant_id) VALUES(%s)",
                        (self.tenant,))
            con.execute("INSERT INTO abc.branches(tenant_id,branch_id) VALUES(%s,%s)",
                        (self.tenant,self.branch))
            con.execute("""INSERT INTO abc.memberships
               (issuer,subject,tenant_id,branch_id,role,active,verified_qualification)
               VALUES(%s,%s,%s,%s,'SPECIALIST',true,true)""",
               (ISSUER,self.subject,self.tenant,self.branch))
        self.sid=self.store.create(self.principal,{"branch_id":self.branch,
            "scope":"IN_SALON_SHARED_SCREEN","client_id":self.client,
            "service_id":"synthetic:hair-color"},"capture-create-"+suffix)["session_id"]
        self.server=create_oidc_pg_http_server(self.store,StaticCIIdentity(self.subject))
        th=threading.Thread(target=self.server.serve_forever,daemon=True)
        th.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.addCleanup(th.join,3)
        self.path="/v1/consultations/"+self.sid+"/media"
        self.consent_id=None

    def _post(self,*,path=None,version="0",authorization="Bearer synthetic-oidc-test-token",
              data=b"FAKE-MEDIA-NOT-TO-BE-PERSISTED",ctype="image/jpeg"):
        conn=http.client.HTTPConnection("127.0.0.1",self.server.server_port,timeout=6)
        try:
            conn.request("POST",path or self.path,body=data,headers={
                "Authorization":authorization,"Content-Type":ctype,
                "X-Expected-State-Version":version})
            response=conn.getresponse()
            return response.status,json.loads(response.read())
        finally:conn.close()

    def _grant(self,*,purposes=("CAPTURE","AI_PROCESSING"),activate=True,
               digest="c"*64):
        cid=uuid.uuid4()
        with psycopg.connect(ADMIN) as con:
            con.execute("""INSERT INTO abc.consent_evidence
                 (consent_id,tenant_id,branch_id,session_id,client_id,status,
                  purpose,evidence_digest,disclosure_version,retention_policy_id)
                 VALUES(%s,%s,%s,%s,%s,'PENDING_VERIFICATION',%s,%s,
                       'ci-disclosure','ci-retention')""",
                 (cid,self.tenant,self.branch,self.sid,self.client,list(purposes),digest))
            if activate:
                con.execute("""UPDATE abc.consent_evidence SET status='ACTIVE',
                   verified_at=clock_timestamp(),
                   valid_until=clock_timestamp()+interval '15 minutes'
                   WHERE consent_id=%s""",(cid,))
        self.consent_id=cid
        return cid

    def _counts(self):
        with psycopg.connect(ADMIN) as con:
            return (con.execute("SELECT count(*) FROM abc.outbox WHERE aggregate_id=%s",
                                (self.sid,)).fetchone()[0],
                    con.execute("SELECT count(*) FROM abc.consent_evidence WHERE session_id=%s",
                                (self.sid,)).fetchone()[0])

    def _denied(self,code,expected_error=None,**kwargs):
        before=self._counts()
        result=self._post(**kwargs)
        self.assertEqual(result[0],code,result)
        if expected_error:self.assertEqual(result[1].get("error"),expected_error)
        self.assertEqual(self._counts(),before,"pre-capture request mutated PG")
        return result

    def test_01_pending_unverified_consent_denied_without_media_mutation(self):
        self._grant(activate=False)
        self._denied(403,"pre_capture_consent_or_session_denied")

    def test_02_missing_consent_denied_before_image_upload(self):
        self._denied(403,"pre_capture_consent_or_session_denied")

    def test_03_capture_only_does_not_grant_ai_processing(self):
        self._grant(purposes=("CAPTURE",))
        self._denied(403,"pre_capture_consent_or_session_denied")

    def test_04_processing_only_does_not_grant_capture(self):
        self._grant(purposes=("AI_PROCESSING",))
        self._denied(403,"pre_capture_consent_or_session_denied")

    def test_05_both_purposes_verified_still_deny_actual_media_upload(self):
        self._grant()
        self._denied(501,"capability_not_implemented")
        self._denied(501,"capability_not_implemented",
                     data=b"\x00\xff" * 512,ctype="application/octet-stream")

    def test_06_wrong_or_missing_token_never_reaches_preflight(self):
        self._grant()
        self._denied(401,"unauthenticated",authorization="")
        self._denied(401,"unauthenticated",authorization="Bearer forged")

    def test_07_missing_or_stale_expected_version_denied(self):
        self._grant()
        self._denied(400,"expected_version_required",version="")
        self._denied(403,"pre_capture_consent_or_session_denied",version="1")

    def test_08_membership_without_verified_specialist_qualification_denied(self):
        self._grant()
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.memberships
               SET verified_qualification=false WHERE issuer=%s AND subject=%s""",
               (ISSUER,self.subject))
        self._denied(403,"pre_capture_consent_or_session_denied")

    def test_09_revoked_specialist_membership_denied(self):
        self._grant()
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.memberships SET active=false
                      WHERE issuer=%s AND subject=%s""",(ISSUER,self.subject))
        self._denied(403,"pre_capture_consent_or_session_denied")

    def test_10_withdrawn_consent_denied_no_media_persistence(self):
        cid=self._grant()
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.consent_evidence
                      SET status='WITHDRAWN',revoked_at=clock_timestamp()
                      WHERE consent_id=%s""",(cid,))
        self._denied(403,"pre_capture_consent_or_session_denied")

    def test_11_expired_consent_denied_no_media_persistence(self):
        cid=self._grant()
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.consent_evidence SET status='EXPIRED'
                        WHERE consent_id=%s""",(cid,))
        self._denied(403,"pre_capture_consent_or_session_denied")

    def test_12_paused_session_is_not_capturable(self):
        self._grant()
        self.store.checkpoint_command(self.principal,self.sid,"pause",0,
                                      "capture-paused-"+uuid.uuid4().hex[:8])
        self._denied(403,"pre_capture_consent_or_session_denied")

    def test_13_unimplemented_media_alias_not_authorized(self):
        self._grant()
        self._denied(501,"capability_not_implemented",
                     path="/v1/consultations/"+self.sid+"/capture")

    def test_14_not_even_qualified_specialist_can_reactivate_withdrawn_proof(self):
        cid=self._grant()
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.consent_evidence
                     SET status='WITHDRAWN',revoked_at=clock_timestamp()
                     WHERE consent_id=%s""",(cid,))
        with psycopg.connect(ADMIN) as con:
            with self.assertRaises(psycopg.errors.CheckViolation):
                con.execute("""UPDATE abc.consent_evidence
                    SET status='ACTIVE',revoked_at=NULL WHERE consent_id=%s""",(cid,))
        self._denied(403,"pre_capture_consent_or_session_denied")

    def test_15_revocation_transaction_serializes_against_preflight(self):
        cid=self._grant()
        with psycopg.connect(ADMIN) as operator, ThreadPoolExecutor(max_workers=1) as pool:
            operator.execute("""UPDATE abc.consent_evidence
                     SET status='WITHDRAWN',revoked_at=clock_timestamp()
                     WHERE consent_id=%s""",(cid,))
            future=pool.submit(self._post)
            # Request will block behind the operator's uncommitted row write.
            time.sleep(0.18)
            self.assertFalse(future.done())
            operator.commit()
            self.assertEqual(future.result(timeout=7)[0],403)
        self.assertEqual(self._counts()[0],1,"no new media/outbox was created")

    def test_16_unverified_specialist_cannot_bypass_via_direct_db_privileges(self):
        with psycopg.connect(ADMIN) as con:
            self.assertFalse(con.execute("""SELECT has_table_privilege(
                'abc_app','abc.consent_evidence','UPDATE')""").fetchone()[0])
            self.assertFalse(con.execute("""SELECT has_table_privilege(
                'abc_app','abc.consent_evidence','INSERT')""").fetchone()[0])


if __name__=="__main__":unittest.main()
