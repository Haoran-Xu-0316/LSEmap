"""Archive named existing-building evidence from two public council records.

Keep drawings and photographs private. A portal session is required for the
public document URLs; discard its cookies after each bounded download batch.
"""

import hashlib
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/collections/aldwych-boundary243"
BASE = "https://idoxpa.westminster.gov.uk"
RECORDS = [
    {
        "application": "25/06721/ADV",
        "key": "T2SGK0RPGAD00",
        "html": "council-documents.html",
        "published": "2025-09-18",
        "files": {
            "LOCATION_PLAN": "location_plan.pdf",
            "SITE_PLAN": "site_plan.pdf",
            "EXISTING_KINGSWAY_ELEVATION": "existing_kingsway_elevation.pdf",
            "EXISTING_ALDWYCH_ELEVATION": "existing_aldwych_elevation.pdf",
            "PHOTO_1": "photo_1.jpg",
            "PHOTO_2": "photo_2.jpg",
        },
    },
    {
        "application": "20/04703/FULL",
        "key": "QDZG8ARPJFB00",
        "html": "con-council-documents.html",
        "published": "2020-08-28",
        "files": {
            "SITE_PLAN_A4": "con_site_plan.pdf",
            "EXISTING_ELEVATION_CON_ELEVATIONA4.PDF_1": "con_existing_elevation.pdf",
            "EXISTING_ELEVATION_COL_ELEVATION_A4.PDF_1": "col_existing_elevation.pdf",
        },
    },
]


def collect(record, previous):
    url = (
        BASE
        + "/online-applications/applicationDetails.do?activeTab=documents&keyVal="
        + record["key"]
    )
    cookies = OUT / "session-cookies.txt"
    html = OUT / record["html"]
    try:
        subprocess.run(
            [
                "curl",
                "--location",
                "--fail",
                "--silent",
                "--show-error",
                "--max-time",
                "30",
                "--cookie-jar",
                str(cookies),
                url,
                "-o",
                str(html),
            ],
            check=True,
        )
        soup = BeautifulSoup(html.read_text(), "html.parser")
        prefix = record["application"].replace("/", "_") + "-"
        sources = {}
        for anchor in soup.select("a[href]"):
            for label in record["files"]:
                if prefix + label + "-" in anchor["href"]:
                    sources[label] = urljoin(BASE, anchor["href"])
        assert set(sources) == set(record["files"])

        def fetch(item):
            label, source_url = item
            path = OUT / record["files"][label]
            old = previous.get(str(path.relative_to(ROOT)))
            if not (
                old
                and path.is_file()
                and hashlib.sha256(path.read_bytes()).hexdigest() == old["sha256"]
            ):
                subprocess.run(
                    [
                        "curl",
                        "--location",
                        "--fail",
                        "--silent",
                        "--show-error",
                        "--cookie",
                        str(cookies),
                        "--referer",
                        url,
                        "--retry",
                        "2",
                        "--max-time",
                        "45",
                        source_url,
                        "-o",
                        str(path),
                    ],
                    check=True,
                )
            content = path.read_bytes()
            assert (
                content.startswith(b"%PDF")
                if path.suffix == ".pdf"
                else content.startswith(b"\xff\xd8")
            )
            return {
                "application": record["application"],
                "label": label,
                "file": str(path.relative_to(ROOT)),
                "url": source_url,
                "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
                "published": record["published"],
                "photographCaptureDate": "unknown" if path.suffix == ".jpg" else None,
                "scope": "Existing-building evidence; application proposals and permission dates do not establish current completed construction",
            }

        with ThreadPoolExecutor(max_workers=3) as pool:
            return list(pool.map(fetch, sorted(sources.items())))
    finally:
        cookies.unlink(missing_ok=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = OUT / "download-manifest.json"
    previous = (
        {r["file"]: r for r in json.loads(manifest.read_text())["sources"]}
        if manifest.exists()
        else {}
    )
    sources = [source for record in RECORDS for source in collect(record, previous)]
    manifest.write_text(
        json.dumps(
            {"council": "Westminster", "checked": "2026-10-18", "sources": sources},
            indent=2,
        )
        + "\n"
    )
    for row in sources:
        print(row["label"], row["bytes"], row["sha256"], flush=True)


if __name__ == "__main__":
    main()
