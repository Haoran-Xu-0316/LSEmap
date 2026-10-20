"""Verify252 diagnostic geometry and its explicit no-model-change boundary.

This CPU check independently recomputes projected substrate absence. It does
not turn that measurement into a claim about visible holes or street grade.
"""

import gzip
import hashlib
import json
from pathlib import Path

from shapely import Polygon, box, make_valid, unary_union

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/houghton-ground252"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    review = json.loads((OUT / "review.json").read_text())
    plan = json.loads((OUT / "plan.json").read_text())
    assert digest(ROOT / review["baseline"]) == review["baselineSha256"]
    assert digest(OUT / review["inventory"]) == review["inventoryCompressedSha256"]
    with gzip.open(OUT / review["inventory"], "rt", encoding="utf-8") as handle:
        inventory = json.load(handle)
    assert inventory["baselineSha256"] == review["baselineSha256"]
    assert len(inventory["objects"]) == 182
    roi = box(-12, -138, 14, -74)
    groups, building_solids = {}, []
    for obj in inventory["objects"]:
        tops = []
        for face in obj["faces"]:
            points = [obj["vertices"][i] for i in face]
            polygon = make_valid(Polygon([p[:2] for p in points]))
            if polygon.area < 1e-9:
                continue
            if (
                obj["name"].startswith(
                    ("OLD", "COL", "CON", "CBG", "SITE175", "SITE173")
                )
                and min(p[2] for p in points) <= 0.07
            ):
                building_solids.append(polygon)
            if (
                max(p[2] for p in points) - min(p[2] for p in points) < 1e-5
                and -0.04 <= points[0][2] <= 0.08
            ):
                tops.append(polygon.intersection(roi))
        if tops:
            groups[obj["name"]] = unary_union(tops)
    paving = groups["SITE243_Houghton_paving_nonoverlapping_edges"]
    support = unary_union(
        [
            g
            for name, g in groups.items()
            if name.startswith(
                ("GROUND", "SITE217", "SITE243_Houghton_paving_support", "SITE173")
            )
        ]
    )
    raw = paving.difference(support)
    bounded = raw.difference(unary_union(building_solids)).buffer(-0.00002)
    parts = [p for p in bounded.geoms if p.area > 0.01]
    area = sum(p.area for p in parts)
    assert abs(raw.area - 96.8046776356674) < 1e-7
    assert abs(area - plan["areaM2"]) < 1e-7 and len(parts) == 11
    assert plan["candidateBuilt"] is False and plan["visibleHoleAreaM2"] is None
    assert not list(OUT.glob("*.blend"))
    assert (
        review["originalGeometryChanged"] is False and review["roomsChanged"] is False
    )
    result = {
        "status": "passed_diagnostic_only",
        "baselineUnchanged": True,
        "inventoryVerified": True,
        "nativeObjectsReviewed": 182,
        "rawXYAbsenceM2": raw.area,
        "buildingExclusionXYAbsenceM2": area,
        "partsAbove0_01M2": len(parts),
        "visibleHoleClaim": False,
        "candidateCreated": False,
        "blenderStartedByVerifier": False,
    }
    (OUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
