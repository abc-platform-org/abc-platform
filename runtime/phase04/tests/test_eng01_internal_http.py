"""Socket-level local test of ENG01 internal dual-bearer ingress fail closed."""
import http.client
import json
from threading import Thread
import unittest

from abc_foundation.eng01_internal_http import make_synthetic_server,PATH
from abc_foundation.store import DomainError


class StubIngress:
    def __init__(self): self.count=0
    def record_synthetic_answer(self,*,user_authorization,service_authorization,command):
        if user_authorization!="Bearer signed-user" or service_authorization!="Bearer signed-engine":
            raise DomainError(401,"verified_dual_identity_required")
        if not isinstance(command,dict) or set(command)!={"test_command"}:
            raise DomainError(400,"invalid_test_command")
        self.count+=1
        return {"status":"SYNTHETIC_ACCEPTED","executions":self.count}


class InternalHTTPTests(unittest.TestCase):
    def setUp(self):
        self.ingress=StubIngress()
        self.server=make_synthetic_server(self.ingress,environ={
            "ABC_ENV":"LOCAL_INTEGRATION_ONLY",
            "ABC_ENABLE_SYNTHETIC_S2S":"yes"})
        self.thread=Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.thread.join,2)
        self.addCleanup(self.server.shutdown)
        self.host,self.port=self.server.server_address

    def send(self,*,method="POST",path=PATH,body=b'{"test_command":"safe"}',headers=None):
        conn=http.client.HTTPConnection(self.host,self.port,timeout=3)
        h={"Content-Type":"application/json",
           "Authorization":"Bearer signed-user",
           "X-ABC-Service-Authorization":"Bearer signed-engine"}
        if headers:
            for key,value in headers.items():
                if value is None: h.pop(key,None)
                else: h[key]=value
        conn.request(method,path,body=body,headers=h)
        resp=conn.getresponse()
        status=resp.status
        data=json.loads(resp.read())
        ctype=resp.getheader("Cache-Control")
        conn.close()
        return status,data,ctype

    def test_loopback_success_and_no_store_cache(self):
        status,doc,cache=self.send()
        self.assertEqual(status,200)
        self.assertEqual(doc["status"],"SYNTHETIC_ACCEPTED")
        self.assertEqual(cache,"no-store")
        self.assertEqual(self.server.server_address[0],"127.0.0.1")

    def test_bad_service_or_human_token_denied(self):
        for patch in ({"Authorization":"Bearer attacker"},
                      {"X-ABC-Service-Authorization":"Bearer attacker"},
                      {"Authorization":None},
                      {"X-ABC-Service-Authorization":None}):
            with self.subTest(patch=patch):
                status,_,_=self.send(headers=patch)
                self.assertEqual(status,401)
        self.assertEqual(self.ingress.count,0)

    def test_browser_and_unexpected_route_denied(self):
        self.assertEqual(self.send(headers={"Origin":"https://evil.example"})[0],403)
        self.assertEqual(self.send(headers={"Cookie":"x=1"})[0],403)
        self.assertEqual(self.send(path=PATH+"?secret=1")[0],404)
        self.assertEqual(self.send(method="GET")[0],405)
        self.assertEqual(self.ingress.count,0)

    def test_duplicate_json_and_oversized_body_denied(self):
        self.assertEqual(self.send(body=b'{"test_command":"ok","test_command":"evil"}')[0],400)
        self.assertEqual(self.send(body=b'{"test_command":NaN}')[0],400)
        self.assertEqual(self.send(body=b'{"test_command":"'+b'a'*20000+b'"}')[0],413)
        self.assertEqual(self.ingress.count,0)

    def test_missing_local_only_config_cannot_bind(self):
        with self.assertRaises(ValueError):
            make_synthetic_server(self.ingress,environ={
                "ABC_ENV":"STAGING_PRIVATE",
                "ABC_ENABLE_SYNTHETIC_S2S":"yes"})
