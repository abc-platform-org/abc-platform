"""Real PostgreSQL16 TLS1.3 mutual client-certificate acceptance in Docker CI.

This is an isolated, disposable security *integration* test. It never uses or
issues a production CA. Neither Render-managed Postgres nor deployed customer
infrastructure is represented as satisfying the managed database gate.
"""
import os
import re
import secrets
import subprocess
import tempfile
import time
import uuid
from datetime import datetime,timedelta,timezone
from pathlib import Path

import psycopg
from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID,ExtendedKeyUsageOID


def cmd(*args,timeout=120,check=True):
    return subprocess.run(args,capture_output=True,text=True,timeout=timeout,
                          check=check)


def write(path,contents):
    path.write_bytes(contents)
    return str(path)


def issue_ca(now):
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,"ABC Disposable DB CI CA")])
    cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now-timedelta(minutes=2))
        .not_valid_after(now+timedelta(hours=2))
        .add_extension(x509.BasicConstraints(ca=True,path_length=0),critical=True)
        .sign(key,hashes.SHA256()))
    return key,cert


def issue_cert(now,ca_key,ca,common,server=False):
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,common)])
    cert=(x509.CertificateBuilder().subject_name(name).issuer_name(ca.subject)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now-timedelta(minutes=2))
        .not_valid_after(now+timedelta(minutes=30))
        .add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True)
        .add_extension(x509.ExtendedKeyUsage([
            ExtendedKeyUsageOID.SERVER_AUTH if server else ExtendedKeyUsageOID.CLIENT_AUTH
        ]),critical=False)
        .add_extension(x509.SubjectAlternativeName([
            x509.DNSName("localhost") if server
            else x509.UniformResourceIdentifier("spiffe://abc.internal/eng01/test-db")
        ]),critical=False)
        .sign(ca_key,hashes.SHA256()))
    return key,cert


def encode_key(key):
    return key.private_bytes(serialization.Encoding.PEM,
                             serialization.PrivateFormat.PKCS8,
                             serialization.NoEncryption())


def assert_denied(description,dsn):
    try:
        with psycopg.connect(dsn,connect_timeout=3):
            pass
    except (psycopg.OperationalError,psycopg.Error):
        return
    raise AssertionError("FAIL OPEN: "+description)


def main():
    if os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY":
        raise ValueError("disposable_CI_only")
    container="abc-mtls-ci-"+uuid.uuid4().hex[:10]
    tag=container+":test"
    now=datetime.now(timezone.utc)
    with tempfile.TemporaryDirectory(prefix="abc-pg-clientcert-ci-") as tmp:
        root=Path(tmp)
        cak,cac=issue_ca(now)
        sk,sc=issue_cert(now,cak,cac,"abc-db-ci-server",server=True)
        ck,cc=issue_cert(now,cak,cac,"abc_api_ci",server=False)
        wrongk,wrongc=issue_cert(now,cak,cac,"wrong_service_login",server=False)
        roguek,rogueca=issue_ca(now)
        untrustedk,untrustedc=issue_cert(now,roguek,rogueca,"abc_api_ci",server=False)
        write(root/"ca.crt",cac.public_bytes(serialization.Encoding.PEM))
        write(root/"server.crt",sc.public_bytes(serialization.Encoding.PEM))
        write(root/"server.key",encode_key(sk))
        for name,k,c in (("client",ck,cc),("wrong",wrongk,wrongc),
                          ("untrusted",untrustedk,untrustedc)):
            write(root/(name+".crt"),c.public_bytes(serialization.Encoding.PEM))
            keypath=root/(name+".key")
            write(keypath,encode_key(k))
            os.chmod(keypath,0o600)
        (root/"pg_hba.conf").write_text("""# test-only! Reject all unauthenticated remote traffic
local all all trust
hostssl all abc_api_ci 0.0.0.0/0 cert clientname=CN
host all all 0.0.0.0/0 reject
host all all ::/0 reject
""")
        (root/"10-ci-role.sql").write_text(
            "CREATE ROLE abc_api_ci LOGIN NOINHERIT NOSUPERUSER NOBYPASSRLS;\n")
        (root/"Dockerfile").write_text("""FROM postgres:16
COPY --chown=postgres:postgres server.crt server.key ca.crt pg_hba.conf /etc/abc-pki/
COPY 10-ci-role.sql /docker-entrypoint-initdb.d/10-ci-role.sql
RUN chmod 0600 /etc/abc-pki/server.key && chmod 0644 /etc/abc-pki/server.crt /etc/abc-pki/ca.crt /etc/abc-pki/pg_hba.conf
CMD ["postgres","-c","ssl=on","-c","ssl_min_protocol_version=TLSv1.3","-c","ssl_cert_file=/etc/abc-pki/server.crt","-c","ssl_key_file=/etc/abc-pki/server.key","-c","ssl_ca_file=/etc/abc-pki/ca.crt","-c","hba_file=/etc/abc-pki/pg_hba.conf"]
""")
        try:
            cmd("docker","build","--quiet","-t",tag,str(root),timeout=180)
            # No external port: bind published ephemeral port exclusively to
            # the runner's loopback. No persistence/managed credentials.
            cmd("docker","run","-d","--rm","--name",container,
                "-e","POSTGRES_PASSWORD="+secrets.token_urlsafe(24),
                "-e","POSTGRES_DB=abc_mtls_ci",
                "-p","127.0.0.1::5432",tag)
            port_text=cmd("docker","port",container,"5432/tcp").stdout.strip()
            match=re.search(r"127\.0\.0\.1:(\d+)",port_text)
            if not match: raise AssertionError("unexpected_docker_private_mapping")
            port=match.group(1)
            # initdb executes 10-ci-role.sql before the server begins
            # listening. Avoid pg_isready's initialization/shutdown race.
            for attempt in range(70):
                ready=cmd("docker","exec",container,"psql","-U","postgres",
                    "-d","abc_mtls_ci","-tAc",
                    "SELECT 1 FROM pg_roles WHERE rolname='abc_api_ci'",
                    check=False,timeout=6)
                if ready.returncode==0 and ready.stdout.strip()=="1":
                    break
                time.sleep(0.2)
            else:raise AssertionError("ephemeral_tls_postgres_role_not_ready")
            base=("host=localhost hostaddr=127.0.0.1 port="+port+
                  " dbname=abc_mtls_ci user=abc_api_ci "+
                  "sslmode=verify-full sslrootcert="+str(root/"ca.crt")+" ")
            good=base+"sslcert="+str(root/"client.crt")+" sslkey="+str(root/"client.key")
            with psycopg.connect(good,connect_timeout=4) as con:
                cert=con.execute("""SELECT ssl,version,client_dn,issuer_dn,
                    client_serial FROM pg_stat_ssl WHERE pid=pg_backend_pid()""").fetchone()
                if (not cert or cert[0] is not True or cert[1]!="TLSv1.3"
                    or "abc_api_ci" not in cert[2]
                    or "ABC Disposable DB CI CA" not in cert[3]
                    or cert[4]!=cc.serial_number):
                    raise AssertionError("cert_not_verified_in_database")
                con.execute("SELECT set_config('abc.tenant','forged-tenant',true)")
                after=con.execute("SELECT client_serial FROM pg_stat_ssl WHERE pid=pg_backend_pid()").fetchone()
                if after[0]!=cc.serial_number:
                    raise AssertionError("forged_GUC_modified_physical_identity")
            assert_denied("missing client cert",base)
            assert_denied("wrong certificate CN",base+
                 "sslcert="+str(root/"wrong.crt")+" sslkey="+str(root/"wrong.key"))
            assert_denied("untrusted client cert",base+
                 "sslcert="+str(root/"untrusted.crt")+" sslkey="+str(root/"untrusted.key"))
            assert_denied("plaintext PostgreSQL connection",
                  "host=localhost hostaddr=127.0.0.1 port="+port+
                  " dbname=abc_mtls_ci user=abc_api_ci sslmode=disable")
            assert_denied("wrong server DNS name",
                  good.replace("host=localhost","host=unexpected.example"))
            print("PASS: real Docker PostgreSQL16 TLS1.3 clientcert authentication; "
                  "missing/wrong/untrusted client, plaintext, hostname, forged GUC all rejected")
        finally:
            cmd("docker","rm","-f",container,check=False,timeout=15)
            cmd("docker","rmi","-f",tag,check=False,timeout=15)


if __name__=="__main__":
    main()
