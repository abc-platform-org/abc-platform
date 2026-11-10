"""Strict private HTTP mTLS certificate admission tests (no external CA)."""
import unittest
from unittest.mock import Mock,patch

from abc_foundation.private_api_mtls import (
    BoundMTLSHTTPServer,create_private_api_server,
    parse_allowed_private_callers,verify_private_api_client_certificate)

A="spiffe://abc.internal/gateway/approved-caller"
A2="spiffe://abc.internal/gateway/second-authorized"
B="spiffe://abc.internal/eng03/eng03-worker"  # legacy per-engine API caller
C="spiffe://abc.internal/staging/eng-03"      # canonical engine principal
D="spiffe://abc.internal/gateway/unapproved"  # valid namespace, not on allowlist


class PrivateApiMTLSTests(unittest.TestCase):
    def test_explicit_exact_client_uri_allowlist(self):
        allowed=parse_allowed_private_callers(A+","+A2)
        self.assertEqual(allowed,frozenset((A,A2)))
        for invalid in ("","spiffe://evil.internal/gateway/approved-caller",
                        "spiffe://abc.internal/gateway/*",
                        "spiffe://abc.internal/eng99/a-service",
                        B,C,A+","+B,A+","+C,
                        "spiffe://abc.internal/staging/eng-19",
                        "spiffe://abc.internal/eng04/legacy-worker",
                        A+",",A+","+A," "+A,A+" "):
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):
                parse_allowed_private_callers(invalid)

    def test_client_certificate_uses_verified_uri_not_cn_or_dns(self):
        allowed=parse_allowed_private_callers(A)
        self.assertEqual(verify_private_api_client_certificate(
            {"subjectAltName":(("URI",A),("DNS","abc.local"))},allowed),A)
        for cert in (
            {},
            {"subject":((("commonName","approved-caller"),),)},
            {"subjectAltName":(("DNS","approved-caller"),)},
            {"subjectAltName":(("URI",B),)},
            {"subjectAltName":(("URI",C),)},
            {"subjectAltName":(("URI",D),)},
            {"subjectAltName":(("URI",A),("URI",B))},
        ):
            with self.subTest(cert=cert),self.assertRaises(ValueError):
                verify_private_api_client_certificate(cert,allowed)

    def test_managed_tls_material_required_before_bind(self):
        env={"ABC_API_TRANSPORT":"MTLS_TLS13",
             "ABC_API_TLS_CERT_FILE":"/mounted/service.crt",
             "ABC_API_TLS_KEY_FILE":"/mounted/service.key",
             "ABC_API_TLS_CA_FILE":"/mounted/ca.crt",
             "ABC_API_ALLOWED_CLIENT_URIS":A}
        for override in ({"ABC_API_TRANSPORT":"HTTP"},
                         {"ABC_API_TLS_KEY_FILE":""},
                         {"ABC_API_ALLOWED_CLIENT_URIS":"*"},
                         {"ABC_API_ALLOWED_CLIENT_URIS":B},
                         {"ABC_API_ALLOWED_CLIENT_URIS":C},
                         {"ABC_API_ALLOWED_CLIENT_URIS":A+","+B}):
            with self.subTest(override=override),self.assertRaises(ValueError):
                create_private_api_server(("0.0.0.0",10000),Mock(),
                                          {**env,**override})
        with (patch("abc_foundation.private_api_mtls.require_mtls_context")
              as mktls,patch("abc_foundation.private_api_mtls.BoundMTLSHTTPServer")
              as server):
            out=create_private_api_server(("0.0.0.0",10000),Mock(),env)
        self.assertIs(out,server.return_value)
        self.assertTrue(mktls.call_args.kwargs["server"])
        self.assertEqual(server.call_args.kwargs["allowed_client_uris"],
                         frozenset([A]))

    def test_manual_allowlist_cannot_bypass_gateway_namespace(self):
        for illegal in (B,C,"spiffe://abc.internal/staging/eng-14"):
            with self.subTest(illegal=illegal):
                forged=frozenset([illegal])
                with self.assertRaisesRegex(
                        ValueError,"api_gateway_only_client_identity_required"):
                    verify_private_api_client_certificate(
                        {"subjectAltName":(("URI",illegal),)},forged)
                # Constructor must refuse an explicitly injected engine SAN
                # before binding a network listener, even without env parsing.
                with patch("http.server.ThreadingHTTPServer.__init__") as bind:
                    with self.assertRaisesRegex(
                            ValueError,"api_gateway_only_client_identity_required"):
                        BoundMTLSHTTPServer(("127.0.0.1",0),Mock(),
                            context=Mock(),allowed_client_uris=forged)
                    bind.assert_not_called()
        for bad in (frozenset(),{"not-a-frozenset"},frozenset([A,B])):
            with self.subTest(bad=repr(bad)),self.assertRaises(ValueError):
                verify_private_api_client_certificate(
                    {"subjectAltName":(("URI",A),)},bad)

    def test_reject_unapproved_client_before_http_dispatch(self):
        listener=BoundMTLSHTTPServer.__new__(BoundMTLSHTTPServer)
        listener.allowed_client_uris=frozenset([A])
        for illegal in (B,C,D):
            with self.subTest(illegal=illegal):
                sock=Mock()
                sock.getpeercert.return_value={
                    "subjectAltName":(("URI",illegal),)}
                with patch("http.server.ThreadingHTTPServer.get_request",
                           return_value=(sock,("127.0.0.1",30000))):
                    with self.assertRaisesRegex(OSError,"private_api_peer_rejected"):
                        listener.get_request()
                sock.close.assert_called_once()

    def test_approved_gateway_socket_remains_accepted(self):
        listener=BoundMTLSHTTPServer.__new__(BoundMTLSHTTPServer)
        listener.allowed_client_uris=frozenset([A])
        sock=Mock()
        sock.getpeercert.return_value={"subjectAltName":(("URI",A),)}
        address=("127.0.0.1",30000)
        with patch("http.server.ThreadingHTTPServer.get_request",
                   return_value=(sock,address)):
            accepted,peer=listener.get_request()
        self.assertIs(accepted,sock)
        self.assertEqual(peer,address)
        sock.close.assert_not_called()
