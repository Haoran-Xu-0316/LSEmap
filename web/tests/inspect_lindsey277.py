"""Read Lindsey House's current context shell and complete-campus surroundings.

Fixed native275and OSMway181939019. No geometry, material, visibility, terrain,
road or metadata changes; writes only private source/mesh evidence. Run main()
in Blender. The adjacent57-58building is recorded solely as a photo control.
"""

import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v275.blend"
SHA = "18a60235fd7c71c6c2864690c574f97b66a9d05577e0c584c626dee41829a4f9"
OUT = ROOT / "result/blender/street277/native-inspection.json"
TARGET = "way/181939019"
NEIGHBOUR = "way/181939035"
COLLECTION = "01_CITY_CONTEXT_estimated_heights"
FRONT_EDGES = (3, 4)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bounds(points):
    return [
        [min(p[i] for p in points) for i in range(3)],
        [max(p[i] for p in points) for i in range(3)],
    ]


def render_eligible(layer):
    names = set()

    def walk(node):
        if node.exclude or node.collection.hide_render:
            return
        names.update(o.name for o in node.collection.objects if not o.hide_render)
        for child in node.children:
            walk(child)

    walk(layer.layer_collection)
    return names


def main():
    sys.path.insert(0, str(ROOT / "web/tools"))
    from integrate_exterior_round194 import object_fingerprint, update_scene
    from refine_portsmouth_exterior207 import material_fingerprint

    assert sha(BASE) == SHA
    site = json.loads((ROOT / "result/blender/site_geometry.json").read_text())
    target = next(b for b in site["buildings"] if b["id"] == TARGET)
    neighbour = next(b for b in site["buildings"] if b["id"] == NEIGHBOUR)
    assert target["code"] is None and target["properties"]["name"] == "Lindsey House"
    assert target["properties"]["addr:housenumber"] == "59-60"
    ring = target["rings"][0]
    x0, y0 = ring[5]
    front = Vector((*ring[3], 0)) - Vector((x0, y0, 0))
    front.normalize()
    outward = Vector((front.y, -front.x, 0))
    frame = {
        "origin": [x0, y0, 0],
        "rightSouthToNorth": list(front),
        "outwardToPark": list(outward),
        "frontOSMRingEdges": list(FRONT_EDGES),
        "registrationStatus": "Inherited two-segment GIS front; do not silently straighten the mapped bend.",
    }
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    campus = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    eligible = render_eligible(campus.view_layers[0])
    prefix = "Context_" + TARGET + "_"
    direct = [
        o
        for o in bpy.data.objects
        if o.name.startswith(prefix) or TARGET in str(o.get("originalObject", ""))
    ]
    assert direct, "Mapped context identity not found"
    identities, materials = [], {}
    for obj in sorted(direct, key=lambda o: o.name):
        record = {
            "name": obj.name,
            "type": obj.type,
            "fingerprint": object_fingerprint(obj),
            "owners": sorted(c.name for c in obj.users_collection),
            "hideRender": obj.hide_render,
            "hideViewport": obj.hide_viewport,
            "inCompleteCampus": obj.name in campus.objects,
            "renderEligibleInCompleteCampus": obj.name in eligible,
            "properties": {
                k: v for k, v in obj.items() if isinstance(v, (str, int, float, bool))
            },
        }
        if obj.type == "MESH":
            points = [obj.matrix_world @ v.co for v in obj.data.vertices]
            record.update(
                matrixWorld=[list(r) for r in obj.matrix_world],
                worldBounds=bounds(points),
                verticesLocal=[list(v.co) for v in obj.data.vertices],
                verticesWorld=[list(p) for p in points],
                faces=[
                    {
                        "index": f.index,
                        "vertices": list(f.vertices),
                        "materialIndex": f.material_index,
                        "smooth": f.use_smooth,
                        "worldNormal": list(
                            (
                                obj.matrix_world.to_3x3().inverted().transposed()
                                @ f.normal
                            ).normalized()
                        ),
                        "uvs": {
                            uv.name: [list(uv.data[i].uv) for i in f.loop_indices]
                            for uv in obj.data.uv_layers
                        },
                    }
                    for f in obj.data.polygons
                ],
                modifiers=[{"name": m.name, "type": m.type} for m in obj.modifiers],
                materials=[m.name for m in obj.data.materials],
            )
            for m in obj.data.materials:
                node = (
                    next(
                        (n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"),
                        None,
                    )
                    if m.use_nodes
                    else None
                )
                materials[m.name] = {
                    "fingerprint": material_fingerprint(m),
                    "baseColor": list(node.inputs["Base Color"].default_value)
                    if node
                    else list(m.diffuse_color),
                    "roughness": float(node.inputs["Roughness"].default_value)
                    if node
                    else None,
                    "webOpacity": m.get("webOpacity"),
                }
        identities.append(record)
    region = [
        [min(p[0] for p in ring) - 5, min(p[1] for p in ring) - 5, -1],
        [max(p[0] for p in ring) + 5, max(p[1] for p in ring) + 5, 28],
    ]

    def intersects(extent):
        return all(
            extent[1][i] >= region[0][i] and extent[0][i] <= region[1][i]
            for i in range(3)
        )

    nearby = []
    deps = bpy.context.evaluated_depsgraph_get()
    for obj in sorted(bpy.data.objects, key=lambda o: o.name):
        if obj.type != "MESH" or obj.name not in eligible or not obj.data.vertices:
            continue
        if not intersects(
            bounds([obj.matrix_world @ Vector(p) for p in obj.bound_box])
        ):
            continue
        evaluated = obj.evaluated_get(deps)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        triangles = []
        for tri in mesh.loop_triangles:
            points = [
                evaluated.matrix_world @ mesh.vertices[i].co for i in tri.vertices
            ]
            if intersects(bounds(points)):
                material = (
                    mesh.materials[tri.material_index] if mesh.materials else None
                )
                triangles.append(
                    {
                        "world": [list(p) for p in points],
                        "material": material.name if material else None,
                    }
                )
        evaluated.to_mesh_clear()
        if triangles:
            nearby.append(
                {
                    "name": obj.name,
                    "fingerprint": object_fingerprint(obj),
                    "owners": sorted(c.name for c in obj.users_collection),
                    "flatDisplayDatumOnly": obj.name
                    == "SITE216_Expanded_flat_map_datum",
                    "triangles": triangles,
                }
            )
    assert all(
        object_fingerprint(bpy.data.objects[r["name"]]) == r["fingerprint"]
        for r in identities + nearby
    )
    assert all(
        material_fingerprint(bpy.data.materials[name]) == r["fingerprint"]
        for name, r in materials.items()
    )
    assert sha(BASE) == SHA
    result = {
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": SHA,
        "inspectorScriptSha256": sha(Path(__file__)),
        "readOnly": True,
        "nativeSaved": False,
        "originalObjects": len(bpy.data.objects),
        "originalMaterials": len(bpy.data.materials),
        "targetOSM": {
            k: target[k]
            for k in ("id", "code", "properties", "rings", "center", "area")
        },
        "photoNeighbourControl": {
            k: neighbour[k] for k in ("id", "properties", "center")
        },
        "frame": frame,
        "targetOriginalObjects": identities,
        "targetMaterialGraphs": materials,
        "roiWorld": region,
        "completeCampusRenderableRegion": nearby,
        "contextCollectionExists": COLLECTION in bpy.data.collections,
        "cameraSuggestions": [
            {
                "id": "park-facing-context",
                "position": [
                    target["center"][0] + outward.x * 38,
                    target["center"][1] + outward.y * 38,
                    10,
                ],
                "target": [target["center"][0], target["center"][1], 6],
                "contextRule": "Use complete campus render-eligible objects including actual roofs, foreground vegetation, ground and paths; do not infer a missing facade from a shell-only isolation.",
            }
        ],
        "sourcePhoto": "result/blender/street277/sources/garden-court-owner-factsheet.pdf page12; right-hand59-60facade only. SourcePDFcreated2021-08-13; photo capture date unknown.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        "LINDSEY277_READ_ONLY_READY",
        len(identities),
        sum(r["renderEligibleInCompleteCampus"] for r in identities),
        len(nearby),
        flush=True,
    )


if __name__ == "__main__":
    main()
