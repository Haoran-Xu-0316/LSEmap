"""Record the smallest evidence-supported SAW270 construction scope.

This CPU-only source review writes private JSON and an annotated proof sheet.
It does not construct masonry from an unclassified floor perimeter. The frozen
263 inspection remains the native reference; current catalogue is not read.
"""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/saw270"
SOURCES = ROOT / "data/建筑图片/SAW_Saw Swee Hock Student Centre/02_图纸与结构"
# Room labels on the original CAD drawings establish these levels. In
# particular034 is4.xx and031 is5.xx; file order is not floor order.
LEVELS = (
    (0, 32, "032", 0.0), (1, 31, "035", 3.45),
    (2, 30, "030", 8.1), (3, 29, "029", 11.1),
    (4, 28, "034", 14.1), (5, 27, "031", 18.0),
    (6, 26, "036", 21.9),
)
CENTRAL_INDICES = {1: [7, 8, 9], 2: [9, 10, 11], 3: [9, 10, 11],
                   4: [9, 10, 11], 5: [9, 10, 11], 6: [10, 11, 12]}
NOTCH_INDICES = {1: [9, 10], 2: [11, 12], 3: [11, 12],
                 4: [11, 12], 5: [11, 12], 6: [12, 13]}
SEMANTICS = {
    0: {"centralReturn": "Recessed glazed frontage and projected brick above; ground glazing is not the upper masonry crease.",
        "terrace": "No upper roof-terrace inference from this plan."},
    1: {"centralReturn": "Mixed brick-screen and raking glazed opening; do not make the full plan segment opaque.",
        "terrace": "No terrace edge is used as a brick control."},
    2: {"centralReturn": "Brick-screen envelope with residual glazed opening near the valley; exact raking head requires elevation control.",
        "terrace": "No terrace edge is used as a brick control."},
    3: {"centralReturn": "Brick-screen envelope near the top of the lower glazed cutout; the plan alone does not measure the glazing-head height.",
        "terrace": "No terrace edge is used as a brick control."},
    4: {"centralReturn": "Thick enclosing outer line supports the folded brick-screen path; neighbouring thin curtain lines remain separate.",
        "terrace": "No terrace edge is used as a brick control."},
    5: {"centralReturn": "Folded brick-screen path retained; office glazing retreat on the other wing is not a replacement outer brick line.",
        "terrace": "Green RoofT01 is outside the enclosed fifth-floor glass line; preserve as roof, not occupied-floor masonry."},
    6: {"centralReturn": "Folded outer screen near the source crease; roof crest and parapet connection are not fixed by a floor plan.",
        "terrace": "Roof GardenT02 includes outside floor/terrace edges; these must not be extruded into opaque walls."},
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mapped(points, matrix):
    return np.asarray(points) @ matrix[:, :2].T + matrix[:, 2]


def fit_same_level(guide, cad):
    mask = np.zeros_like(guide)
    mask[395:1208, 145:1345] = 255
    sift = cv2.SIFT_create(nfeatures=15000, contrastThreshold=.012, edgeThreshold=14)
    left, dl = sift.detectAndCompute(guide, mask)
    right, dr = sift.detectAndCompute(cad, None)
    matches = [a for a, b in cv2.BFMatcher().knnMatch(dl, dr, k=2) if a.distance < .70 * b.distance]
    a = np.float32([left[match.queryIdx].pt for match in matches])
    b = np.float32([right[match.trainIdx].pt for match in matches])
    matrix, selected = cv2.estimateAffinePartial2D(a, b, method=cv2.RANSAC,
        ransacReprojThreshold=3, maxIters=10000, confidence=.999)
    assert matrix is not None and int(selected.sum()) >= 12, (len(matches), None if selected is None else int(selected.sum()))
    error = np.linalg.norm(mapped(a, matrix) - b, axis=1)[selected[:, 0].astype(bool)]
    return matrix, {"method": "Same-level building-feature similarity only; not an independent exterior validation",
        "fitRegionGuidePixels": [145, 395, 1345, 1208], "matches": len(matches),
        "inliers": int(selected.sum()), "medianInlierPixels": float(np.median(error)),
        "matrixGuideToSameLevelCad": matrix.tolist()}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cv2.setRNGSeed(270)
    registration = json.loads((ROOT / "result/blender/saw-floors216/registration.json").read_text())
    design = json.loads((ROOT / "result/blender/saw269/design-registration-candidate.json").read_text())
    placement = json.loads((ROOT / "result/blender/saw269/geographic-placement-candidates.json").read_text())
    design_map = design["transforms"]["guideToMetricDesign"]
    contact = Image.new("RGB", (1800, 1680), "white")
    levels = []
    for index, (level, page, drawing, datum) in enumerate(LEVELS):
        guide_path = ROOT / f"data/previews/saw_occupants_guide_2014_p{page}.png"
        cad_path = SOURCES / f"exteriors_saw_archdaily_{drawing}.jpg"
        guide, cad = [cv2.imread(str(path), cv2.IMREAD_GRAYSCALE) for path in (guide_path, cad_path)]
        matrix, fit = fit_same_level(guide, cad)
        item = {"level": level, "datum": datum, "guidePage": page,
            "guide": str(guide_path.relative_to(ROOT)), "guideSha256": sha(guide_path),
            "sameLevelCad": str(cad_path.relative_to(ROOT)), "cadSha256": sha(cad_path),
            "sameLevelRegistration": fit, "classification": SEMANTICS[level],
            "glazedValley": "Keep distinct from central brick return; a narrow vertical glass joint is visible in909_01/02.",
            "acceptance": "Source semantics and scope only; not accepted construction dimensions."}
        sheet = Image.open(guide_path).convert("RGB")
        draw = ImageDraw.Draw(sheet)
        if level:
            record = registration[str(page)]
            factor = 1501 / (595.276)
            source = np.asarray(record["tracedPdfOutline"]) * factor
            ground = np.asarray(record["groundPagePixelOutline"])
            indices = CENTRAL_INDICES[level]
            notch_indices = NOTCH_INDICES[level]
            central_source = source[indices]
            central_ground = ground[indices]
            central_design = central_ground @ np.asarray(design_map["matrix"]).T + design_map["offset"]
            notch_source = source[notch_indices]
            item["centralReturnControl"] = {"sourceGuidePixels": central_source.tolist(),
                "sameLevelCadPixels": mapped(central_source, matrix).tolist(),
                "groundGuidePixels": central_ground.tolist(), "metricDesignMetres": central_design.tolist(),
                "scope": "Crease->middle->valley grey enclosing line. Explicit glass cutouts still required; not a solid-wall outline."}
            item["valleyJointControl"] = {"sourceGuidePixels": notch_source.tolist(),
                "sameLevelCadPixels": mapped(notch_source, matrix).tolist(),
                "scope": "Adjacent notch connector; narrow glass/brick junction, not an arbitrary masonry cap."}
            draw.line([tuple(p) for p in central_source], fill=(210, 40, 30), width=6)
            draw.line([tuple(p) for p in notch_source], fill=(30, 80, 220), width=6)
            for point, label in zip(central_source, ("crease", "return", "valley")):
                x, y = point
                draw.ellipse((x-7, y-7, x+7, y+7), outline=(160, 20, 20), width=3)
                draw.text((x+9, y-16), label, fill=(170, 20, 20))
        crop = sheet.crop((115, 365, 1380, 1220))
        crop.thumbnail((600, 505))
        x, y = (index % 3) * 600, (index // 3) * 560
        contact.paste(crop, (x, y+35))
        ImageDraw.Draw(contact).text((x+10, y+10), f"Level{level}  guide{page}  CAD{drawing}  z={datum}m", fill=(0, 0, 0))
        levels.append(item)
    report = {"version": 270, "status": "construction-scope-only-not-a-repaired-envelope",
        "inspection263Sha256": design["baselineSha256"],
        "candidate269Sha256": "a44026d64bb57cea159a44b1fa96b7b9be13e7d4af034f57d09beb62480ef21b",
        "sourcePolicy": "Frozen263 inspection, original2014guide/CAD and raw OSM only; current catalogue/metadata not consulted.",
        "levels": levels,
        "residuals": {"designHeldOutMaximumMetres": placement["designRegistrationResiduals"]["heldOutMaximumMetres"],
            "geographicHeldOutMetres": placement["variants"][1]["heldOutPeacockStreetCorner"]["errorMetres"],
            "interpretation": "Keep source drawing registration separate from generalized OSM placement uncertainty."},
        "minimumReplacementScope": ["Central_return pierced wall and its central-return-only perforated bricks/mortar components.",
            "Near-crease part of north_fold only where needed to close the continuous masonry turn; preserve far north-fold panels.",
            "Central-return/vertical-valley interface and canopy connection only after the measured glazing-head and roof join are established."],
        "protected": ["All material datablocks, brick colours and UVs", "Roof and terrace slabs/parapets",
            "Glazing, timber curtain and canopy geometry pending joint proof", "Unrelated facade families and rear/party-wall geometry",
            "All public floors, stairs, lifts and handrails until a complete assembly candidate passes dimensional checks"],
        "coordinateOptions": {"localEnvelopeOnly": "Build source-supported masonry in the existing common guide-to-native frame; public structure widths and supports remain unchanged. Retained legacy metric shear must be stated.",
            "metricWholeAssembly": "One common unshear/design map and one rigid geographic placement for ALL visible SAW display members. Requires widths/support/headroom checks, not just preserved topology."},
        "unresolvedConstraints": ["Exact correspondence of source central crease to the existing roof crest/parapet and roof drainage edges.",
            "Source-controlled raking glass-head elevation and its joint to central brick skin; existing11.5m is a legacy estimate, not measured acceptance.",
            "A full-height perimeter cannot simultaneously preserve an unverified roof edge and shift its wall corner without an evidenced closure."],
        "nextComponentGate": "Run inspect_saw_baseline270.py first. Do not save an accepted replacement shell while roof/glass joint controls remain unresolved.",
        "formalModelWritten": False}
    (OUT / "construction-scope.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    contact.save(OUT / "level-semantics.png")
    print("SAW270_SCOPE", [(x["level"], x["sameLevelRegistration"]["inliers"]) for x in levels], flush=True)


if __name__ == "__main__":
    main()
