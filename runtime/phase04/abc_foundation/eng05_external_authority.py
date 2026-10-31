"""ENG05: curated public-source intake and externally pinned reviewer issuer.

URL discovery is not document-rights clearance. A cryptographically valid
CI credential issuer is never by itself a real license or release authority.
All output is a REVIEW-ONLY envelope; no ENG06 dispatch or customer guidance.
"""
from __future__ import annotations
import base64
import hashlib
import re
from datetime import datetime,timezone
from urllib.parse import urlsplit
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from .eng05_professional_sources import (
    SourceGovernanceError, canonical, digest, adjudicate)

CONTRACT="abc.eng05.official-reference-discovery.v1.review"
ISSUER_CONTRACT="abc.eng05.external-credential-issuer.v1.review"
ALLOWED_HOSTS={
 "single-market-economy.ec.europa.eu",
 "echa.europa.eu",
 "eur-lex.europa.eu",
 "www.gesetze-im-internet.de",
}
VERSION=re.compile(r"^[1-9][0-9]*\.[0-9]+\.[0-9]+$")


def _exact(data,fields,error):
    if not isinstance(data,dict) or set(data)!=set(fields):
        raise SourceGovernanceError(error)


def _time(value):
    if not isinstance(value,str):
        raise SourceGovernanceError("issuer_timestamp_required")
    try:
        dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc:
        raise SourceGovernanceError("issuer_timestamp_invalid") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise SourceGovernanceError("issuer_timestamp_ambiguous")
    return dt.astimezone(timezone.utc)


def _official_url(uri):
    if not isinstance(uri,str) or len(uri)>400:
        raise SourceGovernanceError("reference_url_invalid")
    u=urlsplit(uri)
    if (u.scheme!="https" or u.hostname not in ALLOWED_HOSTS
        or u.username is not None or u.password is not None or u.port is not None
        or not u.path.startswith("/") or u.fragment or
        not u.netloc==u.hostname or u.path.startswith("//")):
        raise SourceGovernanceError("reference_must_be_exact_official_https_origin")
    return u


def validate_discovery_catalog(catalog):
    _exact(catalog,("contract","domain","jurisdiction","discovered_on",
       "status","usage_policy","external_credential_issuer_connected",
       "professional_rights_cleared","specialist_signatures_collected",
       "professional_release_authorized","eng05_to_eng06_dispatch_authorized",
       "references","professional_credential_authority_refs"),"catalog_shape")
    if (catalog["contract"]!=CONTRACT or catalog["domain"]!="HAIR_COLOR"
        or catalog["jurisdiction"]!="EU"
        or catalog["status"]!="REFERENCE_DISCOVERED_NOT_PROFESSIONALLY_APPROVED"
        or catalog["usage_policy"]!="URL_AND_OWN_METADATA_ONLY_NO_SOURCE_DOCUMENT_REPUBLICATION"
        or _time(catalog["discovered_on"]+"T00:00:00+00:00").year<2026
        or catalog["external_credential_issuer_connected"] is not False
        or catalog["professional_rights_cleared"] is not False
        or catalog["specialist_signatures_collected"]!=0
        or catalog["professional_release_authorized"] is not False
        or catalog["eng05_to_eng06_dispatch_authorized"] is not False):
        raise SourceGovernanceError("catalog_authorization_or_scope_invalid")
    refs=catalog["references"]
    if not isinstance(refs,list) or not 1<=len(refs)<=12:
        raise SourceGovernanceError("catalog_reference_count_invalid")
    ids=set();urls=set()
    for entry in refs:
        _exact(entry,("reference_id","title","publisher","url","source_class",
          "jurisdiction","scope","discovery_note","legal_effect",
          "raw_document_sha256","license_to_copy_verified",
          "expert_verified","status"),"reference_entry_shape")
        _official_url(entry["url"])
        if (entry["reference_id"] in ids or entry["url"] in urls
            or entry["status"]!="REFERENCE_ONLY"
            or entry["jurisdiction"]!="EU" or entry["scope"]!="HAIR_COLOR"
            or entry["raw_document_sha256"] is not None
            or entry["license_to_copy_verified"] is not False
            or entry["expert_verified"] is not False
            or any(not isinstance(entry[k],str) or not 3<=len(entry[k])<=500
               for k in ("reference_id","title","publisher","source_class",
                         "discovery_note","legal_effect"))):
            raise SourceGovernanceError("unqualified_reference_claim")
        ids.add(entry["reference_id"])
        urls.add(entry["url"])
    refs=catalog["professional_credential_authority_refs"]
    if not isinstance(refs,list) or not 1<=len(refs)<=10:
        raise SourceGovernanceError("authority_discovery_invalid")
    for entry in refs:
        _exact(entry,("authority_id","publisher","url","purpose"),"authority_entry")
        _official_url(entry["url"])
        if any(not isinstance(entry[k],str) or not 3<=len(entry[k])<=200
               for k in ("authority_id","publisher")):
            raise SourceGovernanceError("authority_reference_invalid")
        if entry["purpose"] not in ("LOCATE_COMPETENT_AUTHORITY_NOT_VERIFY_PERSON",
                                  "IDENTIFY_STATUTORY_REGISTRATION_BASIS_NOT_VERIFY_PERSON"):
            raise SourceGovernanceError("authority_is_not_an_individual_credential")
    return {"catalog_sha256":digest(catalog),"references_identified":len(ids),
       "qualified_source_documents":0,"credential_issuers_connected":0,
       "release_authorized":False}


def _b64(raw,length,label):
    if not isinstance(raw,str):
        raise SourceGovernanceError(label+"_invalid")
    try:
        data=base64.b64decode(raw,validate=True)
    except Exception as exc:
        raise SourceGovernanceError(label+"_invalid") from exc
    if len(data)!=length:
        raise SourceGovernanceError(label+"_length_invalid")
    return data


def verify_external_credential_manifest(signed,*,trusted_root_key_b64,
          independently_pinned_root_sha256,now=None):
    """Test an issuer-signed roster against an OUT-OF-BAND trusted key pin.

    Importantly the pinned root is not read from the submitted manifest,
    the source catalog, GitHub, or a self-declared reviewer. This function
    returns transient anchors only and never grants professional authority.
    """
    _exact(signed,("contract","issuer_id","version","issued_at","expires_at",
       "jurisdiction","credential_records","revoked_credentials",
       "signature_alg","signature_b64"),"issuer_manifest_shape")
    if (signed["contract"]!=ISSUER_CONTRACT or
        not isinstance(signed["version"],str) or not VERSION.fullmatch(signed["version"])
        or signed["signature_alg"]!="Ed25519" or signed["jurisdiction"]!="EU"
        or not isinstance(signed["issuer_id"],str) or not 5<=len(signed["issuer_id"])<=200):
        raise SourceGovernanceError("issuer_contract_or_jurisdiction_invalid")
    root=_b64(trusted_root_key_b64,32,"independent_root")
    if (not isinstance(independently_pinned_root_sha256,str)
        or len(independently_pinned_root_sha256)!=64
        or hashlib.sha256(root).hexdigest()!=independently_pinned_root_sha256):
        raise SourceGovernanceError("externally_pinned_root_mismatch")
    manifest={k:v for k,v in signed.items() if k!="signature_b64"}
    signature=_b64(signed["signature_b64"],64,"issuer_signature")
    try:
        Ed25519PublicKey.from_public_bytes(root).verify(signature,canonical(manifest))
    except Exception as exc:
        raise SourceGovernanceError("issuer_signature_invalid") from exc
    instant=_time(now) if isinstance(now,str) else (now or datetime.now(timezone.utc))
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise SourceGovernanceError("issuer_time_ambiguous")
    if not _time(signed["issued_at"])<=instant<_time(signed["expires_at"]):
        raise SourceGovernanceError("issuer_roster_expired_or_future")
    entries=signed["credential_records"]
    if not isinstance(entries,list) or not 1<=len(entries)<=256:
        raise SourceGovernanceError("issuer_credential_count_invalid")
    revoked=signed["revoked_credentials"]
    if (not isinstance(revoked,list) or len(revoked)!=len(set(revoked))
        or not all(isinstance(x,str) for x in revoked)):
        raise SourceGovernanceError("invalid_issuer_revocation_list")
    anchors={}
    all_ids=set()
    for entry in entries:
        _exact(entry,("credential_id","reviewer_id","credential_status",
           "scopes","jurisdiction","valid_from","valid_until",
           "reviewer_public_key_b64","verification_ref",
           "independent_verifier_ref"),"issuer_credential_shape")
        cred_id=entry["credential_id"]
        if not isinstance(cred_id,str) or not 4<=len(cred_id)<=200 or cred_id in all_ids:
            raise SourceGovernanceError("issuer_duplicate_or_invalid_credential")
        all_ids.add(cred_id)
        _official_url(entry["verification_ref"])
        _official_url(entry["independent_verifier_ref"])
        if (entry["credential_status"] not in ("VERIFIED","REVOKED","EXPIRED")
            or entry["jurisdiction"]!="EU"
            or not isinstance(entry["reviewer_id"],str) or not 4<=len(entry["reviewer_id"])<=200
            or not isinstance(entry["scopes"],list) or
              not entry["scopes"] or not set(entry["scopes"])<={"HAIR_COLOR"}
            or _time(entry["valid_from"])>instant
            or _time(entry["valid_until"])<=_time(entry["valid_from"])):
            raise SourceGovernanceError("issuer_credential_invalid")
        pub=_b64(entry["reviewer_public_key_b64"],32,"reviewer_key")
        if (cred_id in revoked or entry["credential_status"]!="VERIFIED"
            or instant>=_time(entry["valid_until"])):
            continue
        anchors[cred_id]={
         "reviewer_id":entry["reviewer_id"],"credential_status":"VERIFIED",
         "scopes":entry["scopes"],"valid_from":entry["valid_from"],
         "valid_until":entry["valid_until"],
         "public_key":Ed25519PublicKey.from_public_bytes(pub),
         "authority_attested":True}
    if not set(revoked)<=all_ids:
        raise SourceGovernanceError("unknown_credential_revocation_id")
    return {"issuer_manifest_sha256":digest(signed),
       "issuer_root_sha256":independently_pinned_root_sha256,
       "qualified_review_anchors":anchors,
       "qualifying_user_records_count":len(anchors),
       "professional_runtime_authorized":False,
       "eng05_to_eng06_dispatch_authorized":False}


def review_only_external_dossier(documents,reviews,issuer_packet,*,trusted_root_key_b64,
                                independently_pinned_root_sha256,now=None):
    roster=verify_external_credential_manifest(issuer_packet,
      trusted_root_key_b64=trusted_root_key_b64,
      independently_pinned_root_sha256=independently_pinned_root_sha256,now=now)
    decision=adjudicate(documents,reviews,
      trusted_credentials=roster["qualified_review_anchors"],now=now)
    return {**decision,"external_issuer_manifest_sha256":roster["issuer_manifest_sha256"],
       "professionally_released_facts":[],
       "eng05_to_eng06_dispatch_authorized":False,
       "customer_release_approved":False,
       "professional_runtime_authorized":False}
