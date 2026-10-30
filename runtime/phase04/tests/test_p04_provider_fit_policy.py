"""P04 provider-fit negative controls: never turn a candidate into a deploy."""
import copy
import json
import sys
import unittest
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts.validate_p04_provider_fit import CANDIDATE,DECISION,validate


class ProviderFitPolicyTests(unittest.TestCase):
    def setUp(self):
        self.selection=json.loads(DECISION.read_text())
        self.blueprint=yaml.safe_load(CANDIDATE.read_text())

    def test_private_services_only_and_no_approved_spend_or_database(self):
        result=validate(self.selection,self.blueprint)
        self.assertEqual(result["services"],5)
        self.assertEqual(result["public_services"],0)
        self.assertEqual(result["render_database_resources"],0)
        self.assertFalse(result["infrastructure_provisioned"])
        self.assertFalse(result["deployment_allowed"])

    def test_no_public_blueprint_or_render_database(self):
        for corruption in ("web","db","autodeploy","password","plan",
                           "unapproved_v2","wrong_branch","secret"):
            selection=copy.deepcopy(self.selection)
            blueprint=copy.deepcopy(self.blueprint)
            svc=blueprint["services"][0]
            if corruption=="web":svc["type"]="web"
            elif corruption=="db":blueprint["databases"]=[{"name":"unverified"}]
            elif corruption=="autodeploy":svc["autoDeployTrigger"]="on"
            elif corruption=="password":
                svc["envVars"].append({"key":"ABC_DATABASE_PASSWORD","value":"unsafe"})
            elif corruption=="plan":svc["plan"]="free"
            elif corruption=="unapproved_v2":
                selection["compute"]["v2_live_dispatch"]="ENABLED"
            elif corruption=="wrong_branch":svc["branch"]="main"
            else:svc["envVars"].append({"key":"ABC_PG_DSN","value":"insecure"})
            with self.subTest(corruption=corruption),self.assertRaises(AssertionError):
                validate(selection,blueprint)

    def test_billing_approval_and_fake_operator_status_always_block(self):
        for field,value in (
            ("deployment_authorized",True),
            ("billing_authorized",True),
            ("production_release_authorized",True)
        ):
            selection=copy.deepcopy(self.selection)
            selection[field]=value
            with self.subTest(field=field),self.assertRaises(AssertionError):
                validate(selection,self.blueprint)
        selection=copy.deepcopy(self.selection)
        selection["owner_approval"]["monthly_spend_cap_usd"]=100
        with self.assertRaises(AssertionError):
            validate(selection,self.blueprint)
        selection=copy.deepcopy(self.selection)
        selection["database"]["render_managed_postgres_acceptable"]=True
        with self.assertRaises(AssertionError):
            validate(selection,self.blueprint)


if __name__=="__main__":
    unittest.main()
