"""Independently verify the complete campus and its curved CLM inscription.

Run in Blender's editor. This checks every original object, surface normal,
material graph, modifier, owner and room, then ray-tests the replacement against
its actual supporting stone mesh. Fixed project paths; no command-line options.
"""

import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
import itertools

from integrate_exterior_round194 import (
    object_fingerprint,
    update_scene,
)
from refine_kgs_surface237 import normal_record
from refine_ksw_exterior219 import modifier_state
from refine_portsmouth_exterior207 import material_fingerprint

OUT = ROOT / "result/blender/stage241"
BASE = ROOT / "result/blender/LSE_campus_detailed_v239.blend"
FINAL = ROOT / "result/blender/LSE_campus_detailed_v241.blend"
BASE_SHA = "07fae16d2afbe82fed9352b5dbf2fd8df05e809158de72541b09c7b32328403c"
SOURCE = "CLM_D3_street_inscription"
REPLACEMENT = "CLM241_curved_street_inscription"
SUPPORT = "CLM196_FINISH_CLM_D3_main_colonnade_entablature"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture_source():
    metadata = json.loads((ROOT / "web/tools/building-metadata.json").read_text())
    campus = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    return {
        "baselineSha256": BASE_SHA,
        "objects": {
            o.name: {
                "fingerprint": object_fingerprint(o),
                "normals": normal_record(o.data) if o.type == "MESH" else None,
                "owners": sorted(c.name for c in o.users_collection),
                "properties": repr(sorted(o.items())),
                "modifiers": json.loads(json.dumps(modifier_state(o))),
                "hidden": o.hide_render,
            }
            for o in bpy.data.objects
        },
        "materials": {m.name: material_fingerprint(m) for m in bpy.data.materials},
        "rooms": {
            r["collection"]: sorted(
                o.name for o in bpy.data.collections[r["collection"]].all_objects
            )
            for r in metadata["spaces"]
        },
        "campusRooms": {
            r["collection"]: sorted(
                o.name
                for o in bpy.data.collections[r["collection"]].all_objects
                if o.name in campus.objects
            )
            for r in metadata["spaces"]
        },
    }


def support_tree():
    evaluated = bpy.data.objects[SUPPORT].evaluated_get(
        bpy.context.evaluated_depsgraph_get()
    )
    mesh = evaluated.to_mesh()
    tree = BVHTree.FromPolygons(
        [evaluated.matrix_world @ v.co for v in mesh.vertices],
        [tuple(p.vertices) for p in mesh.polygons],
    )
    evaluated.to_mesh_clear()
    return tree


def verify_contact(obj):
    """Test vertices and face centres, not only the builder's registration path."""
    tree = support_tree()
    sites = json.loads((ROOT / "result/blender/site_geometry.json").read_text())
    building = next(b for b in sites["buildings"] if b["code"] == "CLM")
    ring = building["rings"][0]
    points = [Vector(ring[i]) for i in (5, 4, 3, 2, 1)]
    segments = [(a, b, (b - a).normalized()) for a, b in itertools.pairwise(points)]
    coordinates = [obj.matrix_world @ v.co for v in obj.data.vertices]
    coordinates += [obj.matrix_world @ p.center for p in obj.data.polygons]
    distances = []
    nearest_distances = []
    for point in coordinates:
        choices = []
        for a, b, tangent in segments:
            projection = a + tangent * max(
                0, min((point.xy - a).dot(tangent), (b - a).length)
            )
            choices.append(
                (
                    (point.xy - projection).length_squared,
                    Vector((tangent.y, -tangent.x, 0)),
                )
            )
        normal = min(choices, key=lambda row: row[0])[1]
        hit, _, _, distance = tree.ray_cast(point + normal, -normal, 2)
        assert hit is not None, tuple(point)
        distances.append(distance - 1)
        nearest, face_normal, _, nearest_distance = tree.find_nearest(point)
        assert nearest is not None and (point - nearest).dot(face_normal) > 0
        nearest_distances.append(nearest_distance)
    assert min(distances) >= 0.0008, min(distances)
    # At a miter the baseline segment normal can differ from the closest face.
    # Bound the physical Euclidean gap separately from its oblique ray length.
    assert max(distances) <= 0.014, max(distances)
    assert min(nearest_distances) >= 0.0008, min(nearest_distances)
    assert max(nearest_distances) <= 0.01305, max(nearest_distances)
    return {
        "samples": len(distances),
        "minimumClearance": min(distances),
        "maximumClearance": max(nearest_distances),
        "maximumObliqueRayDistance": max(distances),
    }


def main():
    protected = json.loads((OUT / "protected-source-state.json").read_text())
    record = json.loads((OUT / "building-refinement.json").read_text())
    audit = json.loads(
        (ROOT / "result/blender/clm-inscription241/audit.json").read_text()
    )
    assert protected["baselineSha256"] == record["baselineSha256"] == BASE_SHA
    assert sha(FINAL) == record["sourceModelSha256"]
    assert sha(ROOT / audit["componentPath"]) == audit["componentSha256"]
    bpy.ops.wm.open_mainfile(filepath=str(FINAL))
    update_scene()
    assert set(bpy.data.objects.keys()) == set(protected["objects"]) | {REPLACEMENT}
    assert record["archivedObjects"] == [SOURCE] and record["addedObjects"] == [
        REPLACEMENT
    ]
    assert record["changedObjects"] == []
    current = capture_source()
    for name, expected in protected["objects"].items():
        observed = current["objects"][name]
        expected = dict(expected)
        if name == SOURCE:
            expected["hidden"] = True
        assert observed == expected, name
    assert all(
        current["materials"][name] == value
        for name, value in protected["materials"].items()
    )
    assert current["rooms"] == protected["rooms"] and len(current["rooms"]) == 35
    assert current["campusRooms"] == protected["campusRooms"]
    obj = bpy.data.objects[REPLACEMENT]
    assert not obj.hide_render and not obj.modifiers and obj.type == "MESH"
    assert (
        obj["originalObject"] == SOURCE
        and obj["body"] == bpy.data.objects[SOURCE].data.body
    )
    assert object_fingerprint(obj) == audit["addedFingerprints"][REPLACEMENT]
    assert normal_record(obj.data) == audit["replacementNormals"][REPLACEMENT]
    assert [m.name for m in obj.data.materials] == audit["replacementMaterialBindings"][
        REPLACEMENT
    ]
    assert (
        sorted(c.name for c in obj.users_collection)
        == protected["objects"][SOURCE]["owners"]
    )
    contact = verify_contact(obj)
    result = {
        "completeNativeReopened": True,
        "originalObjectsVerified": len(protected["objects"]),
        "originalMaterialGraphsVerified": len(protected["materials"]),
        "protectedRooms": 35,
        "protectedRoomMembers": sum(map(len, protected["rooms"].values())),
        "originalGeometryNormalsUVsModifiersAndOwnersPreserved": True,
        "contact": contact,
        "sourceModelSha256": sha(FINAL),
    }
    (OUT / "native-verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print("CAMPUS241_VERIFIED", result["originalObjectsVerified"], contact, flush=True)


if __name__ == "__main__":
    main()
