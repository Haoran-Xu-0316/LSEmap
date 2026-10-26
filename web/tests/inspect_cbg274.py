"""Read native269CBG's upper facade without editing or saving the model.

Inventories the full visible exterior and exports actual connected top-front
members, face/UV records and primary profiles for boundedG4mask verification.
Fixed paths and main(); no command-line options or model save.
"""

import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v269.blend"
SHA = "a44026d64bb57cea159a44b1fa96b7b9be13e7d4af034f57d09beb62480ef21b"
OUT = ROOT / "result/blender/cbg274/native-inspection.json"
DETAIL = (
    "gold_solar_blades",
    "pale_solar_blades",
    "shade_cantilever_brackets",
    "shade_module_caps",
    "shade_fixing_bolt_heads",
    "shade_mid_tie_rods",
    "shade_leading_silver_strips",
    "metric_office_solid",
    "metric_office_glass",
    "metric_front_jambs",
    "metric_front_heads_sills",
    "metric_office_vent_transoms",
    "retained_circulation_glass",
    "external_floor_beams",
    "tower_external_I_columns",
    "tower_I_flanges",
    "tower_I_webs",
    "tower_column_caps",
)
STEP = 52.2 / 13


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def components(mesh):
    links = [set() for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        links[a].add(b)
        links[b].add(a)
    remaining = set(range(len(links)))
    groups = []
    while remaining:
        first = min(remaining)
        remaining.remove(first)
        found, todo = {first}, [first]
        while todo:
            for index in links[todo.pop()] & remaining:
                remaining.remove(index)
                found.add(index)
                todo.append(index)
        groups.append(sorted(found))
    return groups


def bounds(points):
    return [
        [min(p[i] for p in points) for i in range(3)],
        [max(p[i] for p in points) for i in range(3)],
    ]


def material_record(material):
    node = (
        next((n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if material.use_nodes
        else None
    )
    return {
        "name": material.name,
        "baseColor": list(node.inputs["Base Color"].default_value)
        if node
        else list(material.diffuse_color),
        "metallic": float(node.inputs["Metallic"].default_value) if node else None,
        "roughness": float(node.inputs["Roughness"].default_value) if node else None,
        "webOpacity": material.get("webOpacity"),
    }


def main():
    sys.path.insert(0, str(ROOT / "web/tools"))
    from integrate_exterior_round194 import object_fingerprint, update_scene
    from refine_portsmouth_exterior207 import material_fingerprint

    assert sha(BASE) == SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    frame = json.loads(
        (
            ROOT / "result/blender/cbg-georegistration202/rebuild-mapping.json"
        ).read_text()
    )["frame"]
    origin = Vector((*frame["origin_G7_SW_world"], 0))
    x_axis, y_axis = [Vector((*frame[n], 0)) for n in ("x_unit_SW", "y_unit_SE_rear")]

    def local(point):
        delta = point - origin
        return [delta.dot(x_axis), delta.dot(y_axis), point.z]

    before = {o.name: object_fingerprint(o) for o in bpy.data.objects}
    materials = {m.name: material_fingerprint(m) for m in bpy.data.materials}
    rows = []
    for obj in sorted(
        bpy.data.collections["CBG_EXTERIOR"].all_objects, key=lambda o: o.name
    ):
        if obj.hide_render or obj.type != "MESH" or not obj.data.vertices:
            continue
        points = [local(obj.matrix_world @ v.co) for v in obj.data.vertices]
        row = {
            "name": obj.name,
            "fingerprint": before[obj.name],
            "owners": sorted(c.name for c in obj.users_collection),
            "matrixWorld": [list(r) for r in obj.matrix_world],
            "localBounds": bounds(points),
            "materials": [material_record(m) for m in obj.data.materials],
            "vertices": len(obj.data.vertices),
            "faces": len(obj.data.polygons),
            "modifiers": [{"name": m.name, "type": m.type} for m in obj.modifiers],
        }
        if any(obj.name.endswith(suffix) for suffix in DETAIL):
            all_groups = components(obj.data)
            selected, selected_vertices = [], set()
            for index, vertices in enumerate(all_groups):
                extent = bounds([points[v] for v in vertices])
                lo, hi = extent
                # Whole actual components intersecting the two upper source
                # storeys and front plane. Include two left bays as controls.
                if (
                    hi[0] < -24
                    or lo[0] > 1
                    or hi[1] < -2
                    or lo[1] > 0.30
                    or hi[2] < 11 * STEP - 0.10
                ):
                    continue
                selected_vertices.update(vertices)
                selected.append(
                    {
                        "component": index,
                        "vertices": vertices,
                        "localBounds": extent,
                        "localCentre": [
                            (a + b) / 2 for a, b in zip(lo, hi, strict=True)
                        ],
                    }
                )
            row["allComponentCount"] = len(all_groups)
            row["topFrontComponents"] = selected
            row["selectedVertices"] = [
                {
                    "index": i,
                    "objectLocal": list(obj.data.vertices[i].co),
                    "world": list(obj.matrix_world @ obj.data.vertices[i].co),
                    "facadeLocal": points[i],
                }
                for i in sorted(selected_vertices)
            ]
            row["selectedFaces"] = [
                {
                    "index": f.index,
                    "vertices": list(f.vertices),
                    "materialIndex": f.material_index,
                    "smooth": f.use_smooth,
                    "uvs": {
                        uv.name: [list(uv.data[i].uv) for i in f.loop_indices]
                        for uv in obj.data.uv_layers
                    },
                }
                for f in obj.data.polygons
                if set(f.vertices) <= selected_vertices
            ]
        rows.append(row)
    assert {o.name: object_fingerprint(o) for o in bpy.data.objects} == before
    assert {m.name: material_fingerprint(m) for m in bpy.data.materials} == materials
    assert sha(BASE) == SHA
    result = {
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": SHA,
        "originalObjects": len(before),
        "originalMaterials": len(materials),
        "readOnly": True,
        "inspectorScriptSha256": sha(Path(__file__)),
        "nativeSaved": False,
        "frame": frame,
        "storeyStepRetained": STEP,
        "sourceTarget": "Highest two storeys atG4=-18m; do not infer the whole fin rhythm or other floor boundaries.",
        "visibleExterior": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        "CBG274_READ_ONLY_READY",
        len(rows),
        sum(len(r.get("topFrontComponents", [])) for r in rows),
        flush=True,
    )


if __name__ == "__main__":
    main()
