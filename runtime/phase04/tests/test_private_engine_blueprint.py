"""Static no-deploy three-engine private topology contract."""
import pathlib
import unittest
import yaml


class PrivateEngineBlueprintTests(unittest.TestCase):
    def test_independent_private_services_and_disabled_automatic_rollout(self):
        path=pathlib.Path(__file__).resolve().parents[3] / "infra" / "render" / "private_engine_services.staging.template.yaml"
        body=yaml.safe_load(path.read_text())
        services=body["services"]
        self.assertEqual(len(services),3)
        self.assertEqual(len({s["name"] for s in services}),3)
        for i, service in enumerate(services,4):
            with self.subTest(engine=i):
                self.assertEqual(service["type"],"pserv")
                self.assertEqual(service["runtime"],"docker")
                self.assertIn("private_engine_service_server",service["dockerCommand"])
                self.assertEqual(service["autoDeployTrigger"],"off")
                env={x["key"]:x for x in service["envVars"]}
                self.assertEqual(env["ABC_ENGINE_ID"]["value"],f"ENG-{i:02d}")
                self.assertEqual(env["ABC_NETWORK_BOUNDARY"]["value"],
                                 "RENDER_PRIVATE_SERVICE")
                self.assertEqual(env["ABC_ENGINE_SYNTHETIC_ONLY"]["value"],"true")
                for key in ("ABC_WORKLOAD_ISSUER","ABC_WORKLOAD_JWKS_URL",
                            "ABC_TLS_CERT_FILE","ABC_TLS_KEY_FILE","ABC_TLS_CA_FILE",
                            "ABC_ENGINE_CONSUMER_ID"):
                    self.assertIs(env[key]["sync"],False)
                    self.assertNotIn("value",env[key])
                self.assertNotIn("url",service)
                self.assertNotIn("routes",service)
