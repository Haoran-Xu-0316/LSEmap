"""Independently verify the saved LRB258source-calibrated frontage component.

proof_geometry(audit) checks the currently loaded scene without reopening it.
main() appends the component to257and also proves full original-scene protection.
"""

import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/lrb258"
BASE = ROOT / "result/blender/LSE_campus_detailed_v257.blend"
SHA = "5f73b29480de08425d4d8ab3c39aa1e2b9231656f81f1f763ee1ffa200568db9"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
import itertools

from integrate_exterior_round194 import (
    object_fingerprint,
    set_layer_hidden,
    update_scene,
)
from public_interior_objects import public_interior_objects


def capture():
    spec = importlib.util.spec_from_file_location(
        "lrb258_verify_protection", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = SHA
    return helper.capture_source()


def area(points):
    if len(points) < 3:
        return 0.0
    return sum(
        (points[i] - points[0]).cross(points[i + 1] - points[0]).length / 2
        for i in range(1, len(points) - 1)
    )


def face_records(obj):
    rows = []
    for face in obj.data.polygons:
        points = [obj.matrix_world @ obj.data.vertices[i].co for i in face.vertices]
        uv = [
            [tuple(layer.data[li].uv) for li in face.loop_indices]
            for layer in obj.data.uv_layers
        ]
        rows.append((points, uv, face.material_index))
    return rows


def match_face(a, b):
    pa, ua, ma = a
    pb, ub, mb = b
    if ma != mb or len(pa) != len(pb) or len(ua) != len(ub):
        return False
    # Copies preserve original loop order, even though world-space coordinates
    # require one normal float32serialization on mesh creation.
    return all((x - y).length < 2e-5 for x, y in zip(pa, pb)) and all(
        abs(x - y) < 1e-7
        for la, lb in zip(ua, ub)
        for va, vb in zip(la, lb)
        for x, y in zip(va, vb)
    )


def proof_geometry(audit):
    assert audit["baselineSha256"] == SHA
    assert audit["geometryBudget"]["newMaterials"] == 0
    assert (
        audit["sourceRegistration"]["gisLength"] > 68
        and len(audit["sourceRegistration"]["gisPolyline"]) == 4
    )
    for name in audit["addedObjects"]:
        obj = bpy.data.objects[name]
        assert (
            not obj.hide_render
            and object_fingerprint(obj) == audit["addedFingerprints"][name]
        ), name
    split = audit["sharedRoofBatchSplit"]
    actual_faces = Counter()
    for name in split["sourceObjects"] + split["sharedObjects"]:
        obj = bpy.data.objects[name]
        for face in obj.data.polygons:
            points = [
                list(obj.matrix_world @ obj.data.vertices[i].co) for i in face.vertices
            ]
            uv = [
                {
                    "name": layer.name,
                    "uv": [list(layer.data[i].uv) for i in face.loop_indices],
                }
                for layer in obj.data.uv_layers
            ]
            material = obj.data.materials[face.material_index].name
            signature = hashlib.sha256(
                json.dumps(
                    [points, uv, material, list(face.normal)], separators=(",", ":")
                ).encode()
            ).hexdigest()
            actual_faces[signature] += 1
    assert dict(actual_faces) == split["actualFaceMultiset"], (
        "Roof-only rebatching changed a real face position, UV, material or winding"
    )
    catalogue = json.loads((ROOT / "web/public/models/catalogue.json").read_text())
    record = next(r for r in catalogue["buildings"] if r["code"] == "LRB")
    public = {obj.name for obj in public_interior_objects(record)}
    shared = set(split["sharedObjects"]) | {
        "LRB258_source_SW_roof",
        audit["lowerRoof"]["replacement"],
    }
    assert shared <= public
    assert all(
        bpy.data.objects[name].get("sharedInteriorRoof")
        and not bpy.data.objects[name].hide_render
        for name in shared
    )
    assert not (set(split["sourceObjects"]) & public), (
        "Ordinary southwest facade leaked into the public roof export"
    )
    plan = audit["sourceRegistration"]
    chain = [Vector(p) for p in plan["gisPolyline"]]
    prefix = plan["gisStations"]

    def local(p):
        candidates = []
        for i, (a, b) in enumerate(itertools.pairwise(chain)):
            u = (b - a).normalized()
            n = Vector((u.y, -u.x, 0))
            d = max(0.0, min((p - a).dot(u), (b - a).length))
            q = a + u * d
            candidates.append(((p.xy - q.xy).length, prefix[i] + d, (p - q).dot(n)))
        _, s, d = min(candidates)
        return s, d, p.z

    source_length = sum((b - a).length for a, b in itertools.pairwise(chain))
    assert abs(source_length - 68.09920987927293) < 2e-5
    # Independent hard controls: source-wide fitting, rather than the previous
    # wrong historical-window centre or the old ten-column repeated proxy.
    scale = source_length / (1954.199 - 46.56)
    station = lambda x: (x - 46.56) * scale
    expected = [
        ("Library_lower_glazed_divisions", 294.48, 444.359),
        ("modern_1_ground_window", 490.32, 662.16),
        ("modern_6_ground_window", 1578.84, 1748.76),
    ]
    windows = {r["name"]: r for r in audit["windows"]}
    for name, left, right in expected:
        row = windows[name]
        assert (
            abs(row["a"] - station(left)) < 1e-7
            and abs(row["b"] - station(right)) < 1e-7
        )
    entry = windows["Library_lower_glazed_divisions"]
    transom = windows["Library_upper_three_by_two"]
    assert (
        entry["columns"] == 5
        and entry["rows"] == 1
        and abs(entry["bottom"] - 0.3319997787475586) < 1e-7
    )
    assert (
        transom["columns"] == 3
        and transom["rows"] == 2
        and transom["columnFractions"] == [0.4, 0.6]
    )
    assert abs((entry["a"] + entry["b"]) / 2 - 11.5254913807157) < 1e-6
    assert 5.34 < entry["b"] - entry["a"] < 5.36
    assert sum(r["name"].startswith("historic_dormer_") for r in audit["windows"]) == 4
    assert (
        sum(
            r["name"].startswith("modern_") and r["name"].endswith("_ground_window")
            for r in audit["windows"]
        )
        == 6
    )
    historic = [r for r in audit["windows"] if r["kind"] == "historic_upper"]
    assert len(historic) == 18
    for r in historic:
        assert r["columns"] == 4 and r["rows"] == (6 if "_upper_1_" in r["name"] else 4)
    for r in audit["windows"]:
        if r["name"].startswith("modern_") and r["name"].endswith("_upper_1"):
            assert [len(v) for v in r["perColumnRowFractions"]] == [1, 2, 1]
            assert len(r["glassFaceIndices"]) == 7
    for row in audit["windows"]:
        obj = bpy.data.objects[row["glassObject"]]
        assert row["glassFaceIndices"]
        seen = []
        for index in row["glassFaceIndices"]:
            face = obj.data.polygons[index]
            world_normal = (obj.matrix_world.to_3x3() @ face.normal).normalized()
            segment = max(
                range(3),
                key=lambda i: world_normal.dot(
                    Vector(
                        (
                            (chain[i + 1] - chain[i]).normalized().y,
                            -(chain[i + 1] - chain[i]).normalized().x,
                            0,
                        )
                    )
                ),
            )
            tangent = (chain[segment + 1] - chain[segment]).normalized()
            outward = Vector((tangent.y, -tangent.x, 0))
            for vi in face.vertices:
                point = obj.matrix_world @ obj.data.vertices[vi].co
                delta = point - chain[segment]
                s, d, z = (
                    prefix[segment] + delta.dot(tangent),
                    delta.dot(outward),
                    point.z,
                )
                seen.append((s, d, z))
                assert row["a"] + 0.023 < s < row["b"] - 0.023, (row["name"], s)
                assert row["bottom"] + 0.020 < z < row["top"] - 0.020, (row["name"], z)
                assert abs(d - row["glassDepth"]) < 3e-5, (
                    row["name"],
                    d,
                )
        assert abs(min(p[0] for p in seen) - (row["a"] + 0.025)) < 3e-5
        assert abs(max(p[0] for p in seen) - (row["b"] - 0.025)) < 3e-5
    # Retained parts in multi-side batches have exact original vertices, faces,
    # material indices and UVs after source-index remapping.
    retained_count = 0
    for row in audit["retainedFacadeParts"]:
        original = bpy.data.objects[row["source"]]
        removed = set(row["removedSourceVertexIndices"])
        retained = row["retainedSourceVertexIndices"]
        assert removed.isdisjoint(retained) and removed | set(retained) == set(
            range(len(original.data.vertices))
        )
        if not retained:
            assert row["replacement"] is None
            continue
        copy = bpy.data.objects[row["replacement"]]
        assert len(copy.data.vertices) == len(retained)
        for vertex, index in zip(copy.data.vertices, retained):
            assert vertex.co == original.data.vertices[index].co
        old_faces = [
            f for f in original.data.polygons if not (set(f.vertices) & removed)
        ]
        assert len(copy.data.polygons) == len(old_faces)
        mapping = {old: new for new, old in enumerate(retained)}
        for old, new in zip(old_faces, copy.data.polygons):
            assert (
                tuple(new.vertices) == tuple(mapping[v] for v in old.vertices)
                and new.material_index == old.material_index
            )
            for old_layer, new_layer in zip(
                original.data.uv_layers, copy.data.uv_layers
            ):
                for a, b in zip(old.loop_indices, new.loop_indices):
                    assert old_layer.data[a].uv == new_layer.data[b].uv
        retained_count += len(retained)
    oldroof = bpy.data.objects[audit["lowerRoof"]["source"]]
    newroof = bpy.data.objects[audit["lowerRoof"]["replacement"]]
    old_records = face_records(oldroof)
    new_records = face_records(newroof)
    unchanged = [
        r for r in old_records if not all(abs(p.z - 20.24) < 0.002 for p in r[0])
    ]
    for record in unchanged:
        assert any(match_face(record, candidate) for candidate in new_records), (
            "Nonlower roof face changed"
        )
    old_area = sum(
        area(r[0]) for r in old_records if all(abs(p.z - 20.24) < 0.002 for p in r[0])
    )
    new_area = sum(
        area(r[0]) for r in new_records if all(abs(p.z - 20.24) < 0.002 for p in r[0])
    )
    cut_area = sum(
        area([Vector(p) for p in row["points"]])
        for row in audit["lowerRoof"]["sourceCutPolygons"]
    )
    assert cut_area > 100 and abs(old_area - new_area - cut_area) < 0.01, (
        old_area,
        new_area,
        cut_area,
    )
    assert audit["lowerRoof"]["estimatedReturnDepth"] == 2.5
    # Each replacement roof-plane rear edge is at the actual retained20.24m
    # plane; the original lower strip cannot remain floating over the slope.
    roof = bpy.data.objects["LRB258_source_SW_roof"]
    back = [
        v.co
        for v in roof.data.vertices
        if abs(local(v.co)[1] + 2.5) < 3e-5 and abs(v.co.z - 20.24) < 3e-5
    ]
    assert len(back) >= 8
    # Verify true triangle probes against real visible exterior geometry. This
    # catches residual legacy panes/masonry and wrong opaque overlays.
    trees = []
    for obj in bpy.data.collections["LRB_EXTERIOR"].all_objects:
        if obj.type not in {"MESH", "FONT"} or obj.hide_render:
            continue
        data = obj.to_mesh() if obj.type == "FONT" else obj.data
        trees.append(
            (
                obj,
                BVHTree.FromPolygons(
                    [obj.matrix_world @ v.co for v in data.vertices],
                    [tuple(f.vertices) for f in data.polygons],
                    all_triangles=False,
                ),
            )
        )
        if obj.type == "FONT":
            obj.to_mesh_clear()
    label_record = audit["labelProof"]
    label = bpy.data.objects[label_record["object"]]
    evaluated = label.to_mesh()
    label_points = [label.matrix_world @ v.co for v in evaluated.vertices]
    bounds = [
        [min(p[i] for p in label_points), max(p[i] for p in label_points)]
        for i in range(3)
    ]
    for actual, recorded in zip(bounds, label_record["actualWorldBounds"]):
        assert max(abs(a - b) for a, b in zip(actual, recorded)) < 2e-5
    low, high = label_record["allowedZBounds"]
    assert low - 2e-5 <= bounds[2][0] < bounds[2][1] <= high + 2e-5
    label_hits = []
    for record in label_record["probes"]:
        point = sum((label_points[i] for i in record["triangle"]), Vector()) / 3
        assert (point - Vector(record["point"])).length < 2e-5
        normal = Vector(record["normal"])
        hits = []
        for obj, tree in trees:
            hit = tree.ray_cast(point + normal * 0.15, -normal, 0.2)
            if hit[0] is not None:
                hits.append((hit[3], obj))
        distance, first = min(hits, key=lambda r: r[0])
        assert first == label and abs(distance - 0.15) < 2e-5, (
            "Library lettering occluded",
            first.name,
            distance,
        )
        label_hits.append({"object": first.name, "distance": distance})
    label.to_mesh_clear()
    rooflights = audit["sourceRooflights"]
    assert len(rooflights) == 3
    assert all(r["sourceSlopePageYBounds"] == [659.801, 715.0] for r in rooflights)
    assert all(
        r["estimatedVisibleSlopeDepth"] == 2.25
        and r["estimatedHiddenReturnDepth"] == 0.25
        for r in rooflights
    )
    for record in rooflights:
        assert len(record["sourcePageCorners"]) == 4
        assert min(p[1] for p in record["sourcePageCorners"]) == 672.52
        assert max(p[1] for p in record["sourcePageCorners"]) == 702.52
        obj = bpy.data.objects[record["glassObject"]]
        face = obj.data.polygons[record["glassFaceIndices"][0]]
        assert (obj.matrix_world.to_3x3() @ face.normal).z > 0
    hit_rows = []
    for row in audit["glassTriangleProbes"]:
        obj = bpy.data.objects[row["object"]]
        indices = row["triangle"]
        center = (
            sum((obj.matrix_world @ obj.data.vertices[i].co for i in indices), Vector())
            / 3
        )
        assert (center - Vector(row["point"])).length < 2e-5
        normal = Vector(row["normal"])
        origin = center + normal * 1.0
        hits = []
        for other, tree in trees:
            hit = tree.ray_cast(origin, -normal, 1.05)
            if hit[0] is not None:
                hits.append((hit[3], other, hit))
        assert hits, (row["window"], "no hit")
        distance, actual, hit = min(hits, key=lambda h: h[0])
        assert actual == obj and abs(distance - 1.0) < 3e-5, (
            row["window"],
            actual.name,
            distance,
        )
        assert (
            actual.data.materials[actual.data.polygons[hit[2]].material_index].name
            == row["expectedMaterial"]
        )
        if row["window"].startswith("low_wing_rooflight_"):
            backing = []
            for other, tree in trees:
                hidden = tree.ray_cast(center - normal * 0.001, -normal, 0.04)
                if hidden[0] is not None:
                    backing.append((other.name, hidden[3]))
            assert not backing, (
                "Rooflight has an opaque backing instead of a true roof opening",
                row["window"],
                backing,
            )
        hit_rows.append(
            {
                "window": row["window"],
                "actualObject": actual.name,
                "actualMaterial": row["expectedMaterial"],
                "distance": distance,
            }
        )
    return {
        "passed": True,
        "sourceRegisteredWindows": len(windows),
        "realVisibleWindowProbes": hit_rows,
        "sourceRooflights": len(rooflights),
        "rooflightRealOpeningsVerifiedFromGlassBack": True,
        "publicRoofSharedObjects": sorted(shared),
        "roofOnlyRebatchFacesExact": sum(actual_faces.values()),
        "LibraryLetteringActualFirstSurfaceHits": label_hits,
        "retainedOtherFacadeVertices": retained_count,
        "lowerRoofOriginalArea": old_area,
        "lowerRoofRetainedArea": new_area,
        "lowerRoofCutArea": cut_area,
        "protectedNonlowerRoofFaces": len(unchanged),
        "upperRoofAndDomePreserved": True,
        "widthAndFloorProof": {
            "entryWidth": entry["b"] - entry["a"],
            "entryFFL": entry["bottom"],
            "fiveLowerDivisions": True,
            "threeByTwoUpperLights": True,
        },
    }


def main():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == SHA
    audit = json.loads((OUT / "audit.json").read_text())
    component = ROOT / audit["componentPath"]
    assert (
        hashlib.sha256(component.read_bytes()).hexdigest() == audit["componentSha256"]
    )
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = capture()
    with bpy.data.libraries.load(str(component), link=False) as (_source, target):
        target.objects = list(audit["addedObjects"])
    for obj in target.objects:
        bpy.data.collections["LRB_EXTERIOR"].objects.link(obj)
        bindings = audit["replacementMaterialBindings"][obj.name]
        assert len(obj.data.materials) == len(bindings)
        for index, name in enumerate(bindings):
            obj.data.materials[index] = bpy.data.materials[name]
        for field, name in (
            audit.get("replacementFontBindings", {}).get(obj.name, {}).items()
        ):
            setattr(obj.data, field, bpy.data.fonts[name])
        obj.hide_render = False
        set_layer_hidden(obj, False)
    for name in audit["archivedObjects"]:
        obj = bpy.data.objects[name]
        obj.hide_render = True
        set_layer_hidden(obj, True)
    update_scene()
    proof = proof_geometry(audit)
    after = capture()
    for name, row in before["objects"].items():
        expected = dict(row)
        if name in audit["archivedObjects"]:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
    assert all(after["materials"][n] == v for n, v in before["materials"].items())
    assert (
        before["rooms"] == after["rooms"]
        and before["campusRooms"] == after["campusRooms"]
        and len(before["rooms"]) == 35
    )
    proof["all35RoomsAndOriginalSceneProtected"] = True
    (OUT / "verification.json").write_text(json.dumps(proof, indent=2) + "\n")
    print(
        "LRB258_INDEPENDENT_VERIFIED", len(audit["addedObjects"]), "objects", flush=True
    )


if __name__ == "__main__":
    main()
