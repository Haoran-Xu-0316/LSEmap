"""Register MAR's published third-floor plan without modifying native geometry.

Run with the existing project Python runtime. The small, retained vector-control
file comes from the immutable architect PDF; no raster scaling or freeform
stretch is used for the shared-core fit. This is source evidence, not permission
to extend a third-floor wall schedule to higher floors or blank native windows.
"""

import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/mar-exterior249"
SOURCE = (
    ROOT
    / "data/collections/mar-built-registration-2026/grafton-marshall-built-plans-2022.pdf"
)
SOURCE_SHA = "d675da320087039168890f7afbf055490f9c8e4530f59921e9e5e53f6fc8bc47"
from refine_mar_registration217 import (
    CORE_SHAFTS,
    METRES_PER_POINT,
    rectangle,
    similarity,
    transform,
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert digest(SOURCE) == SOURCE_SHA
    controls = json.loads((OUT / "source-vector-controls.json").read_text())
    vectors = {row["id"]: row for row in controls}

    def bounds(ids):
        points = np.vstack([vectors[item]["pts"] for item in ids])
        return [
            float(points[:, 0].min()),
            float(points[:, 1].min()),
            float(points[:, 0].max()),
            float(points[:, 1].max()),
        ]

    identifiers = [
        [f"line-{number}" for number in [62208, 62209, 62210, 62211]],
        [f"line-{number}" for number in [62158, 62159, 62160, 62161]],
        [f"line-{number}" for number in [62114, 62115, 62116, 62117]],
    ]
    third = [bounds(items) for items in identifiers]
    first = np.vstack([rectangle(row) for row in third])
    second = np.vstack([rectangle(row["second"]) for row in CORE_SHAFTS])
    registration = similarity(first, second)
    residuals = (
        np.linalg.norm(transform(first, registration) - second, axis=1)
        * METRES_PER_POINT
    )
    service_ids = [f"line-{number}" for number in [62280, 62281, 62282, 62283]]
    service = bounds(service_ids)
    held = [
        {
            "id": "east-service-shaft",
            "thirdPdfBounds": service,
            "secondPdfBounds": [176.803, 289.905, 185.82, 294.872],
            "sourceVectorIds": service_ids,
        }
    ]
    for name, point, reference, vector in [
        ("stair-left-upper", [379.5251, 541.8791], [134.616, 286.691], "line-59443"),
        ("stair-left-lower", [379.5371, 552.2291], [134.622, 297.098], "line-59443"),
        ("stair-right-lower", [401.822, 552.2356], [156.908, 297.104], "line-62296"),
    ]:
        held.append(
            {
                "id": name,
                "thirdPdfPoint": point,
                "secondPdfPoint": reference,
                "sourceVectorIds": [vector],
            }
        )
    for row in held:
        if "thirdPdfBounds" in row:
            a, b = rectangle(row["thirdPdfBounds"]), rectangle(row["secondPdfBounds"])
        else:
            a, b = [row["thirdPdfPoint"]], [row["secondPdfPoint"]]
        errors = (
            np.linalg.norm(transform(a, registration) - b, axis=1) * METRES_PER_POINT
        )
        row["residualsMetres"] = errors.tolist()
        row["maximumMetres"] = float(errors.max())
    assert residuals.max() < 0.03
    assert max(row["maximumMetres"] for row in held) < 0.11
    prior = json.loads(
        (ROOT / "result/blender/mar-registration217/audit.json").read_text()
    )
    geographic = prior["geographicRegistration"]
    geography = geographic["secondPdfToNativeLocalCandidate"]
    angle = math.radians(geographic["nativeBasisDegrees"])
    basis = np.array(
        [[math.cos(angle), math.sin(angle)], [-math.sin(angle), math.cos(angle)]]
    )
    origin = np.array(geographic["nativeOrigin"])

    def native(points):
        second_points = transform(points, registration)
        local = transform(second_points[:, ::-1], geography)
        return local, origin + local @ basis

    # Selected exterior references retain the visible step/fin projection instead
    # of force-fitting them to the different Level02 perimeter line selection.
    perimeter = [
        [492.0, 377.2912],
        [491.996, 555.599],
        [338.872, 555.60],
        [338.8774, 476.2707],
        [433.6921, 377.2825],
    ]
    local, world = native(perimeter)
    comparison = []
    for point, row, local_point in zip(perimeter, geographic["controls"], local):
        comparison.append(
            {
                "id": row["id"],
                "thirdPdfPoint": point,
                "nativeLocal": local_point.tolist(),
                "retainedOsmLocal": row["nativeLocal"],
                "residualMetres": float(
                    np.linalg.norm(local_point - row["nativeLocal"])
                ),
            }
        )
    ranges = []
    # Actual walls and perimeter strips visible in this third-floor plan. These
    # identify finite floors/planes for subsequent native extraction, not a full
    # inferred upper-wing elevation or fabricated window count.
    for name, points, meaning, ids in [
        (
            "plan-left-continuous-perimeter-return",
            [[343.4068, 475.4807], [343.4148, 507.1307]],
            "Continuous perimeter return beside planted terrace. The plan line alone does not prove a full opaque wall or justify filling native windows.",
            ["line-72178"],
        ),
        (
            "plan-left-lower-glazed-perimeter",
            [[341.6761, 509.1248], [341.6731, 553.0538]],
            "Glazed perimeter of group-office zone; do not cover this real third-floor facade with a blank wall.",
            ["line-68044"],
        ),
        (
            "third-floor-short-end-return-reference",
            [[433.6921, 377.2825], [487.3235, 377.2845]],
            "Top-of-sheet short end includes a projecting concrete return; separate the projection reference from inner wall alignment.",
            ["line-77338", "curve-20122"],
        ),
    ]:
        loc, glob = native(points)
        ranges.append(
            {
                "id": name,
                "sourcePdfEndpoints": points,
                "sourceVectorIds": ids,
                "nativeLocalEndpoints": loc.tolist(),
                "nativeWorldEndpointsXY": glob.tolist(),
                "lengthMetres": float(np.linalg.norm(glob[1] - glob[0])),
                "interpretation": meaning,
                "floorScope": "third floor only; Z datum retained from native, not derived here",
            }
        )
    report = {
        "edition": 249,
        "building": "MAR",
        "status": "third-floor-source-registration-verified-no-native-change",
        "source": {
            "path": str(SOURCE.relative_to(ROOT)),
            "sha256": SOURCE_SHA,
            "page": 1,
            "publicationYear": 2022,
            "captureDate": None,
            "retainedVectorControlsSha256": digest(OUT / "source-vector-controls.json"),
            "url": "https://cdn.ca.emap.com/wp-content/uploads/sites/12/2022/04/grafton-architects-architectural-review.pdf",
            "author": "Grafton Architects",
            "thirdFloorRegionPdfPoints": [335, 370, 498, 565],
        },
        "coreRegistration": {
            "thirdPdfToSecondPdf": registration,
            "fitSourceBounds": third,
            "fitReferenceBounds": [row["second"] for row in CORE_SHAFTS],
            "sourceVectorIds": identifiers,
            "fitResidualsMetres": residuals.tolist(),
            "fitMaximumMetres": float(residuals.max()),
            "heldOut": held,
            "heldOutMaximumMetres": max(row["maximumMetres"] for row in held),
        },
        "geographicRegistration": {
            "chain": "ThirdPDF -> shared-core similarity -> SecondPDF -> accepted217 geographic estimate",
            "priorAudit": "result/blender/mar-registration217/audit.json",
            "priorHeldOutMaximumMetres": geographic["independentMaximumMetres"],
            "thirdPerimeterPdfPoints": perimeter,
            "thirdPerimeterMaximumResidualMetres": max(
                row["residualMetres"] for row in comparison
            ),
            "thirdPerimeterAcceptedForNativeReplacement": False,
            "nativeLocalRing": local.tolist(),
            "nativeWorldRingXY": world.tolist(),
            "perimeterComparisons": comparison,
            "interpretation": "Different facade/screen stroke references remain separate. Core residual is not geographic precision. Diagonal endpoints reach0.95m against retained OSM; not accepted as a new native envelope.",
        },
        "boundedFacadeRanges": ranges,
        "nativeExtractionWhitelist": [
            "MAR_NEXT_PANEL_registered_8546_0_blank_wall",
            "MAR188_trim_V115_retained_MAR_rear_way/1376078543_5_pierced_wall",
            "MAR_V115_retained_MAR_rear_way/1376078543_1_pierced_wall",
            "MAR_MAR_rear_way/1376078545_3_pierced_wall",
        ],
        "implementationPlan": [
            "Extract current visible polygons and connected window/frame islands only for boundedFacadeRanges at retained native third-floor slab height.",
            "Project actual candidate surfaces into these finite registered strips and inspect source plans with native plans together; reject corners beyond recorded source/OSM residual.",
            "Protect the lower glazed perimeter and accepted8546_0 blank side. Any source-confirmed wall replacement must remove matched glass/frame/reveal islands together, retain UV and archive originals.",
            "Do not continue a third-floor facade schedule into levels04–09 or alter roof heights without further actual source geometry.",
        ],
        "approvedGeometryChanges": [],
        "builderCreated": False,
        "resolvedOldBlocker": {
            "prior": "result/blender/mar_left_wing_next/audit.json",
            "finding": "A readable third-floor plan now exists locally and shares the accepted three-shaft core; no further repeated search for this plan is needed.",
            "remaining": "It is not a uniquely registered schedule of all upper-wing windows or roof footprints.",
        },
        "sculpture": {
            "productionReference": "web/public/images/mar-lse-sign.webp",
            "objectWhitelist": [
                f"MAR_V48_LSE_{letter}_{part}"
                for letter in "LSE"
                for part in ["body", "face"]
            ],
            "heightMetres": 2.4502716135,
            "widthMetres": 2.4724496029,
            "whiteBodyDepthMetres": 0.38,
            "redFaceDepthMetres": 0.01,
            "nativeLocalOrigin": [-24, 24.8, 0.05],
            "nativeWorldOrigin": [-40.2389831543, 63.335144043, 0.05],
            "frontNormal": [-0.3746065795, 0.9271838665, 0],
            "decision": "Red front, white deep sides and LS connection already present. User photo confirms shape/material family, not an exact surveyed relocation or fabrication dimensions.",
        },
        "limitations": [
            "Only third-floor source registration performed; Blender not started; current native not reopened or modified.",
            "Upper massing, full blank-wall attribution and floors04–09 remain unresolved.",
            "Boundary control picks have different fin/wall datums; no anisotropic warp, surveyed position or current2026condition claimed.",
            "No new colour or glass change is proposed; previous247 material review is not repeated.",
            "No reference photo or PDF was uploaded or republished, and no shared metadata/export/build files were changed.",
        ],
    }
    (OUT / "review.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    )
    # Source registration overlay: third plan vectors versus Level02 core boxes.
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="860" height="600" viewBox="0 0 860 600"><rect width="860" height="600" fill="white"/>',
        '<text x="24" y="30" font-family="sans-serif" font-size="20">MAR third-floor shared-core registration</text>',
        '<text x="24" y="55" font-family="sans-serif" font-size="14">Blue: transformed Level03. Red: accepted Level02. Three fitted shafts; service shaft and stair held out.</text>',
    ]

    def points(poly):
        return " ".join(
            f"{50 + 17 * (x - 130):.3f},{100 + 17 * (y - 275):.3f}" for x, y in poly
        )

    for row in CORE_SHAFTS:
        lines.append(
            f'<polygon points="{points(rectangle(row["second"]))}" fill="none" stroke="#b44739" stroke-width="2"/>'
        )
    for box in third:
        lines.append(
            f'<polygon points="{points(transform(rectangle(box), registration))}" fill="none" stroke="#206e9d" stroke-width="1"/>'
        )
    lines.append(
        f'<text x="24" y="570" font-family="sans-serif" font-size="15">Fit max {residuals.max():.4f}m. Held-out max {max(row["maximumMetres"] for row in held):.4f}m. Level02 geographic residual up to0.62m; third perimeter candidates up to0.95m.</text></svg>'
    )
    (OUT / "shared-core-registration.svg").write_text("".join(lines) + "\n")
    print(
        "MAR249_SOURCE_REGISTERED",
        float(residuals.max()),
        max(row["maximumMetres"] for row in held),
    )


if __name__ == "__main__":
    main()
