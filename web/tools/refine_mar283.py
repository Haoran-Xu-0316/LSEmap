"""Source-bounded MAR283 ground lift-core coordination.

Fixed immutable279baseline; private component only. main('inspect') uses Blender,
main('prepare') uses MachineLearning, main('build') uses Blender. No CLI options,
new environment, global metadata or complete-campus save. Higher floor datums
remain inherited model estimates and no higher shaft footprint is extrapolated.
"""

import hashlib
import importlib.util
import json
import math
import struct
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v279.blend"
SHA = "b03a0caec932c50e0c7d8ad2a725a43b80eb38abee716f1d1c2d30cde767982c"
OUT = ROOT / "result/blender/mar283"
OWNER = "MAR_PUBLIC_INTERIOR_study"
SOURCE = (
    ROOT
    / "data/collections/mar-built-registration-2026/grafton-marshall-built-plans-2022.pdf"
)
SOURCE_SHA = "d675da320087039168890f7afbf055490f9c8e4530f59921e9e5e53f6fc8bc47"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads((ROOT / path).read_text())


def write(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def inspect():
    import bpy

    sys.path.insert(0, str(ROOT / "web/tools"))
    from integrate_exterior_round194 import object_fingerprint, update_scene
    from refine_portsmouth_exterior207 import material_fingerprint

    spec = importlib.util.spec_from_file_location(
        "mar283_snapshot_helpers", ROOT / "web/tests/inspect_mar_shafts273.py"
    )
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    assert sha(BASE) == SHA and sha(SOURCE) == SOURCE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    p = read("result/blender/mar273/plan.json")
    points = [v for row in p["envelopes"] for v in row["outer"]]
    roi = [
        min(v[0] for v in points) - 1.0,
        min(v[1] for v in points) - 1.0,
        0.0,
        max(v[0] for v in points) + 1.0,
        max(v[1] for v in points) + 1.0,
        13.0,
    ]
    selected = set(bpy.data.collections[OWNER].all_objects) | set(
        bpy.data.collections["MAR_EXTERIOR"].all_objects
    )
    targets = []
    inventory = []
    deps = bpy.context.evaluated_depsgraph_get()
    for obj in sorted(selected, key=lambda o: o.name):
        if obj.type != "MESH" or obj.hide_render or not obj.data.vertices:
            continue
        xyz = [obj.matrix_world @ v.co for v in obj.data.vertices]
        bounds = [[min(p[i] for p in xyz), max(p[i] for p in xyz)] for i in range(3)]
        if bounds[2][0] > 13:
            continue
        inventory.append(
            {
                "name": obj.name,
                "bounds": bounds,
                "materials": [m.name if m else None for m in obj.data.materials],
                "faces": len(obj.data.polygons),
                "fingerprint": object_fingerprint(obj),
            }
        )
        if helpers.outside(xyz, roi):
            continue
        if not obj.modifiers:
            targets.append(helpers.target_snapshot(obj))
        evaluated = obj.evaluated_get(deps)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        triangles = []
        for tri in mesh.loop_triangles:
            pts = [evaluated.matrix_world @ mesh.vertices[i].co for i in tri.vertices]
            if not helpers.outside(pts, roi):
                triangles.append(
                    {
                        "points": [list(p) for p in pts],
                        "materialIndex": tri.material_index,
                    }
                )
        evaluated.to_mesh_clear()
        inventory[-1]["roiTriangles"] = triangles
    glass_names = [
        "MAR217_ground_glass_panes",
        "MAR217_revolving_drum_side_glass",
        "MAR217_revolving_door_leaves",
    ]
    glass = [helpers.target_snapshot(bpy.data.objects[name]) for name in glass_names]
    materials = {m for r in targets + glass for m in r["materials"] if m}
    result = {
        "baselineSha256": SHA,
        "readOnly": True,
        "nativeSaved": False,
        "objectCount": len(bpy.data.objects),
        "materialCount": len(bpy.data.materials),
        "roiXYZ": roi,
        "targets": targets,
        "inventory": inventory,
        "entryGlass": glass,
        "entryGlassShaders": {
            n: {
                "diffuseColor": list(bpy.data.materials[n].diffuse_color),
                "nodes": [
                    {
                        "type": node.type,
                        "inputs": {
                            sock.name: (
                                list(sock.default_value)
                                if hasattr(sock.default_value, "__len__")
                                else sock.default_value
                            )
                            for sock in node.inputs
                            if hasattr(sock, "default_value")
                            and sock.type in ["VALUE", "RGBA", "VECTOR"]
                        },
                    }
                    for node in bpy.data.materials[n].node_tree.nodes
                ],
                "surfaceRenderMethod": getattr(
                    bpy.data.materials[n], "surface_render_method", None
                ),
            }
            for n in {m for row in glass for m in row["materials"] if m}
        },
        "materialGraphs": {
            n: material_fingerprint(bpy.data.materials[n]) for n in materials
        },
        "limits": "Actual279meshes; all Zdatums are inherited estimates. Ground drawing does not authorize whole-height shafts.",
    }
    write(OUT / "native-inspection.json", result)
    assert sha(BASE) == SHA
    print("MAR283_READ_ONLY_INSPECTED", len(targets), len(inventory), flush=True)


def main(stage="inspect"):
    return globals()[stage]()


GROUND_WALL_FILLS = ["curve-43007", "curve-43009", "curve-43015", "curve-43017"]
GROUND_DOORS = [
    (
        "west-upper-stair-side",
        [
            [158.4539, 535.0477],
            [159.5289, 535.1067],
            [159.6692, 539.5933],
            [158.4572, 539.5923],
        ],
    ),
    (
        "west-upper-corridor-side",
        [
            [166.5389, 535.0497],
            [167.6859, 535.0247],
            [167.7412, 539.6683],
            [166.5232, 539.5883],
        ],
    ),
    (
        "west-lower-corridor-side",
        [
            [166.5252, 545.2513],
            [167.6862, 545.1933],
            [167.6992, 549.9333],
            [166.5282, 549.7953],
        ],
    ),
    (
        "east-upper-corridor-side",
        [
            [176.9053, 534.9823],
            [178.0483, 535.0513],
            [178.0036, 539.7096],
            [176.8996, 539.6766],
        ],
    ),
    (
        "east-lower-transverse-corridor-side",
        [
            [176.8916, 544.8246],
            [178.0386, 544.9326],
            [178.0146, 550.2996],
            [176.8896, 550.2726],
        ],
    ),
]


def source_geometry():
    """Ground cut-wall fills are CMYKdark fills; car outlines stay excluded."""
    import numpy as np
    from shapely import set_precision
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    sys.path.insert(0, str(ROOT / "web/tools"))
    from refine_mar273 import parts, record_shape

    rows = read("result/blender/mar283/source-ground-fills.json")
    retained = [r for r in rows if r["id"] in GROUND_WALL_FILLS]
    assert len(retained) == 4 and all(
        r["fill"] and r["color"] == [0.745, 0.652, 0.622, 0.814] for r in retained
    )
    # 43017is both filled and stroked. The0.199ptoutline is part of the
    # published cut profile: omitting it creates a narrow acute air wedge where
    # its sloped end meets43015. Include only this explicitly painted outline;
    # the other fill-only paths are never inflated by their inactive linewidth.
    source_profiles = []
    for row in retained:
        profile = Polygon(row["pts"]).buffer(0)
        if row["stroke"]:
            assert row["linewidth"] == 0.199 and row["strokingColor"] == row["color"]
            profile = profile.buffer(row["linewidth"] / 2, join_style=2)
        source_profiles.append(set_precision(profile, 0.0001))
    lower_pdf = unary_union(source_profiles)
    full_pdf = unary_union(
        [lower_pdf] + [set_precision(Polygon(p), 0.0001) for _, p in GROUND_DOORS]
    )
    assert sorted(len(p.interiors) for p in parts(full_pdf)) == [2, 2]
    prior = read("result/blender/mar-registration217/audit.json")
    ground_fit = prior["coreRegistration"]["groundPdfToSecondPdf"]
    registration = prior["geographicRegistration"]
    place = registration["secondPdfToNativeLocalCandidate"]
    angle = math.radians(registration["nativeBasisDegrees"])
    basis = np.array(
        [[math.cos(angle), math.sin(angle)], [-math.sin(angle), math.cos(angle)]]
    )

    def world(points):
        second = ground_fit["scale"] * np.asarray(points) @ np.asarray(
            ground_fit["rotation"]
        ) + np.asarray(ground_fit["translation"])
        local = place["scale"] * second[:, ::-1] @ np.asarray(
            place["rotation"]
        ) + np.asarray(place["translation"])
        return np.asarray(registration["nativeOrigin"]) + local @ basis

    def mapped(shape):
        return unary_union(
            [
                Polygon(
                    world(p.exterior.coords), [world(r.coords) for r in p.interiors]
                )
                for p in parts(shape)
            ]
        )

    lower, full = mapped(lower_pdf), mapped(full_pdf)
    holes = [Polygon(r) for p in parts(full) for r in p.interiors]
    upper = read("result/blender/mar273/plan.json")["registration"]["shafts"]
    classified = []
    for row in upper:
        reference = Polygon(row["secondInner"])
        candidate = min(holes, key=lambda h: h.centroid.distance(reference.centroid))
        classified.append(
            {
                "id": row["id"],
                "groundInner": list(candidate.exterior.coords)[:-1],
                "groundAreaM2": candidate.area,
                "secondInner": row["secondInner"],
                "maximumBoundaryDifferenceM": candidate.hausdorff_distance(reference),
                "axisOffsetM": candidate.centroid.distance(reference.centroid),
            }
        )
    assert len({tuple(map(tuple, r["groundInner"])) for r in classified}) == 4
    updated_bound = (
        prior["coreRegistration"]["heldOutMaximumMetres"]
        * place["scale"]
        / (5 / (84 * 595.276 / 2970))
    )
    evidence = {
        "sourcePath": str(SOURCE.relative_to(ROOT)),
        "sourceSha256": SOURCE_SHA,
        "page": 1,
        "sourcePeriod": "2022architect-authored built publication;not a2026survey",
        "identifiedFloor": "Ground",
        "sourceFills": retained,
        "extraction": "Four dark-CMYKcut-wall paths;43017includes its explicit0.199ptstroke. Other inactive linewidths,lift-car outlines,furniture and columns are excluded.",
        "sourceStrokePolicy": "Painted PDFcut profile,not measured wall dimensions. The43017half-stroke is0.0995pt;it closes a printing-scale acute wedge at its43015joint.",
        "groundSourceLower": record_shape(lower),
        "groundSourceFull": record_shape(full),
        "sourceDoors": [
            {"id": name, "pdf": points, "world": world(points).tolist()}
            for name, points in GROUND_DOORS
        ],
        "shaftCount": 4,
        "shafts": classified,
        "coreRegistration": prior["coreRegistration"],
        "currentNativeScaleHeldOutMaximumM": updated_bound,
        "higherShaftPolicy": "Ground wall outlines remain separate fromSecond/Third. No shared all-height cut mask and no unobservedFirst-floor door positions are inferred.",
        "heightPolicy": "All floor/ceiling Zdatums and2.1mdoor heads are inherited or display estimates,not measured elevations.",
    }
    return evidence, lower, full


def island_targets(target):
    """Preserve independent native boxes instead of welding coincident caps."""
    adjacency = {i: set() for i in range(len(target["verticesWorld"]))}
    for face in target["faces"]:
        for index in face["vertices"]:
            adjacency[index].update(face["vertices"])
    remaining = set(adjacency)
    groups = []
    while remaining:
        pending = [min(remaining)]
        found = set()
        while pending:
            index = pending.pop()
            if index in found:
                continue
            found.add(index)
            pending.extend(adjacency[index] - found)
        remaining -= found
        faces = [f for f in target["faces"] if set(f["vertices"]) <= found]
        if faces:
            groups.append(
                {
                    **target,
                    "faces": faces,
                    "verticesWorld": target["verticesWorld"],
                    "_islandVertices": sorted(found),
                }
            )
    return groups


def independent_clipped_mesh(target, cut, replacement):
    """Clip one native solid island at a time; untouched faces/UVs remain exact."""
    sys.path.insert(0, str(ROOT / "web/tools"))
    from refine_mar273 import clipped_mesh, horizontal_footprint

    result = {
        "sourceObject": target["name"],
        "replacement": replacement,
        "sourceFingerprint": target["fingerprint"],
        "materials": target["materials"],
        "sourceZ": [
            min(p[2] for p in target["verticesWorld"]),
            max(p[2] for p in target["verticesWorld"]),
        ],
        "faceRecords": [],
        "touchedSourceFaces": [],
        "expectedRemovedVolumeM3": 0.0,
        "expectedTopAreaRemovedM2": 0.0,
        "independentSolidIslands": 0,
    }
    for number, island in enumerate(island_targets(target)):
        points = [island["verticesWorld"][i] for i in island["_islandVertices"]]
        low, high = min(p[2] for p in points), max(p[2] for p in points)
        island["verticesWorld"] = [
            p if i in island["_islandVertices"] else [p[0], p[1], low]
            for i, p in enumerate(island["verticesWorld"])
        ]
        footprint = horizontal_footprint(island, high)
        overlap = footprint.intersection(cut).area
        if overlap < 1e-10:
            records = [
                {
                    "sourceFace": f["index"],
                    "role": "retained-native-face",
                    "points": [target["verticesWorld"][i] for i in f["vertices"]],
                    "uvs": f["uvs"],
                    "materialIndex": f["materialIndex"],
                    "smooth": f["smooth"],
                }
                for f in island["faces"]
            ]
        elif footprint.difference(cut).area < 1e-10:
            records = []
            result["expectedRemovedVolumeM3"] += footprint.area * (high - low)
            result["touchedSourceFaces"].extend(f["index"] for f in island["faces"])
            if abs(high - result["sourceZ"][1]) < 1e-6:
                result["expectedTopAreaRemovedM2"] += footprint.area
        else:
            clipped = clipped_mesh(island, cut, replacement)
            records = clipped["faceRecords"]
            result["touchedSourceFaces"].extend(clipped["touchedSourceFaces"])
            result["expectedRemovedVolumeM3"] += clipped["expectedRemovedVolumeM3"]
            if abs(high - result["sourceZ"][1]) < 1e-6:
                result["expectedTopAreaRemovedM2"] += clipped[
                    "expectedTopAreaRemovedM2"
                ]
        if records:
            result["independentSolidIslands"] += 1
        for record in records:
            record["solidIsland"] = number
        result["faceRecords"].extend(records)
    return result


def source_thickness_probes(source_full, holes):
    """Expected normal intervals come from the painted source,not output mesh."""
    import numpy as np
    from shapely.geometry import LineString

    x0, y0, x1, y1 = source_full.bounds
    reach = math.hypot(x1 - x0, y1 - y0) + 0.1
    result = []
    for number, hole in enumerate(holes):
        ring = list(hole.exterior.coords)[:-1]
        signed = sum(
            a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1])
        )
        for edge, (a, b) in enumerate(zip(ring, ring[1:] + ring[:1])):
            tangent = np.asarray(b) - a
            if np.linalg.norm(tangent) < 0.05:
                continue
            tangent /= np.linalg.norm(tangent)
            outward = np.asarray([tangent[1], -tangent[0]]) * (1 if signed > 0 else -1)
            for fraction in [0.1, 0.5, 0.9]:
                xy = np.asarray(a) + fraction * (np.asarray(b) - a)
                origin = xy - outward * 0.01
                hit = LineString([origin, origin + outward * reach]).intersection(
                    source_full
                )
                parts = list(hit.geoms) if hasattr(hit, "geoms") else [hit]
                intervals = []
                for part in parts:
                    if part.geom_type == "LineString":
                        t = [
                            float((np.asarray(c) - origin) @ outward)
                            for c in part.coords
                        ]
                        intervals.append([min(t), max(t)])
                intervals.sort()
                assert intervals and 0.005 < intervals[0][0] < 0.015, (
                    number,
                    edge,
                    fraction,
                    intervals,
                )
                start, end = intervals[0]
                assert end - start > 0.2, (number, edge, fraction, end - start)
                result.append(
                    {
                        "shaftIndex": number,
                        "edge": edge,
                        "edgeFraction": fraction,
                        "originXY": origin.tolist(),
                        "outwardXY": outward.tolist(),
                        "sourceEntryDistanceM": start,
                        "sourceExitDistanceM": end,
                        "sourceThicknessM": end - start,
                    }
                )
    assert len(result) > 30
    return result


def close_legacy_soffit(target):
    """Supply missing outer edge faces between the two native soffit skins."""
    import collections

    xyz = target["verticesWorld"]
    low, high = min(p[2] for p in xyz), max(p[2] for p in xyz)
    count = collections.Counter()
    top_edges = []
    for face in target["faces"]:
        points = [tuple(xyz[i]) for i in face["vertices"]]
        if not all(abs(p[2] - high) < 1e-6 for p in points):
            continue
        for a, b in zip(points, points[1:] + points[:1]):
            count[tuple(sorted((a, b)))] += 1
            top_edges.append((a, b))
    lookup = {tuple(p): i for i, p in enumerate(xyz)}
    faces = list(target["faces"])
    for a, b in top_edges:
        if count[tuple(sorted((a, b)))] != 1:
            continue
        points = [(*a[:2], low), (*b[:2], low), b, a]
        vertices = [lookup[p] for p in points]
        length = math.dist(a, b)
        faces.append(
            {
                "index": len(faces),
                "vertices": vertices,
                "materialIndex": 0,
                "smooth": False,
                "uvs": {
                    name: [[0, 0], [length, 0], [length, high - low], [0, high - low]]
                    for name in target["faces"][0]["uvs"]
                },
            }
        )
    assert len(faces) > len(target["faces"])
    return {**target, "faces": faces}


def prepare():
    from shapely import set_precision
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    sys.path.insert(0, str(ROOT / "web/tools"))
    from refine_mar273 import horizontal_footprint, parts, record_shape, wall_mesh

    assert sha(BASE) == SHA and sha(SOURCE) == SOURCE_SHA
    native = read("result/blender/mar283/native-inspection.json")
    assert native["baselineSha256"] == SHA and native["readOnly"]
    targets = {r["name"]: r for r in native["targets"]}
    evidence, _source_lower, source_full = source_geometry()
    holes = [Polygon(r["groundInner"]) for r in evidence["shafts"]]
    cut = unary_union(holes).buffer(0.00003, join_style=2)
    core_domain = unary_union([Polygon(p.exterior) for p in parts(source_full)]).buffer(
        0.00003, join_style=2
    )
    names = ["MAR217_coordinated_acoustic_soffit", "MAR217_coordinated_mezzanine_slab"]
    assert all(n in targets for n in names)
    low = min(p[2] for p in targets["MAR_MAR_public_floor"]["verticesWorld"])
    top = min(p[2] for p in targets[names[0]]["verticesWorld"])
    rows = []
    for name in names:
        target = targets[name]
        replacement = name.replace("MAR217_", "MAR283_") + "_ground_lift_apertures"
        if name == "MAR217_coordinated_acoustic_soffit":
            from refine_mar273 import clipped_mesh

            virtual = close_legacy_soffit(target)
            row = clipped_mesh(virtual, cut, replacement)
            row["legacyOpenSoffitOriginalFaceCount"] = len(target["faces"])
            row["legacyAddedPerimeterFaces"] = len(virtual["faces"]) - len(
                target["faces"]
            )
            row["legacyClosedSourceVolumeM3"] = horizontal_footprint(
                target, row["sourceZ"][1]
            ).area * (row["sourceZ"][1] - row["sourceZ"][0])
            for record in row["faceRecords"]:
                if record["sourceFace"] is not None and record["sourceFace"] >= len(
                    target["faces"]
                ):
                    record["sourceFace"] = None
                    record["role"] = "legacy-soffit-outer-edge-closure"
            row["touchedSourceFaces"] = [
                i for i in row["touchedSourceFaces"] if i < len(target["faces"])
            ]
        else:
            row = independent_clipped_mesh(target, cut, replacement)
        row["destinationCollection"] = target["owners"][0]
        row["componentRole"] = "ground-ceiling-aperture"
        assert row["expectedRemovedVolumeM3"] > 0.05
        rows.append(row)
    for source_name, replacement, role in [
        (
            "MAR217_ground_service_enclosure",
            "MAR283_ground_service_enclosure_clear_of_lifts",
            "cleared-existing-service-wall",
        ),
        (
            "MAR217_ground_sills",
            "MAR283_ground_sills_clear_of_lifts",
            "cleared-existing-sill",
        ),
    ]:
        service = targets[source_name]
        row = independent_clipped_mesh(service, core_domain, replacement)
        row["componentRole"] = role
        row["destinationCollection"] = service["owners"][0]
        assert row["expectedRemovedVolumeM3"] > 0.01
        rows.append(row)
    floor = horizontal_footprint(targets["MAR_MAR_public_floor"], low)
    ceiling = horizontal_footprint(targets[names[0]], top).difference(cut)
    full = set_precision(
        source_full.intersection(floor)
        .intersection(ceiling)
        .buffer(-0.0001, join_style=2),
        0.00002,
    )
    assert sorted(len(p.interiors) for p in parts(full)) == [2, 2]
    source_doors = evidence["sourceDoors"]
    lower = set_precision(
        full.difference(
            unary_union(
                [Polygon(r["world"]).buffer(0.0002, join_style=2) for r in source_doors]
            )
        ),
        0.00002,
    )
    head = struct.unpack("f", struct.pack("f", low + 2.1))[0]
    wall_row = {
        "sourceObject": None,
        "sourceFingerprint": None,
        "replacement": "MAR283_ground_source_lift_core_walls",
        "sourceZ": [low, top],
        "componentRole": "source-ground-lift-wall",
        "destinationCollection": OWNER,
        "materials": ["MAR_D3_concrete"],
        "faceRecords": wall_mesh(lower, full, low, head, top, ["UVMap"]),
        "touchedSourceFaces": [],
    }
    rows.append(wall_row)
    for r in rows:
        assert all(m for m in r["materials"])
    evidence["groundWallBearingClippedAreaM2"] = source_full.area - full.area
    evidence["groundWallFullFootprint"] = record_shape(full)
    evidence["groundWallLowerFootprint"] = record_shape(lower)
    write(OUT / "source-evidence.json", evidence)
    plan = {
        "version": 283,
        "building": "MAR",
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": SHA,
        "targetCollection": OWNER,
        "objects": rows,
        "shaftCount": 4,
        "groundLow": low,
        "groundTop": top,
        "doorHead": head,
        "doors": source_doors,
        "holes": [list(p.exterior.coords)[:-1] for p in holes],
        "cutMasks": record_shape(cut),
        "serviceWallClearanceDomain": record_shape(core_domain),
        "sourceThicknessProbes": source_thickness_probes(source_full, holes),
        "sourceThicknessNumericToleranceM": 0.0005,
        "groundSourceFull": record_shape(source_full),
        "wallFull": record_shape(full),
        "wallLower": record_shape(lower),
        "scope": "Ground-only four-lift walls and five open doorway positions;local service-wall/sill clearance and immediately adjoining mezzanine slab/soffit apertures.",
        "heightPolicy": evidence["heightPolicy"],
        "fullHeightShaftAcceptance": False,
        "unmodifiedHigherPlate": "MAR_MAR_floor_way/1376078546_21.9",
        "entryGlassReview": {
            "sourcePhoto": "data/collections/architecture_round5/images/MAR/MAR_mar_kane_03.jpg",
            "sourcePhotoSha256": sha(
                ROOT
                / "data/collections/architecture_round5/images/MAR/MAR_mar_kane_03.jpg"
            ),
            "observation": "Photograph shows transparent curved entrance glazing; no new metric entrance geometry is inferred.",
            "currentShaders": native["entryGlassShaders"],
        },
        "sourceHashes": {
            p: sha(ROOT / p)
            for p in [
                "result/blender/mar283/native-inspection.json",
                "result/blender/mar283/source-ground-fills.json",
                "result/blender/mar283/source-evidence.json",
                "result/blender/mar-registration217/audit.json",
                "result/blender/mar273/plan.json",
                str(SOURCE.relative_to(ROOT)),
            ]
        },
        "newMaterials": 0,
        "candidateOnly": True,
        "wholeNativeSaved": False,
    }
    write(OUT / "plan.json", plan)
    print(
        "MAR283_PLAN_READY",
        [(r["replacement"], len(r["faceRecords"])) for r in rows],
        "groundHeight",
        [low, top],
        flush=True,
    )


def capture():
    sys.path.insert(0, str(ROOT / "web/tools"))
    from refine_mar273 import capture as base_capture

    result = base_capture()
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
    assert after["materials"] == before["materials"]
    assert (
        after["rooms"] == before["rooms"]
        and after["campusRooms"] == before["campusRooms"]
    )
    assert len(after["rooms"]) == 35 and sha(BASE) == SHA


def build_mesh(row):
    import bmesh
    import bpy

    mesh = bpy.data.meshes.new(row["replacement"] + "_mesh")
    vertices, faces, lookup = [], [], {}
    for record in row["faceRecords"]:
        face = []
        for point in record["points"]:
            point = tuple(struct.unpack("fff", struct.pack("fff", *point)))
            key = (record.get("solidIsland", 0), point)
            if key not in lookup:
                lookup[key] = len(vertices)
                vertices.append(point)
            face.append(lookup[key])
        assert len(face) >= 3 and len(set(face)) == len(face)
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
    assert all(e.is_manifold for e in bm.edges), row["replacement"]
    assert bm.calc_volume(signed=True) > 0
    bm.free()
    obj = bpy.data.objects.new(row["replacement"], mesh)
    obj.use_fake_user = True
    if row["sourceObject"]:
        source = bpy.data.objects[row["sourceObject"]]
        for key, value in source.items():
            obj[key] = value
    obj["originalObject"] = row["sourceObject"] or ""
    obj["destinationCollection"] = row["destinationCollection"]
    obj["sourceScope"] = (
        "Ground-only lift-core display estimate;no full-height shaft or unobservedFirst-floor doors"
    )
    obj["publicInteriorComponent"] = row["destinationCollection"] == OWNER
    bpy.data.collections[row["destinationCollection"]].objects.link(obj)
    return obj


def build():
    import bpy

    sys.path.insert(0, str(ROOT / "web/tools"))
    from integrate_exterior_round194 import object_fingerprint, update_scene
    from refine_portsmouth_exterior207 import material_fingerprint

    plan = read("result/blender/mar283/plan.json")
    assert sha(BASE) == SHA == plan["baselineSha256"]
    assert all(sha(ROOT / p) == h for p, h in plan["sourceHashes"].items())
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = capture()
    objects = []
    for row in plan["objects"]:
        if row["sourceObject"]:
            original = bpy.data.objects[row["sourceObject"]]
            assert (
                not original.hide_render
                and object_fingerprint(original) == row["sourceFingerprint"]
            )
        objects.append(build_mesh(row))
    update_scene()
    protection(before, [o.name for o in objects])
    component = OUT / "component.blend"
    audit = {
        "version": 283,
        "building": "MAR",
        "status": "ground-component-awaiting-verification",
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": SHA,
        "componentPath": str(component.relative_to(ROOT)),
        "targetCollection": OWNER,
        "addedObjects": [o.name for o in objects],
        "archivedObjects": [
            r["sourceObject"] for r in plan["objects"] if r["sourceObject"]
        ],
        "changedObjects": [],
        "objectOwners": {o.name: o["destinationCollection"] for o in objects},
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
        "sourcePlan": "result/blender/mar283/plan.json",
        "sourcePlanSha256": sha(OUT / "plan.json"),
        "sourceEvidence": "result/blender/mar283/source-evidence.json",
        "sourceHashes": {
            **plan["sourceHashes"],
            "result/blender/mar283/plan.json": sha(OUT / "plan.json"),
        },
        "originalObjectCount": len(before["objects"]),
        "originalMaterialCount": len(before["materials"]),
        "retainedHigherPlateFingerprint": object_fingerprint(
            bpy.data.objects[plan["unmodifiedHigherPlate"]]
        ),
        "shaftCount": 4,
        "fullHeightShaftAcceptance": False,
        "scope": plan["scope"],
        "limitations": [
            plan["heightPolicy"],
            "Ground plan and inherited ceiling assembly only; noFirst-floor room/door plan is available.",
            "Ground retains its independently identified painted-source outlines;no common all-height mask is inferred.",
            "Ground base floor stays intact;no basement opening or completed all-height lift is claimed.",
        ],
        "candidateOnly": True,
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
    spec = importlib.util.spec_from_file_location(
        "mar283_verifier", ROOT / "web/tests/verify_mar283.py"
    )
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    verifier.apply_component(audit)
    proof = verifier.geometry_proof(audit)
    audit["status"] = "passed-builder-roundtrip-ground-lift-component"
    audit["verification"] = proof
    audit["authoringScriptSha256"] = sha(Path(__file__))
    audit["verificationScriptSha256"] = sha(ROOT / "web/tests/verify_mar283.py")
    write(OUT / "audit.json", audit)
    print("MAR283_COMPONENT_READY", audit["componentSha256"], flush=True)


if __name__ == "__main__":
    main()
