"""Reopen PEL canopy material correction and ray-test the actual physical lower face."""

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import (
    object_fingerprint,
    set_layer_hidden,
    update_scene,
)
from refine_col_finish252 import sha
from refine_pel_exterior257 import (
    BASE,
    COLLECTION,
    OUT,
    REPLACEMENT,
    SHA,
    SOURCE,
    YELLOW,
    capture,
    check_protection,
    lower_face,
    verify_geometry,
    write,
)


def main():
    record = json.loads((OUT / "audit.json").read_text())
    protected = json.loads((OUT / "protected-source-state.json").read_text())
    component = ROOT / record["componentPath"]
    assert sha(BASE) == SHA == record["baselineSha256"]
    assert sha(component) == record["componentSha256"]
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    assert capture() == protected
    source = bpy.data.objects[SOURCE]
    index, selection = lower_face(source)
    assert selection == record["worldFaceSelection"]
    with bpy.data.libraries.load(str(component), link=False) as (_, loaded):
        loaded.objects = [REPLACEMENT]
    obj = loaded.objects[0]
    assert obj.name == REPLACEMENT
    bpy.data.collections[COLLECTION].objects.link(obj)
    for slot, name in enumerate(record["replacementMaterialBindings"][REPLACEMENT]):
        obj.data.materials[slot] = bpy.data.materials[name]
    obj.hide_render = False
    set_layer_hidden(obj, False)
    source.hide_render = True
    set_layer_hidden(source, True)
    update_scene()
    assert object_fingerprint(obj) == record["addedFingerprints"][REPLACEMENT]
    verify_geometry(source, obj, index)
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    vertices = [evaluated.matrix_world @ v.co for v in mesh.vertices]
    triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
    materials = [
        mesh.materials[mesh.polygons[t.polygon_index].material_index].name
        for t in mesh.loop_triangles
    ]
    tree = BVHTree.FromPolygons(vertices, triangles, all_triangles=True)
    rays = []
    for probe in record["faceProbes"]:
        hit, normal, triangle, distance = tree.ray_cast(
            Vector(probe["origin"]), Vector(probe["direction"]), 0.2
        )
        assert hit is not None and abs(distance - 0.1) < 2e-5
        assert materials[triangle] == YELLOW
        assert abs(normal.z) > 0.999999
        rays.append(
            {
                "origin": probe["origin"],
                "direction": probe["direction"],
                "distance": distance,
                "material": materials[triangle],
                "storedNormal": list(normal),
            }
        )
    evaluated.to_mesh_clear()
    assert len(rays) == 2
    check_protection(protected, capture())
    assert len(bpy.data.objects) == len(protected["objects"]) + 1
    assert sha(BASE) == SHA
    write(
        "verification.json",
        {
            "passed": True,
            "componentSha256": sha(component),
            "protectedOriginalObjects": len(protected["objects"]),
            "protectedOriginalMaterials": len(protected["materials"]),
            "protectedRoomStudies": len(protected["rooms"]),
            "sourceGeometryUVNormalsExact": True,
            "onlyPhysicalLowerFaceReassigned": True,
            "remainingFiveFacesDark": True,
            "actualEvaluatedTriangleRays": rays,
            "newMaterials": 0,
            "newTriangles": 0,
            "actualProductionRenderRequired": True,
        },
    )
    print("PEL257_INDEPENDENT_UNDERSIDE_VERIFICATION_PASSED", flush=True)


if __name__ == "__main__":
    main()
