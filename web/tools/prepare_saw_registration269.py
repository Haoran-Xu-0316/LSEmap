"""Derive a private, non-shearing SAW design-coordinate candidate.

Run with the existing MachineLearning environment. Original sources, native263,
shared metadata and catalogue are read only. No Blender is launched here.
"""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/saw269"
GUIDE_GROUND = ROOT / "data/previews/saw_occupants_guide_2014_p32.png"
ARCHITECT_GROUND = ROOT / "data/建筑图片/SAW_Saw Swee Hock Student Centre/02_图纸与结构/exteriors_saw_archdaily_032.jpg"
LEGACY_A = np.array([-65.223399, -15.905616])
LEGACY_B = np.array([-84.252182, 28.425])
LEGACY_C = np.array([-55.301, 36.609104])
PLAN_ORIGIN = np.array([145.0, 400.0])
LEGACY_BASIS = np.column_stack([(LEGACY_B - LEGACY_A) / 1200, (LEGACY_C - LEGACY_B) / 785])
# The enlarged original CAD dimension reads48565mm. Witness positions are
# independent blue extension lines, not a distance chosen from the fitted map.
OVERALL_DIMENSION_METRES = 48.565
DIMENSION_WITNESS_X = (59.0, 1588.5)
HELD_OUT_CORNERS = {
    "party-wall-A": [145.0, 398.0], "party-wall-B": [1346.0, 398.0],
    "entrance-wing-tip": [219.0, 610.0], "entrance-stair-end": [150.0, 548.0],
    "opposite-wing-tip": [1118.0, 1145.0], "opposite-wing-return": [895.0, 1146.0],
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply(points, matrix, offset):
    return np.asarray(points) @ matrix.T + offset


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    guide = cv2.imread(str(GUIDE_GROUND), cv2.IMREAD_GRAYSCALE)
    architect = cv2.imread(str(ARCHITECT_GROUND), cv2.IMREAD_GRAYSCALE)
    assert guide is not None and architect is not None
    # The external validation corners below lie outside this fit rectangle.
    fit_mask = np.zeros_like(guide)
    fit_mask[500:1030, 575:1030] = 255
    sift = cv2.SIFT_create(nfeatures=12000, contrastThreshold=.012, edgeThreshold=14)
    left, descriptors_left = sift.detectAndCompute(guide, fit_mask)
    right, descriptors_right = sift.detectAndCompute(architect, None)
    matches = cv2.BFMatcher().knnMatch(descriptors_left, descriptors_right, k=2)
    matches = [a for a, b in matches if a.distance < .70 * b.distance]
    source = np.float32([left[match.queryIdx].pt for match in matches])
    target = np.float32([right[match.trainIdx].pt for match in matches])
    matrix, selected = cv2.estimateAffinePartial2D(source, target, method=cv2.RANSAC,
        ransacReprojThreshold=3, maxIters=10000, confidence=.999)
    assert matrix is not None and int(selected.sum()) >= 12
    rotation_scale, offset = matrix[:, :2], matrix[:, 2]
    residual = np.linalg.norm(apply(source, rotation_scale, offset) - target, axis=1)
    selected = selected[:, 0].astype(bool)
    singular = np.linalg.svd(rotation_scale, compute_uv=False)
    assert abs(singular[0] - singular[1]) < 1e-10, "A design map must not introduce shear"
    metres_per_cad_pixel = OVERALL_DIMENSION_METRES / (DIMENSION_WITNESS_X[1] - DIMENSION_WITNESS_X[0])

    cad_corners = cv2.goodFeaturesToTrack(architect, maxCorners=25000, qualityLevel=.004,
        minDistance=3, blockSize=3)[:, 0]
    held_out = []
    for name, point in HELD_OUT_CORNERS.items():
        predicted = apply([point], rotation_scale, offset)[0]
        distance = np.linalg.norm(cad_corners - predicted, axis=1)
        nearest = int(distance.argmin())
        held_out.append({"name": name, "guidePixel": point, "predictedArchitectPixel": predicted.tolist(),
            "observedArchitectCorner": cad_corners[nearest].tolist(), "errorPixels": float(distance[nearest]),
            "errorMetres": float(distance[nearest] * metres_per_cad_pixel),
            "validationMethod": "Known external corner; nearest independent CAD raster corner. Not used for fitting.",
            "uncertainty": "Guide corner is manually identified on a thick wall line; pixel-level choice is not survey precision."})
    predicted_length_pixels = float(np.linalg.norm(apply([HELD_OUT_CORNERS["party-wall-A"],
        HELD_OUT_CORNERS["party-wall-B"]], rotation_scale, offset)[1] -
        apply([HELD_OUT_CORNERS["party-wall-A"], HELD_OUT_CORNERS["party-wall-B"]], rotation_scale, offset)[0]))

    # Design XY uses metric CAD pixels with Y-up and an explicitly chosen local
    # origin. Its placement in campus coordinates remains a separate hypothesis.
    cad_origin = apply([PLAN_ORIGIN], rotation_scale, offset)[0]
    pixel_to_metric = np.diag([metres_per_cad_pixel, -metres_per_cad_pixel])
    guide_to_design = pixel_to_metric @ rotation_scale
    guide_design_offset = pixel_to_metric @ (offset - cad_origin)
    native_to_guide = np.linalg.inv(LEGACY_BASIS)
    native_guide_offset = PLAN_ORIGIN - native_to_guide @ LEGACY_A
    native_to_design = guide_to_design @ native_to_guide
    native_design_offset = guide_to_design @ native_guide_offset + guide_design_offset

    contours = json.loads((ROOT / "result/blender/saw-floors216/surface-plan.json").read_text())
    levels = []
    for floor in contours["floors"]:
        old_world = np.asarray(floor["outlineWorld"])
        guide_points = apply(old_world, native_to_guide, native_guide_offset)
        design_points = apply(guide_points, guide_to_design, guide_design_offset)
        levels.append({"level": floor["level"], "datum": floor["datum"],
            "sourceGuideGroundPixelContour": guide_points.tolist(), "designMetresContour": design_points.tolist()})

    record = {
        "version": 269, "status": "private-design-coordinate-candidate-not-release-accepted",
        "baselineSha256": "f55f5975ea5e4d755f0c883bc64965b928a3d03add666c598a9b7e987bb70c2d",
        "sources": [{"path": str(path.relative_to(ROOT)), "sha256": sha(path)}
                    for path in [GUIDE_GROUND, ARCHITECT_GROUND]],
        "fit": {"regionGuidePixels": [575, 500, 1030, 1030], "matches": len(matches), "inliers": int(selected.sum()),
            "method": "Similarity-only RANSAC over central source features; no external validation corner included.",
            "matrixGuideToArchitect": matrix.tolist(), "principalScales": singular.tolist(),
            "medianInlierErrorPixels": float(np.median(residual[selected])),
            "maxInlierErrorPixels": float(max(residual[selected])),
            "trainingControls": [{"guide": a.tolist(), "architect": b.tolist(), "errorPixels": float(e)}
                for a, b, e in zip(source[selected], target[selected], residual[selected])]},
        "heldOutExteriorControls": held_out,
        "independentOverallDimension": {"sourceLabelMetres": OVERALL_DIMENSION_METRES,
            "cadWitnessXPixels": list(DIMENSION_WITNESS_X), "metresPerCadPixel": metres_per_cad_pixel,
            "predictedGuidePartyWallMetres": predicted_length_pixels * metres_per_cad_pixel,
            "differenceMetres": predicted_length_pixels * metres_per_cad_pixel - OVERALL_DIMENSION_METRES,
            "usedInGuideToArchitectFit": False},
        "transforms": {"guideToMetricDesign": {"matrix": guide_to_design.tolist(), "offset": guide_design_offset.tolist()},
            "legacyNativeToMetricDesign": {"matrix": native_to_design.tolist(), "offset": native_design_offset.tolist(),
                "scope": "Undo the single inherited absolute affine, then apply the same non-shearing design map to the whole public assembly; Z unchanged.",
                "relationshipPreservation": "One invertible planar transform for every floor/stair/lift preserves contacts and non-intersection topology; it does not preserve old sheared Euclidean widths.",
                "requiredChecks": "Recheck widths, usable routes, all vertical headroom and exterior relationships before any accepted component."}},
        "levelWallLineControls": levels,
        "oldEnvelopeAuthority": False,
        "photoConstraints": ["No repeated external white slab shelves in909_01/02.",
            "Preserve the narrow central glazed valley and continuous folded brick face.",
            "A plan-wall control line does not establish brick perforation, glazing head, roof or concealed rear facade detail."],
        "remainingConstraints": ["Absolute campus translation and bearing require independent exterior/site controls; the old OSM shell alone is not acceptance evidence.",
            "A local design coordinate system is established. Full-height central-return skin still needs correspondence between level-dependent grey wall lines and the photographed crease/glass head.",
            "Do not loft every contour edge into an opaque wall: the sixth-floor contour includes a roof terrace, and lower notches include glass.",
            "The2014architect drawing is published design evidence, not a certified2026as-built survey."],
    }
    (OUT / "design-registration-candidate.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    # This annotated source sheet makes the independent exterior controls reviewable.
    sheet = Image.open(ARCHITECT_GROUND).convert("RGB")
    draw = ImageDraw.Draw(sheet)
    for row in held_out:
        x, y = row["predictedArchitectPixel"]
        draw.ellipse((x-8, y-8, x+8, y+8), outline=(215, 30, 30), width=2)
        qx, qy = row["observedArchitectCorner"]
        draw.line((x, y, qx, qy), fill=(30, 60, 210), width=2)
        draw.text((x+10, y-10), row["name"], fill=(190, 20, 20))
    sheet.save(OUT / "held-out-exterior-controls.png")
    print("SAW269_DESIGN_REGISTRATION", json.dumps({"inliers": int(selected.sum()),
        "sourceScale": singular.tolist(), "heldOutMaxMetres": max(r["errorMetres"] for r in held_out),
        "dimensionDifferenceMetres": record["independentOverallDimension"]["differenceMetres"]}), flush=True)


if __name__ == "__main__":
    main()
