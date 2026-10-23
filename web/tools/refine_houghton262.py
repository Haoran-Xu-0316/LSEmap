"""Build the photographed Houghton notice-cabinet group and one camera fixture.

The undated user photograph establishes these visible fixture types. Dimensions,
profile sections and exact stations are estimates registered to accepted261wall
surfaces. Original objects,material graphs,visibility and35rooms remain intact.
Fixed Blender component output; no full-campus save or command-line options.
"""

import importlib.util
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v261.blend"
SHA = "9890521a376afabfbb3d6c130d20ce40988315c49b8adea4c00749960a97482a"
OUT = ROOT / "result/blender/houghton262"
COLLECTION = "OLD_EXTERIOR"
WALL = "OLD194_STONE_OLD_D5_houghton112_middle_stone"
CAMERA_WALL = "OLD194_STONE_OLD_V112_entry_V97_Corner_rusticated_quoins"
STATIONS = [-17.2827083, -14.3324300, -11.4261832, -8.4759050]
WIDTH, HEIGHT, CENTRE_Z = 0.80, 1.20, 2.75
NAMES = {
    "shell": "HOUGHTON262_notice_cabinets_closed_metal",
    "inserts": "HOUGHTON262_notice_cabinet_inserts",
    "glass": "HOUGHTON262_notice_cabinet_clear_covers",
    "camera": "HOUGHTON262_entry_camera_white_housing",
    "dome": "HOUGHTON262_entry_camera_dark_dome",
}
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint, update_scene
from refine_col_finish252 import sha
from refine_old_exterior259 import frame
from refine_portsmouth_exterior207 import material_fingerprint


def capture():
    spec = importlib.util.spec_from_file_location(
        "houghton262_protection", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = SHA
    result = helper.capture_source()
    result["visibility"] = {
        o.name: [o.hide_render, o.hide_viewport, o.hide_get()] for o in bpy.data.objects
    }
    return result


def tree(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    result = BVHTree.FromPolygons(
        [evaluated.matrix_world @ v.co for v in mesh.vertices],
        [tuple(t.vertices) for t in mesh.loop_triangles],
        all_triangles=True,
    )
    evaluated.to_mesh_clear()
    return result


def world(x, depth, z):
    origin, right, normal = frame()
    return origin + right * x + normal * depth + Vector((0, 0, z))


def local(p):
    origin, right, normal = frame()
    delta = p - origin
    return Vector((delta.dot(right), delta.dot(normal), p.z))


def wall_hit(source, x, z):
    normal = frame()[2]
    result = source.ray_cast(world(x, 4, z), -normal, 8)
    assert result[0] is not None, (x, z)
    assert abs(result[1].dot(normal)) > 0.99, (x, z, list(result[1]))
    return local(result[0]).y


class Batch:
    def __init__(self, name, materials):
        self.name, self.materials = name, materials
        self.vertices, self.faces, self.slots, self.solids = [], [], [], []
        self.point_transform = None

    def solid(self, points, faces, slot=0, role="fixture"):
        start = len(self.vertices)
        self.vertices.extend(
            self.point_transform(p) if self.point_transform else world(*p)
            for p in points
        )
        self.faces.extend(tuple(start + i for i in f) for f in faces)
        self.slots.extend([slot] * len(faces))
        self.solids.append(
            {"role": role, "vertices": list(range(start, len(self.vertices)))}
        )

    def box(self, lo, hi, slot=0, role="fixture"):
        pts = [
            (x, y, z)
            for x in [lo[0], hi[0]]
            for y in [lo[1], hi[1]]
            for z in [lo[2], hi[2]]
        ]
        self.solid(
            pts,
            [
                (0, 4, 6, 2),
                (1, 3, 7, 5),
                (0, 1, 5, 4),
                (2, 6, 7, 3),
                (0, 2, 3, 1),
                (4, 5, 7, 6),
            ],
            slot,
            role,
        )

    def revolve(self, centre, profile, slot=0, role="housing"):
        points = []
        segments = 24
        for z, radius in profile:
            points.extend(
                (
                    centre[0] + radius * math.cos(i * math.tau / segments),
                    centre[1] + radius * math.sin(i * math.tau / segments),
                    centre[2] + z,
                )
                for i in range(segments)
            )
        faces = [tuple(reversed(range(segments)))]
        for row in range(len(profile) - 1):
            faces.extend(
                (
                    row * segments + i,
                    row * segments + (i + 1) % segments,
                    (row + 1) * segments + (i + 1) % segments,
                    (row + 1) * segments + i,
                )
                for i in range(segments)
            )
        faces.append(tuple((len(profile) - 1) * segments + i for i in range(segments)))
        self.solid(points, faces, slot, role)

    def finish(self):
        mesh = bpy.data.meshes.new(self.name + "_mesh")
        mesh.from_pydata(self.vertices, [], self.faces)
        for material in self.materials:
            mesh.materials.append(material)
        for polygon, slot in zip(mesh.polygons, self.slots):
            polygon.material_index = slot
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(mesh)
        bm.free()
        uv = mesh.uv_layers.new(name="Metric")
        for loop in mesh.loops:
            p = local(mesh.vertices[loop.vertex_index].co)
            uv.data[loop.index].uv = (p.x, p.z)
        mesh.update()
        obj = bpy.data.objects.new(self.name, mesh)
        bpy.data.collections[COLLECTION].objects.link(obj)
        obj["destinationCollection"] = COLLECTION
        obj["dimensionsEstimated"] = True
        obj["sourceScope"] = (
            "Undated user Houghton photograph;photo-estimated street fixtures attached to actual261wall surfaces"
        )
        return obj


def new_material(name, colour, roughness=0.65, alpha=1, transmission=0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = (*colour, alpha)
    node = material.node_tree.nodes["Principled BSDF"]
    node.inputs["Base Color"].default_value = (*colour, 1)
    node.inputs["Roughness"].default_value = roughness
    node.inputs["Metallic"].default_value = 0
    node.inputs["Alpha"].default_value = alpha
    node.inputs["Transmission Weight"].default_value = transmission
    node.inputs["IOR"].default_value = 1.45
    material["webOpacity"] = alpha
    material["sourceScope"] = (
        "Photo-guided visual estimate;not measured material specification"
    )
    return material


def welcome_text(material, depth):
    _origin, right, normal = frame()
    objects = []
    for index, (body, z, size) in enumerate(
        [("Welcome to", 2.91, 0.106), ("LSE", 2.74, 0.19)]
    ):
        name = "HOUGHTON262_observed_welcome_lettering_" + str(index + 1)
        curve = bpy.data.curves.new(name, "FONT")
        curve.body = body
        curve.align_x = "CENTER"
        curve.align_y = "CENTER"
        curve.size = size
        curve.extrude = 0.0007
        obj = bpy.data.objects.new(name + "_temporary_font", curve)
        bpy.data.collections[COLLECTION].objects.link(obj)
        obj.location = world(STATIONS[0], depth, z)
        # Text lies in the frontage plane;its front normal points into the street.
        from mathutils import Matrix

        obj.rotation_euler = (
            Matrix((right, Vector((0, 0, 1)), normal)).transposed().to_euler()
        )
        curve.materials.append(material)
        update_scene()
        mesh = bpy.data.meshes.new_from_object(
            obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        )
        converted = bpy.data.objects.new(name, mesh)
        converted.matrix_world = obj.matrix_world.copy()
        bpy.data.collections[COLLECTION].objects.link(converted)
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.curves.remove(curve)
        obj = converted
        obj["destinationCollection"] = COLLECTION
        obj["sourceScope"] = (
            "Only readable Welcome to LSE wording observed in undated user photograph;no current event or merchant inferred"
        )
        objects.append(obj)
    return objects


def build():
    metal = bpy.data.materials["OLD178_Houghton_black_post_coating"]
    white = bpy.data.materials["OLD_Sign_white"]
    materials = [
        new_material("HOUGHTON262_estimated_notice_yellow", (0.74, 0.55, 0.055)),
        new_material("HOUGHTON262_estimated_notice_paper", (0.69, 0.68, 0.62)),
        new_material("HOUGHTON262_estimated_notice_muted_blue", (0.12, 0.19, 0.23)),
        new_material("HOUGHTON262_estimated_notice_muted_red", (0.30, 0.045, 0.045)),
        new_material(
            "HOUGHTON262_estimated_clear_case_glass",
            (0.72, 0.78, 0.79),
            0.16,
            0.13,
            0.45,
        ),
    ]
    shell = Batch(NAMES["shell"], [metal])
    inserts = Batch(NAMES["inserts"], materials[:4])
    glazing = Batch(NAMES["glass"], [materials[4]])
    wall_tree = tree(bpy.data.objects[WALL])
    records = []
    for index, x in enumerate(STATIONS):
        left, right = x - WIDTH / 2, x + WIDTH / 2
        low, high = CENTRE_Z - HEIGHT / 2, CENTRE_Z + HEIGHT / 2
        supports = []
        for xx in [left + 0.065, x, right - 0.065]:
            for zz in [low + 0.065, CENTRE_Z, high - 0.065]:
                supports.append(
                    {"x": xx, "z": zz, "wallDepth": wall_hit(wall_tree, xx, zz)}
                )
        maximum = max(q["wallDepth"] for q in supports)
        assert maximum - min(q["wallDepth"] for q in supports) < 0.025
        back = maximum + 0.027
        front = back + 0.105
        shell.box((left, back, low), (right, back + 0.014, high), role="cabinet_back")
        trim = 0.030
        for xx in [left, right - trim]:
            shell.box(
                (xx, back + 0.014, low),
                (xx + trim, front, high),
                role="cabinet_vertical_edge",
            )
        for zz in [low, high - trim]:
            shell.box(
                (left + trim, back + 0.014, zz),
                (right - trim, front, zz + trim),
                role="cabinet_horizontal_edge",
            )
        mounts = []
        for xx in [left + 0.07, right - 0.07]:
            for zz in [low + 0.07, high - 0.07]:
                d = wall_hit(wall_tree, xx, zz)
                shell.box(
                    (xx - 0.027, d + 0.0004, zz - 0.027),
                    (xx + 0.027, back, zz + 0.027),
                    role="cabinet_wall_fixing",
                )
                mounts.append(
                    {
                        "x": xx,
                        "z": zz,
                        "wallDepth": d,
                        "mountRear": d + 0.0004,
                        "mountFront": back,
                    }
                )
        insert_front = back + 0.026
        inserts.box(
            (left + trim + 0.006, back + 0.019, low + trim + 0.006),
            (right - trim - 0.006, insert_front, high - trim - 0.006),
            slot=index,
            role="recessed_notice_insert",
        )
        glass_front = front - 0.022
        glazing.box(
            (left + trim, glass_front - 0.004, low + trim),
            (right - trim, glass_front, high - trim),
            role="thin_clear_cover",
        )
        # Further source posters are not transcribed. Restrained nonsemantic
        # colour blocks indicate physical inserts,not invented current notices.
        if index:
            inserts.box(
                (left + 0.10, insert_front, high - 0.27),
                (right - 0.10, insert_front + 0.001, high - 0.12),
                slot=1,
                role="unreadable_insert_header_field",
            )
            inserts.box(
                (left + 0.10, insert_front, low + 0.11),
                (right - 0.10, insert_front + 0.001, low + 0.23),
                slot=1,
                role="unreadable_insert_footer_field",
            )
        records.append(
            {
                "index": index,
                "x": x,
                "width": WIDTH,
                "low": low,
                "high": high,
                "back": back,
                "front": front,
                "insertFront": insert_front,
                "glassFront": glass_front,
                "supports": supports,
                "mounts": mounts,
            }
        )
    camera = Batch(NAMES["camera"], [white])
    dome = Batch(NAMES["dome"], [metal])
    ct = tree(bpy.data.objects[CAMERA_WALL])
    cz = 6.2
    camera_support = None
    rejected = []
    normal = frame()[2]
    # The photograph estimates the station;the native quoin is finite. Select
    # the nearest complete plate footprint,not a centre hit across its edge.
    for cx in [-19.0, -19.05, -19.10, -19.15, -19.20]:
        samples = []
        for xx in [cx - 0.09, cx, cx + 0.09]:
            for zz in [cz - 0.14, cz, cz + 0.14]:
                hit = ct.ray_cast(world(xx, 4, zz), -normal, 8)
                valid = hit[0] is not None and abs(hit[1].dot(normal)) > 0.99
                samples.append(
                    {
                        "x": xx,
                        "z": zz,
                        "hit": valid,
                        "wallDepth": local(hit[0]).y if valid else None,
                    }
                )
        if all(q["hit"] for q in samples):
            spread = max(q["wallDepth"] for q in samples) - min(
                q["wallDepth"] for q in samples
            )
            if spread < 0.025:
                camera_support = samples
                break
        rejected.append({"candidateX": cx, "samples": samples})
    assert camera_support is not None, (
        "No complete native quoin patch for the photographed camera plate"
    )
    centre_hit = ct.ray_cast(world(cx, 4, cz), -normal, 8)
    assert centre_hit[0] is not None
    camera_origin = centre_hit[0]
    camera_normal = centre_hit[1].normalized()
    if camera_normal.dot(normal) < 0:
        camera_normal = -camera_normal
    assert abs(camera_normal.z) < 0.00001
    camera_right = Vector((0, 0, 1)).cross(camera_normal).normalized()
    cd = local(camera_origin).y

    def camera_point(p):
        return (
            camera_origin
            + camera_right * (p[0] - cx)
            + camera_normal * (p[1] - cd)
            + Vector((0, 0, p[2] - cz))
        )

    camera.point_transform = camera_point
    dome.point_transform = camera_point
    native_frame = {
        "origin": list(camera_origin),
        "right": list(camera_right),
        "outward": list(camera_normal),
        "up": [0, 0, 1],
    }
    (OUT / "camera-native-registration.json").write_text(
        json.dumps(
            {
                "originalPhotoStationEstimate": -19.0,
                "registeredX": cx,
                "rejectedPatches": rejected,
                "acceptedWholePlateSupport": camera_support,
                "actualQuoinFrame": native_frame,
                "dimensionBasis": "Actual native quoin BVH normal,tangent and attachment point;photograph station and camera dimensions remain estimates.",
            },
            indent=2,
        )
        + "\n"
    )
    camera.box(
        (cx - 0.09, cd + 0.0004, cz - 0.14),
        (cx + 0.09, cd + 0.026, cz + 0.14),
        role="camera_wall_plate",
    )
    camera.box(
        (cx - 0.035, cd + 0.026, cz - 0.035),
        (cx + 0.035, cd + 0.32, cz + 0.035),
        role="camera_short_arm",
    )
    camera.revolve(
        (cx, cd + 0.32, cz - 0.065),
        [(-0.015, 0.105), (0, 0.105), (0.02, 0.095), (0.03, 0.075)],
        role="camera_white_cap",
    )
    dome.revolve(
        (cx, cd + 0.32, cz - 0.065),
        [
            (-0.105, 0.012),
            (-0.095, 0.045),
            (-0.075, 0.070),
            (-0.045, 0.087),
            (-0.015, 0.090),
        ],
        role="camera_dark_closed_dome",
    )
    objects = [batch.finish() for batch in [shell, inserts, glazing, camera, dome]]
    objects.extend(welcome_text(metal, records[0]["insertFront"] + 0.001))
    return (
        objects,
        materials,
        records,
        {
            "x": cx,
            "z": cz,
            "wallDepth": cd,
            "supports": camera_support,
            "rejectedPatches": rejected,
            "nativeWallFrame": native_frame,
            "estimated": True,
        },
    )


def main():
    assert sha(BASE) == SHA
    assert not (OUT / "component.blend").exists(), (
        "Review existing component before replacement"
    )
    review = json.loads((OUT / "source-review-plan.json").read_text())
    assert all(sha(ROOT / r["path"]) == r["sha256"] for r in review["references"])
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = capture()
    assert (
        len(before["objects"]) == 8735
        and len(before["materials"]) == 2350
        and len(before["rooms"]) == 35
    )
    objects, materials, cabinets, camera = build()
    update_scene()
    after = capture()
    for key in ["objects", "materials", "visibility"]:
        assert all(after[key][name] == row for name, row in before[key].items()), key
    assert (
        after["rooms"] == before["rooms"]
        and after["campusRooms"] == before["campusRooms"]
    )
    component = OUT / "component.blend"
    bpy.data.libraries.write(
        str(component), set(objects), fake_user=True, compress=True
    )
    for obj in objects:
        obj.data.calc_loop_triangles()
    report = {
        "version": 262,
        "building": "OLD",
        "scope": "Four Houghton wall-mounted notice cabinets with closed frames,recessed inserts,thin clear covers and actual wall fixings;one visible entry-side camera fixture. Dimensions and exact stations estimated from undated photograph.",
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": SHA,
        "componentPath": str(component.relative_to(ROOT)),
        "componentSha256": sha(component),
        "targetCollection": COLLECTION,
        "destinationCollection": COLLECTION,
        "addedObjects": [o.name for o in objects],
        "archivedObjects": [],
        "changedObjects": [],
        "addedFingerprints": {o.name: object_fingerprint(o) for o in objects},
        "replacementMaterialBindings": {
            o.name: [m.name for m in o.data.materials] for o in objects
        },
        "newMaterials": [m.name for m in materials],
        "newMaterialGraphs": {m.name: material_fingerprint(m) for m in materials},
        "retainNewMaterials": True,
        "addedTriangles": sum(len(o.data.loop_triangles) for o in objects),
        "removedDisplayTriangles": 0,
        "cabinets": cabinets,
        "camera": camera,
        "sourceReviewSha256": sha(OUT / "source-review-plan.json"),
        "nativeInspectionSha256": sha(OUT / "native-inspection.json"),
        "limitations": review["limitations"]
        + [
            "Only the readable Welcome to LSE wording is transcribed;other insert fields are approximate colour blocks without fabricated current activities.",
            "Camera geometry represents a photographed physical housing only;model,operation and current coverage are unverified.",
            "No source photograph pixels are included in the component or public textures.",
        ],
    }
    report["netTriangleChange"] = report["addedTriangles"]
    (OUT / "protected-source-state.json").write_text(
        json.dumps(before, indent=2) + "\n"
    )
    (OUT / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
    assert sha(BASE) == SHA
    print(
        "HOUGHTON262_STREET_FIXTURE_COMPONENT_SAVED",
        len(objects),
        report["addedTriangles"],
        flush=True,
    )


if __name__ == "__main__":
    main()
