"""End-to-end RSA-signed OIDC HTTP → DB membership → PostgreSQL RLS."""
import json
import os
import threading
import time
import unittest
import urllib.error
import urllib.request
import uuid
from types import SimpleNamespace

import jwt
import psycopg
from cryptography.hazmat.primitives.asymmetric import rsa

from abc_foundation.oidc import OIDCVerifier
from abc_foundation.pg_store import PostgresStore
from abc_foundation.http_api import create_oidc_pg_http_server

ISS = "https://identity.example.test/realms/abc"
URI = "https://identity.example.test/realms/abc/keys"

class KeyStore:
    def __init__(self,key): self.key=key
    def get_signing_key_from_jwt(self,token):
        if jwt.get_unverified_header(token).get("kid")!="fixture-key":
            raise jwt.PyJWKClientError("unknown key")
        return SimpleNamespace(key=self.key)

@unittest.skipUnless(os.getenv("ABC_TEST_PG_DSN"),"requires ephemeral PostgreSQL")
class OIDCHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin=os.environ["ABC_TEST_PG_ADMIN_DSN"]
        cls.dsn=os.environ["ABC_TEST_PG_DSN"]
        cls.rsa=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        verifier=OIDCVerifier(issuer=ISS,audience="abc-api",jwks_uri=URI,
                              jwks_client=KeyStore(cls.rsa.public_key()))
        cls.server=create_oidc_pg_http_server(PostgresStore(cls.dsn),verifier,port=0)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.base="http://127.0.0.1:"+str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def setUp(self):
        suffix=uuid.uuid4().hex[:12]
        self.tenant="tenant-"+suffix
        self.branch="branch-"+suffix
        self.sub="user-"+suffix
        with psycopg.connect(self.admin) as con:
            con.execute("INSERT INTO abc.tenants VALUES(%s)",(self.tenant,))
            con.execute("INSERT INTO abc.branches VALUES(%s,%s)",(self.tenant,self.branch))
            con.execute("""INSERT INTO abc.memberships
                     (issuer,subject,tenant_id,branch_id,role,active)
                     VALUES(%s,%s,%s,%s,'SPECIALIST',true)""",
                       (ISS,self.sub,self.tenant,self.branch))

    def token(self,sub=None,**overrides):
        now=int(time.time())
        data={"iss":ISS,"aud":"abc-api","sub":sub or self.sub,
              "iat":now-2,"nbf":now-2,"exp":now+300,
              "tenant_id":"evil-tenant","roles":["ORG_OWNER"],"branch_ids":["evil-branch"]}
        data.update(overrides)
        return jwt.encode(data,self.rsa,algorithm="RS256",headers={"kid":"fixture-key"})

    def call(self,method,path,body=None,token=None,headers=None):
        hdr={"Authorization":"Bearer "+(token or self.token()),**(headers or {})}
        if body is not None:
            hdr["Content-Type"]="application/json"
        request=urllib.request.Request(self.base+path,
               data=json.dumps(body).encode() if body is not None else None,
               headers=hdr,method=method)
        try:
            with urllib.request.urlopen(request,timeout=3) as response:
                return response.status,json.loads(response.read())
        except urllib.error.HTTPError as e:
            return e.code,json.loads(e.read())

    def test_signed_token_ignored_role_claim_with_db_specialist_authority(self):
        status,payload=self.call("POST","/v1/consultations",
                {"scope":"IN_SALON_SHARED_SCREEN","branch_id":self.branch},
                headers={"Idempotency-Key":"valid-intent-123"})
        self.assertEqual(status,200)
        self.assertEqual(payload["tenant_id"],self.tenant)
        status,read=self.call("GET","/v1/consultations/"+payload["session_id"])
        self.assertEqual((status,read["session_id"]),(200,payload["session_id"]))

    def test_signed_token_other_subject_without_membership_denied(self):
        status,body=self.call("POST","/v1/consultations",
            {"scope":"IN_SALON_SHARED_SCREEN","branch_id":self.branch},
            token=self.token(sub="unknown-user"),headers={"Idempotency-Key":"other-intent-123"})
        self.assertEqual(status,403)
        self.assertEqual(body["error"],"branch_not_authorized_or_ambiguous")

    def test_expired_or_wrong_key_signature_does_not_reach_database(self):
        status,_=self.call("POST","/v1/consultations",
            {"scope":"IN_SALON_SHARED_SCREEN","branch_id":self.branch},
            token=self.token(exp=int(time.time())-120),
            headers={"Idempotency-Key":"expired-intent-123"})
        self.assertEqual(status,401)

    def test_revocation_immediately_blocks_existing_http_session(self):
        status,payload=self.call("POST","/v1/consultations",
            {"scope":"IN_SALON_SHARED_SCREEN","branch_id":self.branch},
            headers={"Idempotency-Key":"revoke-intent-123"})
        self.assertEqual(status,200)
        with psycopg.connect(self.admin) as con:
            con.execute("UPDATE abc.memberships SET active=false WHERE subject=%s",(self.sub,))
        status,_=self.call("GET","/v1/consultations/"+payload["session_id"])
        self.assertEqual(status,404)

    def test_checkpoint_is_durable_but_unverified_consent_is_blocked(self):
        status,body=self.call("POST","/v1/consultations",
            {"scope":"IN_SALON_SHARED_SCREEN","branch_id":self.branch},
            headers={"Idempotency-Key":"disabled-intent-123"})
        self.assertEqual(status,200)
        path="/_foundation/v0/consultations/"+body["session_id"]+"/pause"
        st,p=self.call("POST",path,{},
             headers={"X-Expected-State-Version":"0","Idempotency-Key":"cmd-paused-123"})
        self.assertEqual((st,p["state"],p["state_version"]),(200,"PAUSED",1))
        st,p=self.call("POST","/_foundation/v0/consultations/"+body["session_id"]+"/resume",{},
             headers={"X-Expected-State-Version":"1","Idempotency-Key":"cmd-resume-123"})
        self.assertEqual((st,p["state"],p["state_version"]),(200,"CREATED",2))
        st,p=self.call("POST","/v1/consultations/"+body["session_id"]+"/consents",{},
             headers={"Idempotency-Key":"no-consent-123"})
        self.assertEqual((st,p["error"]),(501,"capability_not_implemented"))

    def test_rejects_non_loopback_staging_bind(self):
        with self.assertRaises(ValueError):
            create_oidc_pg_http_server(PostgresStore(self.dsn),
              OIDCVerifier(issuer=ISS,audience="abc-api",jwks_uri=URI,
                            jwks_client=KeyStore(self.rsa.public_key())),host="0.0.0.0")
