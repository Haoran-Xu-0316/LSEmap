"""Read-only CKK252 glass review against retained built photographs.

The exported campus and detail assets are checked together. This module creates
an audit only: no colour-calibrated source or modeled room support justifies a
new optical candidate, and opacity must not be relaxed into an empty envelope.
"""

import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/ckk-glass252"
BASE = ROOT / "result/blender/LSE_campus_detailed_v251.blend"
BASE_SHA = "6fa67b6a4640411c1065f9ca5f4d660150bb9075968f8adf881267fe1a39a6e9"
REFERENCES = [
    (
        "data/collections/exteriors/images/ckk_grimshaw_010.jpg",
        "https://grimshaw.global/projects/education-and-science/london-school-of-economics-new-academic-building/",
        "Historic principal elevation. Grey reflective glazing, some lit rooms; not calibrated glass-colour measurements.",
    ),
    (
        "data/collections/library_round5/photos/CKK_8f06506667f1.jpg",
        "https://www.willebrand.com/en/projects/lse-london-school-of-economics-grimshaw-architects.398",
        "Historic principal elevation and dormers corroborate neutral reflective panes.",
    ),
    (
        "data/collections/exteriors/images/ckk_grimshaw_009.jpg",
        "https://grimshaw.global/projects/education-and-science/london-school-of-economics-new-academic-building/",
        "Atrium skylight and clear gallery guards; does not establish side-wing room geometry.",
    ),
    (
        "data/collections/exteriors/images/ckk_grimshaw_014.jpg",
        "https://grimshaw.global/projects/education-and-science/london-school-of-economics-new-academic-building/",
        "Atrium doors, timber hall and gallery transparency; no measured external entrance registration.",
    ),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_glb(path):
    raw = path.read_bytes()
    magic, version, total = struct.unpack_from("<III", raw)
    assert magic == 0x46546C67 and version == 2 and total == len(raw)
    length, kind = struct.unpack_from("<II", raw, 12)
    assert kind == 0x4E4F534A
    return json.loads(raw[20 : 20 + length])


def glass_inventory(path):
    document = read_glb(path)
    nodes = [
        n for n in document["nodes"] if n.get("extras", {}).get("buildingCode") == "CKK"
    ]
    assert len(nodes) == 1
    primitives = document["meshes"][nodes[0]["mesh"]]["primitives"]
    used = sorted({p["material"] for p in primitives})
    rows = []
    for index in used:
        material = document["materials"][index]
        name = material["name"]
        extras = material.get("extras", {})
        if extras.get("webSurfaceRole") != "glazing" and not any(
            word in name.lower() for word in ("glass", "glazing")
        ):
            continue
        relevant = [p for p in primitives if p["material"] == index]
        bounds = [document["accessors"][p["attributes"]["POSITION"]] for p in relevant]
        colour = material.get("pbrMetallicRoughness", {}).get(
            "baseColorFactor", [1, 1, 1, 1]
        )
        rows.append(
            {
                "name": name.removeprefix("WEB_DETAIL_").removeprefix("WEB_"),
                "material": material,
                "rgbSpreadRatio": max(colour[:3]) / min(colour[:3]),
                "positionBounds": [
                    {"min": b.get("min"), "max": b.get("max"), "count": b["count"]}
                    for b in bounds
                ],
                "primitiveCount": len(relevant),
            }
        )
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": sha(path),
        "bytes": path.stat().st_size,
        "glassMaterials": rows,
    }


def main():
    assert sha(BASE) == BASE_SHA
    catalogue_path = ROOT / "web/public/models/catalogue.json"
    metadata_path = ROOT / "web/tools/building-metadata.json"
    protected = {
        str(p.relative_to(ROOT)): sha(p) for p in (BASE, catalogue_path, metadata_path)
    }
    catalogue = json.loads(catalogue_path.read_text())
    ckk = next(b for b in catalogue["buildings"] if b["code"] == "CKK")
    detail = ROOT / "web/public" / ckk["detailedExterior"]["url"].lstrip("/")
    assets = [
        glass_inventory(ROOT / "web/public/models/campus.glb"),
        glass_inventory(detail),
    ]
    mappings = [{r["name"]: r["material"] for r in a["glassMaterials"]} for a in assets]
    assert set(mappings[0]) == set(mappings[1])
    for name in mappings[0]:
        a, b = dict(mappings[0][name]), dict(mappings[1][name])
        a.pop("name")
        b.pop("name")
        assert a == b, name
    references = [
        {
            "path": path,
            "sha256": sha(ROOT / path),
            "url": url,
            "supports": role,
            "stage": "Historical built photograph; capture date and exact2026 condition unverified; no colour calibration",
        }
        for path, url, role in REFERENCES
    ]
    findings = [
        {
            "region": "Principal historic elevation and dormers",
            "decision": "retain",
            "evidence": "Three219 glass material groups have neutral smoke-grey RGB ratios below1.06 and metallic0 in both current exports. No stronger blue base was reintroduced. Existing source photos support reflective grey panes.",
            "opacity": "Retain reflective opaque proxies. Prior219 backing audit found0 of198 near backing samples; that is historical evidence, not a new251 ray result.",
        },
        {
            "region": "Atrium roof, gallery guards and door glass",
            "decision": "retain",
            "evidence": "Current exports retain BLEND alpha0.30 roof and0.16 guards/doors, metallic0. The official atrium images support transparency; no all-opaque regression is present.",
            "limitation": "Retained234 entrance diagnosis identifies an opaque backing and absent registered inner-street support. Reducing pane opacity would not fix that missing room/route boundary.",
        },
        {
            "region": "Roof pavilion",
            "decision": "retain",
            "evidence": "Current pavilion remains metallic0, roughness0.16 and BLEND alpha0.55; no new opacity or brightness regression identified. No calibrated source establishes a replacement tint or opacity.",
        },
        {
            "region": "Legacy side/rear glass",
            "decision": "no_supported_change",
            "evidence": "Cooler RGB0.105/0.200/0.235 persists on explicitly closed or opaque legacy proxy materials. The inspected principal/atrium photographs do not establish the matching side/rear room and optical condition.",
            "limitation": "Do not neutralize every cool reflection globally or expose unmodeled room shells.",
        },
    ]
    report = {
        "version": 252,
        "building": "CKK",
        "status": "audit_only_no_source_supported_optical_candidate",
        "baselinePath": str(BASE.relative_to(ROOT)),
        "baselineSha256": BASE_SHA,
        "assets": assets,
        "campusDetailGlassMatch": True,
        "references": references,
        "findings": findings,
        "candidateProduced": False,
        "addedObjects": [],
        "archivedObjects": [],
        "changedObjects": [],
        "currentNativeOpened": False,
        "blenderStarted": False,
        "currentNativeRaysPerformed": False,
        "newBeforeAfterRenders": False,
        "protectedPaths": protected,
        "roomsInUnchangedMetadata": len(
            json.loads(metadata_path.read_text())["spaces"]
        ),
        "limits": [
            "Colour and perceived brightness depend on exposure and reflections; uncalibrated photographs do not establish measured values.",
            "No current251 native visual defect or backing-ray result is claimed.",
            "Geometry, UV, depth, all35 room collections and global lighting remain unchanged because the full native and shared files were not modified.",
        ],
    }
    assert all(sha(ROOT / p) == value for p, value in protected.items())
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "review.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "CKK252_REVIEW",
        len(assets[0]["glassMaterials"]),
        "matching glass materials; no candidate",
    )


if __name__ == "__main__":
    main()
