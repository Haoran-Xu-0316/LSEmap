"""Verify public-basement export ownership without changing native LRBgeometry.

Uses the actual production AST functions. Overview/detail exterior derivatives
must excludeLG, while fallback/detail interiors retain the authoredLGlevels.
Run in Blender via the parent's serial validation process; no model is saved.
"""

import ast
import hashlib
import importlib.util
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v258.blend"
SHA = "46a6d58baf708af45c8a8669f85fa6b24efdbfb1d3721cd4aca315e85ba0d835"
OUT = ROOT / "result/blender/lrb259"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import update_scene


def capture():
    spec = importlib.util.spec_from_file_location(
        "lrb259_source_protection", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = SHA
    return helper.capture_source()


def horizontal_carpet_levels(objects):
    result = defaultdict(lambda: {"area": 0.0, "points": []})
    for obj in objects:
        obj.data.calc_loop_triangles()
        for triangle in obj.data.loop_triangles:
            material = obj.data.materials[
                obj.data.polygons[triangle.polygon_index].material_index
            ]
            if not material.name.endswith("ATRIA_blue_carpet"):
                continue
            points = [
                obj.matrix_world @ obj.data.vertices[i].co for i in triangle.vertices
            ]
            if max(p.z for p in points) - min(p.z for p in points) > 1e-5:
                continue
            level = round(sum(p.z for p in points) / 3, 5)
            result[level]["area"] += (points[1] - points[0]).cross(
                points[2] - points[0]
            ).length / 2
            result[level]["points"].extend(points)
    return {
        level: {
            "area": row["area"],
            "bounds": [
                [min(p[i] for p in row["points"]), max(p[i] for p in row["points"])]
                for i in range(3)
            ],
        }
        for level, row in result.items()
    }


def assert_same_levels(expected, actual):
    assert set(expected) == set(actual), (set(expected), set(actual))
    for level, source in expected.items():
        target = actual[level]
        assert abs(source["area"] - target["area"]) < 0.002, (
            level,
            source["area"],
            target["area"],
        )
        assert (
            max(
                abs(a - b)
                for x, y in zip(source["bounds"], target["bounds"])
                for a, b in zip(x, y)
            )
            < 2e-5
        ), level


def main():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = capture()
    records = json.loads((ROOT / "web/tools/building-metadata.json").read_text())[
        "buildings"
    ]
    record = next(r for r in records if r["code"] == "LRB")
    code = record["code"]
    public = bpy.data.collections[
        record.get("interiorCollection", code + "_PUBLIC_INTERIOR_study")
    ]
    source_objects = [
        o
        for o in public.all_objects
        if o.type == "MESH"
        and not o.hide_render
        and ("carpet" in o.name.lower() or "floor_slabs" in o.name.lower())
    ]
    assert source_objects and any(o.name.startswith("LRB168__") for o in source_objects)
    expected = horizontal_carpet_levels(source_objects)
    assert any(level < -3.6 for level in expected) and any(
        0.33 < level < 0.34 for level in expected
    )
    path = ROOT / "web/tools/export_scene.py"
    parsed = ast.parse(path.read_text())
    names = {
        "source_geometry_name",
        "surface_descriptor",
        "web_material",
        "clip_below_ground",
        "is_public_interior_object",
        "clone_group",
    }
    functions = [
        node
        for node in parsed.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    assert len(functions) == len(names)
    ns = {
        "bpy": bpy,
        "bmesh": bmesh,
        "Vector": Vector,
        "re": re,
        "records": records,
        "depsgraph": bpy.context.evaluated_depsgraph_get(),
        "material_cache": {},
        "full_detail": False,
    }
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), "exec"), ns)  # noqa:S102 - exact trusted production functions
    assert all(ns["is_public_interior_object"](o) for o in source_objects)
    # Semantic ownership also survives a new collection name without editing
    # a version-specific string or adding it to the authored records.
    role = bpy.data.collections.new("LRB259_TEST_PUBLIC_ROLE")
    role["publicInteriorStudy"] = True
    fixture = bpy.data.objects.new("LRB259_TEST_ROLE_OWNER", None)
    role.objects.link(fixture)
    assert ns["is_public_interior_object"](fixture)
    bpy.data.objects.remove(fixture, do_unlink=True)
    bpy.data.collections.remove(role)
    jobs = [
        ("overview-exterior", False, True),
        ("detailed-exterior", True, True),
        ("fallback-interior", False, False),
        ("detailed-interior", True, False),
    ]
    results = []
    for label, detail, hide in jobs:
        ns["full_detail"] = detail
        scene = bpy.data.scenes.new("LRB259_TEST_" + label)
        obj, _ = ns["clone_group"](
            source_objects, "LRB259_" + label, scene, hide_basement=hide
        )
        assert obj is not None
        actual = horizontal_carpet_levels([obj])
        required = (
            {level: row for level, row in expected.items() if level >= 0}
            if hide
            else expected
        )
        assert_same_levels(required, actual)
        minimum = min((obj.matrix_world @ v.co).z for v in obj.data.vertices)
        if hide:
            assert minimum >= -1e-5 and all(level >= 0 for level in actual)
        else:
            assert minimum < -3.9 and any(level < -3.6 for level in actual)
        results.append(
            {
                "mode": label,
                "clippedOnlyTemporaryDerivative": hide,
                "actualMinimumZ": minimum,
                "horizontalBlueCarpetLevels": actual,
                "allRetainedAboveGroundCarpetLevelsExact": True,
            }
        )
        mesh = obj.data
        bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.meshes.remove(mesh)
        bpy.data.scenes.remove(scene)
    update_scene()
    after = capture()
    assert before["objects"] == after["objects"], (
        "A native object changed during temporary export"
    )
    assert all(
        after["materials"][name] == value for name, value in before["materials"].items()
    )
    assert (
        before["rooms"] == after["rooms"]
        and before["campusRooms"] == after["campusRooms"]
        and len(before["rooms"]) == 35
    )
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == SHA
    report = {
        "passed": True,
        "nativeBaselineSha256": SHA,
        "sourceObjectCount": len(before["objects"]),
        "sourceMaterialGraphs": len(before["materials"]),
        "nativeObjectsMaterialsAnd35RoomsUnchanged": True,
        "declaredPublicCollection": public.name,
        "semanticCollectionRoleVerified": True,
        "testedSourceObjects": [o.name for o in source_objects],
        "cases": results,
        "nativeComponentWritten": False,
        "finding": "The visible blue strip isLGcarpet atZ−3.668 beneath a transparent shadow receiver, not a carpet or slab outside theGISfootprint.",
    }
    (OUT / "export-policy-verification.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(
        "LRB259_EXPORT_POLICY_VERIFIED",
        len(results),
        "modes",
        len(source_objects),
        "source floor/carpet batches; native protected",
        flush=True,
    )


if __name__ == "__main__":
    main()
