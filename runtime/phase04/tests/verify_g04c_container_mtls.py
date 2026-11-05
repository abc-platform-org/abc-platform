"""G04-C: real inter-container TLS1.3 mTLS + bound RS256 JWT + network isolation.

No customer data, paid service, external identity issuer, or production keys.
Runs in a disposable GitHub Actions Docker --internal network. Three *real*
ABC engine dispatch servers run in distinct containers, with per-container
certificates, private network names, and exact ENG03->04->05->06 caller policy.
Do not interpret green CI as managed hosted infrastructure or A2 approval.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "runtime" / "phase04"))
from abc_foundation.eng02_consultation import SYNTHETIC_SERVICE  # noqa: E402
from abc_foundation.eng04_analysis import FIELDS  # noqa: E402
from abc_foundation.isolated_engine_service import VERSION  # noqa: E402

CONSUMER = "ci-pipeline-worker"
ISSUER = "https://issuer.abc-ci.example"
TARGETS = ("04", "05", "06")
CALLERS = {"04": "03", "05": "04", "06": "05"}
IMAGE = "abc-g04c-engine:ci"
PROBE = r'''
import json,sys
from abc_foundation.private_engine_transport import send_private_engine_message
a=json.load(sys.stdin)
target=a["message"]["engine_id"]
name="abc-"+target.lower().replace("-","")+"-private-synthetic"
base="/run/bad" if a.get("wrong_cert") else "/run/caller"
out=send_private_engine_message(
 host=name,port=int(target[-2:])+11000,server_name=name,
 certfile=base+"/cert.pem",keyfile=base+"/key.pem",
 ca_file="/run/trust/ca.pem",token=a["token"],
 message=a["message"],managed_private=True)
print(json.dumps(out,sort_keys=True))
'''


def command(*args, stdin=None, check=True, timeout=45):
    result = subprocess.run(
        ["docker", *map(str, args)], input=stdin, capture_output=True,
        text=True, timeout=timeout,
    )
    if check and result.returncode:
        # Never place JWTs or ephemeral signing material on the command line.
        raise RuntimeError(
            "docker command failed: " + " ".join(map(str, args[:3])) + ": " +
            (result.stderr or result.stdout)[-1200:]
        )
    return result


def new_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o755)
    path.write_bytes(content)
    # Temporary CI-only material; rootless image UID 10001 must read mounts.
    # Every credential directory is mounted ONLY into its owner container.
    path.chmod(0o444)


def make_pki(root):
    now = datetime.now(timezone.utc)
    ca_key = new_key()
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "ABC G04C disposable CI CA")])
    ca = (
        x509.CertificateBuilder()
        .subject_name(name).issuer_name(name).public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=3))
        .not_valid_after(now + timedelta(hours=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(ca_key, hashes.SHA256())
    )
    write(root / "trust" / "ca.pem", ca.public_bytes(serialization.Encoding.PEM))

    def issue(directory, name, san, is_server):
        key = new_key()
        crt = (
            x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)]))
            .issuer_name(ca.subject).public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=2))
            .not_valid_after(now + timedelta(minutes=20))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.SubjectAlternativeName([san]), critical=False)
            .add_extension(
                x509.ExtendedKeyUsage([
                    ExtendedKeyUsageOID.SERVER_AUTH if is_server
                    else ExtendedKeyUsageOID.CLIENT_AUTH
                ]), critical=False
            )
            .sign(ca_key, hashes.SHA256())
        )
        write(directory / "cert.pem", crt.public_bytes(serialization.Encoding.PEM))
        write(directory / "key.pem", key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ))
        return crt

    clients = {}
    for ident in ("03", "04", "05", "06"):
        clients[ident] = issue(
            root / "client" / ident, "abc-ci-caller-" + ident,
            x509.UniformResourceIdentifier(
                "spiffe://abc.internal/staging/eng-" + ident
            ), False,
        )
    issue(
        root / "client" / "bad", "abc-ci-untrusted-identity",
        x509.UniformResourceIdentifier("spiffe://abc.internal/staging/eng-06"),
        False,
    )
    for ident in TARGETS:
        issue(
            root / "server" / ident, "abc-ci-server-" + ident,
            x509.DNSName("abc-eng" + ident + "-private-synthetic"), True,
        )
    signer = new_key()
    write(root / "issuer" / "public.pem", signer.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo,
    ))
    return signer, clients


def signed_token(signer, clients, caller, target, *, audience=None):
    cert_der = clients[caller].public_bytes(serialization.Encoding.DER)
    thumb = base64.urlsafe_b64encode(hashlib.sha256(cert_der).digest()).rstrip(b"=").decode()
    moment = int(datetime.now(timezone.utc).timestamp())
    claims = {
        "iss": ISSUER, "aud": audience or "abc-engine:ENG-" + target,
        "sub": "spiffe://abc.internal/staging/eng-" + caller,
        "engine_id": "ENG-" + caller, "consumer_id": CONSUMER,
        "token_use": "service", "iat": moment, "nbf": moment, "exp": moment + 60,
        "jti": str(uuid.uuid4()), "cnf": {"x5t#S256": thumb},
    }
    return jwt.encode(claims, signer, algorithm="RS256",
                      headers={"kid": "g04c-ephemeral-1"})


def start_container(name, network, image, root, *, role=None, target=None, extra=()):
    common = [
        "run", "-d", "--name", name, "--network", network,
        "--read-only", "--cap-drop", "ALL", "--security-opt",
        "no-new-privileges:true", "--pids-limit", "128",
    ]
    if target:
        common += [
            "--network-alias", "abc-eng" + target + "-private-synthetic",
            "-v", str(root / "server" / target) + ":/run/engine:ro",
            "-v", str(root / "issuer") + ":/run/issuer:ro",
            "-v", str(REPO / "runtime" / "phase04" / "tests" /
                      "ci_g04c_intercontainer_server.py") +
                  ":/srv/abc/ci_g04c_server.py:ro",
            "-e", "ABC_ENV=LOCAL_INTEGRATION_ONLY",
            "-e", "ABC_NETWORK_BOUNDARY=CI_DOCKER_INTERNAL",
            "-e", "ABC_ENGINE_SYNTHETIC_ONLY=true",
            "-e", "ABC_CI_MTLS_TEST_ONLY=true",
            "-e", "ABC_ENGINE_ID=ENG-" + target,
            "-e", "ABC_CALLER_ENGINE_ID=ENG-" + CALLERS[target],
            "-e", "ABC_ENGINE_PORT=" + str(11000 + int(target)),
        ]
    if role:
        common += ["-v", str(root / "client" / role) + ":/run/caller:ro"]
    if extra:
        common += list(extra)
    common += ["-v", str(root / "trust") + ":/run/trust:ro", image]
    common += ["python", "-u", "/srv/abc/ci_g04c_server.py"] if target else ["sleep", "180"]
    command(*common)


def probe(container, target, caller, signer, certs, session, payload,
          *, token=None, wrong_cert=False, expected_failure=False):
    request = {
        "request_id": str(uuid.uuid4()), "engine_id": "ENG-" + target,
        "contract_version": VERSION, "consumer_id": CONSUMER,
        "session_id": session, "payload": payload,
    }
    credential = token if token is not None else signed_token(signer, certs, caller, target)
    p = command(
        "exec", "-i", container, "python", "-c", PROBE,
        stdin=json.dumps({"token": credential, "message": request,
                          "wrong_cert": wrong_cert}),
        check=not expected_failure, timeout=15,
    )
    if expected_failure:
        if p.returncode == 0:
            raise AssertionError("a disconnected engine unexpectedly accepted traffic")
        return None
    reply = json.loads(p.stdout)
    return reply, request


def assert_ok(result, request, target):
    if (result.get("engine_id") != "ENG-" + target
        or result.get("request_id") != request["request_id"]
        or result.get("session_id") != request["session_id"]
        or result.get("consumer_id") != CONSUMER
        or result.get("release_approved") is not False
        or not isinstance(result.get("result"), dict)):
        raise AssertionError("untrusted engine response")
    return result["result"]


def wait_ready(entry, target, *, attempts=45):
    name = "abc-eng" + target + "-private-synthetic"
    code = ("import socket; s=socket.create_connection((" +
            repr(name) + "," + str(11000 + int(target)) + "),timeout=1); s.close()")
    for _ in range(attempts):
        if command("exec", entry, "python", "-c", code, check=False).returncode == 0:
            return
        time.sleep(0.3)
    raise AssertionError("engine container readiness deadline: ENG-" + target)


def negative_exec(container, code):
    p = command("exec", container, "python", "-c", code, check=False, timeout=12)
    if p.returncode == 0:
        raise AssertionError("network/TLS isolation was bypassed")


def run(root, evidence):
    slug = (os.environ.get("GITHUB_RUN_ID", "manual") + "-" + uuid.uuid4().hex[:6])[:30]
    mesh = "abc-g04c-mesh-" + slug
    outside = "abc-g04c-outside-" + slug
    names = {x: "abc-g04c-" + slug + "-" + x for x in ("03", "04", "05", "06", "outside")}
    networks, containers = [], []
    signer, certs = make_pki(root)
    try:
        for network in (mesh, outside):
            command("network", "create", "--internal", network)
            networks.append(network)
            metadata = json.loads(command("network", "inspect", network).stdout)[0]
            assert metadata["Internal"] is True, "Docker network not internal"
        def start(identifier, network, **kwargs):
            start_container(names[identifier], network, IMAGE, root, **kwargs)
            containers.append(names[identifier])

        start("03", mesh, role="03",
              extra=("-v", str(root / "client" / "bad") + ":/run/bad:ro"))
        for ident in TARGETS:
            start(ident, mesh, role=ident if ident != "06" else None, target=ident)
        start("outside", outside)
        for target in TARGETS:
            wait_ready(names["03"], target)
        evidence["three_real_server_containers"] = True
        evidence["private_container_networks"] = True

        # Check actual transport paths, not HTTP demo/sleep simulation.
        session = str(uuid.uuid4())
        fields = [{
            "attribute_key": field, "evidence_id": str(uuid.uuid4()),
            "service_id": SYNTHETIC_SERVICE, "session_id": session,
            "evidence_class": "UNKNOWN", "source_type": "NOT_AVAILABLE", "value": None,
        } for field in sorted(FIELDS)]
        analysis_reply, request = probe(
            names["03"], "04", "03", signer, certs, session, {"evidence": fields})
        analysis = assert_ok(analysis_reply, request, "04")
        knowledge_reply, request = probe(
            names["04"], "05", "04", signer, certs, session,
            {"service_id": SYNTHETIC_SERVICE, "fixture": None})
        knowledge = assert_ok(knowledge_reply, request, "05")
        decision_reply, request = probe(
            names["05"], "06", "05", signer, certs, session,
            {"analysis": analysis, "knowledge": knowledge})
        decision = assert_ok(decision_reply, request, "06")
        if knowledge["unknowns"] != ["SOURCE_UNVERIFIED"] or decision["candidates"] != []:
            raise AssertionError("professional safety boundary bypass")
        evidence["eng03_to_eng04_mtls"] = True
        evidence["eng04_to_eng05_mtls"] = True
        evidence["eng05_to_eng06_mtls"] = True
        evidence["synthetic_decision_release_approved"] = False

        # Exact JWT replay denial, incorrect audience, certificate-bound identity.
        same = signed_token(signer, certs, "03", "04")
        first, req = probe(names["03"], "04", "03", signer, certs, session,
                           {"evidence": fields}, token=same)
        assert_ok(first, req, "04")
        again, _ = probe(names["03"], "04", "03", signer, certs, session,
                         {"evidence": fields}, token=same)
        if again.get("error") != "engine_request_rejected":
            raise AssertionError("JWT jti replay accepted")
        bad_aud = signed_token(signer, certs, "03", "04",
                               audience="abc-engine:ENG-06")
        reply, _ = probe(names["03"], "04", "03", signer, certs, session,
                         {"evidence": fields}, token=bad_aud)
        if reply.get("error") != "engine_request_rejected":
            raise AssertionError("JWT target audience bypass")
        reply, _ = probe(names["03"], "04", "03", signer, certs, session,
                         {"evidence": fields}, wrong_cert=True)
        if reply.get("error") != "engine_request_rejected":
            raise AssertionError("wrong mTLS client certificate accepted")
        reply, _ = probe(names["03"], "04", "03", signer, certs, session,
                         {"evidence": fields}, token="")
        if reply.get("error") != "engine_request_rejected":
            raise AssertionError("unauthenticated token accepted")
        evidence["cert_bound_jwt_replay_audience_and_absent_auth_denied"] = True

        # A peer in the correct network, but WITHOUT any client certificate,
        # must not receive a valid TLS engine response.
        no_cert = r'''
import socket,ssl
ctx=ssl.create_default_context(cafile="/run/trust/ca.pem")
ctx.minimum_version=ssl.TLSVersion.TLSv1_3
host="abc-eng05-private-synthetic"
with socket.create_connection((host,11005),timeout=3) as raw:
    with ctx.wrap_socket(raw,server_hostname=host) as s:
        s.sendall(b"\x00\x00\x00\x01x")
        assert len(s.recv(4))==4, "certificate-less engine traffic not accepted"
'''
        negative_exec(names["03"], no_cert)
        evidence["client_certificate_required"] = True

        # DNS AND routing denied from another --internal Docker bridge.
        negative_exec(names["outside"],
                      "import socket; socket.gethostbyname('abc-eng05-private-synthetic')")
        target_ip = command(
            "inspect", "-f",
            "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
            names["05"],
        ).stdout.strip()
        if not target_ip:
            raise AssertionError("missing inspected private IP")
        negative_exec(names["outside"],
                      "import socket; socket.create_connection((" +
                      repr(target_ip) + ",11005),timeout=2)")
        evidence["untrusted_network_dns_and_ip_denied"] = True

        # Fault injection: disconnect peer, reject traffic, reconnect and recover.
        command("network", "disconnect", mesh, names["05"])
        probe(names["04"], "05", "04", signer, certs, session,
              {"service_id": SYNTHETIC_SERVICE, "fixture": None},
              expected_failure=True)
        command("network", "connect", "--alias",
                "abc-eng05-private-synthetic", mesh, names["05"])
        wait_ready(names["04"], "05")
        again, req = probe(names["04"], "05", "04", signer, certs, session,
                           {"service_id": SYNTHETIC_SERVICE, "fixture": None})
        assert_ok(again, req, "05")
        evidence["peer_network_disconnect_reconnect_recovery"] = True

        # Real process crash and restart without cross-engine process loss.
        command("kill", names["05"])
        probe(names["04"], "05", "04", signer, certs, session,
              {"service_id": SYNTHETIC_SERVICE, "fixture": None},
              expected_failure=True)
        if command("inspect", "-f", "{{.State.Running}}", names["04"]).stdout.strip() != "true":
            raise AssertionError("ENG04 died when ENG05 crashed")
        if command("inspect", "-f", "{{.State.Running}}", names["06"]).stdout.strip() != "true":
            raise AssertionError("ENG06 died when ENG05 crashed")
        command("start", names["05"])
        wait_ready(names["04"], "05")
        again, req = probe(names["04"], "05", "04", signer, certs, session,
                           {"service_id": SYNTHETIC_SERVICE, "fixture": None})
        assert_ok(again, req, "05")
        evidence["peer_crash_containment_and_restart"] = True

        for target in TARGETS:
            bindings = json.loads(command("inspect", "-f",
                                "{{json .HostConfig.PortBindings}}",
                                names[target]).stdout)
            if bindings:
                raise AssertionError("engine port published to CI host")
        evidence["zero_published_engine_ports"] = True
    finally:
        for container in reversed(containers):
            command("rm", "-f", container, check=False)
        for network in reversed(networks):
            command("network", "rm", network, check=False)


def main():
    if os.environ.get("ABC_ENV") != "LOCAL_INTEGRATION_ONLY":
        raise SystemExit("synthetic_ci_only")
    if not os.environ.get("GITHUB_ACTIONS"):
        raise SystemExit("github_actions_disposable_runner_required")
    output = REPO / "a2" / "g04c"
    output.mkdir(parents=True, exist_ok=True)
    evidence = {
        "gate": "G04-C", "scope": "DISPOSABLE_DOCKER_CI_INTERCONTAINER",
        "git_sha": os.environ.get("GITHUB_SHA"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "tls_minimum_version": "TLSv1.3",
        "identity_provider": "CI_EPHEMERAL_OFFLINE_JWKS_TEST_KEY",
        "managed_identity_proven": False,
        "independent_managed_deployment_proven": False,
        "network_isolation_in_managed_staging_proven": False,
        "external_approvals_proven": False,
        "eng06_production_release_approved": False,
        "status": "FAIL",
    }
    with tempfile.TemporaryDirectory(prefix="abc-g04c-ephemeral-") as tmp:
        root = Path(tmp)
        root.chmod(0o755)
        try:
            run(root, evidence)
            evidence["status"] = "PASS"
        finally:
            # No private keys, JWTs, or client/customer records in the artifact.
            (output / "intercontainer-mtls-evidence.json").write_text(
                json.dumps(evidence, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            print(json.dumps(evidence, sort_keys=True))
    if evidence["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
