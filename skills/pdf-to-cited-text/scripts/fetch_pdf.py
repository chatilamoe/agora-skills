#!/usr/bin/env python3
"""Download a PDF to research/pdfs/<id>.pdf, check that it really is a PDF, and record where it came
from in research/pdfs/<id>.pdf.json (URL, final URL after redirects, SHA-256, date, source id) so
that pdf_text.py and cite_find.py can cite it later.
"""
import hashlib
import json
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c  # noqa: E402

MAX_BYTES = 300 * 1024 * 1024

EPILOG = """examples:
  python3 fetch_pdf.py https://documents1.worldbank.org/curated/en/545241624880584363/pdf/Financial-Inclusion-Women-and-Building-Back-Better.pdf --id brief-161098

Then: python3 pdf_text.py research/pdfs/<id>.pdf
A landing page (HTML) instead of a PDF is refused with a message; look for the direct PDF link.
"""


def download(url, out_dir="research", file_id=None, source_id=None):
    """Fetch url; save <out_dir>/pdfs/<id>.pdf and its .json sidecar; return the sidecar dict."""
    body, headers, final = c.http_get(url, headers={"Accept": "application/pdf,*/*;q=0.8"})
    if len(body) > MAX_BYTES:
        raise c.FetchError("refusing a %d MB file" % (len(body) // 2**20))
    if body.lstrip()[:4] != b"%PDF":
        ctype = (headers.get("Content-Type") or "unknown type").split(";")[0]
        raise c.FetchError("%s did not return a PDF (%s, %d bytes): probably a landing page; find the direct "
                           "PDF link" % (urllib.parse.urlsplit(final).netloc, ctype, len(body)))
    if not file_id:
        file_id = c.slug(source_id) if source_id else c.slug(Path(urllib.parse.urlsplit(final).path).name)
    folder = Path(out_dir) / "pdfs"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (file_id + ".pdf")
    path.write_bytes(body)
    meta = {"id": file_id, "file": str(path), "url": url, "final_url": final, "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(), "fetched": c.today(), "source_id": source_id}
    Path(str(path) + ".json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def main(argv=None):
    ap = c.parser(__doc__.split("\n\n")[0], EPILOG)
    ap.add_argument("url", help="direct link to a PDF")
    ap.add_argument("--id", help="file name to use (default: from --source-id or the URL)")
    ap.add_argument("--source-id", help="the sources.jsonl id this PDF belongs to, e.g. wds:34285961")
    a = ap.parse_args(argv)
    try:
        meta = download(a.url, a.out, a.id, a.source_id)
    except c.FetchError as err:
        print("error: %s" % err, file=sys.stderr)
        return 1
    if a.json:
        c.print_json(meta)
        return 0
    print("saved %s (%.1f MB, sha256 %s...)" % (meta["file"], meta["bytes"] / 2**20, meta["sha256"][:12]))
    if meta["final_url"] != meta["url"]:
        print("redirected to %s" % meta["final_url"])
    print("next: python3 pdf_text.py %s" % meta["file"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
