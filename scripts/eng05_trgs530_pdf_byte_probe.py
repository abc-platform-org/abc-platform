"""ENG05: reproducible, no-retention official TRGS530 PDF byte receipt.

Use in an isolated ephemeral runner; never commit raw third-party PDFs.
The full-file SHA256 attests bytes fetched, NOT a publisher-signed file,
licence to commercialise, current legal interpretation, practitioner review,
or ENG05/ENG06 authorisation.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import ssl
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler

OFFICIAL={
 "BGW":"https://www.bgw-online.de/resource/blob/20628/29cbf999ca5c2d91e741fa6964c6c619/trgs530-gefahrstoffe-friseurhandwerk-data.pdf",
 "BAUA":"https://www.baua.de/DE/Angebote/Rechtstexte-und-Technische-Regeln/Regelwerk/TRGS/pdf/TRGS-530.pdf?__blob=publicationFile",
}
MAX_BYTES=6_000_000
PDF_BEGIN=b"%PDF-"
SAFE_FIELDS=("source_document_sha256","source_bytes","pdf_pages",
  "publisher","requested_url","resolved_url","pdf_identity_checked",
  "source_bytes_verified","source_edition","retrieved_at_utc")


class SourceFetchError(ValueError):
    pass


def _allowed(url):
    if not isinstance(url,str) or url not in OFFICIAL.values():
        raise SourceFetchError("non_pinned_url")
    p=urlparse(url)
    if (p.scheme!="https" or p.hostname not in
        {"www.bgw-online.de","www.baua.de"} or p.port is not None
        or p.username is not None or p.password is not None
        or p.fragment):
        raise SourceFetchError("source_origin_invalid")
    return url


class BoundedRedirects(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        _allowed(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def verify_pdf_bytes(data,*,requested_url,resolved_url):
    """Strict PDF structure and 2023 rule identity, no legal approval."""
    _allowed(requested_url);_allowed(resolved_url)
    if (not isinstance(data,bytes) or not 32_000<=len(data)<=MAX_BYTES
        or not data.startswith(PDF_BEGIN)
        or b"%%EOF" not in data[-2048:]):
        raise SourceFetchError("not_complete_bounded_pdf")
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise SourceFetchError("pypdf_dependency_unavailable") from exc
    try:
        reader=PdfReader(io.BytesIO(data),strict=True)
        if len(reader.pages)!=15:
            raise SourceFetchError("unexpected_pdf_page_count")
        front=reader.pages[0].extract_text() or ""
        words=("TRGS 530","Friseurhandwerk","20.04.2023")
        if not all(x in front for x in words):
            raise SourceFetchError("document_title_or_edition_mismatch")
    except SourceFetchError:
        raise
    except Exception as exc:
        raise SourceFetchError("pdf_parser_or_document_identity_failed") from exc
    label=next(k for k,v in OFFICIAL.items() if v==requested_url)
    return {
      "contract":"abc.eng05.actual-pdf-byte-receipt.v1.review",
      "source_document_sha256":hashlib.sha256(data).hexdigest(),
      "source_bytes":len(data),"pdf_pages":15,"publisher":label,
      "requested_url":requested_url,"resolved_url":resolved_url,
      "pdf_identity_checked":True,"source_bytes_verified":True,
      "source_edition":"TRGS530_FASSUNG_20_04_2023",
      "not_publisher_signed_checksum":True,
      "rights_cleared":False,"expert_signatures_verified":0,
      "eng05_knowledge_ingestion_authorized":False,
      "eng05_to_eng06_dispatch_authorized":False,
      "customer_release_approved":False
    }


def download_one(url,opener=None):
    _allowed(url)
    opener=opener or build_opener(HTTPSHandler(context=ssl.create_default_context()),
                                   BoundedRedirects())
    req=Request(url,headers={"User-Agent":"ABC-ENG05-Verification/1.0",
                              "Accept":"application/pdf"})
    try:
        with opener.open(req,timeout=18) as response:
            final=response.geturl()
            _allowed(final)
            content_type=response.headers.get("Content-Type","").lower().split(";")[0]
            if content_type not in ("application/pdf","application/octet-stream"):
                raise SourceFetchError("unexpected_content_type")
            initial=response.headers.get("Content-Length")
            if initial is not None and int(initial)>MAX_BYTES:
                raise SourceFetchError("oversize_document")
            blob=response.read(MAX_BYTES+1)
            if len(blob)>MAX_BYTES:
                raise SourceFetchError("oversize_document")
    except SourceFetchError:
        raise
    except Exception as exc:
        raise SourceFetchError("official_source_transport_unavailable") from exc
    return verify_pdf_bytes(blob,requested_url=url,resolved_url=final)


def probe():
    attempts=[]
    for publisher in ("BGW","BAUA"):
        try:
            result=download_one(OFFICIAL[publisher])
            return {**result,"attempts":attempts,
                "verification_status":"ACTUAL_SOURCE_BYTES_VERIFIED",
                "requires_independent_publisher_checksum":True}
        except SourceFetchError as exc:
            attempts.append({"publisher":publisher,
                 "status":"FETCH_OR_VALIDATION_FAILED","reason":str(exc)})
    return {
      "contract":"abc.eng05.actual-pdf-byte-receipt.v1.review",
      "verification_status":"NO_VERIFIED_PDF_BYTES",
      "source_document_sha256":None,
      "source_bytes_verified":False,
      "attempts":attempts,"rights_cleared":False,
      "expert_signatures_verified":0,
      "eng05_knowledge_ingestion_authorized":False,
      "eng05_to_eng06_dispatch_authorized":False,
      "customer_release_approved":False}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--probe",action="store_true")
    p.add_argument("--input-file",default=None)
    p.add_argument("--source",choices=list(OFFICIAL),default="BGW")
    p.add_argument("--output",default=None)
    args=p.parse_args()
    if bool(args.probe)==bool(args.input_file):
        p.error("choose exactly one of --probe or --input-file")
    if args.probe:
        result=probe()
    else:
        source=Path(args.input_file)
        if not source.is_file():
            raise SystemExit("source_file_missing")
        if source.stat().st_size>MAX_BYTES:
            raise SystemExit("source_file_oversized")
        try:
            receipt=verify_pdf_bytes(source.read_bytes(),
               requested_url=OFFICIAL[args.source],resolved_url=OFFICIAL[args.source])
        except SourceFetchError as exc:
            raise SystemExit("source_file_verification_denied: "+str(exc)) from exc
        result={**receipt,"verification_status":"LOCAL_SOURCE_BYTES_VERIFIED_UNTRUSTED_SUPPLY"}
    out=json.dumps(result,sort_keys=True,separators=(",",":"))
    print("ENG05_TRGS530_SOURCE_BYTE_RECEIPT="+out)
    if args.output:
        Path(args.output).write_text(out+"\n",encoding="utf-8")
    # A blocked download never passes as a verified digest. The separate
    # report-only probe step cannot approve professional use by itself.
    return 0


if __name__=="__main__":
    raise SystemExit(main())
