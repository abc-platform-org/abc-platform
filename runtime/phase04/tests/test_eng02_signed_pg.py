"""Disposable PG16 integration: signed dual auth + admin ACL + atomic ENG02 event.

All IDs, service packs, tokens and answers are synthetic. No client records.
"""
import json
import os
import time
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import jwt
import psycopg
from cryptography.hazmat.primitives.asymmetric import rsa
from jsonschema import Draft202012Validator
from referencing import Registry,Resource
from pathlib import Path

from abc_foundation.eng01_service_identity import ENG01InternalIngress,WorkloadVerifier
from abc_foundation.eng02_pg_outbox import PGENG02CommandWriter
from abc_foundation.oidc import OIDCVerifier,Principal
from abc_foundation.pg_store import PostgresStore
from abc_foundation.store import DomainError

PG=os.getenv("ABC_TEST_PG_DSN")
ORCH=os.getenv("ABC_TEST_PG_ORCHESTRATOR_DSN")
ADMIN=os.getenv("ABC_TEST_PG_ADMIN_DSN")
WORKER=os.getenv("ABC_TEST_PG_WORKER_DSN")
ISS="https://identity.example.test/abc"
SISS="https://workload.identity.example.test/abc"


class Key:
    def __init__(self,pub): self.pub=pub
    def get_signing_key_from_jwt(self,token):
        if jwt.get_unverified_header(token).get("kid")!="test-rsa-1":
            raise jwt.PyJWKClientError("bad_kid")
        return SimpleNamespace(key=self.pub)


@unittest.skipUnless(PG and ORCH and ADMIN and WORKER,"disposable PG service required")
class ENG02PostgresIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hpriv=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        cls.spriv=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        cls.hverifier=OIDCVerifier(issuer=ISS,audience="abc-api",jwks_uri=ISS+"/jwks",
                         jwks_client=Key(cls.hpriv.public_key()))
        cls.sverifier=WorkloadVerifier(issuer=SISS,audience="abc-eng01-internal",
                         jwks_uri=SISS+"/jwks",jwks_client=Key(cls.spriv.public_key()))

    def setUp(self):
        suffix=uuid.uuid4().hex[:12]
        self.tenant="eg02-tenant-"+suffix
        self.branch="eg02-branch-"+suffix
        self.subject="eg02-spec-"+suffix
        self.principal=Principal(self.subject,ISS)
        self.store=PostgresStore(PG)
        self.writer=PGENG02CommandWriter(ORCH)
        self.ingress=ENG01InternalIngress(user_verifier=self.hverifier,
                                         service_verifier=self.sverifier,writer=self.writer)
        with psycopg.connect(ADMIN) as con:
            con.execute("INSERT INTO abc.tenants VALUES(%s)",(self.tenant,))
            con.execute("INSERT INTO abc.branches VALUES(%s,%s)",(self.tenant,self.branch))
            con.execute("""INSERT INTO abc.memberships
                  (issuer,subject,tenant_id,branch_id,role,active)
                  VALUES(%s,%s,%s,%s,'SPECIALIST',true)""",
                  (ISS,self.subject,self.tenant,self.branch))
            con.execute("""INSERT INTO abc.engine_workload_grants
               (issuer,service_subject,engine_id,tenant_id,branch_id,permission,active)
               VALUES(%s,'svc:abc-eng02','ENG-02',%s,%s,'ENG02_RECORD_ANSWER',true)""",
               (SISS,self.tenant,self.branch))
        self.sid=self.store.create(self.principal,{
             "branch_id":self.branch,"scope":"IN_SALON_SHARED_SCREEN",
             "service_id":"synthetic:hair-color"},"create-eng02-"+suffix)["session_id"]
        self.cmdid=str(uuid.uuid4())
        self.correlation=str(uuid.uuid4())
        self.tokenid=str(uuid.uuid4())
        self.user_header=self.human_token()
        self.service_header=self.service_token()
        self.cmd={
            "command_id":self.cmdid,"correlation_id":self.correlation,
            "session_id":self.sid,"tenant_id":self.tenant,"branch_id":self.branch,
            "engine_id":"ENG-02","contract_version":"1.0.0-draft",
            "profile_version":"synthetic-1.0.0",
            "question_id":"synthetic:prior-treatment","value":"NO",
            "answer_source":"CLIENT","expected_state_version":0,
            "requested_at":self.now()
        }

    def now(self):
        from datetime import datetime,timezone
        return datetime.now(timezone.utc).isoformat()

    def human_token(self,sub=None,**changes):
        n=int(time.time())
        claims={"iss":ISS,"aud":"abc-api","sub":sub or self.subject,
                "iat":n-2,"nbf":n-2,"exp":n+180}
        claims.update(changes)
        return "Bearer "+jwt.encode(claims,self.hpriv,algorithm="RS256",
                headers={"kid":"test-rsa-1"})

    def service_token(self,**changes):
        n=int(time.time())
        claims={"iss":SISS,"aud":"abc-eng01-internal","sub":"svc:abc-eng02",
                "iat":n-2,"nbf":n-2,"exp":n+90,"token_use":"service",
                "engine_id":"ENG-02","jti":self.tokenid}
        claims.update(changes)
        return "Bearer "+jwt.encode(claims,self.spriv,algorithm="RS256",
                headers={"kid":"test-rsa-1"})

    def execute(self,cmd=None,service_header=None,user_header=None):
        return self.ingress.record_synthetic_answer(
             user_authorization=user_header or self.user_header,
             service_authorization=service_header or self.service_header,
             command=cmd or self.cmd)

    def count(self,table):
        if table not in ("abc.outbox","abc.eng02_answers","abc.eng02_command_receipts"):
            raise AssertionError("invalid_test_table")
        col="aggregate_id" if table=="abc.outbox" else "session_id"
        with psycopg.connect(ADMIN) as con:
            return con.execute("SELECT count(*) FROM "+table+
                " WHERE "+col+"=%s",(self.sid,)).fetchone()[0]

    def test_one_transaction_answer_event_version_and_receipt(self):
        result=self.execute()
        self.assertEqual(result,self.execute())
        self.assertEqual(result["aggregate_version"],1)
        self.assertEqual(self.count("abc.eng02_answers"),1)
        self.assertEqual(self.count("abc.eng02_command_receipts"),1)
        self.assertEqual(self.count("abc.outbox"),2)
        with psycopg.connect(ADMIN) as con:
            row=con.execute("SELECT state,state_version,last_event_id FROM abc.sessions WHERE session_id=%s",(self.sid,)).fetchone()
            self.assertEqual(row[0:2],("CREATED",1))
            self.assertEqual(str(row[2]),result["event_id"])
            event=con.execute("SELECT event_json FROM abc.outbox WHERE event_id=%s",
                              (result["event_id"],)).fetchone()[0]
        self.assertEqual(event["event_type"],"ANSWER_RECORDED")
        self.assertEqual(event["producer_engine_id"],"ENG-02")
        self.assertEqual(event["aggregate_version"],1)
        self.assertEqual(event["payload"]["question_id"],"synthetic:prior-treatment")
        self.assertEqual(event["payload"]["answer_id"],result["answer_id"])
        root=Path(__file__).resolve().parents[3]/"contracts"/"v1"/"schemas"
        schema=json.loads((root/"event.schema.json").read_text())
        common=json.loads((root/"common.schema.json").read_text())
        registry=Registry().with_resource(common["$id"],Resource.from_contents(common))
        Draft202012Validator(schema,registry=registry).validate(event)

    def test_same_command_changed_value_claim_or_token_denied(self):
        self.execute()
        for changed in ({**self.cmd,"value":"YES"},
                        {**self.cmd,"correlation_id":str(uuid.uuid4())},
                        {**self.cmd,"requested_at":self.now()}):
            if changed==self.cmd: continue
            with self.subTest(changed=changed),self.assertRaises(DomainError) as e:
                self.execute(cmd=changed)
            self.assertEqual(e.exception.status,409)
        with self.assertRaises(DomainError) as e:
            self.execute(service_header=self.service_token(jti=str(uuid.uuid4())))
        self.assertEqual(e.exception.status,409)
        self.assertEqual(self.count("abc.outbox"),2)

    def test_six_parallel_copies_create_one_answer_event(self):
        with ThreadPoolExecutor(max_workers=6) as pool:
            rows=list(pool.map(lambda _:self.execute(),range(6)))
        self.assertTrue(all(x==rows[0] for x in rows))
        self.assertEqual(self.count("abc.outbox"),2)
        self.assertEqual(self.count("abc.eng02_command_receipts"),1)

    def test_new_command_stale_and_wrong_order_do_not_insert_event(self):
        self.execute()
        new={**self.cmd,"command_id":str(uuid.uuid4())}
        with self.assertRaises(DomainError) as e:
            self.execute(cmd=new)
        self.assertEqual(e.exception.status,409)
        self.assertEqual(self.count("abc.outbox"),2)

    def test_missing_admin_workload_grant_denied_before_write(self):
        with psycopg.connect(ADMIN) as con:
            con.execute("UPDATE abc.engine_workload_grants SET active=false WHERE tenant_id=%s",(self.tenant,))
        with self.assertRaises(DomainError) as e: self.execute()
        self.assertEqual(e.exception.status,403)
        self.assertEqual(self.count("abc.eng02_answers"),0)

    def test_revoked_human_membership_denied_even_on_replay(self):
        self.execute()
        with psycopg.connect(ADMIN) as con:
            con.execute("UPDATE abc.memberships SET active=false WHERE subject=%s",(self.subject,))
        with self.assertRaises(DomainError) as e: self.execute()
        self.assertIn(e.exception.status,(403,404))
        self.assertEqual(self.count("abc.outbox"),2)

    def test_forged_service_claim_or_human_actor_denied(self):
        for header in (self.service_token(engine_id="ENG-01"),
                       self.service_token(sub="svc:abc-eng19"),
                       self.service_token(aud="wrong")):
            with self.assertRaises(DomainError) as e:
                self.execute(service_header=header)
            self.assertEqual(e.exception.status,401)
        with self.assertRaises(DomainError):
            self.execute(user_header=self.human_token(sub="not-member"))
        self.assertEqual(self.count("abc.outbox"),1)

    def test_scope_forgery_denied(self):
        for col in ("tenant_id","branch_id"):
            with self.subTest(column=col),self.assertRaises(DomainError):
                self.execute(cmd={**self.cmd,col:"other-"+col})
        self.assertEqual(self.count("abc.eng02_answers"),0)

    def test_no_unknown_after_safety_halt(self):
        first=self.execute(cmd={**self.cmd,"value":"UNKNOWN"})
        next_command={**self.cmd,"command_id":str(uuid.uuid4()),"question_id":"synthetic:sensitivity",
                      "value":"NO","expected_state_version":1}
        with self.assertRaises(DomainError) as e:
            self.execute(cmd=next_command)
        self.assertEqual(e.exception.code,"critical_unknown_requires_specialist")
        self.assertEqual(self.count("abc.outbox"),2)

    def test_transaction_rollback_on_duplicate_aggregate_version(self):
        # Inject an extra unique aggregate-version receipt under admin into
        # a new session; no answer persists and no version is advanced.
        with psycopg.connect(ADMIN) as con:
            eid=uuid.uuid4()
            con.execute("INSERT INTO abc.outbox(event_id,tenant_id,aggregate_id,aggregate_version,event_json,created_at) VALUES(%s,%s,%s,1,%s,now())",
                (eid,self.tenant,self.sid,json.dumps({"synthetic":"collision"})))
        with self.assertRaises(psycopg.errors.UniqueViolation):
            self.execute()
        self.assertEqual(self.count("abc.eng02_answers"),0)
        self.assertEqual(self.count("abc.eng02_command_receipts"),0)
        with psycopg.connect(ADMIN) as con:
            state=con.execute("SELECT state_version FROM abc.sessions WHERE session_id=%s",(self.sid,)).fetchone()[0]
        self.assertEqual(state,0)

    def test_four_answer_sequence_is_versioned_and_outboxed_once_each(self):
        ids=("synthetic:prior-treatment","synthetic:sensitivity",
             "synthetic:desired-goal","synthetic:maintenance")
        values=("NO","NO","SUBTLE","LOW")
        for index,(qid,val) in enumerate(zip(ids,values),start=1):
            command={**self.cmd,"command_id":str(uuid.uuid4()),
                 "question_id":qid,"value":val,"expected_state_version":index-1}
            outcome=self.execute(cmd=command)
            self.assertEqual(outcome["aggregate_version"],index)
            self.assertEqual(outcome,self.execute(cmd=command))
        self.assertEqual(self.count("abc.eng02_answers"),4)
        self.assertEqual(self.count("abc.outbox"),5)
        self.assertEqual(self.count("abc.eng02_command_receipts"),4)
        with psycopg.connect(ADMIN) as con:
            rows=con.execute("""SELECT aggregate_version,event_json
                FROM abc.outbox WHERE aggregate_id=%s ORDER BY aggregate_version""",
                (self.sid,)).fetchall()
            self.assertEqual([x[0] for x in rows],[0,1,2,3,4])
            self.assertEqual([x[1]["payload"]["question_id"] for x in rows[1:]],list(ids))
            self.assertEqual(con.execute("""SELECT state,state_version FROM abc.sessions
                WHERE session_id=%s""",(self.sid,)).fetchone(),("CREATED",4))

    def test_out_of_order_question_and_malicious_answer_type_denied(self):
        wrong={**self.cmd,"question_id":"synthetic:maintenance","value":"LOW"}
        with self.assertRaises(DomainError) as e:
            self.execute(cmd=wrong)
        self.assertEqual(e.exception.code,"question_order_or_duplicate_denied")
        wrong={**self.cmd,"value":"NOT_AN_APPROVED_VALUE"}
        with self.assertRaises(DomainError) as e:
            self.execute(cmd=wrong)
        self.assertEqual(e.exception.status,400)
        self.assertEqual(self.count("abc.outbox"),1)

    def test_gateway_identity_cannot_provision_its_own_workload_grant(self):
        with psycopg.connect(ORCH) as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("""UPDATE abc.engine_workload_grants SET active=true
                         WHERE tenant_id=%s""",(self.tenant,))

    def test_actual_signed_http_socket_through_pg_commit(self):
        import http.client
        from threading import Thread
        from abc_foundation.eng01_internal_http import make_synthetic_server,PATH
        server=make_synthetic_server(self.ingress,environ={
            "ABC_ENV":"LOCAL_INTEGRATION_ONLY",
            "ABC_ENABLE_SYNTHETIC_S2S":"yes"})
        thread=Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            def request(service_header):
                conn=http.client.HTTPConnection("127.0.0.1",server.server_port,timeout=4)
                headers={"Content-Type":"application/json",
                         "Authorization":self.user_header}
                if service_header:
                    headers["X-ABC-Service-Authorization"]=service_header
                conn.request("POST",PATH,body=json.dumps(self.cmd),headers=headers)
                response=conn.getresponse()
                status=response.status
                data=json.loads(response.read())
                conn.close()
                return status,data
            self.assertEqual(request(None)[0],401)
            self.assertEqual(self.count("abc.outbox"),1)
            status,receipt=request(self.service_header)
            self.assertEqual(status,200)
            self.assertEqual(receipt["status"],"ANSWER_RECORDED_ATOMICALLY_SYNTHETIC_ONLY")
            self.assertEqual(receipt,request(self.service_header)[1])
            self.assertEqual(self.count("abc.eng02_answers"),1)
            self.assertEqual(self.count("abc.outbox"),2)
            self.assertEqual(self.count("abc.eng02_command_receipts"),1)
        finally:
            server.shutdown()
            thread.join(timeout=3)
            server.server_close()

    def test_role_cannot_read_other_engine_records(self):
        with psycopg.connect(ORCH) as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("SELECT * FROM abc.consent_evidence")
        with psycopg.connect(PG) as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("SELECT * FROM abc.eng02_answers")
        with psycopg.connect(WORKER) as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("SELECT * FROM abc.engine_workload_grants")
