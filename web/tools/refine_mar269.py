"""Cut only three source-proven Second-floor lift bores through MAR's223stack.

Fixed263baseline and separate component. main('prepare') runs in MachineLearning;
main('build') runs in Blender. No command-line options,shared metadata or native
save. Source masks come from Second-floor opaque-fill boundaries,not Level03.
"""

import collections
import hashlib
import importlib.util
import json
import math
import struct
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
STAGE = "build"
BASE = ROOT / "result/blender/LSE_campus_detailed_v263.blend"
SHA = "f55f5975ea5e4d755f0c883bc64965b928a3d03add666c598a9b7e987bb70c2d"
OUT = ROOT / "result/blender/mar269"
EVIDENCE = ROOT / "result/blender/mar269-evidence.json"
INSPECTION = OUT / "native-second-inspection.json"
OWNER = "MAR_PUBLIC_INTERIOR_study"
NAMES = {
    "MAR223_second_structural_slab": "MAR269_second_structural_slab_with_source_shafts",
    "MAR223_second_floor_finish": "MAR269_second_floor_finish_with_source_shafts",
    "MAR223_second_soffit": "MAR269_second_soffit_with_source_shafts",
}


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def f32(point):
    return tuple(struct.unpack("fff", struct.pack("fff", *point)))


def face_area(points):
    a, b, c = points[:3]
    return abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) / 2


def prepare():
    from shapely import constrained_delaunay_triangles
    from shapely.geometry import LineString, Point, Polygon
    from shapely.ops import unary_union

    evidence = json.loads(EVIDENCE.read_text())
    native = json.loads(INSPECTION.read_text())
    assert native["baselineSha256"] == evidence["baseline"]["sha256"] == SHA
    holes = evidence["confirmedGap"]["newSecondSourceShafts"]
    masks = [Polygon(r["cutWorldXY"]) for r in holes]
    cut = unary_union(masks)
    assert len(masks) == 3 and cut.geom_type == "MultiPolygon"
    plans = []
    for target in native["targets"]:
        assert target["name"] in NAMES and target["owners"] == [OWNER]
        assert target["matrixWorld"] == [
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ]
        source = target["verticesLocal"]
        low, high = min(p[2] for p in source), max(p[2] for p in source)
        records = []
        touched = []
        for face in target["faces"]:
            points = [source[i] for i in face["vertices"]]
            flat = max(p[2] for p in points) - min(p[2] for p in points) < 1e-7
            shape = Polygon([p[:2] for p in points]) if flat else None
            overlap = shape.intersection(cut).area if flat else 0
            if overlap < 1e-9:
                records.append(
                    {
                        "sourceFace": face["index"],
                        "points": points,
                        "uvs": face["uvs"],
                        "materialIndex": face["materialIndex"],
                        "smooth": face["smooth"],
                        "role": "retained-native-face",
                    }
                )
                continue
            assert len(points) == 3
            touched.append(face["index"])
            remaining = shape.difference(cut)
            sign = (points[1][0] - points[0][0]) * (points[2][1] - points[0][1]) - (
                points[1][1] - points[0][1]
            ) * (points[2][0] - points[0][0])
            for tri in constrained_delaunay_triangles(remaining).geoms:
                xy = list(tri.exterior.coords)[:3]
                triangle_sign = (xy[1][0] - xy[0][0]) * (xy[2][1] - xy[0][1]) - (
                    xy[1][1] - xy[0][1]
                ) * (xy[2][0] - xy[0][0])
                if sign * triangle_sign < 0:
                    xy.reverse()
                new = [f32((*p, points[0][2])) for p in xy]
                assert face_area(new) > 1e-9, (
                    target["name"],
                    "Float32collapsed triangle",
                )
                uvs = {}
                for layer, values in face["uvs"].items():
                    result = []
                    a, b, c = points
                    det = (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])
                    for p in new:
                        wb = (
                            (p[0] - a[0]) * (c[1] - a[1])
                            - (c[0] - a[0]) * (p[1] - a[1])
                        ) / det
                        wc = (
                            (b[0] - a[0]) * (p[1] - a[1])
                            - (p[0] - a[0]) * (b[1] - a[1])
                        ) / det
                        result.append(
                            [
                                sum(
                                    w * v[j]
                                    for w, v in zip(
                                        [1 - wb - wc, wb, wc], values, strict=False
                                    )
                                )
                                for j in range(2)
                            ]
                        )
                    uvs[layer] = result
                records.append(
                    {
                        "sourceFace": face["index"],
                        "points": new,
                        "uvs": uvs,
                        "materialIndex": face["materialIndex"],
                        "smooth": face["smooth"],
                        "role": "source-face-cut",
                    }
                )
        # Discover new inner vertical faces from the actual Float32top boundary.
        # Splits made by original native triangle edges are retained on the bore.
        edge_counts = collections.Counter()
        top_edges = []
        for face in records:
            p = [f32(v) for v in face["points"]]
            if not all(abs(v[2] - high) < 1e-7 for v in p):
                continue
            for a, b in zip(p, p[1:] + p[:1], strict=False):
                edge_counts[tuple(sorted((a, b)))] += 1
                top_edges.append((a, b))
        boundary = []
        for a, b in top_edges:
            if edge_counts[tuple(sorted((a, b)))] != 1:
                continue
            segment = LineString([a[:2], b[:2]])
            if cut.boundary.distance(
                segment.interpolate(0.5, normalized=True)
            ) < 0.00005 and all(
                cut.boundary.distance(Point(p[:2])) < 0.00005 for p in [a, b]
            ):
                boundary.append((a, b))
        following = dict(boundary)
        assert len(following) == len(boundary) and set(following) == set(
            following.values()
        )
        unseen = set(following)
        loops = []
        while unseen:
            first = min(unseen)
            current = first
            loop = []
            while current in unseen:
                unseen.remove(current)
                loop.append(current)
                current = following[current]
            assert current == first
            loops.append(loop)
        assert len(loops) == 3
        for a, b in boundary:
            points = [a, (*a[:2], low), (*b[:2], low), b]
            records.append(
                {
                    "sourceFace": None,
                    "points": points,
                    "uvs": {
                        n: [
                            [0, high - low],
                            [0, 0],
                            [math.dist(a, b), 0],
                            [math.dist(a, b), high - low],
                        ]
                        for n in target["faces"][0]["uvs"]
                    },
                    "materialIndex": 0,
                    "smooth": False,
                    "role": "new-source-shaft-edge",
                }
            )
        edges = collections.Counter()
        for row in records:
            points = [f32(p) for p in row["points"]]
            assert len(set(points)) == len(points)
            for a, b in zip(points, points[1:] + points[:1], strict=False):
                edges[tuple(sorted((a, b)))] += 1
        assert set(edges.values()) == {2}, (
            target["name"],
            collections.Counter(edges.values()),
        )
        top = unary_union(
            [
                Polygon([p[:2] for p in r["points"]])
                for r in records
                if all(abs(p[2] - high) < 1e-7 for p in r["points"])
            ]
        )
        original = unary_union(
            [
                Polygon([source[i][:2] for i in f["vertices"]])
                for f in target["faces"]
                if all(abs(source[i][2] - high) < 1e-7 for i in f["vertices"])
            ]
        )
        error = top.symmetric_difference(original.difference(cut)).area
        assert error < 0.0002
        plans.append(
            {
                "sourceObject": target["name"],
                "sourceFingerprint": target["fingerprint"],
                "replacement": NAMES[target["name"]],
                "materials": target["materials"],
                "sourceZ": [low, high],
                "faceRecords": records,
                "touchedSourceFaces": touched,
                "newInnerBoundaryLoops": loops,
                "areaDifferenceM2": original.area - top.area,
                "planarCoverageErrorM2": error,
            }
        )
    OUT.mkdir(parents=True, exist_ok=True)
    plan = {
        "version": 269,
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": SHA,
        "sourceFloor": "Second floor",
        "sourcePage": 1,
        "holes": holes,
        "objects": plans,
        "sourceHashes": {
            str(p.relative_to(ROOT)): sha(p)
            for p in [
                EVIDENCE,
                INSPECTION,
                ROOT
                / "data/collections/mar-built-registration-2026/grafton-marshall-built-plans-2022.pdf",
            ]
        },
        "noThirdFloorPolygonsUsed": True,
        "newMaterials": 0,
    }
    write(OUT / "plan.json", plan)
    print(
        "MAR269_SOURCE_PLAN_READY",
        [
            (p["replacement"], len(p["faceRecords"]), p["areaDifferenceM2"])
            for p in plans
        ],
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
    assert after["materials"] == before["materials"]
    assert after["rooms"] == before["rooms"] and len(after["rooms"]) == 35
    assert after["campusRooms"] == before["campusRooms"]
    assert sha(BASE) == SHA


def build_mesh(row, source):
    import bmesh
    import bpy

    mesh = bpy.data.meshes.new(row["replacement"] + "_mesh")
    points = []
    faces = []
    lookup = {}
    for face in row["faceRecords"]:
        indices = []
        for point in face["points"]:
            key = f32(point)
            if key not in lookup:
                lookup[key] = len(points)
                points.append(key)
            indices.append(lookup[key])
        faces.append(indices)
    mesh.from_pydata(points, [], faces)
    for mat in source.data.materials:
        mesh.materials.append(mat)
    for face, record in zip(mesh.polygons, row["faceRecords"], strict=False):
        face.material_index = record["materialIndex"]
        face.use_smooth = record["smooth"]
    for name in (layer.name for layer in source.data.uv_layers):
        layer = mesh.uv_layers.new(name=name)
        for face, record in zip(mesh.polygons, row["faceRecords"], strict=False):
            for index, value in zip(
                face.loop_indices, record["uvs"][name], strict=False
            ):
                layer.data[index].uv = value
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    assert all(e.is_manifold for e in bm.edges)
    assert bm.calc_volume(signed=True) > 0
    bm.free()
    obj = source.copy()
    obj.data = mesh
    obj.name = row["replacement"]
    obj.use_fake_user = True
    obj["originalObject"] = source.name
    obj["destinationCollection"] = OWNER
    obj["publicInteriorComponent"] = True
    obj["sourceScope"] = (
        "Three lift bores from the2022Second-floor plan; all vertical datums retained"
    )
    bpy.data.collections[OWNER].objects.link(obj)
    return obj


def build():
    import bpy

    sys.path.insert(0, str(ROOT / "web/tools"))
    from integrate_exterior_round194 import (
        object_fingerprint,
        set_layer_hidden,
        update_scene,
    )
    from refine_portsmouth_exterior207 import material_fingerprint

    plan = json.loads((OUT / "plan.json").read_text())
    assert plan["baselineSha256"] == SHA == sha(BASE)
    assert all(sha(ROOT / p) == h for p, h in plan["sourceHashes"].items())
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = capture()
    assert (
        len(before["objects"]) == 8748
        and len(before["materials"]) == 2355
        and len(before["rooms"]) == 35
    )
    write(OUT / "protected-source-state.json", before)
    objects = []
    for row in plan["objects"]:
        source = bpy.data.objects[row["sourceObject"]]
        assert (
            not source.hide_render
            and object_fingerprint(source) == row["sourceFingerprint"]
        )
        obj = build_mesh(row, source)
        objects.append(obj)
    update_scene()
    protection(before, [o.name for o in objects])
    component = OUT / "component.blend"
    audit = {
        "version": 269,
        "building": "MAR",
        "status": "candidate-only-second-floor-bores",
        "candidateOnly": True,
        "fullHeightShaftAcceptance": False,
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": SHA,
        "componentPath": str(component.relative_to(ROOT)),
        "destinationCollection": OWNER,
        "targetCollection": OWNER,
        "addedObjects": [o.name for o in objects],
        "archivedObjects": list(NAMES),
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
        "addedMaterialFingerprints": {},
        "sourcePlan": "result/blender/mar269/plan.json",
        "sourcePlanSha256": sha(OUT / "plan.json"),
        "sourceEvidence": "result/blender/mar269-evidence.json",
        "sourceHashes": plan["sourceHashes"],
        "scope": "Three source-proven Second-floor lift bores through the existing structural,finish and soffit layers only. No new core walls,other floor changes or complete shaft claim.",
        "limitations": [
            "Source2022architect plans are not a2026survey.",
            "Existing12.455\u201312.8mstack and all storey heights remain inherited estimates.",
            "Only the floor bores are corrected; second-storey walls,lift equipment and higher shaft continuity are not reconstructed.",
        ],
        "noFullNativeSaved": True,
    }
    bpy.data.libraries.write(str(component), set(objects), fake_user=False)
    audit["componentSha256"] = sha(component)
    bpy.ops.wm.open_mainfile(filepath=str(component))
    assert set(bpy.data.objects.keys()) == set(audit["addedObjects"])
    assert all(
        object_fingerprint(bpy.data.objects[n]) == v
        for n, v in audit["addedFingerprints"].items()
    )
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    with bpy.data.libraries.load(str(component), link=False) as (_, destination):
        destination.objects = list(audit["addedObjects"])
    for obj in destination.objects:
        for index, name in enumerate(audit["replacementMaterialBindings"][obj.name]):
            obj.data.materials[index] = bpy.data.materials[name]
        bpy.data.collections[OWNER].objects.link(obj)
        obj.hide_render = False
        set_layer_hidden(obj, False)
    for material in list(bpy.data.materials):
        if material.name not in before["materials"]:
            assert material.users == 0
            bpy.data.materials.remove(material)
    for name in audit["archivedObjects"]:
        bpy.data.objects[name].hide_render = True
        set_layer_hidden(bpy.data.objects[name], True)
    update_scene()
    protection(before, audit["addedObjects"], audit["archivedObjects"])
    path = ROOT / "web/tests/verify_mar269.py"
    spec = importlib.util.spec_from_file_location("mar269_independent", path)
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    proof = verifier.geometry_proof(audit)
    audit["verification"] = proof
    audit["authoringScriptSha256"] = sha(Path(__file__))
    audit["verificationScriptSha256"] = sha(path)
    write(OUT / "audit.json", audit)
    write(
        OUT / "verification.json",
        {
            "status": "passed-builder-roundtrip",
            "freshBlenderProcess": False,
            "componentSha256": audit["componentSha256"],
            "actualMeshProof": proof,
            "originalObjectsProtected": 8748,
            "originalMaterialGraphsProtected": 2355,
            "roomMembershipsProtected": 35,
            "noFullNativeSaved": True,
        },
    )
    print("MAR269_COMPONENT_READY", audit["componentSha256"], flush=True)


def main(stage=STAGE):
    if stage == "prepare":
        prepare()
    elif stage == "build":
        build()
    else:
        raise ValueError("Stage must be prepare or build")


if __name__ == "__main__":
    main()
