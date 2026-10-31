"""Fetch and hash actual official TRGS 530 PDF bytes, never grant professional authority."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
from urllib.parse import urlsplit

SOURCES=(
 ("BAUA_CURRENT","https://www.baua.de/DE/Angebote/Regelwerk/TRGS/pdf/TRGS-530.pdf?__blob=publicationFile"),
 ("BAUA_LEGACY","https://www.baua.de/DE/Angebote/Rechtstexte-und-Technische-Regeln/Regelwerk/TRGS/pdf/TRGS-530.pdf?__blob=publicationFile"),
 ("BGW_OFFICIAL","https://www.bgw-online.de/resource/blob/20628/29cbf999ca5c2d91e741fa6964c6c619/trgs530-gefahrstoffe-friseurhandwerk-data.pdf"))
HOSTS={"www.baua.de","www.bgw-online.de"}
MAX_SIZE=5_000_000

def check_url(uri):
    try:
        u=urlsplit(uri)
        valid=(u.scheme=="https" and u.hostname in HOSTS and
               u.netloc==u.hostname and not u.username and not u.password
               and u.port is None and not u.fragment and
               u.path.startswith("/") and not u.path.startswith("//"))
    except (TypeError,ValueError):
        valid=False
    if not valid:
        raise ValueError("not_exact_official_https_origin")
    return uri

class OfficialRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        check_url(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def check_identity(text,pages):
    first=re.sub(r"\s+"," ",text)
    if type(pages) is not int or pages!=15:
        raise ValueError("expected_15_pages_missing")
    if not re.search(r"TRGS\s*530",first,re.I) or "Friseurhandwerk" not in first:
        raise ValueError("trgs530_title_missing")
    if not re.search(r"20\s*\.\s*0?4\s*\.\s*20\s*23",first):
        raise ValueError("2023_edition_missing")
    return True

def inspect_pdf(blob):
    if not isinstance(blob,bytes) or not 10_000<=len(blob)<=MAX_SIZE:
        raise ValueError("pdf_byte_size_invalid")
    if not blob.startswith(b"%PDF-") or b"%%EOF" not in blob[-2048:]:
        raise ValueError("pdf_structure_invalid")
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/"source.pdf"
        p.write_bytes(blob)
        try:
            info=subprocess.run(["pdfinfo",str(p)],capture_output=True,
                                text=True,check=True,timeout=15).stdout
            m=re.search(r"(?m)^Pages:\s*(\d+)\s*$",info)
            pages=int(m.group(1)) if m else -1
            first=subprocess.run(["pdftotext","-f","1","-l","1","-layout",
                                  str(p),"-"],capture_output=True,text=True,
                                  check=True,timeout=15).stdout
        except (OSError,subprocess.CalledProcessError,subprocess.TimeoutExpired) as exc:
            raise ValueError("pdf_parser_unavailable_or_failed") from exc
    check_identity(first,pages)
    return {"sha256_actual_pdf_bytes":hashlib.sha256(blob).hexdigest(),
            "byte_count":len(blob),"page_count":pages,
            "first_page_edition_verified":True}

def acquire(name,uri):
    check_url(uri)
    op=urllib.request.build_opener(OfficialRedirects())
    req=urllib.request.Request(uri,headers={
      "User-Agent":"ABC-ENG05-Review-Provenance/1.0","Accept":"application/pdf"})
    with op.open(req,timeout=24) as res:
        check_url(res.geturl())
        if int(res.headers.get("Content-Length","0"))>MAX_SIZE:
            raise ValueError("declared_pdf_too_large")
        details=inspect_pdf(res.read(MAX_SIZE+1))
        return {"source_id":name,"request_url":uri,"effective_url":res.geturl(),
                "http_status":res.getcode(),"content_type":res.headers.get("Content-Type"),
                **details,"status":"PDF_BYTES_HASHED_AND_EDITION_CHECKED"}

def run():
    attempts=[];verified=[]
    for name,uri in SOURCES:
        try:
            a=acquire(name,uri)
            verified.append(a)
            attempts.append({"source_id":name,"status":a["status"]})
        except (ValueError,urllib.error.URLError,TimeoutError,OSError) as exc:
            attempts.append({"source_id":name,"status":"SOURCE_NOT_VERIFIED",
                             "error_type":type(exc).__name__,
                             "failure_reason":str(exc)[:150]})
    return {"contract":"abc.eng05.trgs530.raw-byte-attestation.v1.review",
            "source_case":"eng05-de-hair-color-worker-safety-trgs530-20230420",
            "attempts":attempts,"verified_downloads":verified,
            "status":"PDF_BYTES_HASHED_AND_EDITION_CHECKED" if verified else "BLOCKED_SOURCE_BYTES_UNAVAILABLE",
            "original_pdf_hash_available":bool(verified),
            "current_version_requires_independent_recheck":True,
            "legal_reuse_clearance":False,"real_specialist_signatures":0,
            "professionally_released_facts":[],"eng05_review_worker_connected":False,
            "eng05_to_eng06_dispatch_authorized":False,"customer_release_approved":False}

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    result=run()
    p=Path(args.output)
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"status":result["status"],
                      "verified_files":len(result["verified_downloads"]),
                      "eng06_release":False}))
    summary=os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary,"a") as f:
            f.write("## ENG05 TRGS530 source evidence\n\nStatus: "+result["status"]+
                    "\n\nActual PDF bytes verified: "+str(len(result["verified_downloads"]))+
                    "\n\nProfessional and ENG06 release: **BLOCKED**\n")
