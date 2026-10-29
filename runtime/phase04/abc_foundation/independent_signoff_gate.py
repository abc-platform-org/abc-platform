"""Independent signed governance evidence verification; NEVER authorizes release.

Professional and Security reviewer JWTs must be independently issued and
validated against two distinct pinned managed HTTPS issuers. An approval
signature alone cannot attest that real infrastructure exists, so success
means evidence reviewed, never release authorization.
"""
import re
import uuid
from datetime import datetime,timezone
from urllib.parse import urlparse

import jwt
from jwt import PyJWKClient

from .store import DomainError

_HEX64=re.compile(r"^[a-f0-9]{64}$")
_HEX40=re.compile(r"^[a-f0-9]{40}$")
_KINDS=("professional","security")


class IndependentSignoffEvidenceGate:
    def __init__(self,*,authorities,clock=None):
        if not isinstance(authorities,dict) or set(authorities)!=set(_KINDS):
            raise ValueError("two_independent_signing_authorities_required")
        self.authorities={}
        issuers=set()
        for kind in _KINDS:
            cfg=authorities[kind]
            if not isinstance(cfg,dict) or not all(x in cfg for x in
                   ("issuer","jwks_uri")):
                raise ValueError("pinned_signoff_authority_required")
            issuer=cfg["issuer"]; uri=cfg["jwks_uri"]
            parsed=urlparse(issuer); jwks=urlparse(uri)
            if (parsed.scheme!="https" or not parsed.hostname
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or jwks.scheme!="https" or jwks.hostname!=parsed.hostname
                or jwks.username or jwks.password or jwks.query or jwks.fragment
                or issuer in issuers):
                raise ValueError("distinct_https_signoff_issuers_required")
            issuers.add(issuer)
            client=cfg.get("jwks_client")
            if client is None:
                client=PyJWKClient(uri,cache_keys=False,cache_jwk_set=True,
                                   lifespan=30,timeout=3)
            self.authorities[kind]=(issuer,client)
        self.clock=clock or (lambda:datetime.now(timezone.utc))

    def _verify(self,kind,token,*,head_sha,evidence_digest,scope):
        issuer,jwks=self.authorities[kind]
        if not isinstance(token,str) or len(token)>8192 or token.count(".")!=2:
            raise DomainError(403,"independent_signoff_missing_or_invalid")
        try:
            header=jwt.get_unverified_header(token)
            if (header.get("alg")!="RS256" or header.get("crit")
                or not isinstance(header.get("kid"),str) or not header["kid"]):
                raise ValueError("signing_algorithm_or_key_invalid")
            pub=jwks.get_signing_key_from_jwt(token).key
            payload=jwt.decode(token,pub,algorithms=["RS256"],
                audience="abc-phase04-signoff:"+kind,issuer=issuer,
                leeway=5,options={"require":["iss","aud","iat","nbf","exp",
                    "jti","sub","reviewer_role","decision","head_sha",
                    "evidence_digest","scope","approval_id"]})
            iat,nbf,exp=(payload[k] for k in ("iat","nbf","exp"))
            now=self.clock()
            if now.tzinfo is None:raise ValueError("invalid_trust_clock")
            t=int(now.astimezone(timezone.utc).timestamp())
            if (any(type(x) is not int for x in (iat,nbf,exp))
                or nbf>t+5 or iat>t+5 or exp<=t-5 or exp<=iat
                or exp-iat>900
                or payload["reviewer_role"]!=kind.upper()
                or payload["decision"]!="APPROVED"
                or payload["head_sha"]!=head_sha
                or payload["evidence_digest"]!=evidence_digest
                or payload["scope"]!=scope
                or not isinstance(payload["sub"],str) or len(payload["sub"])<5
                or str(uuid.UUID(payload["jti"]))!=payload["jti"]
                or str(uuid.UUID(payload["approval_id"]))!=payload["approval_id"]):
                raise ValueError("mismatched_signoff_scope_or_lifetime")
            if kind=="professional":
                if (not isinstance(payload.get("qualification_ref"),str)
                    or not payload["qualification_ref"].strip()
                    or not isinstance(payload.get("sop_version"),str)
                    or not payload["sop_version"].strip()):
                    raise ValueError("unbound_professional_qualification_or_sop")
            else:
                if (not isinstance(payload.get("security_review_ref"),str)
                    or not payload["security_review_ref"].strip()):
                    raise ValueError("missing_independent_security_review")
            return {"issuer":issuer,"reviewer":payload["sub"],
                    "approval_id":payload["approval_id"],
                    "jti":payload["jti"],"kind":kind}
        except (jwt.PyJWTError,ValueError,TypeError,KeyError,OverflowError) as exc:
            raise DomainError(403,"independent_signoff_invalid") from exc

    def evaluate(self,*,tokens,head_sha,evidence_digest,scope):
        if (not isinstance(head_sha,str) or not _HEX40.fullmatch(head_sha)
            or not isinstance(evidence_digest,str) or not _HEX64.fullmatch(evidence_digest)
            or scope!="ABC_PHASE04_SYNTHETIC_PRIVATE_STAGING"):
            raise DomainError(403,"unapproved_signoff_scope")
        if not isinstance(tokens,dict) or set(tokens)!=set(_KINDS):
            return {"status":"BLOCKED_MISSING_INDEPENDENT_REVIEW",
                    "release_approved":False,"verified_signoffs":0}
        verified=[self._verify(kind,tokens[kind],head_sha=head_sha,
                              evidence_digest=evidence_digest,scope=scope)
                  for kind in _KINDS]
        if (verified[0]["reviewer"]==verified[1]["reviewer"]
            or verified[0]["approval_id"]==verified[1]["approval_id"]
            or verified[0]["jti"]==verified[1]["jti"]):
            raise DomainError(403,"non_independent_signoff_identities")
        return {"status":"INDEPENDENT_EVIDENCE_SIGNED_NOT_DEPLOYMENT_APPROVED",
                "release_approved":False,"verified_signoffs":2,
                "review_ids":[item["approval_id"] for item in verified]}
