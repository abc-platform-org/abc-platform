"""Official-source intake is never mistaken for authenticated expert knowledge."""
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
FILE=ROOT/"governance/professional_source_intake.v1.json"


class SourceIntakeSafetyTests(unittest.TestCase):
    def test_sources_remain_pending_and_no_signed_sop_is_fabricated(self):
        manifest=json.loads(FILE.read_text())
        self.assertEqual(manifest["state"],"REVIEW_PENDING_NO_SIGNED_CONTENT")
        self.assertEqual(manifest["authority"],"NONE_CONFIGURED")
        self.assertFalse(manifest["automatically_ingestable"])
        self.assertFalse(manifest["engine05_publish_allowed"])
        self.assertFalse(manifest["engine06_sop_publish_allowed"])
        self.assertEqual(len(manifest["sources"]),3)
        for item in manifest["sources"]:
            self.assertEqual(item["validation"],
                "SOURCE_IDENTIFIED_NOT_SPECIALIST_APPROVED")
            self.assertTrue(item["url"].startswith("https://"))
            self.assertEqual(item["service_kind"],"HAIR_COLOR")
        sop=manifest["professional_sop_intake"]
        self.assertEqual(sop["status"],"AWAITING_QUALIFIED_SPECIALIST")
        self.assertFalse(sop["operations_authorized"])
        self.assertFalse(sop["chemical_parameters_published"])
        self.assertGreaterEqual(len(sop["requires"]),10)


if __name__=="__main__":
    unittest.main()
