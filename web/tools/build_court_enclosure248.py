"""Restore the mapped court enclosure without changing park paths or fixtures.

Open in Blender's Text Editor. Only the mapped XY alignment is authoritative;
height, posts, wire pitch and the generous corner opening remain estimates.
"""

import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/court-enclosure248"
BASE = ROOT / "result/blender/LSE_campus_detailed_v246.blend"
SHA = "44f7745ab4c84681b9d9528b6fd5955761cf6eeb769ef6afdc7bbf05c8df0c4d"
OWNER = "03_PUBLIC_REALM"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint, update_scene


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n")


def capture():
    spec = importlib.util.spec_from_file_location(
        "native_capture", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = SHA
    return helper.capture_source()


def material(name, grid=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.diffuse_color = (0.018, 0.04, 0.025, 1)
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = m.diffuse_color
    p.inputs["Roughness"].default_value = 0.78
    p.inputs["Metallic"].default_value = 0
    m["presentationEstimated"] = True
    if grid:
        m["webWireGrid"] = True
        m["webWirePitch"] = [0.075, 0.15]
        m["webWireWidth"] = 0.0025
        m.surface_render_method = "DITHERED"
        nodes, links = m.node_tree.nodes, m.node_tree.links
        uv = nodes.new("ShaderNodeTexCoord")
        separate = nodes.new("ShaderNodeSeparateXYZ")
        links.new(uv.outputs["UV"], separate.inputs[0])
        coverage = []
        for axis, pitch in zip(["X", "Y"], [0.075, 0.15]):
            distance = nodes.new("ShaderNodeMath")
            distance.operation = "PINGPONG"
            distance.inputs[1].default_value = pitch / 2
            links.new(separate.outputs[axis], distance.inputs[0])
            wire = nodes.new("ShaderNodeMath")
            wire.operation = "LESS_THAN"
            wire.inputs[1].default_value = 0.00125
            links.new(distance.outputs[0], wire.inputs[0])
            coverage.append(wire.outputs[0])
        union = nodes.new("ShaderNodeMath")
        union.operation = "MAXIMUM"
        for i, socket in enumerate(coverage):
            links.new(socket, union.inputs[i])
        links.new(union.outputs[0], p.inputs["Alpha"])
    return m


def mesh(name, vertices, faces, finish, uvs=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    data.materials.append(finish)
    if uvs:
        layer = data.uv_layers.new(name="UVMap")
        for face, values in zip(data.polygons, uvs):
            for index, uv in zip(face.loop_indices, values):
                layer.data[index].uv = uv
    obj = bpy.data.objects.new(name, data)
    bpy.data.collections[OWNER].objects.link(obj)
    obj["sourceWay"] = "301471945"
    obj["presentationEstimated"] = True
    return obj


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    component = OUT / "component.blend"
    assert not component.exists(), "Do not overwrite a reviewed component"
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == SHA
    review_path = ROOT / "result/blender/park-road-review248/review.json"
    review = json.loads(review_path.read_text())
    for path, digest in review["sourceHashes"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    plan = review["recommendations"][0]["minimalBoundedPlan"]
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = capture()
    write("protected-source-state.json", before)
    scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    segments = plan["retainedFenceAlignmentSegments"]
    posts, post_points = {}, []
    for segment in segments:
        a, b = Vector(segment["from"]), Vector(segment["to"])
        axis = (b - a).normalized()
        length = (b - a).length
        a += axis * 0.031
        b -= axis * 0.031
        count = math.ceil((b - a).length / 3)
        for i in range(count + 1):
            xy = a.lerp(b, i / count)
            key = tuple(round(v, 5) for v in xy)
            if key in posts:
                continue
            # Existing ground only: no raised datum or foundation sheet.
            hit, point, _normal, _face, obj, _matrix = scene.ray_cast(
                bpy.context.evaluated_depsgraph_get(),
                Vector((xy.x, xy.y, 0.15)),
                Vector((0, 0, -1)),
                distance=0.3,
            )
            assert hit and 0.039 <= point.z <= 0.075, (
                list(xy),
                hit,
                list(point),
                obj.name if obj else None,
            )
            posts[key] = (xy.x, xy.y, point.z - 0.01)
            post_points.append(
                {"xy": list(xy), "supportZ": point.z, "supportObject": obj.name}
            )
    vertices, faces = [], []
    for x, y, z in posts.values():
        base = len(vertices)
        vertices.extend(
            (x + dx * 0.03, y + dy * 0.03, level)
            for level in [z, 3.057]
            for dx, dy in [(-1, -1), (1, -1), (1, 1), (-1, 1)]
        )
        faces.extend(
            tuple(base + i for i in f)
            for f in [
                (0, 3, 2, 1),
                (4, 5, 6, 7),
                (0, 1, 5, 4),
                (1, 2, 6, 5),
                (2, 3, 7, 6),
                (3, 0, 4, 7),
            ]
        )
    post_obj = mesh(
        "COURT248_mapped_enclosure_posts",
        vertices,
        faces,
        material("COURT248_estimated_coated_posts"),
    )
    vertices, faces, uvs = [], [], []
    for segment in segments:
        a, b = segment["from"], segment["to"]
        length = math.dist(a, b)
        offset = len(vertices)
        vertices.extend(
            [
                (a[0], a[1], 0.057),
                (b[0], b[1], 0.057),
                (b[0], b[1], 3.057),
                (a[0], a[1], 3.057),
            ]
        )
        faces.append(tuple(range(offset, offset + 4)))
        uvs.append([(0, 0), (length, 0), (length, 3), (0, 3)])
    grid_obj = mesh(
        "COURT248_mapped_perforated_wire_panels",
        vertices,
        faces,
        material("COURT248_estimated_coated_wire_grid", True),
        uvs,
    )
    added = [post_obj, grid_obj]
    update_scene()
    current = capture()
    assert all(
        current["objects"][name] == value for name, value in before["objects"].items()
    )
    assert all(
        current["materials"][name] == value
        for name, value in before["materials"].items()
    )
    assert (
        current["rooms"] == before["rooms"]
        and current["campusRooms"] == before["campusRooms"]
    )
    fingerprints = {obj.name: object_fingerprint(obj) for obj in added}
    bpy.data.libraries.write(str(component), set(added), fake_user=True, compress=True)
    digest = hashlib.sha256(component.read_bytes()).hexdigest()
    write(
        "plan.json",
        {
            "baselineSha256": SHA,
            "sourceReviewSha256": hashlib.sha256(review_path.read_bytes()).hexdigest(),
            "plan": plan,
            "supports": post_points,
            "wirePitch": [0.075, 0.15],
            "wireWidth": 0.0025,
            "wireRendering": "Native procedural alpha; browser analytically filtered alpha, not glass or an opaque wall",
        },
    )
    write(
        "audit.json",
        {
            "version": 248,
            "baselineSha256": SHA,
            "componentPath": str(component.relative_to(ROOT)),
            "componentSha256": digest,
            "targetCollection": OWNER,
            "destinationCollection": OWNER,
            "addedObjects": list(fingerprints),
            "archivedObjects": [],
            "changedObjects": [],
            "addedFingerprints": fingerprints,
            "replacementMaterialBindings": {
                o.name: [m.name for m in o.data.materials] for o in added
            },
            "scope": "Restore the independently photographed and mapped court perimeter wire enclosure with a conservative clear corner opening. Preserve all ground, paths, courts, trees, park gates, buildings and rooms.",
            "status": "candidate_requires_saved_mesh_and_visual_review",
            "sourceReview": "result/blender/park-road-review248/review.json",
            "limitations": [
                "OSM2024 boundary is not a2026 survey. Official photograph capture date unknown.",
                "3m height,60mm post section,75x150mm rectangular wire pitch and2.5mm wire width are estimates.",
                "Mapped corner gate has no measured width. Reserve2m along each adjoining edge, with no gate leaf, diagonal closure or top crossbar.",
            ],
        },
    )
    # Review on the exact full native, then discard all temporary cameras/settings.
    camera = bpy.data.objects.new(
        "COURT248_review_camera", bpy.data.cameras.new("COURT248_review_camera")
    )
    scene.collection.objects.link(camera)
    scene.camera = camera
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 825
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    views = [
        ("court", [-77, 89, 14], [-15, 132, 1.7], 54),
        ("entry", [-33, 102, 2.3], [-24, 118, 1.6], 64),
    ]
    for name, eye, target, fov in views:
        camera.location = eye
        camera.rotation_euler = (
            (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
        )
        camera.data.lens = camera.data.sensor_height / (
            2 * math.tan(math.radians(fov) / 2)
        )
        for phase in ["before", "after"]:
            for obj in added:
                obj.hide_render = phase == "before"
            update_scene()
            scene.render.filepath = str(OUT / (phase + "-" + name + ".png"))
            bpy.ops.render.render(write_still=True)
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == SHA
    print(
        "COURT248_COMPONENT",
        digest,
        "posts",
        len(posts),
        "panels",
        len(segments),
        flush=True,
    )


if __name__ == "__main__":
    main()
