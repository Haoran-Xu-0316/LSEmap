"""Place the historical COL source on its actual Houghton frontage.

This plan bounds old-skin clipping and preserves all other frontages. It is a
candidate registration, not permission to replace an unverified roof volume.
"""

import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/col-registration249"
N = (3.46404238662079, -99.55374993886971)
S = (5.831283376451804, -125.39900274397166)
BASE = ROOT / "result/blender/LSE_campus_detailed_v248.blend"
BASE_SHA = "f43da0940bf835c6f769ae52341376721b3a934d8875160d7f8544e2067bcd50"


def main():
    source_path = ROOT / "result/blender/col-component244/geometry-plan.json"
    source = json.loads(source_path.read_text())
    review = json.loads(
        (
            ROOT / "result/blender/col-frontage243/col-frontage243-review.json"
        ).read_text()
    )
    mask_path = ROOT / "result/blender/col-registration248/skin-candidates.json"
    mask = json.loads(mask_path.read_text())
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    length = math.dist(N, S)
    axis = [(S[i] - N[i]) / length for i in range(2)]
    inward = [-axis[1], axis[0]]
    scale = source["metresPerPoint"]
    metric_height = (438.52 - 96.76) * scale
    marked_height = 48.21 - 18.07
    corner_faces = {}
    for corner in mask["cornerFacesToRetain"]:
        corner_faces.setdefault(corner["object"], set()).update(
            corner["polygonIndices"]
        )
    objects = []
    for entry in mask["objects"]:
        candidate = dict(entry)
        candidate["clipPolygonIndices"] = sorted(corner_faces.get(entry["name"], set()))
        if candidate["explicitlyProtected"]:
            assert (
                not candidate["removePolygonIndices"]
                and not candidate["clipPolygonIndices"]
            )
        if candidate["removePolygonIndices"] or candidate["clipPolygonIndices"]:
            objects.append(candidate)
    assert len(objects) == 17
    plan = {
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": BASE_SHA,
        "sourcePlan": str(source_path.relative_to(ROOT)),
        "sourcePlanSha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "sourcePdfSha256": source["sourceSha256"],
        "sourceMask": str(mask_path.relative_to(ROOT)),
        "sourceMaskSha256": hashlib.sha256(mask_path.read_bytes()).hexdigest(),
        "frontageNorthToSouth": [N, S],
        "nativeLengthM": length,
        "axis": axis,
        "inwardNormal": inward,
        "sourceWidthM": source["sourceWidthM"],
        "horizontalFit": length / source["sourceWidthM"],
        "horizontalCompressionPercent": (1 - length / source["sourceWidthM"]) * 100,
        "clipNormalLimitM": mask["normalLimitM"],
        "objects": objects,
        "sourceRoofM": (source["sourceOrigin"][1] - 96.76) * scale,
        "unidentifiedProjectionTopM": (source["sourceOrigin"][1] - 52.12) * scale,
        "sourceLevelCrossCheck": {
            "roofAodM": 48.21,
            "lowerOpeningAodM": 18.07,
            "markedDifferenceM": marked_height,
            "printedScaleDifferenceM": metric_height,
            "differenceM": metric_height - marked_height,
            "status": "Roof-to-lower-opening height agrees within2mm; lower opening is not ground or FFL.",
            "roofFaceBaseMarker": {
                "pdfY": 162.76,
                "printedLabel": 42.30,
                "warning": "Not the R2 sill at168.88. Label and nominal-scale prediction differ by about89mm; no floor datum is inferred.",
            },
        },
        "flatStreetThresholdM": 0.02,
        "roofDecision": "Original roof retained for comparison. Whole-building roof depth, closure and unidentified rectangular projection remain separate gates before integration.",
        "limitations": [
            "2020 existing elevation, not a2026 measured or photographed whole-building survey.",
            "North-to-south frontage compressed0.5155percent to the unchanged mapped segment; this is a presentation fit.",
            "The drawn0.41275m north ground rise is not imposed on the retained native street; lowest edge and source entrance use flat native thresholds.",
            "Reveal depth, backing depth, optical coefficients and neutral palette remain estimates.",
            "Protected Aldwych entrance, Garrick chamfer, roofs, materials and35room studies are not replaced by this private candidate.",
        ],
        "status": "private_registration_plan",
    }
    assert abs(metric_height - marked_height) < 0.002
    assert all(entry["sourcePolygonCount"] > 0 for entry in objects)
    assert review["counts"]["totalFrontageModules"] == 72
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "registration-plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    print(
        "COL249_PLAN",
        len(objects),
        "bounded skins",
        sum(len(o["clipPolygonIndices"]) for o in objects),
        "corner faces",
        plan["horizontalCompressionPercent"],
    )


if __name__ == "__main__":
    main()
