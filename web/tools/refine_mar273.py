"""Coordinate MAR's identified Second-to-Third lift-core segment only.

main('prepare') uses MachineLearning;main('build') uses Blender. Fixed private
outputs and exact269baseline. No command-line options or complete-campus save.
The coordination envelope is a drawing-error-bounded estimate, not a new survey.
"""

import collections
import hashlib
import json
import math
import struct
import sys
from itertools import pairwise
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v269.blend"
SHA = "a44026d64bb57cea159a44b1fa96b7b9be13e7d4af034f57d09beb62480ef21b"
OUT = ROOT / "result/blender/mar273"
OWNER = "MAR_PUBLIC_INTERIOR_study"
STAGE = "build"
DOORS_PDF = [
    (
        "west-upper-stair-side",
        [
            (156.9055, 279.8816),
            (156.9135, 279.8846),
            (157.7285, 279.8746),
            (157.7295, 279.8726),
            (157.7316, 284.431),
            (156.9096, 284.442),
        ],
    ),
    (
        "west-upper-corridor-side",
        [
            (164.6595, 279.8716),
            (165.4935, 279.8666),
            (165.4945, 279.8636),
            (165.4906, 284.440),
            (164.6636, 284.428),
            (164.6616, 284.428),
        ],
    ),
    (
        "west-lower-corridor-side",
        [
            (164.6636, 290.105),
            (165.4936, 290.117),
            (165.4936, 290.115),
            (165.4956, 294.673),
            (164.6716, 294.686),
        ],
    ),
    (
        "east-upper-corridor-side",
        [
            (175.4022, 279.8771),
            (176.2182, 279.8791),
            (176.2182, 279.8781),
            (176.2192, 284.4361),
            (175.4042, 284.4331),
        ],
    ),
]
DOORS_PDF.append(
    (
        "east-lower-transverse-corridor-side",
        [
            (175.3932, 289.7811),
            (176.2242, 289.7921),
            (176.2362, 294.9981),
            (176.2352, 295.0001),
            (175.3982, 295.0031),
            (175.3972, 295.0051),
        ],
    )
)
DOMAINS_PDF = [
    (156.9006, 276.6186, 165.5016, 297.931),
    (175.3932, 276.6211, 183.9912, 287.6931),
    (175.3932, 286.8581, 188.2892, 297.9321),
]


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as s:
        for block in iter(lambda: s.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads((ROOT / path).read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def f32(p):
    return tuple(struct.unpack("fff", struct.pack("fff", *p)))


def parts(shape):
    if shape.is_empty:
        return []
    if shape.geom_type == "Polygon":
        return [shape]
    return [p for p in shape.geoms if p.geom_type == "Polygon"]


def record_shape(shape):
    return [
        {
            "outer": list(p.exterior.coords)[:-1],
            "holes": [list(r.coords)[:-1] for r in p.interiors],
        }
        for p in parts(shape)
    ]


def source_geometry():
    """Read four shaft interiors independently from the two identified plans."""
    import numpy as np
    from shapely import set_precision
    from shapely.geometry import Polygon, box
    from shapely.ops import unary_union

    evidence = read("result/blender/mar269-evidence.json")
    registration = read("result/blender/mar-registration217/audit.json")[
        "geographicRegistration"
    ]
    place = registration["secondPdfToNativeLocalCandidate"]
    relative = read("result/blender/mar-exterior249/review.json")["coreRegistration"][
        "thirdPdfToSecondPdf"
    ]
    angle = math.radians(registration["nativeBasisDegrees"])
    basis = np.array(
        [[math.cos(angle), math.sin(angle)], [-math.sin(angle), math.cos(angle)]]
    )

    def second_world(points):
        local = place["scale"] * np.asarray(points)[:, ::-1] @ np.asarray(
            place["rotation"]
        ) + np.asarray(place["translation"])
        return np.asarray(registration["nativeOrigin"]) + local @ basis

    def third_world(points):
        second_pdf = relative["scale"] * np.asarray(points) @ np.asarray(
            relative["rotation"]
        ) + np.asarray(relative["translation"])
        return second_world(second_pdf)

    def mapped(shape, transform):
        return unary_union(
            [
                Polygon(
                    transform(p.exterior.coords),
                    [transform(r.coords) for r in p.interiors],
                )
                for p in parts(shape)
            ]
        )

    raw_second = unary_union(
        [
            set_precision(Polygon(row["sourcePdfPoints"]).buffer(0), 0.0001)
            for row in evidence["wallEvidence"]["sourceFills"].values()
        ]
    )
    domain_second = unary_union([box(*bounds) for bounds in DOMAINS_PDF])
    lower_second = raw_second.intersection(domain_second)
    second_doors = [
        {"id": name, "pdf": points, "shape": Polygon(second_world(points))}
        for name, points in DOORS_PDF
    ]
    full_second = unary_union(
        [lower_second]
        + [set_precision(Polygon(points), 0.0001) for _, points in DOORS_PDF]
    ).intersection(domain_second)
    fourth_second_pdf = [
        [176.2252, 287.6871],
        [187.2912, 287.6931],
        [187.2822, 297.1061],
        [176.2322, 297.1071],
    ]
    fourth_third_pdf = [
        [421.1401, 542.818],
        [432.2051, 542.825],
        [432.1971, 552.238],
        [421.1481, 552.238],
    ]
    second_fourth_fill = evidence["wallEvidence"]["sourceFills"]["curve-17364"][
        "sourcePdfPoints"
    ]
    assert (
        max(
            min(math.dist(point, vertex) for vertex in second_fourth_fill)
            for point in fourth_second_pdf
        )
        < 1e-7
    )
    shaft_points = [
        Polygon(row["pdf"]).centroid
        for row in evidence["confirmedGap"]["newSecondSourceShafts"]
    ] + [Polygon(fourth_second_pdf).centroid]
    full_second = unary_union(
        [
            p
            for p in parts(full_second)
            if any(Polygon(p.exterior).covers(c) for c in shaft_points)
        ]
    )
    assert sorted(len(p.interiors) for p in parts(full_second)) == [2, 2]
    lower_second = lower_second.intersection(full_second)

    third_fills = read("result/blender/mar-core251/retained-source-wall-fills.json")
    assert all(
        row["fill"] and not row["stroke"] and row["non_stroking_color"] == [0, 0, 0, 1]
        for row in third_fills
    )
    raw_third = unary_union(
        [set_precision(Polygon(row["pts"]).buffer(0), 0.0001) for row in third_fills]
    )
    third_fourth_fill = next(
        row["pts"] for row in third_fills if row["id"] == "curve-26287"
    )
    assert (
        max(
            min(math.dist(point, vertex) for vertex in third_fourth_fill)
            for point in fourth_third_pdf
        )
        < 1e-7
    )
    extension_domain = (420.3081, 542.002, 433.3332, 553.067)
    fourth_third_door_pdf = [
        [420.3081, 544.913],
        [421.1381, 544.925],
        [421.1501, 550.13],
        [420.3121, 550.136],
    ]
    third_lower = raw_third.intersection(box(*extension_domain))
    third_full = unary_union(
        [third_lower, set_precision(Polygon(fourth_third_door_pdf), 0.0001)]
    ).intersection(box(*extension_domain))
    assert len(parts(third_full)) == 1 and len(parts(third_full)[0].interiors) == 1
    second_raw_world = mapped(raw_second, second_world)
    third_raw_world = mapped(raw_third, third_world)
    fourth_second = (
        Polygon(second_world(fourth_second_pdf))
        .difference(second_raw_world)
        .simplify(0.00001, preserve_topology=True)
    )
    fourth_third = (
        Polygon(third_world(fourth_third_pdf))
        .difference(third_raw_world)
        .simplify(0.00001, preserve_topology=True)
    )
    assert all(
        p.geom_type == "Polygon" and not p.interiors
        for p in [fourth_second, fourth_third]
    )
    evidence["fourthSource"] = {
        "id": "east-lower-transverse",
        "identityPolicy": "Fourth lift supported by2022plan symbols and surveyed four-lift core count;not assigned a goods-lift designation.",
        "second": {
            "pdfInnerCorners": fourth_second_pdf,
            "cutWorldXY": list(fourth_second.exterior.coords)[:-1],
            "sourceFill": "curve-17364",
        },
        "third": {
            "pdfInnerCorners": fourth_third_pdf,
            "cutWorldXY": list(fourth_third.exterior.coords)[:-1],
            "sourceFill": "curve-26287",
        },
        "thirdExtensionDomainPdf": extension_domain,
        "thirdDoorPdf": fourth_third_door_pdf,
    }
    third_source = {
        "full": mapped(third_full, third_world),
        "lower": mapped(third_lower, third_world),
        "door": {
            "id": "east-lower-transverse-corridor-side",
            "pdf": fourth_third_door_pdf,
            "shape": Polygon(third_world(fourth_third_door_pdf)),
        },
        "domainPdf": extension_domain,
    }
    return (
        evidence,
        mapped(lower_second, second_world),
        mapped(full_second, second_world),
        second_doors,
        third_source,
    )


def registration_proof(evidence):
    import numpy as np
    from shapely.geometry import Point, Polygon

    review = read("result/blender/mar-exterior249/review.json")["coreRegistration"]
    native = read("result/blender/mar273/native-inspection.json")

    def corners(bounds):
        return [
            [bounds[0], bounds[1]],
            [bounds[2], bounds[1]],
            [bounds[2], bounds[3]],
            [bounds[0], bounds[3]],
        ]

    source = np.asarray(
        [p for bounds in review["fitSourceBounds"] for p in corners(bounds)]
    )
    target = np.asarray(
        [p for bounds in review["fitReferenceBounds"] for p in corners(bounds)]
    )
    centred_source = source - source.mean(0)
    centred_target = target - target.mean(0)
    u, _, vt = np.linalg.svd(centred_source.T @ centred_target)
    rotation = u @ vt
    scale = float(
        np.sum((centred_source @ rotation) * centred_target)
        / np.sum(centred_source * centred_source)
    )
    translation = target.mean(0) - scale * source.mean(0) @ rotation
    assert (
        np.max(np.abs(rotation - np.asarray(review["thirdPdfToSecondPdf"]["rotation"])))
        < 1e-10
    )
    assert abs(scale - review["thirdPdfToSecondPdf"]["scale"]) < 1e-10
    second_scale = evidence["independentSecondRegistration"]["scale"]
    fitted_residuals = (
        np.linalg.norm(scale * source @ rotation + translation - target, axis=1)
        * second_scale
    )
    held_out = []
    for row in review["heldOut"]:
        source_control = (
            corners(row["thirdPdfBounds"])
            if "thirdPdfBounds" in row
            else [row["thirdPdfPoint"]]
        )
        target_control = (
            corners(row["secondPdfBounds"])
            if "secondPdfBounds" in row
            else [row["secondPdfPoint"]]
        )
        residuals = (
            np.linalg.norm(
                scale * np.asarray(source_control) @ rotation
                + translation
                - np.asarray(target_control),
                axis=1,
            )
            * second_scale
        )
        held_out.append(
            {
                "id": row["id"],
                "residualsM": residuals.tolist(),
                "maximumM": float(max(residuals)),
            }
        )
    bound = max(row["maximumM"] for row in held_out)
    assert bound < 0.101
    controls = {row["id"]: row for row in held_out}
    targets = {row["name"]: row for row in native["targets"]}
    second = horizontal_footprint(
        targets["MAR269_second_floor_finish_with_source_shafts"], 12.800000190734863
    )
    third = horizontal_footprint(targets["MAR258_third_south_deck_solid"], 17.5)
    actual_second = [Polygon(ring) for ring in second.interiors]
    actual_third = [Polygon(ring) for ring in third.interiors]
    rows = []
    envelopes = []
    source_rows = list(evidence["confirmedGap"]["newSecondSourceShafts"]) + [
        {
            "id": evidence["fourthSource"]["id"],
            "cutWorldXY": evidence["fourthSource"]["second"]["cutWorldXY"],
        }
    ]
    for index, row in enumerate(source_rows):
        control = Polygon(row["cutWorldXY"]).centroid
        if index < 3:
            second_opening = min(
                actual_second, key=lambda p: p.centroid.distance(control)
            )
            third_opening = min(
                actual_third, key=lambda p: p.centroid.distance(control)
            )
        else:
            second_opening = Polygon(evidence["fourthSource"]["second"]["cutWorldXY"])
            third_opening = Polygon(evidence["fourthSource"]["third"]["cutWorldXY"])
            assert (
                second.intersection(second_opening).area / second_opening.area > 0.99999
            )
            assert third.intersection(third_opening).area / third_opening.area > 0.99999
        deviation = second_opening.hausdorff_distance(third_opening)
        assert deviation < bound
        envelope = second_opening.union(third_opening)
        assert envelope.geom_type == "Polygon" and not envelope.interiors
        nearest_control = "stair-right-lower" if index < 2 else "east-service-shaft"
        local_bound = controls[nearest_control]["maximumM"]
        rows.append(
            {
                "id": row["id"],
                "existingNativeOpeningBefore273": index < 3,
                "secondAreaM2": second_opening.area,
                "thirdAreaM2": third_opening.area,
                "axisOffsetM": second_opening.centroid.distance(third_opening.centroid),
                "maximumBoundaryDeviationM": deviation,
                "maximumSecondCornerToThirdBoundaryM": max(
                    third_opening.boundary.distance(Point(p))
                    for p in second_opening.exterior.coords
                ),
                "maximumThirdCornerToSecondBoundaryM": max(
                    second_opening.boundary.distance(Point(p))
                    for p in third_opening.exterior.coords
                ),
                "overallHeldOutBoundContainsDeviation": True,
                "nearestHeldOutControl": nearest_control,
                "nearestHeldOutResidualM": local_bound,
                "exceedsNearestHeldOutResidual": deviation > local_bound,
                "actualSecondFilledAreaToCutM2": second.intersection(envelope).area,
                "actualThirdFilledAreaToCutM2": third.intersection(envelope).area,
                "secondExtraBeyondOwnSourceM2": envelope.area - second_opening.area,
                "thirdExtraBeyondOwnSourceM2": envelope.area - third_opening.area,
                "secondInner": list(second_opening.exterior.coords)[:-1],
                "thirdInner": list(third_opening.exterior.coords)[:-1],
                "envelope": list(envelope.exterior.coords)[:-1],
            }
        )
        envelopes.append(envelope)
    return {
        "method": "Independent similarity refit of12car corners from the original three lifts;all fourth-car and stair controls remain held out. The fourth structural inner boundaries are read separately onSecondandThird.",
        "fitMaximumM": float(max(fitted_residuals)),
        "heldOut": held_out,
        "heldOutMaximumM": bound,
        "prior249ReportedHeldOutMaximumM": review["heldOutMaximumMetres"],
        "metricCorrection": "Current native Second-floor scale0.3055464766makes the earlier249metre residuals about2.88%larger.",
        "float32CoordinateResolutionBoundM": 0.000008,
        "pdfPrecisionGridM": 0.0001 * second_scale,
        "interpretation": "All four differences remain below the overall held-out residual. The fourth boundary difference exceeds its nearest car-control residual;source-error causation is not proved and this is an estimated coordination envelope,not a survey.",
        "shafts": rows,
    }, envelopes


def prepare():
    from shapely.geometry import Polygon

    native = read("result/blender/mar273/native-inspection.json")
    assert native["baselineSha256"] == SHA and native["readOnly"] and sha(BASE) == SHA
    evidence, lower, full, doors, third_source = source_geometry()
    proof, envelopes = registration_proof(evidence)
    targets = {row["name"]: row for row in native["targets"]}
    old_third = horizontal_footprint(
        targets["MAR251_third_south_lift_core_walls"], 21.899999618530273
    )
    third_combined = old_third.union(third_source["full"])
    assert sorted(len(p.interiors) for p in parts(third_combined)) == [2, 2]
    thickness = []
    for row, envelope in zip(proof["shafts"], envelopes):
        item = {"id": row["id"]}
        for label, walls in [("second", full), ("third", third_combined)]:
            shell = next(
                p
                for p in parts(walls)
                if Polygon(p.exterior).covers(envelope.representative_point())
            )
            assert envelope.difference(Polygon(shell.exterior)).area < 1e-9
            item[label + "MinimumRemainingWallM"] = envelope.boundary.distance(
                shell.exterior
            )
            assert item[label + "MinimumRemainingWallM"] > 0.2
        thickness.append(item)
    write(
        OUT / "coordination-evidence.json",
        {
            "baselineSha256": SHA,
            "shaftCount": 4,
            "registration": proof,
            "minimumWallThicknessBeforeBearingClip": thickness,
            "secondSourceDomainsPdf": DOMAINS_PDF,
            "secondSourceLowerWall": record_shape(lower),
            "secondSourceFullWall": record_shape(full),
            "secondSourceDoorHeads": [
                {
                    "id": d["id"],
                    "sourcePdf": d["pdf"],
                    "world": record_shape(d["shape"]),
                }
                for d in doors
            ],
            "fourthSource": evidence["fourthSource"],
            "thirdFourthSourceFullWall": record_shape(third_source["full"]),
            "rejectedThreeShaftRecord": "result/blender/mar273/source-review/rejected-three-shaft.json",
            "scope": "Four identified lift shafts betweenSecondandThird;the21.9mplate and higher geometry remain unchanged. Fourth lift is not assigned a goods-lift label.",
            "sourceHashes": {
                p: sha(ROOT / p)
                for p in [
                    "result/blender/mar273/native-inspection.json",
                    "result/blender/mar269-evidence.json",
                    "result/blender/mar-exterior249/review.json",
                    "result/blender/mar-core251/retained-source-wall-fills.json",
                    "result/blender/mar273/source-review/fourth-lift-identity.json",
                ]
            },
        },
    )
    print(
        "MAR273_FOUR_SOURCE_EVIDENCE",
        [(r["id"], r["maximumBoundaryDeviationM"]) for r in proof["shafts"]],
        thickness,
        flush=True,
    )
    prepare_geometry(
        native, evidence, lower, full, doors, proof, envelopes, third_source
    )


def clipped_mesh(target, cut, replacement):
    """Subtract a fixed vertical envelope, preserving uncut native faces/UVs."""
    import numpy as np
    from shapely import constrained_delaunay_triangles
    from shapely.geometry import LineString, Polygon, box
    from shapely.ops import unary_union

    xyz = target["verticesWorld"]
    records = []
    touched = []
    zlevels = sorted({p[2] for p in xyz})

    def interpolated(face, points, original):
        origin = np.asarray(original[0])
        normal = np.cross(
            np.asarray(original[1]) - origin, np.asarray(original[2]) - origin
        )
        normal /= np.linalg.norm(normal)
        u = np.asarray(original[1]) - origin
        u /= np.linalg.norm(u)
        v = np.cross(normal, u)
        old = np.asarray(
            [
                [(np.asarray(p) - origin) @ u, (np.asarray(p) - origin) @ v, 1]
                for p in original
            ]
        )
        new = np.asarray(
            [
                [(np.asarray(p) - origin) @ u, (np.asarray(p) - origin) @ v, 1]
                for p in points
            ]
        )
        return {
            name: (
                new @ np.linalg.lstsq(old, np.asarray(values), rcond=None)[0]
            ).tolist()
            for name, values in face["uvs"].items()
        }

    for face in target["faces"]:
        original = [xyz[i] for i in face["vertices"]]
        high = max(p[2] for p in original)
        low = min(p[2] for p in original)
        horizontal = high - low < 1e-7
        if horizontal:
            shape = Polygon([p[:2] for p in original])
            remaining = shape.difference(cut)
            overlap = shape.area - remaining.area

            def restore(q, source_z=original[0][2]):
                return [*q, source_z]
        else:
            pairs = [
                (math.dist(a[:2], b[:2]), a, b) for a in original for b in original
            ]
            length, a, b = max(pairs)
            assert length > 1e-7
            direction = np.asarray(b[:2]) - np.asarray(a[:2])
            direction /= length
            assert (
                max(
                    abs(direction[0] * (p[1] - a[1]) - direction[1] * (p[0] - a[0]))
                    for p in original
                )
                < 0.00001
            )
            shape = Polygon(
                [[(np.asarray(p[:2]) - a[:2]) @ direction, p[2]] for p in original]
            )
            line = LineString([a[:2], b[:2]])
            intersect = line.intersection(cut)
            segments = (
                list(intersect.geoms) if hasattr(intersect, "geoms") else [intersect]
            )
            intervals = []
            for segment in segments:
                if (
                    segment.geom_type != "LineString"
                    or segment.length < 1e-8
                    or not cut.contains(segment.interpolate(0.5, normalized=True))
                ):
                    continue
                t = [(np.asarray(p) - a[:2]) @ direction for p in segment.coords]
                intervals.append(box(min(t), low - 1, max(t), high + 1))
            remaining = shape.difference(unary_union(intervals)) if intervals else shape
            overlap = shape.area - remaining.area

            def restore(q, a=a, direction=direction):
                return [*(np.asarray(a[:2]) + direction * q[0]), q[1]]

        if overlap < 1e-14:
            records.append(
                {
                    "sourceFace": face["index"],
                    "role": "retained-native-face",
                    "points": original,
                    "uvs": face["uvs"],
                    "materialIndex": face["materialIndex"],
                    "smooth": face["smooth"],
                }
            )
            continue
        touched.append(face["index"])
        original_normal = np.cross(
            np.asarray(original[1]) - original[0], np.asarray(original[2]) - original[0]
        )
        for triangle in constrained_delaunay_triangles(remaining).geoms:
            points = [f32(restore(p)) for p in list(triangle.exterior.coords)[:3]]
            if len(set(points)) < 3:
                continue
            normal = np.cross(
                np.asarray(points[1]) - points[0], np.asarray(points[2]) - points[0]
            )
            if np.linalg.norm(normal) < 1e-10:
                continue
            if normal @ original_normal < 0:
                points.reverse()
            records.append(
                {
                    "sourceFace": face["index"],
                    "role": "source-face-cut",
                    "points": points,
                    "uvs": interpolated(face, points, original),
                    "materialIndex": face["materialIndex"],
                    "smooth": face["smooth"],
                }
            )
    # Recover each actual horizontal section from upward caps minus downward
    # overhang undersides above it. Native251has the explicit19.6mdoor-head seam.
    sections = []
    for low, high in pairwise(zlevels):
        up = []
        down = []
        middle = (low + high) / 2
        for face in target["faces"]:
            p = [xyz[i] for i in face["vertices"]]
            if max(q[2] for q in p) - min(q[2] for q in p) > 1e-7 or p[0][2] < middle:
                continue
            signed = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(p, p[1:] + p[:1]))
            (up if signed > 0 else down).append(Polygon([q[:2] for q in p]))
        footprint = unary_union(up).difference(unary_union(down))
        sections.append((low, high, footprint))
    for polygon in parts(cut):
        ring = list(polygon.exterior.coords)[:-1]
        signed = sum(
            a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1])
        )
        for a, b in zip(ring, ring[1:] + ring[:1]):
            line = LineString([a, b])
            direction = np.asarray(b) - a
            length = np.linalg.norm(direction)
            if length < 1e-7:
                continue
            direction /= length
            for low, high, footprint in sections:
                hit = line.intersection(footprint)
                segments = list(hit.geoms) if hasattr(hit, "geoms") else [hit]
                for segment in segments:
                    if (
                        segment.geom_type != "LineString"
                        or segment.length < 1e-7
                        or not footprint.contains(
                            segment.interpolate(0.5, normalized=True)
                        )
                    ):
                        continue
                    first, last = segment.coords[0], segment.coords[-1]
                    if (np.asarray(last) - first) @ direction < 0:
                        first, last = last, first
                    points = [
                        f32((*first, low)),
                        f32((*last, low)),
                        f32((*last, high)),
                        f32((*first, high)),
                    ]
                    if signed > 0:
                        points.reverse()
                    # CCWcut boundary has material outside it;surface normal faces
                    # into the void, opposite the positive extrusion's outer side.
                    uvs = [
                        [0, 0],
                        [segment.length, 0],
                        [segment.length, high - low],
                        [0, high - low],
                    ]
                    if signed > 0:
                        uvs.reverse()
                    records.append(
                        {
                            "sourceFace": None,
                            "role": "new-envelope-edge",
                            "points": points,
                            "uvs": {n: uvs for n in target["faces"][0]["uvs"]},
                            "materialIndex": 0,
                            "smooth": False,
                        }
                    )
    records = conform_records(records, cut)
    return {
        "sourceObject": target["name"],
        "replacement": replacement,
        "sourceFingerprint": target["fingerprint"],
        "sourceZ": [min(zlevels), max(zlevels)],
        "materials": target["materials"],
        "faceRecords": records,
        "touchedSourceFaces": touched,
        "expectedRemovedVolumeM3": sum(
            footprint.intersection(cut).area * (high - low)
            for low, high, footprint in sections
        ),
        "expectedTopAreaRemovedM2": horizontal_footprint(target, max(zlevels))
        .intersection(cut)
        .area,
    }


def conform_records(records, cut=None):
    """Share Float32cut intersections and split collinear face-edge junctions."""
    import numpy as np

    pool = []
    lookup = {}
    # Original positions remain exact;only newly computed intersections may snap.
    for row in records:
        if row["role"] == "retained-native-face":
            for p in row["points"]:
                q = f32(p)
                if q not in lookup:
                    lookup[q] = q
                    pool.append(q)
    for row in records:
        points = []
        for p in row["points"]:
            q = f32(p)
            if q not in lookup:
                near = [k for k in pool if math.dist(q, k) < 0.000006]
                if near:
                    q = min(near, key=lambda k: math.dist(q, k))
                else:
                    pool.append(q)
                lookup[f32(p)] = q
            points.append(lookup[f32(p)])
        row["points"] = points
    all_points = np.asarray(pool)
    for row in records:
        if row["role"] == "retained-native-face":
            continue
        points = row["points"]
        uvs = row["uvs"]
        new = []
        newuv = {n: [] for n in uvs}
        for i, (a, b) in enumerate(zip(points, points[1:] + points[:1])):
            delta = np.asarray(b) - a
            length2 = delta @ delta
            if length2 < 1e-16:
                continue
            t = (all_points - a) @ delta / length2
            distance = np.linalg.norm(
                all_points - (np.asarray(a) + t[:, None] * delta), axis=1
            )
            from shapely.geometry import Point

            near_cut = (
                cut is None
                or cut.boundary.distance(Point((np.asarray(a[:2]) + b[:2]) / 2))
                < 0.00001
            )
            candidates = [(0.0, a)] + (
                [
                    (float(t[k]), tuple(all_points[k]))
                    for k in range(len(pool))
                    if 1e-7 < t[k] < 1 - 1e-7 and distance[k] < 0.000006
                ]
                if near_cut
                else []
            )
            for fraction, p in sorted(candidates):
                if new and p == new[-1]:
                    continue
                new.append(p)
                for name, values in uvs.items():
                    newuv[name].append(
                        [
                            (1 - fraction) * values[i][j]
                            + fraction * values[(i + 1) % len(points)][j]
                            for j in range(2)
                        ]
                    )
        if new and new[0] == new[-1]:
            new.pop()
            [v.pop() for v in newuv.values()]
        row["points"] = new
        row["uvs"] = newuv
    records = [
        r for r in records if len(r["points"]) >= 3 and len(set(r["points"])) >= 3
    ]
    edge_counts = collections.Counter(
        tuple(sorted((a, b)))
        for r in records
        for a, b in zip(r["points"], r["points"][1:] + r["points"][:1])
    )
    if set(edge_counts.values()) != {2}:
        write(OUT / "mesh-debug.json", records)
    assert set(edge_counts.values()) == {2}, (
        "nonmanifold",
        collections.Counter(edge_counts.values()),
        [e for e, n in edge_counts.items() if n != 2][:8],
    )
    return records


def horizontal_footprint(target, height):
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    xyz = target["verticesWorld"]
    return unary_union(
        [
            Polygon([xyz[i][:2] for i in f["vertices"]])
            for f in target["faces"]
            if all(abs(xyz[i][2] - height) < 1e-6 for i in f["vertices"])
        ]
    )


def wall_mesh(lower, full, low, head, top, uv_names):
    from shapely import constrained_delaunay_triangles, set_precision
    from shapely.geometry.polygon import orient
    from shapely.ops import polygonize, unary_union

    lines = unary_union(
        set_precision(unary_union([lower.boundary, full.boundary]), 0.00002)
    )
    cells = [
        orient(p, sign=1)
        for p in polygonize(lines)
        if p.area > 1e-10 and full.covers(p.representative_point())
    ]
    assert unary_union(cells).symmetric_difference(full).area < 0.00005, (
        len(cells),
        unary_union(cells).symmetric_difference(full).area,
        full.area,
        unary_union(cells).area,
    )
    bottoms = [low if lower.covers(p.representative_point()) else head for p in cells]
    edges = collections.defaultdict(list)
    for index, cell in enumerate(cells):
        for ring in [cell.exterior] + list(cell.interiors):
            coordinates = list(ring.coords)
            for a, b in pairwise(coordinates):
                edges[tuple(sorted((a, b)))].append((index, a, b))
    records = []

    def add(points, uvs):
        points = [f32(p) for p in points]
        assert len(set(points)) == len(points)
        records.append(
            {
                "sourceFace": None,
                "role": "new-source-second-core-wall",
                "points": points,
                "uvs": {n: uvs for n in uv_names},
                "materialIndex": 0,
                "smooth": False,
            }
        )

    for index, cell in enumerate(cells):
        for tri in constrained_delaunay_triangles(cell).geoms:
            xy = list(orient(tri, sign=1).exterior.coords)[:3]
            add([(*p, top) for p in xy], xy)
            xy.reverse()
            add([(*p, bottoms[index]) for p in xy], xy)
    for owners in edges.values():
        assert len(owners) <= 2
        for index, a, b in owners:
            others = [other for other, _, _ in owners if other != index]
            for z0, z1 in [(low, head), (head, top)]:
                if bottoms[index] > z0 + 1e-6 or any(
                    bottoms[o] <= z0 + 1e-6 for o in others
                ):
                    continue
                length = math.dist(a, b)
                add(
                    [(*a, z0), (*b, z0), (*b, z1), (*a, z1)],
                    [
                        [0, z0 - low],
                        [length, z0 - low],
                        [length, z1 - low],
                        [0, z1 - low],
                    ],
                )
    counts = collections.Counter(
        tuple(sorted((a, b)))
        for r in records
        for a, b in zip(r["points"], r["points"][1:] + r["points"][:1])
    )
    assert set(counts.values()) == {2}, collections.Counter(counts.values())
    return records


def prepare_geometry(
    native, evidence, lower, full, doors, proof, envelopes, third_source
):
    """Keep native three-shaft wall faces and add only the missing fourth wall."""
    import numpy as np
    from shapely import set_precision
    from shapely.geometry import Point, Polygon
    from shapely.geometry.polygon import orient
    from shapely.ops import unary_union

    cut = unary_union(envelopes).buffer(0.00003, join_style=2)
    assert len(parts(cut)) == 4
    targets = {row["name"]: row for row in native["targets"]}
    names = {
        name: name.replace("MAR269", "MAR273")
        .replace("MAR258", "MAR273")
        .replace("MAR251", "MAR273")
        + "_coordinated"
        for name in targets
    }
    plans = [clipped_mesh(target, cut, names[name]) for name, target in targets.items()]
    second = targets["MAR269_second_floor_finish_with_source_shafts"]
    third = targets["MAR258_third_south_deck_solid"]
    old_core = targets["MAR251_third_south_lift_core_walls"]
    second_z = max(p[2] for p in second["verticesWorld"])
    third_bottom = min(p[2] for p in third["verticesWorld"])
    third_z = max(p[2] for p in third["verticesWorld"])
    ceiling_z = max(p[2] for p in old_core["verticesWorld"])
    support_second = horizontal_footprint(second, second_z).difference(cut)
    support_third = horizontal_footprint(third, third_bottom).difference(cut)
    second_source_full = full.difference(cut.buffer(0.0001, join_style=2))
    second_bearing = support_second.intersection(support_third).buffer(
        -0.0001, join_style=2
    )
    full = set_precision(second_source_full.intersection(second_bearing), 0.00002)
    lower = set_precision(
        full.difference(
            unary_union([door["shape"].buffer(0.0002, join_style=2) for door in doors])
        ),
        0.00002,
    )
    assert sorted(len(p.interiors) for p in parts(full)) == [2, 2]
    thickness = []
    for row, envelope in zip(proof["shafts"], envelopes):
        shell = next(
            p
            for p in parts(full)
            if Polygon(p.exterior).covers(envelope.representative_point())
        )
        remaining = envelope.boundary.distance(shell.exterior)
        assert remaining > 0.2
        thickness.append({"id": row["id"], "secondMinimumAfterBearingClipM": remaining})
    uv_names = list(old_core["faces"][0]["uvs"])
    second_head = f32((0, 0, second_z + 2.1))[2]
    plans.append(
        {
            "sourceObject": None,
            "replacement": "MAR273_second_south_lift_core_walls",
            "componentRole": "second-core-wall",
            "sourceFingerprint": None,
            "sourceZ": [second_z, third_bottom],
            "materials": ["MAR_D3_concrete"],
            "faceRecords": wall_mesh(
                lower, full, second_z, second_head, third_bottom, uv_names
            ),
            "touchedSourceFaces": [],
        }
    )

    old_full = horizontal_footprint(old_core, ceiling_z)
    old_lower = horizontal_footprint(old_core, third_z)
    ceiling_name = "MAR_MAR_floor_way/1376078546_21.9"
    ceiling = next(row for row in native["neighbours"] if row["name"] == ceiling_name)
    ceiling_footprint = unary_union(
        [
            Polygon([p[:2] for p in triangle["points"]])
            for triangle in ceiling["triangles"]
        ]
    )
    third_bearing = (
        horizontal_footprint(third, third_z)
        .difference(cut)
        .intersection(ceiling_footprint)
        .buffer(-0.0001, join_style=2)
    )
    extension_source = (
        third_source["full"]
        .difference(old_full)
        .difference(cut.buffer(0.0001, join_style=2))
    )
    extension_full = set_precision(
        extension_source.intersection(third_bearing), 0.00002
    )
    extension_lower = set_precision(
        extension_full.difference(
            third_source["door"]["shape"].buffer(0.0002, join_style=2)
        ),
        0.00002,
    )
    third_head = f32((0, 0, third_z + 2.1))[2]
    plans.append(
        {
            "sourceObject": None,
            "replacement": "MAR273_third_transverse_lift_core_extension",
            "componentRole": "third-core-extension",
            "sourceFingerprint": None,
            "sourceZ": [third_z, ceiling_z],
            "materials": ["MAR_D3_concrete"],
            "faceRecords": wall_mesh(
                extension_lower,
                extension_full,
                third_z,
                third_head,
                ceiling_z,
                uv_names,
            ),
            "touchedSourceFaces": [],
        }
    )
    actual_old_full = old_full.difference(cut)
    combined_third_full = actual_old_full.union(extension_full)
    # Separate native batches meet within the explicit50micrometre seam
    # tolerance. This conservative shell screen is followed by actual3Dseam rays.
    thickness_shell = combined_third_full.buffer(0.00005, join_style=2)
    third_thickness = []
    for row, envelope in zip(proof["shafts"], envelopes):
        shell = next(
            p
            for p in parts(thickness_shell)
            if Polygon(p.exterior).covers(envelope.representative_point())
        )
        value = envelope.boundary.distance(shell.exterior) - 0.00005
        assert value > 0.2
        third_thickness.append(
            {"id": row["id"], "thirdMinimumAfterBearingClipM": value}
        )
    overlap = extension_full.intersection(actual_old_full).area
    assert overlap < 0.00015
    seam_probes = []
    for poly in parts(old_full):
        poly = orient(poly, sign=1)
        for ring in [poly.exterior] + list(poly.interiors):
            xy = list(ring.coords)
            for first, last in pairwise(xy):
                tangent = np.asarray(last) - first
                length = np.linalg.norm(tangent)
                if length < 0.02:
                    continue
                tangent /= length
                outward = np.array([tangent[1], -tangent[0]])
                centre = (np.asarray(first) + last) / 2
                if cut.distance(Point(centre)) < 0.01:
                    continue
                if old_full.contains(
                    Point(centre - outward * 0.005)
                ) and extension_full.contains(Point(centre + outward * 0.005)):
                    seam_probes.append(
                        {
                            "pointXY": centre.tolist(),
                            "outwardXY": outward.tolist(),
                            "height": 20.0,
                        }
                    )
    assert len(seam_probes) >= 2
    old_doors = read("result/blender/mar-core251/plan.json")["doors"]
    third_doors = old_doors + [
        {
            "id": third_source["door"]["id"],
            "world": record_shape(third_source["door"]["shape"]),
        }
    ]
    plan = {
        "version": 273,
        "building": "MAR",
        "shaftCount": 4,
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": SHA,
        "targetCollection": OWNER,
        "candidateOnly": True,
        "fullHeightShaftAcceptance": False,
        "registration": proof,
        "envelopes": record_shape(cut),
        "objects": plans,
        "secondWall": {
            "lowerFootprint": record_shape(lower),
            "fullFootprint": record_shape(full),
            "low": second_z,
            "doorHead": second_head,
            "top": third_bottom,
            "sourceWallAreaM2": second_source_full.area,
            "bearingClippedAreaM2": second_source_full.area - full.area,
            "minimumWallThicknessAfterBearingClip": thickness,
            "numericalInsetM": 0.0001,
            "coordinateGridM": 0.00002,
            "doors": [
                {"id": door["id"], "world": record_shape(door["shape"])}
                for door in doors
            ],
        },
        "thirdExtension": {
            "object": "MAR273_third_transverse_lift_core_extension",
            "low": third_z,
            "doorHead": third_head,
            "top": ceiling_z,
            "sourceFullFootprint": record_shape(third_source["full"]),
            "fullFootprint": record_shape(extension_full),
            "lowerFootprint": record_shape(extension_lower),
            "sourceExtensionAreaM2": extension_source.area,
            "bearingClippedAreaM2": extension_source.area - extension_full.area,
            "oldFullFootprint": record_shape(old_full),
            "oldLowerFootprint": record_shape(old_lower),
            "numericProjectedOverlapWithRetainedCoreM2": overlap,
            "seamProbes": seam_probes,
            "seamToleranceM": 0.00005,
            "thicknessShellJoinToleranceM": 0.00005,
            "minimumWallThicknessAfterBearingClip": third_thickness,
            "doors": third_doors,
        },
        "envelopeNumericalExpansionM": 0.00003,
        "doorMaskNumericalExtensionM": 0.0002,
        "newMaterials": 0,
        "unmodifiedHigherPlate": ceiling_name,
        "rejectedThreeShaftRecord": "result/blender/mar273/source-review/rejected-three-shaft.json",
        "fourthIdentity": "Transverse fourth lift;not assigned a goods-lift designation.",
        "sourceHashes": {
            path: sha(ROOT / path)
            for path in [
                "result/blender/mar273/native-inspection.json",
                "result/blender/mar273/coordination-evidence.json",
                "result/blender/mar-core251/retained-source-wall-fills.json",
                "result/blender/mar273/source-review/fourth-lift-identity.json",
                "result/blender/mar273/source-review/rejected-three-shaft.json",
                "data/collections/mar-built-registration-2026/grafton-marshall-built-plans-2022.pdf",
            ]
        },
    }
    write(OUT / "plan.json", plan)
    print(
        "MAR273_FOUR_PLAN_READY",
        [(row["replacement"], len(row["faceRecords"])) for row in plans],
        thickness,
        third_thickness,
        "seams",
        len(seam_probes),
        flush=True,
    )


def capture():
    from refine_houghton262 import capture as original_capture

    result = original_capture()
    result["baselineSha256"] = SHA
    return result


def protection(before, added=(), archived=()):
    after = capture()
    for name, value in before["objects"].items():
        expected = dict(value)
        if name in archived:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
        expected_visibility = (
            [True, before["visibility"][name][1], True]
            if name in archived
            else before["visibility"][name]
        )
        assert after["visibility"][name] == expected_visibility, name
    assert set(after["objects"]) == set(before["objects"]) | set(added)
    assert (
        after["materials"] == before["materials"]
        and after["rooms"] == before["rooms"]
        and len(after["rooms"]) == 35
    )
    assert after["campusRooms"] == before["campusRooms"] and sha(BASE) == SHA


def build_mesh(row, source):
    import bmesh
    import bpy

    mesh = bpy.data.meshes.new(row["replacement"] + "_mesh")
    vertices = []
    faces = []
    lookup = {}
    for record in row["faceRecords"]:
        face = []
        for point in record["points"]:
            point = f32(point)
            if point not in lookup:
                lookup[point] = len(vertices)
                vertices.append(point)
            face.append(lookup[point])
        assert len(set(face)) == len(face) and len(face) >= 3
        faces.append(face)
    mesh.from_pydata(vertices, [], faces)
    for name in row["materials"]:
        mesh.materials.append(bpy.data.materials[name])
    for face, record in zip(mesh.polygons, row["faceRecords"]):
        face.material_index = record["materialIndex"]
        face.use_smooth = record["smooth"]
    for name in row["faceRecords"][0]["uvs"]:
        layer = mesh.uv_layers.new(name=name)
        for face, record in zip(mesh.polygons, row["faceRecords"]):
            for index, uv in zip(face.loop_indices, record["uvs"][name]):
                layer.data[index].uv = uv
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    assert all(e.is_manifold for e in bm.edges) and bm.calc_volume(signed=True) > 0
    bm.free()
    obj = source.copy()
    obj.data = mesh
    obj.name = row["replacement"]
    obj.use_fake_user = True
    obj["originalObject"] = row["sourceObject"] or ""
    obj["destinationCollection"] = OWNER
    obj["publicInteriorComponent"] = True
    obj["sourceScope"] = (
        "Second-to-Third bounded lift-core coordination;inherited height and estimated2.1mdoor heads"
    )
    bpy.data.collections[OWNER].objects.link(obj)
    return obj


def build():
    import importlib.util

    import bpy

    sys.path.insert(0, str(ROOT / "web/tools"))
    from integrate_exterior_round194 import object_fingerprint, update_scene
    from refine_portsmouth_exterior207 import material_fingerprint

    plan = read("result/blender/mar273/plan.json")
    assert plan["baselineSha256"] == SHA == sha(BASE)
    assert all(sha(ROOT / p) == h for p, h in plan["sourceHashes"].items())
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = capture()
    assert (
        len(before["objects"]) == 8752
        and len(before["materials"]) == 2355
        and len(before["rooms"]) == 35
    )
    objects = []
    for row in plan["objects"]:
        source = bpy.data.objects[
            row["sourceObject"] or "MAR251_third_south_lift_core_walls"
        ]
        if row["sourceObject"]:
            assert (
                not source.hide_render
                and object_fingerprint(source) == row["sourceFingerprint"]
            )
        objects.append(build_mesh(row, source))
    update_scene()
    protection(before, [o.name for o in objects])
    component = OUT / "component.blend"
    audit = {
        "version": 273,
        "building": "MAR",
        "status": "bounded-two-floor-component-awaiting-verification",
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": SHA,
        "componentPath": str(component.relative_to(ROOT)),
        "targetCollection": OWNER,
        "destinationCollection": OWNER,
        "addedObjects": [o.name for o in objects],
        "archivedObjects": [
            r["sourceObject"] for r in plan["objects"] if r["sourceObject"]
        ],
        "changedObjects": [],
        "objectOwners": {o.name: OWNER for o in objects},
        "addedFingerprints": {o.name: object_fingerprint(o) for o in objects},
        "replacementMaterialBindings": {
            o.name: [m.name for m in o.data.materials] for o in objects
        },
        "reusedMaterialGraphs": {
            m.name: material_fingerprint(m) for o in objects for m in o.data.materials
        },
        "newMaterials": 0,
        "newMaterialGraphs": {},
        "retainNewMaterials": [],
        "addedMaterialFingerprints": {},
        "shaftCount": 4,
        "sourcePlan": "result/blender/mar273/plan.json",
        "sourcePlanSha256": sha(OUT / "plan.json"),
        "sourceEvidence": "result/blender/mar273/coordination-evidence.json",
        "sourceHashes": {
            **plan["sourceHashes"],
            "result/blender/mar273/plan.json": sha(OUT / "plan.json"),
        },
        "retainedHigherPlateFingerprint": object_fingerprint(
            bpy.data.objects[plan["unmodifiedHigherPlate"]]
        ),
        "scope": "Estimate-bounded coordination of four identified Second/Thirdlift apertures and source-filled core walls. Five native meshes remain hidden archives. The21.9mplate remains uncut. The fourth lift is not named as a goods lift.",
        "limitations": [
            "The2022vector plans are not a2026survey.",
            "Zdatums,wall heights and2.1mdoor heads remain estimates.",
            "An envelope within independent held-out registration residuals coordinates these two floors only;physical cause of source differences is not proved.",
        ],
        "candidateOnly": True,
        "fullHeightShaftAcceptance": False,
        "noFullNativeSaved": True,
    }
    bpy.data.libraries.write(str(component), set(objects), fake_user=False)
    audit["componentSha256"] = sha(component)
    write(OUT / "audit.json", audit)
    bpy.ops.wm.open_mainfile(filepath=str(component))
    assert set(bpy.data.objects.keys()) == set(audit["addedObjects"])
    assert all(
        object_fingerprint(bpy.data.objects[n]) == h
        for n, h in audit["addedFingerprints"].items()
    )
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    verifier_path = ROOT / "web/tests/verify_mar273.py"
    spec = importlib.util.spec_from_file_location("mar273_independent", verifier_path)
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    verifier.apply_component(audit)
    proof = verifier.geometry_proof(audit)
    audit["status"] = "passed-builder-roundtrip-bounded-two-floor-component"
    audit["verification"] = proof
    audit["authoringScriptSha256"] = sha(Path(__file__))
    audit["verificationScriptSha256"] = sha(verifier_path)
    write(OUT / "audit.json", audit)
    write(
        OUT / "verification.json",
        {
            "status": "passed-builder-roundtrip",
            "baselineSha256": SHA,
            "componentSha256": audit["componentSha256"],
            "freshBlenderProcess": False,
            "actualMeshProof": proof,
            "wholeNativeSaved": False,
        },
    )
    print("MAR273_COMPONENT_READY", audit["componentSha256"], flush=True)


def main(stage=STAGE):
    if stage == "prepare":
        prepare()
    elif stage == "build":
        build()
    else:
        raise ValueError("Stage must be prepare or build")


if __name__ == "__main__":
    main()
