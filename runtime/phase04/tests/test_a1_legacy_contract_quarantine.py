import hashlib,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/"scripts"))
from a1_inventory_physical_namespaces import build
from a1_legacy_adapter_quarantine import IDS,AdapterRejected,dispatch,inspect_legacy_envelope,build_review_only_canonical_envelope

class A1Tests(unittest.TestCase):
    def sample(self):
        a={"synthetic":True}
        h=hashlib.sha256(json.dumps(a,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
        return dict(tenant_id="test",branch_id="test",session_id="test",
            source_sha256=h,consent_decision_id="test",policy_decision_id="test",
            artifact_version="abc.internal.engine.v2.draft",artifact=a,
            customer_release_approved=False,downstream_dispatch_authorized=False)
    def test_inventory(self):
        x=build()
        self.assertEqual(x["migration_count"],31)
        self.assertGreater(x["declared_table_count"],20)
        self.assertFalse(x["production_catalog_verified"])
    def test_six_adapters(self):
        self.assertEqual(len(IDS),6)
        for key in IDS:
            self.assertFalse(inspect_legacy_envelope(key,self.sample())["runtime_dispatch"])
    def test_all_six_v3_review_projections_preserve_provenance(self):
        for key in IDS:
            src=self.sample()
            out=build_review_only_canonical_envelope(key,src)
            self.assertEqual(out["target_version"],"abc.internal.capability.v3.review")
            self.assertEqual(out["source_sha256"],src["source_sha256"])
            self.assertEqual(out["source_artifact"],src["artifact"])
            self.assertEqual(out["authority"],"UNVERIFIED_REVIEW_ONLY")
            self.assertFalse(out["dispatch_authorized"])
            self.assertFalse(out["customer_release_approved"])
    def test_missing_evidence(self):
        for key in ("tenant_id","branch_id","session_id","source_sha256",
                    "consent_decision_id","policy_decision_id"):
            x=self.sample()
            del x[key]
            with self.assertRaises(AdapterRejected):
                inspect_legacy_envelope(next(iter(IDS)),x)
    def test_digest_and_version(self):
        x=self.sample()
        x["artifact"]["synthetic"]=False
        with self.assertRaises(AdapterRejected):
            inspect_legacy_envelope(next(iter(IDS)),x)
        x=self.sample()
        x["artifact_version"]="unknown"
        with self.assertRaises(AdapterRejected):
            inspect_legacy_envelope(next(iter(IDS)),x)
    def test_no_release(self):
        for key in ("customer_release_approved","downstream_dispatch_authorized"):
            x=self.sample()
            x[key]=True
            with self.assertRaises(AdapterRejected):
                inspect_legacy_envelope(next(iter(IDS)),x)
        with self.assertRaises(AdapterRejected):
            dispatch()
if __name__=="__main__": unittest.main()
