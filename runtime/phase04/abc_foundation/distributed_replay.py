"""ENG14 durable PostgreSQL JTI replay admission; never a token verifier.

A request MAY reach this class only after an external issuer-pinned JWT
signature/audience/expiry verifier and workload mTLS authorization. The
database verifies authenticated physical LOGIN for managed tenant mode, with
a unique constraint enforcing atomic claims across processes and replicas.
"""
import re
import uuid
from datetime import datetime,timezone,timedelta
from .store import DomainError

_ISSUER=re.compile(r"^https://[A-Za-z0-9.-]+(?::443)?(?:/[A-Za-z0-9._~/-]*)?$")
_AUDIENCE=re.compile(r"^[A-Za-z0-9._:/-]{3,256}$")


class PostgresReplayLedger:
    def __init__(self,store):
        if not callable(getattr(store,"_connect",None)):
            raise ValueError("managed_or_synthetic_database_connection_required")
        self.store=store

    def claim(self,*,tenant_id,issuer,audience,jti,expires_at):
        """Atomic single-use. False/replay triggers failure; never retry as a new jti.

        Caller must be a protected private gateway, not an arbitrary browser.
        SQL checks current authenticated DB workload and managed tenant mode.
        """
        if (not isinstance(tenant_id,str) or not 1<=len(tenant_id)<=128
            or not isinstance(issuer,str) or not _ISSUER.fullmatch(issuer)
            or not isinstance(audience,str) or not _AUDIENCE.fullmatch(audience)
            or not isinstance(jti,str)):
            raise DomainError(403,"invalid_replay_claim_context")
        try:
            parsed=uuid.UUID(jti)
            if str(parsed)!=jti or parsed.version!=4:
                raise ValueError()
        except (ValueError,TypeError,AttributeError):
            raise DomainError(403,"invalid_v2_jti") from None
        if (not isinstance(expires_at,datetime) or expires_at.tzinfo is None):
            raise DomainError(403,"untrusted_v2_token_expiry")
        now=datetime.now(timezone.utc)
        exp=expires_at.astimezone(timezone.utc)
        if exp<=now or exp>now+timedelta(minutes=5):
            raise DomainError(403,"v2_expiry_outside_short_lived_window")
        try:
            with self.store._connect() as con:
                # New transaction-scoped tenant claim: never depend on stale
                # connection-pool GUC or token-supplied tenant role.
                con.execute("SELECT set_config('abc.tenant',%s,true)",(tenant_id,))
                row=con.execute(
                  "SELECT abc.eng14_claim_v2_jti(%s,%s,%s,%s,%s) AS admitted",
                  (tenant_id,issuer,audience,parsed,exp)).fetchone()
                if row is None or row["admitted"] is not True:
                    raise DomainError(409,"distributed_replay_detected")
            return {"admitted":True,"token_reusable":False,"release_approved":False}
        except DomainError:
            raise
        except Exception as exc:
            # Fail closed for network outage or misconfigured DB role; do
            # not echo source token or credentials.
            raise DomainError(503,"distributed_replay_ledger_unavailable") from exc
