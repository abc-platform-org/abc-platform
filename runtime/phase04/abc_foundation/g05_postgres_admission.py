"""A2-G05 local synthetic ENG14 admission: DB-atomic consent + replay.

Provides a deliberately opt-in, fail-closed replacement for the earlier
TestOnlySessionScope stub in v2 private engine admission. The existing
mTLS/RSA certificate-bound JWT verifier remains mandatory *before* this gate.

Critical scope: synthetic LOCAL_INTEGRATION_ONLY only. The injected human
issuer/subject are CI fixture bindings, NOT independently attested end-user
identities. In a real managed tenant, a separately approved human identity
issuer, physically certificate-authenticated DB login and deployment are
required. This is neither a professional service approval nor a release gate.
"""
import os
import re
import uuid

import psycopg

from .store import DomainError

ROUTES = frozenset((
    ("ENG-03", "ENG-04"),
    ("ENG-04", "ENG-05"),
    ("ENG-05", "ENG-06"),
))
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class G05PostgresAdmission:
    """Hold session, qualified specialist and consent row locks through dispatch.

    Replay admission uses the existing ENG14 durable ledger in this *same*
    SQL transaction. Failed execution rolls back the JTI claim; no response
    is delivered before a successful commit.
    """

    def __init__(self, *, store, human_issuer, specialist_subject):
        if (not callable(getattr(store, "_connect", None))
            or not isinstance(human_issuer, str)
            or not human_issuer.startswith("https://")
            or not isinstance(specialist_subject, str)
            or not 3 <= len(specialist_subject) <= 128):
            raise ValueError("trusted_local_g05_human_fixture_required")
        self._store = store
        self._human_issuer = human_issuer
        self._specialist = specialist_subject

    def admit_and_execute(self, *, message, identity, caller_engine, execute_fn):
        if os.environ.get("ABC_ENV") != "LOCAL_INTEGRATION_ONLY":
            raise DomainError(403, "g05_managed_service_not_approved")
        if (not isinstance(message, dict)
            or not isinstance(identity, dict)
            or identity.get("verified") is not True
            or identity.get("engine_id") != caller_engine
            or identity.get("consumer_id") != message.get("consumer_id")
            or not isinstance(identity.get("cert_sha256"), str)
            or HEX64.fullmatch(identity["cert_sha256"]) is None
            or identity.get("audience") != "abc-engine:" + str(message.get("engine_id"))
            or (caller_engine, message.get("engine_id")) not in ROUTES
            or not callable(execute_fn)):
            raise DomainError(403, "g05_verified_route_and_workload_required")
        try:
            sid = uuid.UUID(message["session_id"])
            token_id = uuid.UUID(identity["token_id"])
            if (str(sid) != message["session_id"]
                or str(token_id) != identity["token_id"]
                or token_id.version != 4):
                raise ValueError("noncanonical_jti_or_session")
        except (KeyError, ValueError, AttributeError, TypeError) as exc:
            raise DomainError(403, "g05_invalid_authenticated_identifiers") from exc

        # All SQL context values not derived from the JWT (human and operator)
        # are pinned in the trusted local test fixture, not taken from JSON.
        # The PostgreSQL function rechecks that the claimed identity belongs
        # to the exact session/tenant/branch and that the consent row is live.
        try:
            with self._store._connect() as conn:
                for key, val in (
                    ("abc.tenant", message["tenant_id"]),
                    ("abc.branch", message["branch_id"]),
                    ("abc.issuer", self._human_issuer),
                    ("abc.subject", self._specialist),
                ):
                    conn.execute("SELECT set_config(%s,%s,true)", (key, val))
                receipt = conn.execute(
                    """SELECT abc.eng14_g05_cert_bound_admit_and_claim(
                          %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                        ) AS admitted""",
                    (
                        message["tenant_id"], message["branch_id"], sid,
                        message["state_version"], caller_engine,
                        message["engine_id"], message["consumer_id"],
                        self._human_issuer, self._specialist,
                        identity["issuer"], identity["audience"],
                        token_id, identity["expires_at"],
                        identity["cert_sha256"],
                    ),
                ).fetchone()
                if receipt is None or receipt["admitted"] is not True:
                    raise DomainError(403, "g05_atomic_eng14_admission_denied")
                # Locks remain held while the synthetic engine runs. A
                # concurrent consent withdrawal or membership revocation
                # cannot commit in the middle of this protected operation.
                result = execute_fn()
                if (not isinstance(result, dict)
                    or result.get("release_approved") is not False
                    or result.get("execution_authorized") is not False
                    or result.get("engine_id") != message["engine_id"]
                    or result.get("request_id") != message["request_id"]
                    or result.get("session_id") != message["session_id"]
                    or result.get("consumer_id") != message["consumer_id"]):
                    raise DomainError(403, "g05_untrusted_synthetic_output")
                return result
        except DomainError:
            raise
        except psycopg.OperationalError as exc:
            raise DomainError(503, "g05_database_unavailable") from exc
        except psycopg.Error as exc:
            raise DomainError(403, "g05_atomic_eng14_admission_denied") from exc
