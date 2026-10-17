"""Build the source-scale CON Houghton facade as a private native component.

Run from Blender's editor. The accepted campus is read-only. The component is
not integrated until frontage width and the drawn street slope are registered.
No unseen roof mass, property transfer or complete interior is invented here.
"""

import hashlib
import json
import sys
from pathlib import Path

import bmesh
import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/con-frontage243"
BASE = ROOT / "result/blender/LSE_campus_detailed_v242.blend"
BASE_SHA = "b81a627db462ffbd98ca206879fea43d8da018e36edeb2e2bca62c85a2db4589"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint, update_scene


def main():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    plan = json.loads((OUT / "geometry-plan.json").read_text())
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    state = json.loads(
        (ROOT / "result/blender/stage243/protected-source-state.json").read_text()
    )
    assert all(
        object_fingerprint(bpy.data.objects[name]) == row["fingerprint"]
        for name, row in state["objects"].items()
    )
    collection = bpy.data.collections.new("CON243_HOUGHTON_SOURCE_SCALE_COMPONENT")
    bpy.context.scene.collection.children.link(collection)
    groups = {}

    def group(name, material):
        groups[name] = {"vertices": [], "faces": [], "material": material}
        return groups[name]

    stone = bpy.data.materials["Portland limestone warm"]
    bronze = bpy.data.materials["Dark bronze frames"]
    glass = bpy.data.materials["DIELECTRIC166_CON_V41_neutral_glass_1"]
    backing = bronze.copy()
    backing.name = "CON243_recess_shadow_backing"
    backing.diffuse_color = (0.095, 0.105, 0.11, 1)
    node = backing.node_tree.nodes.get("Principled BSDF")
    node.inputs["Base Color"].default_value = backing.diffuse_color
    node.inputs["Metallic"].default_value = 0
    node.inputs["Roughness"].default_value = 0.84
    wall = group("CON243_Houghton_perforated_wall", stone)
    recess = group("CON243_Houghton_reveals", stone)
    frames = group("CON243_Houghton_joinery", bronze)
    panes = group("CON243_Houghton_glazing", glass)
    shadows = group("CON243_Houghton_closed_backing", backing)
    bands = group("CON243_Houghton_stone_bands", stone)
    origin = plan["sourceOrigin"]
    scale = plan["metresPerPoint"]

    def point(x, y, depth):
        return ((x - origin[0]) * scale, depth, (origin[1] - y) * scale)

    def face(target, vertices):
        start = len(target["vertices"])
        target["vertices"].extend(vertices)
        target["faces"].append(tuple(range(start, start + len(vertices))))

    def rectangle(target, bounds, depth):
        x0, y0, x1, y1 = bounds
        face(
            target,
            [
                point(x0, y0, depth),
                point(x1, y0, depth),
                point(x1, y1, depth),
                point(x0, y1, depth),
            ],
        )

    def prism(target, bounds, front, back):
        x0, y0, x1, y1 = bounds
        a = [
            point(x0, y0, front),
            point(x1, y0, front),
            point(x1, y1, front),
            point(x0, y1, front),
        ]
        b = [
            point(x0, y0, back),
            point(x1, y0, back),
            point(x1, y1, back),
            point(x0, y1, back),
        ]
        face(target, a)
        face(target, list(reversed(b)))
        for i in range(4):
            face(target, [a[i], b[i], b[(i + 1) % 4], a[(i + 1) % 4]])

    for triangle in plan["wallTriangles"]:
        face(wall, [point(x, y, 0) for x, y in triangle])
        face(wall, [point(x, y, 0.32) for x, y in reversed(triangle)])
    for a, b in zip(plan["outline"], plan["outline"][1:] + plan["outline"][:1]):
        face(wall, [point(*a, 0), point(*a, 0.32), point(*b, 0.32), point(*b, 0)])
    opening_records = []
    for opening in plan["openings"]:
        x0, y0, x1, y1 = opening["sourceBounds"]
        width = 0.55
        # The reveal closes onto an opaque recessed panel. Glazing never opens
        # an unsupported view into an invented whole-floor interior.
        perimeter = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        for a, b in zip(perimeter, perimeter[1:] + perimeter[:1]):
            face(wall, [point(*a, 0), point(*b, 0), point(*b, 0.32), point(*a, 0.32)])
            face(
                recess,
                [point(*a, 0.32), point(*b, 0.32), point(*b, 0.60), point(*a, 0.60)],
            )
        rectangle(panes, [x0, y0, x1, y1], 0.14)
        rectangle(shadows, [x0, y0, x1, y1], 0.60)
        for rect in [
            [x0, y0, x0 + width, y1],
            [x1 - width, y0, x1, y1],
            [x0 + width, y0, x1 - width, y0 + width],
            [x0 + width, y1 - width, x1 - width, y1],
        ]:
            prism(frames, rect, -0.028, 0.16)
        # Retain the observed line pattern. These bounded thin relief strips are
        # an explicit linework study, not a guess at missing opening subdivisions.
        for a, b, c, d in opening["vectorSegments"]:
            half = 0.10
            bounds = [
                min(a, c) - half,
                min(b, d) - half,
                max(a, c) + half,
                max(b, d) + half,
            ]
            prism(frames, bounds, -0.018, 0.13)
        opening_records.append(
            {
                "id": opening["id"],
                "bounds": opening["sourceBounds"],
                "role": opening["role"],
                "glassDepthM": 0.14,
                "closedBackingDepthM": 0.60,
            }
        )
    # Source-drawn continuous moulding bands; projecting depths remain estimates.
    for y0, y1 in [
        (190.36, 193.84),
        (197.32, 200.08),
        (221.08, 223.24),
        (324.04, 329.80),
        (329.80, 333.52),
        (333.52, 343.00),
        (367.00, 370.48),
    ]:
        prism(bands, [229.16, y0, 566.12, y1], -0.045, 0.03)
    # Eight continuous stone surrounds enclose the three central window rows.
    # Their x extents and head datum are explicit source vectors; the two narrow
    # service strips have no corresponding tall surround in the drawing.
    surrounds = [
        (248.12, 273.56, 250.76, 270.92),
        (279.80, 312.44, 282.56, 309.68),
        (318.92, 344.36, 321.68, 341.60),
        (381.20, 406.64, 383.96, 403.88),
        (413.12, 438.68, 415.88, 435.92),
        (445.04, 470.48, 447.80, 467.72),
        (476.84, 502.40, 479.60, 499.64),
        (508.76, 534.32, 511.52, 531.56),
    ]
    for left, right, inner_left, inner_right in surrounds:
        for bounds in [
            (left, 228.64, inner_left, 324.04),
            (inner_right, 228.64, right, 324.04),
            (inner_left, 228.64, inner_right, 231.40),
        ]:
            prism(bands, bounds, -0.10, 0.012)
    pediment = [(284.60, 119.44), (299.96, 116.44), (315.32, 119.44)]
    face(bands, [point(x, y, -0.11) for x, y in pediment])
    face(bands, [point(x, y, 0.02) for x, y in reversed(pediment)])
    for a, b in zip(pediment, pediment[1:] + pediment[:1]):
        face(
            bands,
            [point(*a, -0.11), point(*a, 0.02), point(*b, 0.02), point(*b, -0.11)],
        )
    owned = []
    for name, data in groups.items():
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(data["vertices"], [], data["faces"])
        mesh.update()
        bm = bmesh.new()
        bm.from_mesh(mesh)
        if name == "CON243_Houghton_perforated_wall":
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
            assert all(edge.is_manifold for edge in bm.edges)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        mesh.materials.append(data["material"])
        uv = mesh.uv_layers.new(name="MetricUV")
        for polygon in mesh.polygons:
            for loop_index in polygon.loop_indices:
                coordinate = mesh.vertices[mesh.loops[loop_index].vertex_index].co
                uv.data[loop_index].uv = (coordinate.x, coordinate.z)
        obj["sourceApplication"] = "20/04703/FULL"
        obj["sourceSha256"] = plan["sourceSha256"]
        obj["scope"] = (
            "Historical Houghton elevation; source-scale private component, not registered campus geometry"
        )
        owned.append(obj)
    update_scene()
    assert all(
        object_fingerprint(bpy.data.objects[name]) == row["fingerprint"]
        for name, row in state["objects"].items()
    )
    fingerprints = {obj.name: object_fingerprint(obj) for obj in owned}
    path = OUT / "component.blend"
    bpy.data.libraries.write(str(path), {collection}, fake_user=True, compress=True)
    record = {
        "component": str(path.relative_to(ROOT)),
        "componentSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "baselineSha256": BASE_SHA,
        "baselineUnchanged": True,
        "originalObjectsPreserved": len(state["objects"]),
        "source": plan["source"],
        "sourceSha256": plan["sourceSha256"],
        "ownedObjects": list(fingerprints),
        "objectFingerprints": fingerprints,
        "openings": opening_records,
        "openingCount": len(opening_records),
        "units": "metres at printed scale; localX along elevation, localZ above the southern source groundline",
        "integrated": False,
        "status": "private-component-awaiting-independent-saved-mesh-verification-and-native-registration",
        "limitations": plan["limitations"],
    }
    (OUT / "component-record.json").write_text(json.dumps(record, indent=2) + "\n")
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    print("CON243_COMPONENT_SAVED", len(owned), len(opening_records), flush=True)


if __name__ == "__main__":
    main()
