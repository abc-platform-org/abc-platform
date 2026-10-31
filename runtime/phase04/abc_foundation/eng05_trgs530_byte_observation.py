"""Local-only evidence capture for TRGS 530 full PDF bytes.

No network access, no redistribution, no claim of structural PDF validity or
independently trusted source identity. Hash only actual supplied file bytes.
A valid digest is NOT a licence, professional review or ENG06 authorization.
"""
from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime,timezone
from pathlib import Path
from .eng05_professional_sources import SourceGovernanceError,canonical,digest
from .eng05_first_source_acceptance import EXPECTED_CASE

CONTRACT="abc.eng05.pdf-byte-observation.v1.review"
ALLOWED_URLS={
 "https://www.baua.de/DE/Angebote/Rechtstexte-und-Technische-Regeln/Regelwerk/TRGS/pdf/TRGS-530.pdf?__blob=publicationFile",
 "https://www.baua.de/DE/Angebote/Regelwerk/TRGS/pdf/TRGS-530.pdf?__blob=publicationFile",
 "https://www.bgw-online.de/resource/blob/20628/29cbf999ca5c2d91e741fa6964c6c619/trgs530-gefahrstoffe-friseurhandwerk-data.pdf",
}
MIN_SIZE=1024
MAX_SIZE=12*1024*1024


def _date(value):
    if not isinstance(value,str):
        raise SourceGovernanceError("observation_timestamp_missing")
    try:
        dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc:
        raise SourceGovernanceError("observation_timestamp_invalid") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise SourceGovernanceError("observation_timestamp_without_zone")
    return dt.astimezone(timezone.utc)


def inspect_pdf_file(pdf_path,*,source_url,retrieved_at,now=None):
    """Produce a NOT independently source-authenticated metadata receipt.

    Requires a human-collected local PDF, never downloads it, never writes the
    actual file to GitHub and never asserts a complete parser validation.
    """
    if source_url not in ALLOWED_URLS:
        raise SourceGovernanceError("pdf_source_url_not_allowlisted")
    when=_date(retrieved_at)
    instant=_date(now) if isinstance(now,str) else (now or datetime.now(timezone.utc))
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise SourceGovernanceError("inspection_clock_not_aware")
    if when>instant or (instant-when).total_seconds()>86400*30:
        raise SourceGovernanceError("pdf_retrieval_timestamp_out_of_window")
    if not isinstance(pdf_path,(str,Path)):
        raise SourceGovernanceError("pdf_file_path_required")
    p=Path(pdf_path)
    if not p.is_file() or p.is_symlink():
        raise SourceGovernanceError("pdf_regular_file_required")
    st=p.stat()
    if st.st_size<MIN_SIZE or st.st_size>MAX_SIZE:
        raise SourceGovernanceError("pdf_file_size_out_of_range")
    raw=p.read_bytes()
    if len(raw)!=st.st_size:
        raise SourceGovernanceError("pdf_size_changed_during_read")
    if re.match(rb"%PDF-(?:1\.[0-7]|2\.0)(?:\r?\n|\r)",raw) is None:
        raise SourceGovernanceError("pdf_magic_invalid")
    end=raw.rfind(b"%%EOF")
    if end<len(raw)-2048 or end<0 or raw[end+5:].strip(b"\x00\x09\x0a\x0c\x0d\x20"):
        raise SourceGovernanceError("pdf_final_eof_marker_missing")
    return {
      "contract":CONTRACT,
      "case_id":EXPECTED_CASE,
      "claimed_source_url":source_url,
      "observed_at":when.isoformat(),
      "raw_document_sha256":hashlib.sha256(raw).hexdigest(),
      "pdf_byte_size":len(raw),
      "header_eof_magic_present":True,
      "pdf_full_parser_validated":False,
      "byte_origin_independently_attested":False,
      "publisher_checksum_verified":False,
      "current_version_independently_attested":False,
      "commercial_ingestion_rights_approved":False,
      "professional_reviewer_approved":False,
      "eng05_runtime_ingestion_authorized":False,
      "eng05_to_eng06_dispatch_authorized":False,
      "customer_release_approved":False,
      "status":"HASH_OBSERVATION_PENDING_INDEPENDENT_PROVENANCE",
    }


def review_receipt_from_observation(observation):
    keys={"contract","case_id","claimed_source_url","observed_at",
      "raw_document_sha256","pdf_byte_size","header_eof_magic_present",
      "pdf_full_parser_validated","byte_origin_independently_attested",
      "publisher_checksum_verified","current_version_independently_attested",
      "commercial_ingestion_rights_approved","professional_reviewer_approved",
      "eng05_runtime_ingestion_authorized",
      "eng05_to_eng06_dispatch_authorized","customer_release_approved","status"}
    if not isinstance(observation,dict) or set(observation)!=keys:
        raise SourceGovernanceError("pdf_observation_contract_invalid")
    if (observation["contract"]!=CONTRACT
        or observation["case_id"]!=EXPECTED_CASE
        or observation["claimed_source_url"] not in ALLOWED_URLS
        or not isinstance(observation["raw_document_sha256"],str)
        or not re.fullmatch(r"[0-9a-f]{64}",observation["raw_document_sha256"])
        or type(observation["pdf_byte_size"]) is not int
        or not MIN_SIZE<=observation["pdf_byte_size"]<=MAX_SIZE
        or observation["header_eof_magic_present"] is not True
        or observation["status"]!="HASH_OBSERVATION_PENDING_INDEPENDENT_PROVENANCE"
        or any(observation[k] is not False for k in (
          "pdf_full_parser_validated","byte_origin_independently_attested",
          "publisher_checksum_verified","current_version_independently_attested",
          "commercial_ingestion_rights_approved","professional_reviewer_approved",
          "eng05_runtime_ingestion_authorized","eng05_to_eng06_dispatch_authorized",
          "customer_release_approved"))):
        raise SourceGovernanceError("pdf_receipt_claims_unverified_approval")
    _date(observation["observed_at"])
    return {"receipt_sha256":digest(observation),"observation":observation,
       "legal_review_status":"AWAITING_INDEPENDENT_LEGAL_OPINION",
       "specialist_review_status":"AWAITING_ACTUAL_CREDENTIAL_ATTESTATION",
       "professional_release_authorized":False,
       "eng05_to_eng06_dispatch_authorized":False}


def main():
    import argparse
    parser=argparse.ArgumentParser(description="Hash a locally supplied official TRGS 530 PDF. NO professional/legal acceptance.")
    parser.add_argument("--file",required=True)
    parser.add_argument("--source-url",required=True,choices=sorted(ALLOWED_URLS))
    parser.add_argument("--retrieved-at",required=True,help="operator-recorded ISO8601 timestamp with timezone")
    args=parser.parse_args()
    receipt=review_receipt_from_observation(inspect_pdf_file(
       args.file,source_url=args.source_url,retrieved_at=args.retrieved_at))
    print(json.dumps(receipt,sort_keys=True,indent=2))


if __name__=="__main__":
    main()
