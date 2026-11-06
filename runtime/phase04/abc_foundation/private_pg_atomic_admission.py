"""Atomic PostgreSQL-backed private engine ingress for *disposable CI only*.

The receiver verifies TLS1.3 peer identity and signed certificate-bound JWT
before calling this adapter. This class then enforces physical DB-login binding,
current ENG14 human qualification, consent and session state; claims JTI in
the existing shared ENG14 replay ledger in the SAME SQL transaction as bounded
synthetic engine evaluation. Locks remain held until result validation/commit.

This is NOT a managed identity, deployed private mesh or human credential
issuer. It never enables staged/production traffic or professional release.
"""
import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone

import psycopg

from .isolated_engine_service import validate as validate_engine_message, VERSION
from .service_mesh_identity import canonical_spiffe_id
from .store import DomainError

_ALLOWED_ROUTES = frozenset((
    ("ENG-03", "ENG-04"),
    ("ENG-04", "ENG-05"),
    ("ENG-05", "ENG-06"),
))
_HEX64 = re.compile(r"^[a-f0-9]{64}$")


class PgAtomicPrivateAdmission:
    """A single-tenant/specialist test-only receiver tied to one real PG login."""

    def __init__(self, *, dsn, tenant_id, branch_id, human_issuer,
                 specialist_subject, caller_engine, target_engine,
                 consumer_id, state_version=0):
        if (os.environ.get("ABC_ENV") != "LOCAL_INTEGRATION_ONLY"
            or not isinstance(dsn,str) or not dsn.startswith("postgresql://")
            or (caller_engine,target_engine) not in _ALLOWED_ROUTES
            or not all(isinstance(v,str) and 3 <= len(v) <= 128 for v in
                       (tenant_id,branch_id,specialist_subject,consumer_id))
            or not isinstance(human_issuer,str)
            or not human_issuer.startswith("https://")
            or type(state_version) is not int or state_version < 0):
            raise ValueError("local_only_explicit_private_atomic_ingress_required")
        self._dsn=dsn
        self._tenant=tenant_id
        self._branch=branch_id
        self._issuer=human_issuer
        self._specialist=specialist_subject
        self._caller=caller_engine
        self._target=target_engine
        self._consumer=consumer_id
        self._version=state_version

    def admit_and_execute(self, identity, message, execute_fn):
        if os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY":
            raise DomainError(403,"managed_private_identity_not_attested")
        if (not isinstance(identity,dict) or identity.get("verified") is not True
            or identity.get("engine_id")!=self._caller
            or identity.get("subject")!=canonical_spiffe_id(self._caller)
            or identity.get("consumer_id")!=self._consumer
            or identity.get("audience")!="abc-engine:"+self._target
            or not isinstance(identity.get("issuer"),str)
            or not identity["issuer"].startswith("https://")
            or not isinstance(identity.get("cert_sha256"),str)
            or _HEX64.fullmatch(identity["cert_sha256"]) is None
            or not callable(execute_fn)):
            raise DomainError(403,"private_ingress_workload_scope_denied")
        validate_engine_message(message,self._target)
        if message["consumer_id"]!=self._consumer:
            raise DomainError(403,"private_ingress_consumer_denied")
        try:
            request_id=uuid.UUID(message["request_id"])
            session_id=uuid.UUID(message["session_id"])
            jti=uuid.UUID(identity["token_id"])
            expiration=identity["expires_at"]
            if (jti.version!=4
                or not isinstance(expiration,datetime)
                or expiration.tzinfo is None
                or expiration<=datetime.now(timezone.utc)):
                raise ValueError("expired_or_noncanonical_identity")
        except (KeyError,TypeError,ValueError,AttributeError) as exc:
            raise DomainError(403,"private_ingress_token_invalid") from exc

        # Hash the complete frozen v1 message, not a supplied digest string.
        message_digest=hashlib.sha256(json.dumps(
            message,sort_keys=True,separators=(",",":"),ensure_ascii=True
        ).encode("utf-8")).hexdigest()
        try:
            with psycopg.connect(self._dsn) as con:
                # The PG session_user remains the physical, independently
                # authenticated login even when this narrow role is selected.
                con.execute("SET LOCAL ROLE abc_private_ingress_exec")
                for key,value in (
                    ("abc.tenant",self._tenant),("abc.branch",self._branch),
                    ("abc.issuer",self._issuer),("abc.subject",self._specialist)):
                    con.execute("SELECT set_config(%s,%s,true)",(key,value))
                receipt=con.execute(
                    """SELECT abc.a2_private_atomic_admit(
                         %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                       ) AS admitted""",
                    (self._tenant,self._branch,session_id,self._version,
                     self._caller,self._target,self._consumer,
                     identity["subject"],identity["cert_sha256"],
                     self._issuer,self._specialist,
                     identity["issuer"],identity["audience"],jti,
                     expiration,request_id,message_digest)
                ).fetchone()
                if receipt is None or receipt[0] is not True:
                    raise DomainError(403,"private_ingress_atomic_eng14_denied")
                # Session/membership/consent/binding are FOR SHARE-locked until
                # bounded dispatch returns and the result is checked.
                result=execute_fn()
                if (not isinstance(result,dict)
                    or result.get("engine_id")!=self._target
                    or result.get("contract_version")!=VERSION
                    or result.get("request_id")!=message["request_id"]
                    or result.get("session_id")!=message["session_id"]
                    or result.get("consumer_id")!=self._consumer
                    or result.get("release_approved") is not False
                    or result.get("execution_authorized") is True
                    or result.get("customer_release_approved") is True
                    or result.get("downstream_dispatch_authorized") is True
                    or expiration<=datetime.now(timezone.utc)):
                    raise DomainError(403,"private_ingress_unsafe_result_denied")
                return result
        except DomainError:
            raise
        except psycopg.OperationalError as exc:
            raise DomainError(503,"private_ingress_database_unavailable") from exc
        except psycopg.Error as exc:
            raise DomainError(403,"private_ingress_atomic_eng14_denied") from exc
