"""Offline co-present visual workspace must not become a data collection endpoint."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
FRONT=ROOT/"prototypes/abc-ai-studio-v2"


class AIStudioV2OfflineUIContractTests(unittest.TestCase):
    def setUp(self):
        self.html=(FRONT/"index.html").read_text()
        self.css=(FRONT/"style.css").read_text()
        self.js=(FRONT/"app.js").read_text()

    def test_three_columns_and_mobile_breakpoints(self):
        for label in ("Input &amp; Controls","Visual Canvas","Look Workspace"):
            self.assertIn(label,self.html)
        self.assertIn("grid-template-columns:",self.css)
        self.assertIn("@media(max-width:700px)",self.css)
        self.assertIn('lang="fa" dir="rtl"',self.html)
        for panel in ("Session","Visual QA","Selected Look Lock","Technical Planning"):
            self.assertIn(panel,self.html)

    def test_no_network_customer_uploads_tracking_or_persistent_data(self):
        self.assertIn("connect-src 'none'",self.html)
        self.assertIn("img-src 'none'",self.html)
        self.assertIn("form-action 'none'",self.html)
        for token in ("fetch(","XMLHttpRequest","WebSocket","EventSource",
                      "localStorage","sessionStorage","indexedDB",
                      "navigator.mediaDevices","getUserMedia","sendBeacon",
                      "http://","https://"):
            self.assertNotIn(token,self.js)
        self.assertNotIn('type="file"',self.html)
        self.assertNotIn('<form',self.html)

    def test_look_selection_is_not_a_real_plan_handoff(self):
        self.assertIn('id="lock-look"',self.html)
        self.assertIn('id="check-plan"',self.html)
        self.assertIn("ENG-06: BLOCKED",self.html)
        self.assertIn("Technical Plan: BLOCKED",self.js)
        self.assertIn("هیچ دستور اجرایی",self.js)
        self.assertIn("بدون شبکه، API، ذخیره‌سازی",self.html)


if __name__=="__main__":
    unittest.main()
