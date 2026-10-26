"""Place the private SAW metric-design candidate using explicit estimated GIS controls.

No Blender, browser, model, catalogue or metadata write. Design-registration
residuals and geographic-placement residuals are deliberately kept separate.
"""
import hashlib
import json
import math
from pathlib import Path

import cv2
import numpy as np
from shapely.geometry import Point, shape
from shapely.ops import transform

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/saw269"
DRAWINGS = ROOT / "data/建筑图片/SAW_Saw Swee Hock Student Centre/02_图纸与结构"
GEOJSON = ROOT / "data/collections/streets/derived/buildings.geojson"
ORIGIN = (-0.1167, 51.5146)
CAD_PARTY_ENDPOINTS = np.array([[59.0, 1637.5], [1588.5, 1637.5]])
CAD_SHORT_EDGE_METRES = 6.340


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rigid(points, matrix, offset):
    return np.asarray(points) @ matrix.T + offset


def project_geometries(features):
    lon0, lat0 = map(math.radians, ORIGIN)
    semimajor, eccentricity_squared = 6378137.0, 6.69437999014e-3

    def ecef(lon, lat):
        lon, lat = map(math.radians, (lon, lat))
        radius = semimajor / math.sqrt(1 - eccentricity_squared * math.sin(lat) ** 2)
        return np.array([radius * math.cos(lat) * math.cos(lon), radius * math.cos(lat) * math.sin(lon),
                         radius * (1 - eccentricity_squared) * math.sin(lat)])

    origin = ecef(*ORIGIN)

    def project(lon, lat, _z=None):
        delta = ecef(lon, lat) - origin
        return (float(-math.sin(lon0) * delta[0] + math.cos(lon0) * delta[1]),
                float(-math.sin(lat0) * math.cos(lon0) * delta[0] - math.sin(lat0) * math.sin(lon0) * delta[1] + math.cos(lat0) * delta[2]))

    return {feature["id"]: transform(project, shape(feature["geometry"]))
            for feature in features if feature["geometry"]["type"] == "Polygon"}


def source_north_direction():
    sketch = cv2.imread(str(DRAWINGS / "exteriors_saw_archdaily_039.jpg"), cv2.IMREAD_GRAYSCALE)
    cad = cv2.imread(str(DRAWINGS / "exteriors_saw_archdaily_032.jpg"), cv2.IMREAD_GRAYSCALE)
    mask = np.zeros_like(sketch)
    mask[200:1450, 200:1100] = 255
    sift = cv2.SIFT_create(nfeatures=15000, contrastThreshold=.012, edgeThreshold=14)
    a, da = sift.detectAndCompute(sketch, mask)
    b, db = sift.detectAndCompute(cad, None)
    matches = cv2.BFMatcher().knnMatch(da, db, k=2)
    matches = [x for x, y in matches if x.distance < .70 * y.distance]
    source = np.float32([a[match.queryIdx].pt for match in matches])
    target = np.float32([b[match.trainIdx].pt for match in matches])
    matrix, selected = cv2.estimateAffinePartial2D(source, target, method=cv2.RANSAC,
        ransacReprojThreshold=4, maxIters=10000, confidence=.999)
    assert matrix is not None and int(selected.sum()) >= 12
    yy, xx = np.mgrid[1660:1705, 1578:1624]
    interior = ((xx - 1600.0) ** 2 + (yy - 1684.0) ** 2 < 14 ** 2) & (sketch[1660:1705, 1578:1624] < 110)
    stroke = np.column_stack([xx[interior], yy[interior]])
    assert len(stroke) >= 15
    _, vectors = np.linalg.eigh(np.cov(stroke.T))
    north_sketch = vectors[:, -1]
    if north_sketch[1] > 0:
        north_sketch = -north_sketch
    north_cad = matrix[:, :2] @ north_sketch
    north_design = north_cad * np.array([1, -1])
    north_design /= np.linalg.norm(north_design)
    return north_design, {"sketchToCadSimilarity": matrix.tolist(), "fitInliers": int(selected.sum()),
        "compassCentreSketchPixel": [1600.0, 1684.0], "strokePixels": len(stroke),
        "northDirectionSketchPixels": north_sketch.tolist(), "northDirectionDesign": north_design.tolist(),
        "bearingUncertaintyDegrees": 3.0,
        "scope": "The small raster compass fixes orientation and resolves the180degree ambiguity; its line width does not support survey bearing precision."}


def main():
    cv2.setRNGSeed(269)
    candidate = json.loads((OUT / "design-registration-candidate.json").read_text())
    features = json.loads(GEOJSON.read_text())["features"]
    geometries = project_geometries(features)
    saw = next(feature for feature in features if feature["properties"].get("short_name") == "SAW")
    peacock = next(feature for feature in features if feature["properties"].get("short_name") == "PEA")
    saw_ring = np.asarray(geometries[saw["id"]].exterior.coords[:-1])
    # Original SAW indices1->4 include the long shared theatre-complex boundary.
    # Index0 is the independent street corner at the end of the short named-PEA edge.
    geographic_party = saw_ring[[4, 1]]
    street_corner = saw_ring[0]
    peacock_corner_distance = geometries[peacock["id"]].boundary.distance(Point(street_corner))
    assert peacock_corner_distance < 1e-7, "Held-out point must also lie on the independent namedPeacock boundary"
    direction = geographic_party[1] - geographic_party[0]
    direction /= np.linalg.norm(direction)
    wall_rotation = np.column_stack([direction, [-direction[1], direction[0]]])
    metres_per_pixel = candidate["independentOverallDimension"]["metresPerCadPixel"]
    source_map = np.asarray(candidate["fit"]["matrixGuideToArchitect"])
    cad_origin = rigid([[145.0, 400.0]], source_map[:, :2], source_map[:, 2])[0]
    design_party = (CAD_PARTY_ENDPOINTS - cad_origin) * np.array([metres_per_pixel, -metres_per_pixel])
    # The short edge uses an independent architect dimension, never a length fit to OSM.
    design_street_corner = design_party[1] + np.array([0, CAD_SHORT_EDGE_METRES])
    geographic_midpoint = geographic_party.mean(axis=0)
    north, north_proof = source_north_direction()
    north_angle = math.pi / 2 - math.atan2(north[1], north[0])
    north_rotation = np.array([[math.cos(north_angle), -math.sin(north_angle)],
                               [math.sin(north_angle), math.cos(north_angle)]])
    variants = []
    for label, rotation, fit in (
        ("north-arrow-and-boundary-midpoint", north_rotation,
         ["039north stroke", "OSM shared-boundary midpoint only"]),
        ("OSM-wall-refined-with-north-arrow-sign-check", wall_rotation,
         ["OSM shared long-wall direction and midpoint", "039north stroke selects orientation sign; no scale fitted"]),
    ):
        offset = geographic_midpoint - rotation @ design_party.mean(axis=0)
        placed_party = rigid(design_party, rotation, offset)
        placed_corner = rigid([design_street_corner], rotation, offset)[0]
        north_after = rotation @ north
        north_error = math.degrees(math.atan2(north_after[0], north_after[1]))
        held_out_error = float(np.linalg.norm(placed_corner - street_corner))
        variants.append({"name": label, "status": "OSM-supported-estimate-not-survey-accepted",
            "designToCampusXY": {"rotation": rotation.tolist(), "translation": offset.tolist(),
                                  "scale": 1.0, "determinant": float(np.linalg.det(rotation))},
            "fitControls": fit, "northBearingResidualDegrees": north_error,
            "partyWallEndpointResidualMetres": np.linalg.norm(placed_party - geographic_party, axis=1).tolist(),
            "heldOutPeacockStreetCorner": {"usedForFit": False, "architectShortEdgeMetres": CAD_SHORT_EDGE_METRES,
                "designPoint": design_street_corner.tolist(), "predictedCampusPoint": placed_corner.tolist(),
                "osmPoint": street_corner.tolist(), "errorMetres": held_out_error},
            "heldOutShortEdgeLength": {"usedForFit": False, "architectMetres": CAD_SHORT_EDGE_METRES,
                "osmMetres": float(np.linalg.norm(saw_ring[0] - saw_ring[1])),
                "differenceMetres": float(np.linalg.norm(saw_ring[0] - saw_ring[1])) - CAD_SHORT_EDGE_METRES}})
    neighbours = []
    for feature in features:
        if feature["id"] not in geometries or feature["id"] == saw["id"]:
            continue
        length = geometries[saw["id"]].boundary.intersection(geometries[feature["id"]].boundary).length
        if length > .05:
            neighbours.append({"osmId": feature["id"], "name": feature["properties"].get("name"),
                "code": feature["properties"].get("short_name"), "sharedMetres": length})
    report = {"version": 269, "status": "private-geographic-placement-candidates", "sourceOsm": str(GEOJSON.relative_to(ROOT)),
        "sourceOsmSha256": sha(GEOJSON), "coordinateSystem": "Same WGS84 ECEF->local ENU as original prepare_site; X east,Y north,origin[-.1167,51.5146]",
        "sources": [{"path": str((DRAWINGS / name).relative_to(ROOT)), "sha256": sha(DRAWINGS / name)}
                    for name in ["exteriors_saw_archdaily_039.jpg", "exteriors_saw_archdaily_032.jpg"]],
        "designRegistrationResiduals": {"heldOutMaximumMetres": max(p["errorMetres"] for p in candidate["heldOutExteriorControls"]),
            "overallDimensionDifferenceMetres": candidate["independentOverallDimension"]["differenceMetres"],
            "scope": "Source guide versus architect drawing only; do not combine these with geographic-placement errors."},
        "northArrowProof": north_proof, "osmNeighbours": neighbours,
        "heldOutPeacockBoundaryDistanceMetres": peacock_corner_distance,
        "theatreBoundaryAttribution": "Architect context labels the adjacent long-side mass asPeacock Theatre. The OSM namedPEAway23613986shares only10.97m;44.14mof the long side belongs to unnamedway181939041. Attribution to a theatre complex is contextual, not an OSM name tag.",
        "partyWallControls": {"cadPixels": CAD_PARTY_ENDPOINTS.tolist(), "designMetres": design_party.tolist(),
            "osmSawIndices": [4, 1], "osmCampusPoints": geographic_party.tolist(),
            "architectLengthMetres": float(np.linalg.norm(design_party[1] - design_party[0])),
            "osmChordMetres": float(np.linalg.norm(geographic_party[1] - geographic_party[0]))},
        "variants": variants,
        "recommendation": "Use the north-arrow-consistent wall-refined variant only as the explicit estimated campus placement for a private coherent candidate; retain the separate held-out street-corner error.",
        "limitations": ["The OSM footprint is generalized and is not certified2026construction geometry.",
            "The small compass stroke limits independent bearing precision to approximately3degrees.",
            "Geographic wall fitting must not change the internal design map, trim a slab or bend a stair.",
            "Source north-arrow/campus context determines orientation; no graphic resemblance of a single facade is used to force geometry."]}
    (OUT / "geographic-placement-candidates.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("SAW269_GEOGRAPHIC_CANDIDATES", json.dumps({"designErrorMetres": report["designRegistrationResiduals"],
        "placement": [{"variant": v["name"], "northResidualDegrees": v["northBearingResidualDegrees"],
            "heldOutStreetCornerMetres": v["heldOutPeacockStreetCorner"]["errorMetres"]} for v in variants]}), flush=True)


if __name__ == "__main__":
    main()
