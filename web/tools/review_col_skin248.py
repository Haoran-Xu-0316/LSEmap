"""Classify the retained COL Houghton skin without changing native geometry.

Whole islands are only removal candidates. Corner overlaps require bounded
face clipping before any integration; roof/threshold choices remain unaccepted.
"""

import hashlib
import json
import math
from pathlib import Path

from review_con_skin243 import connected_islands, index_ranges, projection
from shapely.geometry import MultiPoint

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "result/blender/stage247/col-exterior-geometry.json"
OUT = ROOT / "result/blender/col-registration248"
S = (5.831283376451804, -125.39900274397166)
N = (3.46404238662079, -99.55374993886971)
LIMIT = 0.65


def main():
    raw = SOURCE.read_bytes()
    data = json.loads(raw)
    length = math.dist(S, N)
    axis = [(N[i] - S[i]) / length for i in range(2)]
    normal = [axis[1], -axis[0]]
    strip = MultiPoint(
        [
            [p[i] + sign * normal[i] * LIMIT for i in range(2)]
            for p in [S, N]
            for sign in [-1, 1]
        ]
    ).convex_hull
    masks = []
    corners = []
    removed = []
    for obj in data["objects"]:
        if obj["type"] != "MESH":
            continue
        name = obj["name"]
        vertices = obj["vertices"]
        faces = obj["faces"]
        protected = any(
            token in name.lower()
            for token in [
                "garrick",
                "col_v99",
                "corner",
                "entry",
                "entrance",
                "portal",
                "door",
                "roof",
                "mansard",
                "parapet",
                "unseen_wall",
            ]
        )
        remove = []
        for index, island in enumerate(connected_islands(vertices, faces)):
            points = [vertices[i] for i in {i for face in island for i in faces[face]}]
            local = [projection(p, S, N) for p in points]
            fits = (
                max(abs(p[1]) for p in local) <= LIMIT
                and min(p[0] for p in local) >= -0.00002
                and max(p[0] for p in local) <= length + 0.00002
            )
            if not protected and fits:
                remove.extend(island)
                removed.extend(points)
            elif not protected and MultiPoint(
                [p[:2] for p in points]
            ).convex_hull.intersects(strip):
                affected = [
                    i
                    for i in island
                    if MultiPoint(
                        [vertices[v][:2] for v in faces[i]]
                    ).convex_hull.intersects(strip)
                ]
                corners.append(
                    {
                        "object": name,
                        "island": index,
                        "polygonIndices": affected,
                        "action": "retain pending bounded clipping; never remove a whole corner island",
                    }
                )
        masks.append(
            {
                "name": name,
                "sourceFingerprint": obj["fingerprint"],
                "sourcePolygonCount": len(faces),
                "removePolygonIndices": sorted(remove),
                "retainPolygonIndexRanges": index_ranges(
                    set(range(len(faces))) - set(remove)
                ),
                "explicitlyProtected": protected,
            }
        )
    OUT.mkdir(parents=True, exist_ok=True)
    result = {
        "source": str(SOURCE.relative_to(ROOT)),
        "sourceSha256": hashlib.sha256(raw).hexdigest(),
        "baselineSha256": data["baselineSha256"],
        "frontageSouthToNorth": [S, N],
        "sourceElevationOrder": "North to south; reverse native segment for source registration",
        "normalLimitM": LIMIT,
        "sourceWidthM": 26.087916666666665,
        "nativeLengthM": length,
        "horizontalFit": length / 26.087916666666665,
        "removedCandidateFaces": sum(len(m["removePolygonIndices"]) for m in masks),
        "objects": masks,
        "cornerFacesToRetain": corners,
        "aldwychEntryMinimumCandidateDistanceM": min(
            math.hypot(p[0] - 16.7, p[1] + 127.2) for p in removed
        ),
        "status": "read-only candidates; not a destructive mask approval",
        "unresolved": [
            "Source main roof profile and unidentified high rectangular projection need a bounded roof closure; do not extend that projection over the whole roof.",
            "Retain source floor and entry datums; historical north ground rise must not bury existing street access.",
            "Check72source modules,64glazed versus8opaque, against actual saved registered meshes before any native or web publication.",
        ],
    }
    assert all(not m["removePolygonIndices"] for m in masks if m["explicitlyProtected"])
    assert result["aldwychEntryMinimumCandidateDistanceM"] > 8
    (OUT / "skin-candidates.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        "COL248_READ_ONLY",
        result["removedCandidateFaces"],
        "candidate faces",
        len(corners),
        "corner islands",
    )


if __name__ == "__main__":
    main()
