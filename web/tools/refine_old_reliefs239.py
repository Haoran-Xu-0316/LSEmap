"""Replace the five segmented Clare relief studies with continuous shallow forms.

Run in Blender's editor. Photograph-supported pose ordering and registration are
retained. Contours and depth remain an authored interpretation, not a sculpture
scan. The accepted campus is read-only; this writes a review component only.
"""

from pathlib import Path
import ast
import hashlib
import json
import math
import sys

import bpy
import bmesh
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v238.blend"
SHA = "8f837ee09610a13d31f24fe586737b8f80ddf09a0791e61649047999302995e5"
OUT = ROOT / "result/blender/old-clare239"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint, update_scene
from refine_portsmouth_exterior207 import material_fingerprint
from refine_old_exterior194 import add_world_stone_uv
from refine_kgs_surface237 import normal_record


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n")


def export_private(label):
    """Use actual production merge, UV selection and material conversion."""
    source = ast.parse((ROOT / "web/tools/export_scene.py").read_text())
    wanted = {
        "source_geometry_name",
        "surface_descriptor",
        "web_material",
        "clip_below_ground",
        "clone_group",
        "export_scene",
    }
    ns = dict(
        bpy=bpy,
        bmesh=bmesh,
        Vector=Vector,
        re=__import__("re"),
        json=json,
        full_detail=True,
        material_cache={},
        OUTPUT=OUT,
        depsgraph=bpy.context.evaluated_depsgraph_get(),
    )
    exec(
        compile(
            ast.Module(
                body=[
                    n
                    for n in source.body
                    if isinstance(n, ast.FunctionDef) and n.name in wanted
                ],
                type_ignores=[],
            ),
            "production-export-functions",
            "exec",
        ),
        ns,
    )
    scene = bpy.data.scenes.new("OLD239_PRIVATE_" + label)
    ns["clone_group"](
        list(bpy.data.collections["OLD_EXTERIOR"].all_objects), "OLD", scene
    )
    ns["export_scene"](scene, label + ".glb")
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.scenes.remove(scene)
    update_scene()


class ReliefMesh:
    """Local x/depth/z mesh; curved tube junctions are fused before world mapping."""

    def __init__(self):
        self.vertices, self.faces = [], []

    def add(self, vertices, faces):
        start = len(self.vertices)
        self.vertices.extend(vertices)
        self.faces.extend(tuple(start + i for i in f) for f in faces)

    def tube(self, path, radii, depth=0.14, flatten=0.48):
        points = [Vector(p) for p in path]
        radii = radii if isinstance(radii, list) else [radii] * len(points)
        samples = []
        # Low-tension Hermite interpolation retains elbows and bends while
        # removing the previous three-ring, cut-ended construction.
        for i in range(len(points) - 1):
            a, b = points[i : i + 2]
            ta = (b - points[max(0, i - 1)]) * 0.38
            tb = (points[min(len(points) - 1, i + 2)] - a) * 0.38
            for j in range(8):
                t = j / 8
                q = (2 * t**3 - 3 * t * t + 1) * a + (t**3 - 2 * t * t + t) * ta
                q += (-2 * t**3 + 3 * t * t) * b + (t**3 - t * t) * tb
                samples.append((q, radii[i] * (1 - t) + radii[i + 1] * t))
        samples.append((points[-1], radii[-1]))
        vertices, faces, sides = [], [], 16
        for i, (q, r) in enumerate(samples):
            tangent = (
                samples[min(i + 1, len(samples) - 1)][0] - samples[max(i - 1, 0)][0]
            ).normalized()
            perpendicular = Vector((-tangent.y, tangent.x))
            for k in range(sides):
                angle = k * math.tau / sides
                offset = perpendicular * (r * math.cos(angle))
                vertices.append(
                    (
                        q.x + offset.x,
                        depth + r * flatten * math.sin(angle),
                        q.y + offset.y,
                    )
                )
        for i in range(len(samples) - 1):
            faces.extend(
                (
                    i * sides + k,
                    i * sides + (k + 1) % sides,
                    (i + 1) * sides + (k + 1) % sides,
                    (i + 1) * sides + k,
                )
                for k in range(sides)
            )
        faces.extend(
            [
                tuple(reversed(range(sides))),
                tuple(range((len(samples) - 1) * sides, len(samples) * sides)),
            ]
        )
        self.add(vertices, faces)
        # Small ellipsoids close the formerly flat, disconnected limb ends.
        for q, r in (samples[0], samples[-1]):
            self.ellipsoid((q.x, depth, q.y), (r, r * flatten, r))

    def ellipsoid(self, center, scale):
        vertices, faces = [], []
        sides, rings = 20, 12
        for j in range(rings + 1):
            a = math.pi * (j + 0.001) / (rings + 0.002)
            for k in range(sides):
                b = k * math.tau / sides
                vertices.append(
                    (
                        center[0] + scale[0] * math.sin(a) * math.cos(b),
                        center[1] + scale[1] * math.sin(a) * math.sin(b),
                        center[2] + scale[2] * math.cos(a),
                    )
                )
        faces.extend(
            (
                j * sides + k,
                j * sides + (k + 1) % sides,
                (j + 1) * sides + (k + 1) % sides,
                (j + 1) * sides + k,
            )
            for j in range(rings)
            for k in range(sides)
        )
        faces.extend(
            [
                tuple(reversed(range(sides))),
                tuple(range(rings * sides, (rings + 1) * sides)),
            ]
        )
        self.add(vertices, faces)

    def torso(self, outline):
        count = len(outline)
        triangles = tessellate_polygon([[Vector((x, z, 0)) for x, z in outline]])
        vertices = [(x, d, z) for d in [0.085, 0.155] for x, z in outline]
        faces = [tuple(reversed(t)) for t in triangles]
        faces += [tuple(i + count for i in t) for t in triangles]
        faces += [
            (i, (i + 1) % count, (i + 1) % count + count, i + count)
            for i in range(count)
        ]
        self.add(vertices, faces)

    def object(self, name):
        mesh = bpy.data.meshes.new(name + "_mesh")
        mesh.from_pydata(self.vertices, [], self.faces)
        mesh.update()
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(name, mesh)
        bpy.data.collections["OLD_EXTERIOR"].objects.link(obj)
        return obj


def apply(obj, modifier):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.select_set(False)


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    assert sha(BASE) == SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = {o.name: object_fingerprint(o) for o in bpy.data.objects}
    original_materials = {m.name: material_fingerprint(m) for m in bpy.data.materials}
    export_private("before")
    study = json.loads(
        (ROOT / "result/blender/stage89/old-clare-reliefs-audit.json").read_text()
    )
    frame = study["frame"]
    origin, axis, normal = [Vector(frame[k]) for k in ["origin", "right", "outward"]]
    replacements, changes = [], []
    for panel in study["panels"]:
        index = panel["panel"]
        source_name = "OLD194_STONE_" + panel["name"]
        source = bpy.data.objects[source_name]
        assert not source.hide_render and not source.modifiers
        body = ReliefMesh()
        body.torso(panel["outline"])
        for path, radii in panel["limbs"]:
            body.tube(path, radii)
        hx, hz = panel["head"]
        shoulder = min(
            panel["outline"], key=lambda q: (q[0] - hx) ** 2 + (q[1] - hz) ** 2
        )
        body.tube(
            [shoulder, (hx - 0.045, hz - 0.085), (hx, hz - 0.045)],
            [0.073, 0.062, 0.055],
            0.145,
        )
        body.ellipsoid((hx, 0.15, hz), (0.108, 0.063, 0.13))
        obj = body.object("OLD239_relief_" + str(index))
        # Fuse intersecting volumes rather than hiding the same joints under
        # new disconnected shapes. This runs only during authoring, not on web.
        remesh = obj.modifiers.new("Continuous shallow carved body", "REMESH")
        remesh.mode = "VOXEL"
        remesh.voxel_size = 0.011
        remesh.use_smooth_shade = True
        apply(obj, remesh)
        smooth = obj.modifiers.new("Remove voxel stair steps", "SMOOTH")
        smooth.factor = 0.6
        smooth.iterations = 3
        apply(obj, smooth)
        decimate = obj.modifiers.new("Bound architectural relief budget", "DECIMATE")
        decimate.ratio = 0.24
        apply(obj, decimate)
        # Keep each photo-supported ribbon distinct from the body. No unseen
        # sixth panel, portrait likeness, eye pupils or invented attributes.
        detail = ReliefMesh()
        for wave in panel["waves"]:
            detail.tube(wave, 0.023, 0.10, 0.32)
        detail.tube(
            [
                (hx - 0.075, hz + 0.01),
                (hx - 0.025, hz + 0.03),
                (hx + 0.045, hz + 0.015),
            ],
            0.011,
            0.208,
            0.45,
        )
        detail.tube(
            [
                (hx + 0.005, hz + 0.015),
                (hx - 0.018, hz - 0.035),
                (hx + 0.025, hz - 0.045),
            ],
            0.013,
            0.208,
            0.45,
        )
        detail.tube(
            [(hx - 0.03, hz - 0.073), (hx + 0.023, hz - 0.076)], 0.006, 0.208, 0.4
        )
        extra = detail.object("OLD239_temporary_incisions")
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        extra.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.join()
        # Historical normalized pose coordinates preserve exact panel centres.
        for vertex in obj.data.vertices:
            x, d, z = vertex.co
            vertex.co = (
                origin
                + axis * (panel["centre"] + x * study["width"] * 0.44)
                + normal * d
                + Vector((0, 0, 5.37 + z * 0.96))
            )
        obj.data.update()
        obj.data.materials.clear()
        obj.data.materials.append(source.data.materials[0])
        for face in obj.data.polygons:
            face.use_smooth = True
        add_world_stone_uv(obj)
        obj["originalObject"] = source_name
        obj["webGeometrySource"] = source.get("webGeometrySource", source_name)
        obj["reference_panel"] = index
        obj["scope"] = (
            "Continuous shallow interpretation of existing G,E,F,D,H frontage poses; no scanned likeness or unseen side panel"
        )
        points = [v.co - origin for v in obj.data.vertices]
        coords = [(p.dot(axis) - panel["centre"], p.dot(normal), p.z) for p in points]
        bounds = [
            [min(p[i] for p in coords) for i in range(3)],
            [max(p[i] for p in coords) for i in range(3)],
        ]
        triangles = sum(len(p.vertices) - 2 for p in obj.data.polygons)
        assert 0.04 < bounds[0][1] and bounds[1][1] < 0.23, bounds
        assert 5.30 < bounds[0][2] and bounds[1][2] < 6.34, bounds
        assert triangles < 23000, triangles
        source.hide_render = True
        source.hide_set(True)
        replacements.append(obj)
        changes.append(
            dict(
                source=source_name,
                replacement=obj.name,
                panel=index,
                sourcePose=study["frontageOrder"][index - 1],
                triangles=triangles,
                bounds=bounds,
                centre=panel["centre"],
                uv="Original retained stone finish reprojected with the approved4.5m world-space mapping",
            )
        )
        print("OLD239_PANEL", index, triangles, flush=True)
    update_scene()
    export_private("after")
    assert all(object_fingerprint(bpy.data.objects[n]) == v for n, v in before.items())
    assert all(
        material_fingerprint(bpy.data.materials[n]) == v
        for n, v in original_materials.items()
    )
    component = OUT / "component.blend"
    bpy.data.libraries.write(
        str(component), set(replacements), fake_user=True, compress=True
    )
    audit = dict(
        version=239,
        code="OLD",
        baselineSha256=SHA,
        componentPath=str(component.relative_to(ROOT)),
        componentSha256=sha(component),
        destinationCollection="OLD_EXTERIOR",
        addedObjects=[o.name for o in replacements],
        archivedObjects=[c["source"] for c in changes],
        addedFingerprints={o.name: object_fingerprint(o) for o in replacements},
        replacementMaterialBindings={
            o.name: [m.name for m in o.data.materials] for o in replacements
        },
        replacementNormals={o.name: normal_record(o.data) for o in replacements},
        changes=changes,
        originalObjectsVerified=len(before),
        originalMaterialNodesVerified=len(original_materials),
        frame=frame,
        sourceStudy="data/collections/old-clare-reference/architectural-sculpture-2010.pdf",
        sourceStudySha256=sha(
            ROOT
            / "data/collections/old-clare-reference/architectural-sculpture-2010.pdf"
        ),
        scope="Rebuild the five segmented Clare Market relief studies as continuous shallow bodies with curved limbs and joined necks, retaining the registered G,E,F,D,H ordering, stone finish, backing panels and all other architecture.",
        evidence=[
            "https://www.lse.ac.uk/Events/arts-and-music/art-on-campus/art-on-campus",
            study["studyUrl"],
        ],
        limitations=[
            "Five front poses are authored photographic interpretations, not scans or measured carving depths.",
            "The undated study was published in2010. No assertion of2026 sculptural condition.",
            "The unseen sixth side panel and whole-building current interiors remain unverified.",
        ],
    )
    write("audit.json", audit)
    assert sha(BASE) == SHA
    print("OLD239_COMPONENT_READY", sum(c["triangles"] for c in changes), flush=True)


if __name__ == "__main__":
    run()
