"""Create a private source-scale COL relief component, never campus geometry.

Run this saved script in an isolated Blender session after generating the plan.
It resets that session, reads no campus .blend, and writes only col-component244.
No current facade colour, true roof depth, road level or interior is asserted.
"""

import hashlib
import json
import sys
from pathlib import Path

import bmesh
import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/col-component244"
PLAN = OUT / "geometry-plan.json"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint


def main():
    plan = json.loads(PLAN.read_text())
    source = ROOT / plan["source"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == plan["sourceSha256"]
    assert len(plan["openings"]) == 72 and not plan["nativeRegistrationAccepted"]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    collection = bpy.data.collections.new("COL244_HOUGHTON_SOURCE_SCALE_COMPONENT")
    bpy.context.scene.collection.children.link(collection)

    def material(name, colour, roughness, transmission=0):
        item = bpy.data.materials.new(name)
        item.use_nodes = True
        item.diffuse_color = (*colour, 1)
        shader = item.node_tree.nodes.get("Principled BSDF")
        shader.inputs["Base Color"].default_value = item.diffuse_color
        shader.inputs["Roughness"].default_value = roughness
        shader.inputs["Metallic"].default_value = 0
        shader.inputs["IOR"].default_value = 1.5
        shader.inputs["Transmission Weight"].default_value = transmission
        item["evidenceStatus"] = (
            "estimated neutral study material; not verified current colour"
        )
        return item

    stone = material("COL244_estimated_neutral_stone", (0.57, 0.55, 0.49), 0.8)
    metal = material("COL244_estimated_dark_joinery", (0.085, 0.095, 0.10), 0.42)
    glass = material("COL244_estimated_window_glass", (0.47, 0.58, 0.62), 0.14, 0.58)
    opaque = material("COL244_unverified_ground_infill", (0.15, 0.16, 0.16), 0.7)
    backing = material("COL244_closed_recess_backing", (0.075, 0.085, 0.09), 0.9)
    groups = {}
    for key, assigned in [
        ("perforated_wall", stone),
        ("reveals", stone),
        ("joinery", metal),
        ("glazing", glass),
        ("opaque_ground_infill", opaque),
        ("closed_backing", backing),
        ("stone_bands", stone),
    ]:
        groups[key] = {"vertices": [], "faces": [], "material": assigned}
    origin, scale = plan["sourceOrigin"], plan["metresPerPoint"]

    def point(p, depth):
        return ((p[0] - origin[0]) * scale, depth, (origin[1] - p[1]) * scale)

    def face(target, vertices):
        start = len(target["vertices"])
        target["vertices"].extend(vertices)
        target["faces"].append(tuple(range(start, start + len(vertices))))

    def polygon(target, ring, depth):
        face(target, [point(p, depth) for p in ring])

    def sides(target, ring, front, back):
        for a, b in zip(ring, ring[1:] + ring[:1]):
            face(
                target,
                [point(a, front), point(b, front), point(b, back), point(a, back)],
            )

    def prism(target, ring, front, back):
        polygon(target, ring, front)
        polygon(target, list(reversed(ring)), back)
        sides(target, ring, front, back)

    wall = groups["perforated_wall"]
    for triangle in plan["wallTriangles"]:
        polygon(wall, triangle, 0)
        polygon(wall, list(reversed(triangle)), 0.32)
    # Actual polygon rings include the open-ended door notch, so no false wall
    # strip is inserted through the drawn sloping threshold.
    for ring in plan["wallBoundaryRings"]:
        sides(wall, ring, 0, 0.32)
    records = []
    for opening in plan["openings"]:
        ring = opening["cutPolygonPt"]
        sides(groups["reveals"], ring, 0.32, 0.60)
        target = (
            groups["glazing"]
            if opening["role"] == "regular-window"
            else groups["opaque_ground_infill"]
        )
        polygon(target, ring, 0.14)
        polygon(groups["closed_backing"], ring, 0.60)
        for frame in opening["framePolygonsPt"]:
            prism(groups["joinery"], frame, -0.018, 0.16)
        records.append(
            {
                "id": opening["id"],
                "role": opening["role"],
                "sourceBounds": opening["sourceBounds"],
                "cutPolygonPt": ring,
                "infillDepthM": 0.14,
                "closedBackingDepthM": 0.60,
            }
        )
    # Opaque source spandrels stay intact behind these continuous ribbon edges.
    for edge in plan["continuousRibbonEdgePolygonsPt"]:
        prism(groups["joinery"], edge, -0.018, 0.005)
    for y0, y1 in [
        plan["horizontalBandsYpt"]["upperCorniceLines"],
        plan["horizontalBandsYpt"]["lowerMainCorniceLines"],
        plan["horizontalBandsYpt"]["lowerBlockBandLines"],
    ]:
        prism(
            groups["stone_bands"],
            [[273.32, y0], [569.12, y0], [569.12, y1], [273.32, y1]],
            -0.045,
            0.025,
        )
    owned = []
    wall_volume = None
    for key, group in groups.items():
        name = "COL244_Houghton_" + key
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(group["vertices"], [], group["faces"])
        mesh.update()
        bm = bmesh.new()
        bm.from_mesh(mesh)
        if key == "perforated_wall":
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        if key == "perforated_wall":
            assert all(edge.is_manifold for edge in bm.edges)
            wall_volume = abs(bm.calc_volume(signed=True))
            assert abs(wall_volume - plan["wallAreaM2"] * 0.32) < 0.002
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        mesh.materials.append(group["material"])
        uv = mesh.uv_layers.new(name="MetricUV")
        for polygon_row in mesh.polygons:
            for index in polygon_row.loop_indices:
                coordinate = mesh.vertices[mesh.loops[index].vertex_index].co
                uv.data[index].uv = (coordinate.x, coordinate.z)
        obj["sourceSha256"] = plan["sourceSha256"]
        obj["sourceApplication"] = plan["sourceApplication"]
        obj["scope"] = (
            "Private historical source-scale elevation relief; no native world registration"
        )
        owned.append(obj)
    bpy.context.view_layer.update()
    fingerprints = {obj.name: object_fingerprint(obj) for obj in owned}
    path = OUT / "component.blend"
    bpy.data.libraries.write(str(path), {collection}, fake_user=True, compress=True)
    record = {
        "component": str(path.relative_to(ROOT)),
        "componentSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "planSha256": hashlib.sha256(PLAN.read_bytes()).hexdigest(),
        "source": plan["source"],
        "sourceSha256": plan["sourceSha256"],
        "ownedObjects": list(fingerprints),
        "objectFingerprints": fingerprints,
        "openings": records,
        "openingCount": len(records),
        "wallVolumeM3": wall_volume,
        "coordinateSystem": plan["coordinateSystem"],
        "campusReadOrModified": False,
        "integrated": False,
        "status": "private component awaiting independent saved-mesh verification and registration",
        "limitations": plan["limitations"],
    }
    (OUT / "component-record.json").write_text(json.dumps(record, indent=2) + "\n")
    print("COL244_COMPONENT_SAVED", len(owned), len(records), flush=True)


if __name__ == "__main__":
    main()
