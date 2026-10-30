"""Against disposable PostgreSQL 16 CI service. Not a deployed provider test."""
import os
import uuid
import json
import unittest
from concurrent.futures import ThreadPoolExecutor

import psycopg
from abc_foundation.oidc import Principal
from abc_foundation.pg_store import PostgresStore
from abc_foundation.store import DomainError

ISS="https://identity.example.test/realms/abc"
DSN=os.getenv("ABC_TEST_PG_DSN")
ADMIN=os.getenv("ABC_TEST_PG_ADMIN_DSN")
SCOPE="IN_SALON_SHARED_SCREEN"

@unittest.skipUnless(DSN and ADMIN,"requires disposable Postgres service")
class PostgresRuntimeTests(unittest.TestCase):
    def setUp(self):
        identifier=uuid.uuid4().hex[:14]
        self.tenant="tenant-"+identifier
        self.branch="branch-"+identifier
        self.subject="staff-"+identifier
        self.principal=Principal(self.subject,ISS)
        self.store=PostgresStore(DSN)
        with psycopg.connect(ADMIN) as con:
            con.execute("INSERT INTO abc.tenants VALUES(%s)",(self.tenant,))
            con.execute("INSERT INTO abc.branches VALUES(%s,%s)",(self.tenant,self.branch))
            con.execute("""INSERT INTO abc.memberships
                (issuer,subject,tenant_id,branch_id,role,active,verified_qualification)
                VALUES(%s,%s,%s,%s,'SPECIALIST',true,false)""",
                (ISS,self.subject,self.tenant,self.branch))

    def body(self): return {"branch_id":self.branch,"scope":SCOPE}
    def create(self,key="intent-0001"): return self.store.create(self.principal,self.body(),key)

    def test_pg_session_creation_reads_in_exact_scope(self):
        result=self.create()
        self.assertEqual(result["tenant_id"],self.tenant)
        self.assertEqual(result["specialist_id"],self.subject)
        self.assertEqual(result["state_version"],0)
        self.assertEqual(self.store.get(self.principal,result["session_id"]),result)

    def test_pg_idempotent_replay_is_exact_and_outbox_once(self):
        a=self.create();b=self.create()
        self.assertEqual(a,b)
        with psycopg.connect(ADMIN) as con:
            count=con.execute("SELECT count(*) FROM abc.outbox WHERE aggregate_id=%s",(a["session_id"],)).fetchone()[0]
        self.assertEqual(count,1)

    def test_pg_same_key_changed_payload_conflicts(self):
        self.create()
        with self.assertRaises(DomainError) as e:
            self.store.create(self.principal,{**self.body(),"service_id":"different"},"intent-0001")
        self.assertEqual(e.exception.status,409)

    def test_pg_unassigned_subject_cannot_create_or_read(self):
        bad=Principal("other-subject",ISS)
        sid=self.create()["session_id"]
        with self.assertRaises(DomainError) as e:
            self.store.create(bad,self.body(),"intent-bad")
        self.assertEqual(e.exception.status,403)
        with self.assertRaises(DomainError) as e:
            self.store.get(bad,sid)
        self.assertEqual(e.exception.status,404)

    def test_pg_wrong_issuer_cannot_access(self):
        bad=Principal(self.subject,"https://other-issuer.example.test/")
        sid=self.create()["session_id"]
        with self.assertRaises(DomainError):
            self.store.get(bad,sid)

    def test_pg_revoked_membership_blocks_future_reads_and_create(self):
        sid=self.create()["session_id"]
        with psycopg.connect(ADMIN) as con:
            con.execute("UPDATE abc.memberships SET active=false WHERE subject=%s",(self.subject,))
        with self.assertRaises(DomainError) as e:
            self.store.get(self.principal,sid)
        self.assertEqual(e.exception.status,404)
        with self.assertRaises(DomainError) as e:
            self.store.create(self.principal,self.body(),"intent-revoked")
        self.assertEqual(e.exception.status,403)

    def test_pg_non_specialist_role_not_authorized_by_job_title(self):
        with psycopg.connect(ADMIN) as con:
            con.execute("UPDATE abc.memberships SET role='SALON_MANAGER' WHERE subject=%s",(self.subject,))
        with self.assertRaises(DomainError) as e:
            self.store.create(self.principal,self.body(),"intent-manager")
        self.assertEqual(e.exception.status,403)

    def test_pg_rls_denies_no_context_even_to_authenticated_db_role(self):
        sid=self.create()["session_id"]
        with psycopg.connect(DSN) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM abc.sessions WHERE session_id=%s",(sid,)).fetchone()[0],0)
            self.assertEqual(con.execute("SELECT count(*) FROM abc.memberships WHERE subject=%s",(self.subject,)).fetchone()[0],0)
            con.execute("SELECT set_config('abc.tenant',%s,true)",("wrong-tenant",))
            con.execute("SELECT set_config('abc.branch',%s,true)",(self.branch,))
            con.execute("SELECT set_config('abc.subject',%s,true)",(self.subject,))
            self.assertEqual(con.execute("SELECT count(*) FROM abc.sessions WHERE session_id=%s",(sid,)).fetchone()[0],0)

    def test_pg_consent_evidence_writable_only_by_future_verification_service(self):
        with psycopg.connect(DSN) as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("""INSERT INTO abc.consent_evidence
                    (consent_id,tenant_id,branch_id,session_id,client_id,status,purpose,
                    evidence_digest,disclosure_version,retention_policy_id)
                    VALUES(%s,%s,%s,%s,%s,'PENDING_VERIFICATION',%s,%s,%s,%s)""",
                    (uuid.uuid4(),self.tenant,self.branch,uuid.uuid4(),"client-1",
                     ["AI_PROCESSING"],"fake","v1","retention-1"))

    def test_pg_same_intent_concurrency_returns_one_session(self):
        def call(_): return self.create("race-intent-key")
        with ThreadPoolExecutor(max_workers=5) as pool:
            results=list(pool.map(call,range(5)))
        self.assertTrue(all(r==results[0] for r in results))
        with psycopg.connect(ADMIN) as con:
            count=con.execute("SELECT count(*) FROM abc.sessions WHERE tenant_id=%s",(self.tenant,)).fetchone()[0]
        self.assertEqual(count,1)


    def test_pg_consent_purpose_is_denied_until_verification_and_after_revocation(self):
        client = "synthetic-client-"+uuid.uuid4().hex[:10]
        s = self.store.create(self.principal,{**self.body(),"client_id":client},"consent-intent-1")
        sid = s["session_id"]
        self.assertFalse(self.store.has_verified_consent(self.principal,sid,"AI_PROCESSING"))
        with psycopg.connect(ADMIN) as con:
            consent_id=uuid.uuid4()
            con.execute("""INSERT INTO abc.consent_evidence
                    (consent_id,tenant_id,branch_id,session_id,client_id,status,purpose,
                     evidence_digest,disclosure_version,retention_policy_id)
                    VALUES(%s,%s,%s,%s,%s,'PENDING_VERIFICATION',%s,%s,%s,%s)""",
                    (consent_id,self.tenant,self.branch,sid,client,
                     ["AI_PROCESSING"],"synthetic-evidence-hash","disclosure-1","retention-1"))
        self.assertFalse(self.store.has_verified_consent(self.principal,sid,"AI_PROCESSING"))
        # External proof-verifier is not implemented; admin-only CI seeding models
        # the state after independent verification, NOT client self-consent.
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.consent_evidence
                    SET status='ACTIVE',verified_at=now(),valid_until=now()+interval '1 day' WHERE consent_id=%s""",(consent_id,))
        self.assertTrue(self.store.has_verified_consent(self.principal,sid,"AI_PROCESSING"))
        self.assertFalse(self.store.has_verified_consent(self.principal,sid,"CAPTURE"))
        self.assertFalse(self.store.has_verified_consent(self.principal,sid,"UNKNOWN_PURPOSE"))
        self.assertFalse(self.store.has_verified_consent(Principal("unassigned",ISS),sid,"AI_PROCESSING"))
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.consent_evidence SET status='WITHDRAWN',
                    revoked_at=now() WHERE consent_id=%s""",(consent_id,))
        self.assertFalse(self.store.has_verified_consent(self.principal,sid,"AI_PROCESSING"))

    def test_precapture_requires_current_session_and_both_active_purposes(self):
        client="synthetic-client-"+uuid.uuid4().hex[:12]
        s=self.store.create(self.principal,{**self.body(),"client_id":client},
                            "capture-guard-01")
        sid=s["session_id"]
        with self.assertRaises(DomainError) as denied:
            self.store.authorize_capture_preflight(self.principal,sid,0)
        self.assertEqual(denied.exception.code,"pre_capture_consent_or_session_denied")
        consent=uuid.uuid4()
        with psycopg.connect(ADMIN) as con:
            con.execute("""INSERT INTO abc.consent_evidence(
              consent_id,tenant_id,branch_id,session_id,client_id,status,
              purpose,evidence_digest,disclosure_version,retention_policy_id)
              VALUES(%s,%s,%s,%s,%s,'PENDING_VERIFICATION',
              ARRAY['CAPTURE']::text[],%s,'CI-DISCLOSURE','CI-RETENTION')""",
              (consent,self.tenant,self.branch,sid,client,"e"*64))
            con.execute("""UPDATE abc.consent_evidence SET status='ACTIVE',
              verified_at=clock_timestamp(),
              valid_until=clock_timestamp()+interval '1 hour'
              WHERE consent_id=%s""",(consent,))
        # CAPTURE alone is insufficient for an AI Studio image.
        with self.assertRaises(DomainError):
            self.store.authorize_capture_preflight(self.principal,sid,0)
        # Database permits only one live consent per session. Withdraw
        # CAPTURE-only proof before issuing a separately scoped dual-purpose
        # proof; never weaken the immutable-purpose or uniqueness controls.
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.consent_evidence SET status='WITHDRAWN',
              revoked_at=clock_timestamp() WHERE consent_id=%s""",(consent,))
        paired=uuid.uuid4()
        with psycopg.connect(ADMIN) as con:
            con.execute("""INSERT INTO abc.consent_evidence(
              consent_id,tenant_id,branch_id,session_id,client_id,status,
              purpose,evidence_digest,disclosure_version,retention_policy_id)
              VALUES(%s,%s,%s,%s,%s,'PENDING_VERIFICATION',
              ARRAY['CAPTURE','AI_PROCESSING']::text[],%s,'CI-DISCLOSURE','CI-RETENTION')""",
              (paired,self.tenant,self.branch,sid,client,"f"*64))
            con.execute("""UPDATE abc.consent_evidence SET status='ACTIVE',
              verified_at=clock_timestamp(),
              valid_until=clock_timestamp()+interval '1 hour'
              WHERE consent_id=%s""",(paired,))
        preflight=self.store.authorize_capture_preflight(self.principal,sid,0)
        self.assertTrue(preflight["consent_checked"])
        self.assertFalse(preflight["capture_authorized"])
        self.assertFalse(preflight["customer_media_accepted"])
        with self.assertRaises(DomainError):
            self.store.authorize_capture_preflight(self.principal,sid,1)
        with self.assertRaises(DomainError):
            self.store.authorize_capture_preflight(Principal("outsider",ISS),sid,0)
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.consent_evidence SET status='WITHDRAWN',
              revoked_at=clock_timestamp() WHERE consent_id=%s""",(paired,))
        with self.assertRaises(DomainError):
            self.store.authorize_capture_preflight(self.principal,sid,0)

    def test_precapture_rejects_invalid_version_and_session(self):
        s=self.create("capture-guard-02")
        for v in (-1,True,"0",None):
            with self.subTest(v=v),self.assertRaises(DomainError):
                self.store.authorize_capture_preflight(self.principal,s["session_id"],v)
        with self.assertRaises(DomainError):
            self.store.authorize_capture_preflight(self.principal,"not-a-uuid",0)

    def test_pg_consent_wrong_client_or_session_cannot_authorize_image(self):
        s=self.store.create(self.principal,{**self.body(),"client_id":"client-A"},"consent-intent-2")
        with psycopg.connect(ADMIN) as con:
            con.execute("""INSERT INTO abc.consent_evidence
                    (consent_id,tenant_id,branch_id,session_id,client_id,status,purpose,
                     evidence_digest,disclosure_version,retention_policy_id)
                    VALUES(%s,%s,%s,%s,%s,'PENDING_VERIFICATION',%s,%s,%s,%s)""",
                    (uuid.uuid4(),self.tenant,self.branch,s["session_id"],
                     "client-B",["AI_PROCESSING"],"synthetic-hash","v1","policy-1"))
            con.execute("""UPDATE abc.consent_evidence
                SET status='ACTIVE',verified_at=now(),
                valid_until=now()+interval '1 day'
                WHERE session_id=%s""",(s["session_id"],))
        self.assertFalse(self.store.has_verified_consent(self.principal,s["session_id"],"AI_PROCESSING"))


    def test_pg_checkpoint_is_durable_across_adapter_restart_and_replay(self):
        sid=self.create("create-for-checkpoint")["session_id"]
        first=self.store.checkpoint_command(self.principal,sid,"pause",0,"pause-intent-0001")
        self.assertEqual((first["state"],first["state_version"]),("PAUSED",1))
        restarted=PostgresStore(DSN)
        replay=restarted.checkpoint_command(self.principal,sid,"pause",0,"pause-intent-0001")
        self.assertEqual(replay,first)
        with self.assertRaises(DomainError) as err:
            restarted.checkpoint_command(self.principal,sid,"resume",1,"resume-intent-0001")
        self.assertEqual(err.exception.status,501)
        self.assertEqual(err.exception.code,"resume_requires_eng14_and_verified_consent")
        self.assertEqual(self.store.get(self.principal,sid)["state"],"PAUSED")
        self.assertEqual(self.store.get(self.principal,sid)["state_version"],1)
        with psycopg.connect(ADMIN) as con:
            audit=con.execute("SELECT count(*) FROM abc.state_audit WHERE session_id=%s",(sid,)).fetchone()[0]
        self.assertEqual(audit,1)

    def test_pg_checkpoint_stale_concurrent_change_is_rejected(self):
        sid=self.create("create-for-race")["session_id"]
        def go(i):
            try:
                self.store.checkpoint_command(self.principal,sid,"pause",0,"distinct-race-"+str(i))
                return 200
            except DomainError as e:
                return e.status
        with ThreadPoolExecutor(max_workers=5) as executor:
            results=list(executor.map(go,range(5)))
        self.assertEqual(results.count(200),1)
        self.assertEqual(results.count(409),4)

    def test_pg_checkpoint_replay_denied_after_membership_revocation(self):
        sid=self.create("create-for-revoke")["session_id"]
        self.store.checkpoint_command(self.principal,sid,"pause",0,"pause-revoke-0001")
        with psycopg.connect(ADMIN) as con:
            con.execute("UPDATE abc.memberships SET active=false WHERE subject=%s",(self.subject,))
        with self.assertRaises(DomainError) as e:
            self.store.checkpoint_command(self.principal,sid,"pause",0,"pause-revoke-0001")
        self.assertEqual(e.exception.status,404)


    def test_pg_consent_immutable_proof_and_non_resurrection(self):
        client="synthetic-"+uuid.uuid4().hex[:10]
        sid=self.store.create(self.principal,{**self.body(),"client_id":client},"consent-lifecycle-1")["session_id"]
        cid=uuid.uuid4()
        with psycopg.connect(ADMIN) as con:
            con.execute("""INSERT INTO abc.consent_evidence
                (consent_id,tenant_id,branch_id,session_id,client_id,status,purpose,
                 evidence_digest,disclosure_version,retention_policy_id)
                VALUES(%s,%s,%s,%s,%s,'PENDING_VERIFICATION',%s,%s,%s,%s)""",
                (cid,self.tenant,self.branch,sid,client,["AI_PROCESSING"],
                 "proof-hash-synthetic-123","disclosure-1","retention-1"))
            con.execute("""UPDATE abc.consent_evidence SET status='ACTIVE',
                verified_at=now(),valid_until=now()+interval '1 day' WHERE consent_id=%s""",(cid,))
        self.assertTrue(self.store.has_verified_consent(self.principal,sid,"AI_PROCESSING"))
        with psycopg.connect(ADMIN) as con:
            with self.assertRaises(psycopg.errors.CheckViolation):
                con.execute("UPDATE abc.consent_evidence SET purpose=ARRAY['CAPTURE'] WHERE consent_id=%s",(cid,))
        with psycopg.connect(ADMIN) as con:
            with self.assertRaises(psycopg.errors.CheckViolation):
                con.execute("""UPDATE abc.consent_evidence
                    SET valid_until=now()+interval '2 days' WHERE consent_id=%s""",(cid,))
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.consent_evidence SET status='WITHDRAWN',revoked_at=now()
                         WHERE consent_id=%s""",(cid,))
        self.assertFalse(self.store.has_verified_consent(self.principal,sid,"AI_PROCESSING"))
        with psycopg.connect(ADMIN) as con:
            with self.assertRaises(psycopg.errors.CheckViolation):
                con.execute("""UPDATE abc.consent_evidence SET status='ACTIVE',revoked_at=NULL
                    WHERE consent_id=%s""",(cid,))
        with psycopg.connect(ADMIN) as con:
            audits=con.execute("""SELECT before_status,after_status FROM abc.consent_status_audit
                    WHERE consent_id=%s ORDER BY recorded_at""",(cid,)).fetchall()
        self.assertEqual([a[1] for a in audits],["PENDING_VERIFICATION","ACTIVE","WITHDRAWN"])

    def test_pg_consent_activation_cannot_skip_verification(self):
        client="synthetic-"+uuid.uuid4().hex[:10]
        sid=self.store.create(self.principal,{**self.body(),"client_id":client},"consent-lifecycle-2")["session_id"]
        with psycopg.connect(ADMIN) as con:
            with self.assertRaises(psycopg.errors.CheckViolation):
                con.execute("""INSERT INTO abc.consent_evidence
                    (consent_id,tenant_id,branch_id,session_id,client_id,status,purpose,
                     evidence_digest,disclosure_version,retention_policy_id,verified_at,valid_until)
                    VALUES(%s,%s,%s,%s,%s,'ACTIVE',%s,%s,%s,%s,now(),now()+interval '1 day')""",
                    (uuid.uuid4(),self.tenant,self.branch,sid,client,["AI_PROCESSING"],
                     "synthetic-proof-123","v1","retention-1"))
        cid=uuid.uuid4()
        with psycopg.connect(ADMIN) as con:
            con.execute("""INSERT INTO abc.consent_evidence
                    (consent_id,tenant_id,branch_id,session_id,client_id,status,purpose,
                     evidence_digest,disclosure_version,retention_policy_id)
                    VALUES(%s,%s,%s,%s,%s,'PENDING_VERIFICATION',%s,%s,%s,%s)""",
                    (cid,self.tenant,self.branch,sid,client,["AI_PROCESSING"],
                     "synthetic-proof-123","v1","retention-1"))
        with psycopg.connect(ADMIN) as con:
            with self.assertRaises(psycopg.errors.CheckViolation):
                con.execute("UPDATE abc.consent_evidence SET status='ACTIVE' WHERE consent_id=%s",(cid,))
        self.assertFalse(self.store.has_verified_consent(self.principal,sid,"AI_PROCESSING"))

    def test_pg_event_conforms_to_canonical_base_envelope(self):
        sid=self.create()["session_id"]
        with psycopg.connect(ADMIN) as con:
            doc=con.execute("SELECT event_json FROM abc.outbox WHERE aggregate_id=%s",(sid,)).fetchone()[0]
        self.assertEqual(doc["event_type"],"SESSION_CREATED")
        self.assertEqual(doc["producer_engine_id"],"ENG-01")
        self.assertEqual(doc["tenant_id"],self.tenant)
        self.assertEqual(doc["aggregate_version"],0)
        self.assertEqual(doc["payload"]["branch_id"],self.branch)

    def test_broker_is_only_session_and_outbox_write_authority(self):
        session_id, event_id = uuid.uuid4(), uuid.uuid4()
        with psycopg.connect(DSN) as con:
            self.store._scope(con, ISS, self.subject,self.tenant,self.branch)
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("""INSERT INTO abc.sessions
                   (session_id,tenant_id,branch_id,specialist_id,state,
                    state_version,created_at,updated_at,last_event_id)
                   VALUES(%s,%s,%s,%s,'CREATED',0,now(),now(),%s)""",
                   (session_id,self.tenant,self.branch,self.subject,event_id))
        with psycopg.connect(DSN) as con:
            self.store._scope(con, ISS, self.subject,self.tenant,self.branch)
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("""INSERT INTO abc.outbox
                     (event_id,tenant_id,aggregate_id,aggregate_version,event_json,created_at)
                     VALUES(%s,%s,%s,0,'{}'::jsonb,now())""",
                    (event_id,self.tenant,session_id))
        with psycopg.connect(ADMIN) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM abc.sessions WHERE session_id=%s",
                                         (session_id,)).fetchone()[0],0)

    def test_direct_create_receipt_forgery_denied(self):
        with psycopg.connect(DSN) as con:
            self.store._scope(con,ISS,self.subject,self.tenant,self.branch)
            with self.assertRaises(psycopg.errors.CheckViolation):
                con.execute("""INSERT INTO abc.idempotency
                    (tenant_id,actor_id,operation,request_key,fingerprint,response_json)
                    VALUES(%s,%s,'create','forged-receipt-1','fake','{}'::jsonb)""",
                    (self.tenant,self.subject))

    def test_broker_writes_exactly_one_version_zero_audit_and_event(self):
        result=self.create("create-broker-audit-1")
        sid=result["session_id"]
        with psycopg.connect(ADMIN) as con:
            rows=con.execute("""SELECT a.tenant_id,a.actor_id,
                a.event_id,o.aggregate_version,o.event_json->>'event_type',
                s.state,s.state_version
                FROM abc.eng01_create_audit a
                JOIN abc.sessions s ON s.session_id=a.session_id
                JOIN abc.outbox o ON o.event_id=a.event_id
                WHERE a.session_id=%s""",(sid,)).fetchall()
        self.assertEqual(rows,[(self.tenant,self.subject,
                     uuid.UUID(result["last_event_id"]),0,"SESSION_CREATED","CREATED",0)])
        self.assertEqual(self.create("create-broker-audit-1"),result)
        with psycopg.connect(ADMIN) as con:
            self.assertEqual(con.execute("""SELECT count(*) FROM abc.eng01_create_audit
                   WHERE session_id=%s""",(sid,)).fetchone()[0],1)

    def test_service_login_binding_is_admin_only_and_physically_authenticated(self):
        # Disposable test login: real staging additionally requires mutual TLS
        # and externally managed certificate-to-login enrollment.
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        suffix=uuid.uuid4().hex[:16]
        login="abc_api_"+suffix
        password="ci-disposable-"+suffix
        with psycopg.connect(ADMIN) as admin:
            admin.execute(sql.SQL("""CREATE ROLE {} LOGIN NOINHERIT
                NOSUPERUSER NOCREATEROLE NOBYPASSRLS PASSWORD {}""").format(
                sql.Identifier(login),sql.Literal(password)))
            admin.execute(sql.SQL("GRANT abc_app TO {} WITH SET TRUE").format(
                sql.Identifier(login)))
        login_dsn=make_conninfo(DSN,user=login,password=password)
        body=json.dumps(self.body())
        # No binding => physical session_user cannot invent authorization.
        with self.assertRaises(psycopg.errors.CheckViolation):
            with psycopg.connect(login_dsn) as con:
                con.execute("SET ROLE abc_app")
                self.store._scope(con,ISS,self.subject,self.tenant,self.branch)
                con.execute("SELECT abc.eng01_create_session(%s::jsonb,%s)",
                            (body,"unbound-managed-1"))
        with psycopg.connect(DSN) as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("""INSERT INTO abc.eng01_api_login_bindings
                    (login_name,tenant_id,consumer_id,engine_id,active,approved_at)
                    VALUES(%s,%s,'forged','ENG-01',true,now())""",
                    (login,self.tenant))
        with psycopg.connect(ADMIN) as admin:
            admin.execute("""INSERT INTO abc.eng01_api_login_bindings
                (login_name,tenant_id,consumer_id,engine_id,active,approved_at)
                VALUES(%s,%s,'ci-managed-consumer','ENG-01',true,now())""",
                (login,self.tenant))
        with psycopg.connect(login_dsn) as con:
            con.execute("SET ROLE abc_app")
            self.store._scope(con,ISS,self.subject,self.tenant,self.branch)
            row=con.execute("SELECT abc.eng01_create_session(%s::jsonb,%s)",
                            (body,"approved-managed-1")).fetchone()[0]
        self.assertEqual(row["state"],"CREATED")
        self.assertEqual(row["tenant_id"],self.tenant)
        with psycopg.connect(ADMIN) as admin:
            admin.execute("""UPDATE abc.eng01_api_login_bindings SET active=false
                        WHERE login_name=%s AND tenant_id=%s""",
                        (login,self.tenant))
        with self.assertRaises(psycopg.errors.CheckViolation):
            with psycopg.connect(login_dsn) as con:
                con.execute("SET ROLE abc_app")
                self.store._scope(con,ISS,self.subject,self.tenant,self.branch)
                con.execute("SELECT abc.eng01_create_session(%s::jsonb,%s)",
                            (body,"revoked-managed-1"))

    def test_managed_tenant_mode_denies_shared_login_on_both_create_and_pause(self):
        existing=self.create("create-before-managed-mode")["session_id"]
        with psycopg.connect(ADMIN) as admin:
            admin.execute("""INSERT INTO abc.eng14_tenant_workload_mode
                (tenant_id,managed_required,activated_at,activated_by)
                VALUES(%s,true,clock_timestamp(),'ci-security-operator')""",(self.tenant,))
        with self.assertRaises(DomainError) as create_error:
            self.create("create-after-managed-mode")
        self.assertEqual(create_error.exception.status,403)
        with self.assertRaises(DomainError) as pause_error:
            self.store.checkpoint_command(self.principal,existing,"pause",0,
                                          "pause-after-managed-mode")
        self.assertIn(pause_error.exception.status,(403,404))
        # The restrictive tenant RLS policy must hide the session even when
        # a stolen shared DB credential supplies forged OIDC GUC values.
        with psycopg.connect(DSN) as forged:
            self.store._scope(forged,ISS,self.subject,self.tenant,self.branch)
            visible=forged.execute("SELECT count(*) FROM abc.sessions WHERE session_id=%s",
                                   (existing,)).fetchone()[0]
            self.assertEqual(visible,0)
            receipts=forged.execute(
                "SELECT count(*) FROM abc.idempotency WHERE tenant_id=%s",
                (self.tenant,)).fetchone()[0]
            self.assertEqual(receipts,0)
        with psycopg.connect(ADMIN) as admin:
            session=admin.execute("""SELECT state,state_version FROM abc.sessions
                WHERE session_id=%s""",(existing,)).fetchone()
            self.assertEqual(session,("CREATED",0))
            self.assertEqual(admin.execute("""SELECT count(*) FROM abc.eng14_state_guard_audit
                WHERE session_id=%s""",(existing,)).fetchone()[0],0)
        with psycopg.connect(DSN) as con:
            self.store._scope(con,ISS,self.subject,self.tenant,self.branch)
            self.assertFalse(con.execute("SELECT abc.eng14_workload_allowed(%s)",
                                          (self.tenant,)).fetchone()[0])

    def test_managed_identity_requires_real_server_certificate_not_database_guc(self):
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        suffix=uuid.uuid4().hex[:16]
        login="abc_api_"+suffix
        password="test-synthetic-"+suffix
        with psycopg.connect(ADMIN) as admin:
            admin.execute(sql.SQL("""CREATE ROLE {} LOGIN NOINHERIT NOSUPERUSER
                NOCREATEROLE NOBYPASSRLS PASSWORD {}""").format(
                sql.Identifier(login),sql.Literal(password)))
            admin.execute(sql.SQL("GRANT abc_app TO {} WITH SET TRUE").format(
                sql.Identifier(login)))
            admin.execute("""INSERT INTO abc.eng01_api_login_bindings
              (login_name,tenant_id,consumer_id,engine_id,active,approved_at,
               certificate_client_dn,certificate_issuer_dn,certificate_serial)
              VALUES(%s,%s,'ci-managed-identity','ENG-01',true,clock_timestamp(),
                     'CN=ci-managed','CN=ci-ca','43707')""",
              (login,self.tenant))
            admin.execute("""INSERT INTO abc.eng14_tenant_workload_mode
              (tenant_id,managed_required,activated_at,activated_by)
              VALUES(%s,true,clock_timestamp(),'ci-security-operator')""",
              (self.tenant,))
        dsn=make_conninfo(DSN,user=login,password=password)
        with psycopg.connect(dsn) as con:
            con.execute("SET ROLE abc_app")
            self.store._scope(con,ISS,self.subject,self.tenant,self.branch)
            # Synthetic CI PostgreSQL has no verified mTLS client cert.
            self.assertFalse(con.execute("SELECT abc.eng14_workload_allowed(%s)",
                                          (self.tenant,)).fetchone()[0])
            with self.assertRaises(psycopg.errors.CheckViolation):
                con.execute("SELECT abc.eng01_create_session(%s::jsonb,%s)",
                    (json.dumps(self.body()),"ci-bad-cert-entry-1"))
