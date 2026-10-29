"""Validate the non-active private-only, mutual TLS Render API design."""
import pathlib
import unittest
import yaml


class PrivateAPIBlueprintTests(unittest.TestCase):
    def test_no_public_api_and_all_identity_material_external(self):
        root=pathlib.Path(__file__).resolve().parents[3]
        data=yaml.safe_load((root/"infra/render/private_api.staging.template.yaml").read_text())
        self.assertEqual(len(data["services"]),1)
        service=data["services"][0]
        self.assertEqual(service["type"],"pserv")
        self.assertEqual(service["runtime"],"docker")
        self.assertEqual(service["numInstances"],1)
        self.assertEqual(service["autoDeployTrigger"],"off")
        self.assertEqual(service["dockerfilePath"],"./runtime/phase04/Dockerfile")
        self.assertIn("staging_api",service["dockerCommand"])
        self.assertNotIn("healthCheckPath",service)
        values={item["key"]:item for item in service["envVars"]}
        for key,value in (
            ("ABC_ENV","STAGING_PRIVATE"),
            ("ABC_STAGING_PURPOSE","SYNTHETIC_NO_CLIENT_DATA"),
            ("ABC_NETWORK_BOUNDARY","RENDER_PRIVATE_SERVICE"),
            ("ABC_DB_AUTH_MODE","MANAGED_MTLS"),
            ("ABC_API_TRANSPORT","MTLS_TLS13")):
            self.assertEqual(values[key]["value"],value)
        for secret in (
            "ABC_PG_DSN","ABC_DB_WORKLOAD_LOGIN","ABC_DB_CLIENT_DN",
            "ABC_DB_ISSUER_DN","ABC_DB_CERT_SERIAL",
            "ABC_API_TLS_CERT_FILE","ABC_API_TLS_KEY_FILE",
            "ABC_API_TLS_CA_FILE","ABC_API_ALLOWED_CLIENT_URIS",
            "ABC_OIDC_ISSUER","ABC_OIDC_AUDIENCE","ABC_OIDC_JWKS_URI"):
            self.assertIs(values[secret]["sync"],False)
            self.assertNotIn("value",values[secret])
        for disallowed in ("ABC_SYNTHETIC_LEGACY_DB_COMPAT",
                           "LEGACY_SYNTHETIC","PUBLIC_WEB",
                           "PUBLIC_HTTP"):
            self.assertNotIn(disallowed,values)
