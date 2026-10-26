"""Audit the MAR Second floor's own lift-shaft evidence without opening Blender.

Fixed inputs and output. Run main() in MachineLearning. Native inspection, when
available, replaces saved-template geometry with exact263mesh faces. No shared
metadata, source assets or native files are modified.
"""

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pdfplumber
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[2]
PDF = (
    ROOT
    / "data/collections/mar-built-registration-2026/grafton-marshall-built-plans-2022.pdf"
)
PDF_SHA = "d675da320087039168890f7afbf055490f9c8e4530f59921e9e5e53f6fc8bc47"
NATIVE_SHA = "f55f5975ea5e4d755f0c883bc64965b928a3d03add666c598a9b7e987bb70c2d"
OUT = ROOT / "result/blender/mar269-evidence.json"
NATIVE = ROOT / "result/blender/mar269/native-second-inspection.json"
TARGETS = [
    "MAR223_second_structural_slab",
    "MAR223_second_floor_finish",
    "MAR223_second_soffit",
]
SHAFTS = [
    {
        "id": "second-west-upper",
        "pdf": [
            [157.7335, 277.4456],
            [164.6645, 277.4456],
            [164.6726, 286.8640],
            [157.7246, 286.8580],
        ],
        "sourceFills": ["curve-17461", "curve-17377"],
    },
    {
        "id": "second-west-lower",
        "pdf": [
            [157.7336, 287.6960],
            [164.6606, 287.6940],
            [164.6746, 297.0960],
            [157.7296, 297.0900],
        ],
        "sourceFills": ["curve-17377"],
    },
    {
        "id": "second-east-upper",
        "pdf": [
            [176.2232, 277.4511],
            [183.1532, 277.4501],
            [183.1602, 286.8701],
            [176.2302, 286.8711],
        ],
        "sourceFills": ["curve-17364"],
    },
]


def read(path):
    return json.loads((ROOT / path).read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def similarity(source, target):
    a, b = np.asarray(source), np.asarray(target)
    ac, bc = a - a.mean(axis=0), b - b.mean(axis=0)
    u, _, vt = np.linalg.svd(ac.T @ bc)
    rotation = u @ vt
    assert np.linalg.det(rotation) > 0
    scale = np.sum((ac @ rotation) * bc) / np.sum(ac * ac)
    translation = b.mean(axis=0) - scale * a.mean(axis=0) @ rotation
    return float(scale), rotation, translation


def main():
    assert sha(PDF) == PDF_SHA
    geo = read("result/blender/mar-registration217/audit.json")[
        "geographicRegistration"
    ]
    site = read("result/blender/site_geometry.json")
    source_building = next(b for b in site["buildings"] if b["id"] == "way/61452977")
    angle = math.radians(geo["nativeBasisDegrees"])
    basis = np.array(
        [[math.cos(angle), math.sin(angle)], [-math.sin(angle), math.cos(angle)]]
    )
    origin = np.array(geo["nativeOrigin"])
    controls = [r for r in geo["controls"] if r["fit"]]
    pdf_controls = np.array([r["pdf"] for r in controls])
    local_controls = (
        np.array([source_building["rings"][0][r["siteVertex"]] for r in controls])
        - origin
    ) @ basis.T
    scale, rotation, translation = similarity(pdf_controls[:, ::-1], local_controls)

    def world(points):
        local = scale * np.asarray(points)[:, ::-1] @ rotation + translation
        return origin + local @ basis

    registration_rows = []
    for control in geo["controls"]:
        actual = np.array(source_building["rings"][0][control["siteVertex"]])
        mapped = world([control["pdf"]])[0]
        registration_rows.append(
            {
                "id": control["id"],
                "pdf": control["pdf"],
                "siteVertex": control["siteVertex"],
                "fit": control["fit"],
                "mappedWorldXY": mapped.tolist(),
                "retainedOsmWorldXY": actual.tolist(),
                "residualM": float(np.linalg.norm(mapped - actual)),
            }
        )
    saved = geo["secondPdfToNativeLocalCandidate"]
    assert abs(scale - saved["scale"]) < 1e-9
    assert np.max(np.abs(rotation - np.array(saved["rotation"]))) < 1e-9
    assert np.max(np.abs(translation - np.array(saved["translation"]))) < 1e-7
    print("Independent Second-floor geographic refit complete", flush=True)
    fills = {}
    with pdfplumber.open(PDF) as document:
        assert len(document.pages) == 2
        page = document.pages[0]
        curves = page.curves
        text = page.extract_text()
        assert "The Marshall Building" in text and "Grafton Architects" in text
        assert all(
            label in text.lower()
            for label in ["ground floor", "second floor", "third floor", "section aa"]
        )
        for index in [17364, 17377, 17461]:
            curve = curves[index]
            assert curve["fill"] and not curve["stroke"]
            assert list(curve["non_stroking_color"]) == [0, 0, 0, 1]
            fills["curve-" + str(index)] = {
                "sourcePdfPoints": curve["pts"],
                "opaqueBlackFill": True,
                "stroke": False,
            }
    source_wall = unary_union(
        [Polygon(world(row["sourcePdfPoints"])).buffer(0) for row in fills.values()]
    )
    floor_plan = read("data/collections/mar-structure223/structural-plan.json")
    footprint = unary_union([Polygon(t) for t in floor_plan["floor"]["triangles"]])
    actual = read("result/blender/mar-structure223/audit.json")
    baseline = read("result/blender/stage263/baseline-state.json")
    for name in TARGETS:
        assert baseline["fingerprints"][name] == actual["addedFingerprints"][name]
        assert baseline["visibility"][name] is False
    snapshot = None
    if NATIVE.exists():
        snapshot = json.loads(NATIVE.read_text())
        assert (
            snapshot["baselineSha256"] == NATIVE_SHA
            and snapshot["readOnly"]
            and not snapshot["nativeSaved"]
        )
        assert {r["name"] for r in snapshot["targets"]} == set(TARGETS)
    holes = []
    for row in SHAFTS:
        raw_points = [
            p for key in row["sourceFills"] for p in fills[key]["sourcePdfPoints"]
        ]
        errors = [min(math.dist(p, q) for q in raw_points) for p in row["pdf"]]
        assert max(errors) < 1e-8, (row["id"], errors)
        nominal = Polygon(world(row["pdf"]))
        polygon = nominal.difference(source_wall).simplify(
            0.00001, preserve_topology=True
        )
        assert polygon.geom_type == "Polygon" and not polygon.interiors
        corners = world(row["pdf"])
        occupied = polygon.intersection(footprint).area
        existing_columns = unary_union(
            [Polygon(c["profile"]) for c in floor_plan["columns"]]
        )
        column_overlap = polygon.intersection(existing_columns).area
        assert column_overlap < 1e-6
        covers = []
        if snapshot:
            for target in snapshot["targets"]:
                mesh_floor = []
                for face in target["faces"]:
                    vertices = [target["verticesWorld"][i] for i in face["vertices"]]
                    if (
                        max(p[2] for p in vertices) - min(p[2] for p in vertices)
                        < 0.0001
                    ):
                        projected = Polygon([p[:2] for p in vertices])
                        if projected.area > 1e-8:
                            mesh_floor.append(projected)
                union = unary_union(mesh_floor)
                overlap = polygon.intersection(union).area
                covers.append(
                    {
                        "object": target["name"],
                        "sourceFingerprintMatches263": target["fingerprint"]
                        == baseline["fingerprints"][target["name"]],
                        "shaftAreaCoveredM2": overlap,
                        "coveredFraction": overlap / polygon.area,
                        "materials": target["materials"],
                    }
                )
                assert target["fingerprint"] == baseline["fingerprints"][target["name"]]
                assert overlap / polygon.area > 0.9999
        holes.append(
            {
                **row,
                "worldXY": corners.tolist(),
                "cutWorldXY": list(polygon.exterior.coords)[:-1],
                "areaM2": polygon.area,
                "nominalQuadAreaM2": nominal.area,
                "nominalQuadConcreteOverlapM2": nominal.intersection(source_wall).area,
                "numericalBoundarySimplificationM": 0.00001,
                "nativeDimensionsM": [
                    float(np.linalg.norm(corners[1] - corners[0])),
                    float(np.linalg.norm(corners[2] - corners[1])),
                ],
                "sourceCornerToActualFillVertexMaxPdfPoints": max(errors),
                "sourceConcreteFillIntersectionM2": polygon.intersection(
                    source_wall
                ).area,
                "secondFloorTemplateCoveredM2": occupied,
                "secondFloorTemplateCoveredFraction": occupied / polygon.area,
                "minimumTemplateExternalEdgeDistanceM": polygon.distance(
                    footprint.exterior
                )
                if footprint.geom_type == "Polygon"
                else None,
                "existingSecondColumnIntersectionM2": column_overlap,
                "nearestExistingSecondPublicRouteM": min(
                    polygon.distance(LineString(route))
                    for route in floor_plan["publicRoutes"]
                ),
                "actual263LayerChecks": covers,
            }
        )
        assert occupied / polygon.area > 0.9999
    all_holes = unary_union([Polygon(row["cutWorldXY"]) for row in holes])
    native_summary = {
        "available": snapshot is not None,
        "path": "result/blender/mar269/native-second-inspection.json",
        "neededForAuthoring": snapshot is None,
    }
    if snapshot:
        native_summary.update(
            {
                "originalObjects": snapshot["originalObjects"],
                "originalMaterials": snapshot["originalMaterials"],
                "roomMembershipCount": snapshot["roomMembershipCount"],
                "actualNeighbourMeshes": [
                    {
                        "name": r["name"],
                        "triangles": len(r["triangles"]),
                        "materials": sorted({t["material"] for t in r["triangles"]}),
                    }
                    for r in snapshot["neighbours"]
                ],
                "materialGraphs": snapshot["targetMaterialGraphs"],
            }
        )
    vertical = {
        "status": "native_upper_context_unavailable",
        "fullHeightAcceptance": False,
    }
    if snapshot:
        deck = next(
            r
            for r in snapshot["neighbours"]
            if r["name"] == "MAR258_third_south_deck_solid"
        )
        wall = next(
            r
            for r in snapshot["neighbours"]
            if r["name"] == "MAR251_third_south_lift_core_walls"
        )

        def horizontal_projection(mesh, z):
            return unary_union(
                [
                    Polygon([p[:2] for p in t["points"]])
                    for t in mesh["triangles"]
                    if all(abs(p[2] - z) < 0.00002 for p in t["points"])
                ]
            )

        upper = horizontal_projection(deck, 17.5)
        upper_walls = horizontal_projection(wall, 17.5)
        assert upper.geom_type == "Polygon" and len(upper.interiors) == 3
        upper_holes = [Polygon(ring) for ring in upper.interiors]
        relationships = []
        for row in holes:
            second = Polygon(row["cutWorldXY"])
            third = min(upper_holes, key=lambda p: p.centroid.distance(second.centroid))
            overlap = second.intersection(third).area
            relationships.append(
                {
                    "secondShaft": row["id"],
                    "secondCentroidXY": next(iter(second.centroid.coords)),
                    "thirdActualCentroidXY": next(iter(third.centroid.coords)),
                    "centroidOffsetXY_m": [
                        second.centroid.x - third.centroid.x,
                        second.centroid.y - third.centroid.y,
                    ],
                    "axisOffsetM": second.centroid.distance(third.centroid),
                    "secondAreaM2": second.area,
                    "actualThirdOpeningAreaM2": third.area,
                    "overlapAreaM2": overlap,
                    "overlapFractionOfSecond": overlap / second.area,
                    "overlapFractionOfThird": overlap / third.area,
                    "existingThirdDeckProjectedCapM2": second.intersection(upper).area,
                    "existing251WallFootprintProjectionOverlapM2": second.intersection(
                        upper_walls
                    ).area,
                    "thirdActualOpeningWorldXY": list(third.exterior.coords)[:-1],
                }
            )
        vertical = {
            "status": "relative_axes_close_but_boundaries_not_vertically_coordinated",
            "fullHeightAcceptance": False,
            "candidateOnly": True,
            "relationships": relationships,
            "existingThirdDeckObject": deck["name"],
            "existingThirdDeckFingerprint": deck["fingerprint"],
            "existingThirdCoreObject": wall["name"],
            "existingThirdCoreFingerprint": wall["fingerprint"],
            "totalThirdDeckProjectedCapM2": sum(
                r["existingThirdDeckProjectedCapM2"] for r in relationships
            ),
            "total251ProjectedWallOverlapM2": sum(
                r["existing251WallFootprintProjectionOverlapM2"] for r in relationships
            ),
            "direct3DLayerConflict": "The edited Second-floor stack stops at12.8m; existing251walls begin at17.5m. A floor-bore-only edit does not physically cut251walls,while its vertical projection intersects them.",
            "relativeControlUncertainty": {
                "coreThirdToSecondFitMaximumM": read(
                    "result/blender/mar-exterior249/review.json"
                )["coreRegistration"]["fitMaximumMetres"],
                "independentHeldOutMaximumM": read(
                    "result/blender/mar-exterior249/review.json"
                )["coreRegistration"]["heldOutMaximumMetres"],
                "interpretation": "Both floors share the217geographic placement. The0.619mexternal OSM residual is not an independent relative shaft offset. The0.0977mheld-out inter-floor residual and source edge picks still constrain relative accuracy.",
            },
            "decision": "Retain Second-floor source inner boundaries and keep component candidate-only. Do not align by moving new bores,remove third-deck cap strips or recut251walls without coordinated evidence and separate approval of that scope.",
        }
    labels = read("result/blender/mar-core251/upper-floor/source-labels.json")
    assert labels["sourceSha256"] == PDF_SHA
    assert "Kingston" in labels["pages"][1]["matchingLabels"]
    sources = [
        PDF,
        ROOT / "result/blender/mar-registration217/audit.json",
        ROOT / "result/blender/site_geometry.json",
        ROOT / "data/collections/mar-structure223/structural-plan.json",
        ROOT / "result/blender/mar-structure223/audit.json",
        ROOT / "result/blender/stage263/baseline-state.json",
        ROOT / "result/blender/mar-core251/upper-floor/review.json",
        ROOT / "result/blender/mar258/audit.json",
    ]
    result = {
        "auditId": "mar269-evidence",
        "reviewDate": "2026-10-27",
        "building": "MAR Marshall Building",
        "status": "three_independent_second_floor_shafts_confirmed_native_geometry_available"
        if snapshot
        else "three_independent_second_floor_shafts_confirmed_native_inspection_pending",
        "baseline": {
            "native": "result/blender/LSE_campus_detailed_v263.blend",
            "sha256": NATIVE_SHA,
            "geometrySnapshot": "result/blender/stage263/baseline-state.json",
            "noBlenderRunByAuditor": True,
        },
        "sourceIdentity": {
            "path": str(PDF.relative_to(ROOT)),
            "sha256": PDF_SHA,
            "sourceUrl": "https://cdn.ca.emap.com/wp-content/uploads/sites/12/2022/04/grafton-architects-architectural-review.pdf",
            "architect": "Grafton Architects",
            "publicationYear": 2022,
            "pdfCreationDate": "2022-04-15",
            "page1Owner": "The Marshall Building,LSE",
            "page1Drawings": [
                "Ground floor",
                "Second floor",
                "Third floor",
                "Section AA",
            ],
            "page2Owner": "Kingston Town House;excluded",
            "page1TextVerifiedNow": True,
            "page2IdentityProof": "result/blender/mar-core251/upper-floor/source-labels.json",
            "current2026Survey": False,
        },
        "independentSecondRegistration": {
            "method": "Refit Second-floor exterior controls directly to retained OSM61452977vertices; no Third-floor transform or polygons used.",
            "sourceAxisOrder": ["pdf-y", "pdf-x"],
            "scale": scale,
            "rotation": rotation.tolist(),
            "translation": translation.tolist(),
            "nativeBasisDegrees": geo["nativeBasisDegrees"],
            "nativeOrigin": geo["nativeOrigin"],
            "controls": registration_rows,
            "fitMaximumM": max(r["residualM"] for r in registration_rows if r["fit"]),
            "heldOutMaximumM": max(
                r["residualM"] for r in registration_rows if not r["fit"]
            ),
            "matchesAccepted217Transform": True,
            "accuracy": "Source-aligned estimate; peripheral OSM mismatch retained. Millimetre core coordinates are not geographic survey accuracy.",
        },
        "confirmedGap": {
            "title": "Second-floor floor/soffit stack still fills three architect-drawn lift shafts",
            "currentObjects": TARGETS,
            "currentAuthoringScript": "web/tools/refine_mar_structure223.py",
            "codeEvidenceLines": [42, 43, 100, 111],
            "existingHoles": [h["id"] for h in floor_plan["holes"]],
            "newSecondSourceShafts": holes,
            "totalPlanAreaToRemovePerLayerM2": all_holes.area,
            "proof": "223floor template subtracts only main-stair and diamond-tree voids. All three independently read Second-floor concrete inner boundaries are fully occupied by its floor footprint.263retains identical target fingerprints and visible state.",
            "notRepeated": "250/251registered Third-floor shafts and walls;258only thickened that third south deck. This proposal corrects the different, explicitly drawn Second-floor layer.",
        },
        "nativeInspection": native_summary,
        "verticalCoordination": vertical,
        "acceptanceGate": "Candidate only. Layer-specific source geometry may pass checks while full-height shaft coordination remains unresolved.",
        "minimumExecutableCorrection": {
            "priority": "P1",
            "action": "Cut the three Second-floor source polygons through all three223layers at their existing datums, preserving outer boundaries, all unaffected top triangles/UVs and original material graphs.",
            "targetObjects": TARGETS,
            "targetCollection": "MAR_PUBLIC_INTERIOR_study",
            "sourcePolygons": "confirmedGap.newSecondSourceShafts.cutWorldXY",
            "preserveExistingVoidIds": ["main-stair", "diamond-tree"],
            "newMaterials": 0,
            "verticalPolicy": "Retain existing finish/slab/soffit Zvalues; do not alter storey heights or upper floors.",
            "requiredNativeGuards": [
                "Verify saved faces/materials/UVs against exact263inspection before replacement.",
                "Check3Dhole airspace and finite hole-edge wall topology on the saved component, not only polygon intersections.",
                "Check source Second-floor wall-fill positions against actual second support plane and upper258slab underside before adding any core walls.",
                "Preserve all35room memberships and all unrelated263objects/material graphs.",
            ],
        },
        "wallEvidence": {
            "source": "Second-floor opaque black fills,read directly from page1",
            "sourceFills": fills,
            "boundaryPolicy": "The12corners are actual fill vertices around the shaft interiors. Smaller thin lift-car rectangles are controls only and are not cut boundaries.",
            "feasibleFollowUp": "A finite second-storey core enclosure can use these same-level filled wall footprints after clipping to a bounded core domain and checking native bearing. Door heads and wall height require explicit inherited/estimated vertical policy.",
            "unresolved": "No second-core wall body should be extruded across the entire broad stair/service fill by default. Exact source clipping domain, door openings, third-deck bearing and all contacts must be checked before authoring.",
        },
        "upperFloorDecision": {
            "object": "MAR_MAR_floor_way/1376078546_21.9",
            "decision": "Do not cut or down-project Third-floor polygons into this generic upper plate.",
            "reason": "Page1has no identified Level04orhigherplan. SectionAAalone does not identify completeXYboundaries of all three southern upper shafts.",
            "priorReview": "result/blender/mar-core251/upper-floor/review.json",
            "minimumNewEvidence": "An identified higher-level built plan with independent core controls and held-out residuals.",
        },
        "scopeLimits": [
            "No lift cars,equipment,operating doors,current accessibility certification or full-height shaft completeness is claimed.",
            "2022architect plans support geometry at identified floors; retained native heights and finishes remain estimates.",
            "No new primary-source search needed; the existing identified Second floor already supplies the new correction.",
            "No shared source,metadata,native,export or website file modified.",
        ],
        "sourceHashes": {str(p.relative_to(ROOT)): sha(p) for p in sources},
        "independentCheckScript": "web/tests/audit_mar_second_shafts269.py",
        "nativeReadOnlyScript": "web/tests/inspect_mar_second269.py",
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                "output": str(OUT.relative_to(ROOT)),
                "totalShaftAreaPerLayerM2": all_holes.area,
                "shafts": [
                    {
                        "id": r["id"],
                        "area": r["areaM2"],
                        "coverage": r["secondFloorTemplateCoveredFraction"],
                    }
                    for r in holes
                ],
                "nativeAvailable": snapshot is not None,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
