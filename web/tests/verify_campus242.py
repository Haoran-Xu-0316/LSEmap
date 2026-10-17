"""Verify every original inside the independently reopened complete242 campus."""

import ast
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/stage242"
FINAL = ROOT / "result/blender/LSE_campus_detailed_v242.blend"
BASE_SHA = "3b49385387b8e5c53223a1151762b80b9b3e1e4c2bbfbd474dfa820af4e424b4"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint, update_scene
from refine_kgs_surface237 import normal_record


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    protected = read(OUT / "protected-source-state.json")
    record = read(OUT / "building-refinement.json")
    audit = read(ROOT / "result/blender/saw-circulation242/audit.json")
    proof = read(ROOT / "result/blender/saw-circulation242/saved-triangle-proof.json")
    assert protected["baselineSha256"] == record["baselineSha256"] == BASE_SHA
    assert sha(FINAL) == record["sourceModelSha256"]
    assert (
        sha(ROOT / audit["componentPath"])
        == audit["componentSha256"]
        == proof["componentSha256"]
    )
    assert (
        proof["status"] == "accepted-for-native-integration"
        and proof["conflictCount"] == proof["remainingLiftConflictCount"] == 0
    )
    assert all(row["checks"][0]["connected"] for row in proof["floorConnections"])
    assert (
        sha(ROOT / "result/blender/saw-circulation242/saved-triangle-proof.json")
        == audit["proof"]["sha256"]
    )
    bpy.ops.wm.open_mainfile(filepath=str(FINAL))
    update_scene()
    spec = importlib.util.spec_from_file_location(
        "capture_native_state", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = BASE_SHA
    current = helper.capture_source()
    assert set(current["objects"]) == set(protected["objects"]) | set(
        audit["addedObjects"]
    )
    assert (
        record["addedObjects"] == audit["addedObjects"]
        and record["archivedObjects"] == audit["archivedObjects"]
    )
    assert record["changedObjects"] == []
    for name, expected in protected["objects"].items():
        expected = dict(expected)
        if name in audit["archivedObjects"]:
            expected["hidden"] = True
        assert current["objects"][name] == expected, name
    assert all(
        current["materials"][name] == value
        for name, value in protected["materials"].items()
    )
    assert (
        current["rooms"] == protected["rooms"]
        and current["campusRooms"] == protected["campusRooms"]
    )
    assert len(current["rooms"]) == 35
    for name in audit["addedObjects"]:
        obj = bpy.data.objects[name]
        assert object_fingerprint(obj) == audit["addedFingerprints"][name]
        assert normal_record(obj.data) == audit["replacementNormals"][name]
        assert [m.name for m in obj.data.materials] == audit[
            "replacementMaterialBindings"
        ][name]
        assert (
            not obj.hide_render
            and obj.parent is None
            and not obj.constraints
            and not obj.modifiers
        )
        assert [c.name for c in obj.users_collection] == [
            audit["destinationCollection"]
        ]
    source = ast.parse((ROOT / "web/tools/export_scene.py").read_text())
    selector = next(
        node
        for node in source.body
        if isinstance(node, ast.FunctionDef) and node.name == "exterior_objects"
    )
    namespace = {"bpy": bpy}
    exec(  # noqa: S102 - evaluate only the named local production selector
        compile(
            ast.Module(body=[selector], type_ignores=[]),
            "production-exterior-selector",
            "exec",
        ),
        namespace,
    )
    metadata = read(ROOT / "web/tools/building-metadata.json")
    building = next(b for b in metadata["buildings"] if b["code"] == "SAW")
    exterior = {
        o.name for o in namespace["exterior_objects"](building) if not o.hide_render
    }
    public = {
        o.name
        for o in bpy.data.collections["SAW_PUBLIC_INTERIOR_study"].all_objects
        if not o.hide_render
    }
    assert (
        set(audit["addedObjects"]) <= exterior and set(audit["addedObjects"]) <= public
    )
    assert (
        not set(audit["archivedObjects"]) & exterior
        and not set(audit["archivedObjects"]) & public
    )
    reference = bpy.data.objects[
        "SAW233_Flight2_continuous_waists_treads_flat_platform"
    ]
    display = []
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            if reference.name in layer.objects and reference.visible_get(
                view_layer=layer
            ):
                assert all(
                    name in layer.objects
                    and bpy.data.objects[name].visible_get(view_layer=layer)
                    for name in audit["addedObjects"]
                )
                display.append({"scene": scene.name, "viewLayer": layer.name})
    assert display
    result = {
        "completeNativeReopened": True,
        "sourceModelSha256": sha(FINAL),
        "originalObjectsVerified": len(protected["objects"]),
        "originalMaterialGraphsVerified": len(protected["materials"]),
        "protectedRooms": 35,
        "protectedRoomMembers": sum(map(len, protected["rooms"].values())),
        "allOriginalGeometryNormalsUVsModifiersPropertiesAndOwnersPreserved": True,
        "addedObjectsVerified": len(audit["addedObjects"]),
        "sameObjectsInOverviewExteriorAndPublicInterior": True,
        "nativeDisplayRoutes": display,
        "headroomConflicts": 0,
        "liftVoidConflicts": 0,
        "floorConnections": [
            {k: v for k, v in row.items() if k != "actualFullHeightClearRegion"}
            for row in proof["floorConnections"]
        ],
    }
    (OUT / "native-verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        "CAMPUS242_VERIFIED",
        result["originalObjectsVerified"],
        len(audit["addedObjects"]),
        flush=True,
    )


if __name__ == "__main__":
    main()
