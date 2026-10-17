"""Build a source-constrained private SAW upper-circulation component.

Open in Blender's editor after the fixed MachineLearning planning scripts.
The accepted campus stays read-only. Archive only named superseded upper stair
and floor batches; keep source geometry and every detached room study intact.
A saved-mesh clearance proof is still required before full-campus integration.
"""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import bmesh
import bpy

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v241.blend"
BASE_SHA = "3b49385387b8e5c53223a1151762b80b9b3e1e4c2bbfbd474dfa820af4e424b4"
OUT = ROOT / "result/blender/saw-circulation242"
PROOF = ROOT / "result/blender/stage242"
COLLECTION = "SAW_STRUCTURE173_registered_main_circulation"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import (
    accepted_fingerprints,
    object_fingerprint,
    update_scene,
)
from refine_kgs_surface237 import normal_record


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert sha(BASE) == BASE_SHA
    data = json.loads((OUT / "geometry-plan.json").read_text())
    assert data["baselineSha256"] == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    assert {
        o.name: object_fingerprint(o) for o in bpy.data.objects
    } == accepted_fingerprints(ROOT / "result/blender/stage241", BASE_SHA)
    PROOF.mkdir(parents=True, exist_ok=True)
    snapshot = PROOF / "protected-source-state.json"
    if snapshot.exists():
        assert json.loads(snapshot.read_text())["baselineSha256"] == BASE_SHA
    else:
        spec = importlib.util.spec_from_file_location(
            "capture_native_state", ROOT / "web/tests/verify_campus241.py"
        )
        verifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(verifier)
        verifier.BASE_SHA = BASE_SHA
        snapshot.write_text(json.dumps(verifier.capture_source(), indent=2) + "\n")
    print("SAW242_SOURCE_PROTECTED", len(bpy.data.objects), flush=True)
    objects = []
    retention = []
    solids = []
    for row in data["objects"]:
        source = bpy.data.objects[row["source"]]
        if "retainedSourceFaces" in row:
            selected = [source.data.polygons[i] for i in row["retainedSourceFaces"]]
            ids = sorted({i for face in selected for i in face.vertices})
            lookup = {old: new for new, old in enumerate(ids)}
            vertices = [tuple(source.data.vertices[i].co) for i in ids]
            faces = [tuple(lookup[i] for i in face.vertices) for face in selected]
        else:
            vertices = row["vertices"]
            faces = row["faces"]
        mesh = bpy.data.meshes.new(row["name"])
        mesh.from_pydata(vertices, [], faces)
        for material in source.data.materials:
            mesh.materials.append(material)
        mesh.update()
        obj = bpy.data.objects.new(row["name"], mesh)
        bpy.data.collections[COLLECTION].objects.link(obj)
        if "retainedSourceFaces" in row:
            obj.matrix_world = source.matrix_world.copy()
            for face, original in zip(mesh.polygons, selected, strict=True):
                face.material_index = original.material_index
                face.use_smooth = original.use_smooth
            for layer in source.data.uv_layers:
                target = mesh.uv_layers.new(name=layer.name)
                values = [
                    tuple(layer.data[i].uv)
                    for face in selected
                    for i in face.loop_indices
                ]
                for loop, value in zip(target.data, values, strict=True):
                    loop.uv = value
            retention.append(
                {
                    "source": source.name,
                    "replacement": obj.name,
                    "sourceFaces": row["retainedSourceFaces"],
                    "coordinatesUVsAndMaterialIndicesCopied": True,
                }
            )
        else:
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
            if "continuous_winding_waist" in obj.name:
                manifold = all(edge.is_manifold for edge in bm.edges)
                volume = bm.calc_volume(signed=True)
                assert manifold and volume > 0, (obj.name, manifold, volume)
                solids.append(
                    {
                        "object": obj.name,
                        "closedManifold": True,
                        "positiveVolumeM3": volume,
                    }
                )
            bm.to_mesh(mesh)
            bm.free()
            if "Coordinated_floor" in obj.name:
                for face in mesh.polygons:
                    if face.normal.z < 0:
                        face.flip()
            uv = mesh.uv_layers.new(name="MetricUV")
            for loop in mesh.loops:
                point = mesh.vertices[loop.vertex_index].co
                uv.data[loop.index].uv = (point.x, point.y)
        obj["originalObject"] = source.name
        obj["destinationCollection"] = COLLECTION
        obj["sourceGuideYear"] = 2014
        obj["evidenceStatus"] = (
            "Estimated separate inner/outer winding routes in vector-extracted uncoloured historical circulation; not surveyed construction or2026current layout"
        )
        objects.append(obj)
    update_scene()
    component = OUT / "component.blend"
    bpy.data.libraries.write(
        str(component), set(objects), fake_user=True, compress=True
    )
    record = {
        "version": 242,
        "code": "SAW",
        "baselineSha256": BASE_SHA,
        "componentPath": str(component.relative_to(ROOT)),
        "componentSha256": sha(component),
        "destinationCollection": COLLECTION,
        "targetCollection": COLLECTION,
        "addedObjects": [o.name for o in objects],
        "archivedObjects": data["archivedObjects"],
        "addedFingerprints": {o.name: object_fingerprint(o) for o in objects},
        "replacementNormals": {o.name: normal_record(o.data) for o in objects},
        "replacementMaterialBindings": {
            o.name: [m.name for m in o.data.materials] for o in objects
        },
        "retention": retention,
        "solids": solids,
        "geometryPlanSha256": sha(OUT / "geometry-plan.json"),
        "scope": "Private estimated three-to-four and four-to-five winding stair assemblies, supported outboard guards and local coordinated floors. Pending independent saved-mesh clearance and horizontal source-constrained route checks.",
        "limitations": [
            "The2014guide does not establish2026current condition.",
            "Counts,1.1m usable width,180mm waist,curve radii and guard construction are estimates, not a safety or structural certification.",
            "Existing floors remain thin slab studies. No room, lift enclosure or unseen floor fitout is invented.",
        ],
    }
    (OUT / "component-record.json").write_text(json.dumps(record, indent=2) + "\n")
    assert sha(BASE) == BASE_SHA
    print("SAW242_COMPONENT_SAVED", len(objects), solids, flush=True)


if __name__ == "__main__":
    main()
