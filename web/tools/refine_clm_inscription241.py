"""Conform the retained Clement House school name to its curved stone frieze.

Fixed Blender editor workflow. Reuse the original font contours, size, wording,
height and material. Only the inscription follows the existing front-face path;
no changes to stone, glazing, room geometry or other building dimensions.
The source photograph is undated; this is not surveyed inscription depth.
"""

import ast
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v239.blend"
BASE_SHA = "07fae16d2afbe82fed9352b5dbf2fd8df05e809158de72541b09c7b32328403c"
OUT = ROOT / "result/blender/clm-inscription241"
PROOF = ROOT / "result/blender/stage241"
SOURCE = "CLM_D3_street_inscription"
ADDED = "CLM241_curved_street_inscription"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
import itertools

from integrate_exterior_round194 import (
    accepted_fingerprints,
    object_fingerprint,
    update_scene,
)
from refine_kgs_surface237 import normal_record

spec = importlib.util.spec_from_file_location(
    "verify_campus241", ROOT / "web/tests/verify_campus241.py"
)
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def export_private(label):
    tree = ast.parse((ROOT / "web/tools/export_scene.py").read_text())
    wanted = {
        "source_geometry_name",
        "surface_descriptor",
        "web_material",
        "clip_below_ground",
        "clone_group",
        "export_scene",
    }
    namespace = {
        "bpy": bpy,
        "bmesh": bmesh,
        "Vector": Vector,
        "re": __import__("re"),
        "json": json,
        "full_detail": True,
        "material_cache": {},
        "OUTPUT": OUT,
        "depsgraph": bpy.context.evaluated_depsgraph_get(),
    }
    exec(  # noqa: S102 - Only named exporter definitions from this repository.
        compile(
            ast.Module(
                body=[
                    node
                    for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name in wanted
                ],
                type_ignores=[],
            ),
            "production-export-functions",
            "exec",
        ),
        namespace,
    )
    scene = bpy.data.scenes.new("CLM241_REVIEW_" + label)
    namespace["clone_group"](
        list(bpy.data.collections["CLM_EXTERIOR"].all_objects), "CLM", scene
    )
    namespace["export_scene"](scene, label + ".glb")
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.scenes.remove(scene)
    update_scene()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    PROOF.mkdir(parents=True, exist_ok=True)
    assert sha(BASE) == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    snapshot = PROOF / "protected-source-state.json"
    if snapshot.exists():
        protected = json.loads(snapshot.read_text())
        assert protected["baselineSha256"] == BASE_SHA
    else:
        protected = verifier.capture_source()
        write(snapshot, protected)
    assert {
        name: row["fingerprint"] for name, row in protected["objects"].items()
    } == accepted_fingerprints(ROOT / "result/blender/stage239", BASE_SHA)
    assert {o.name: object_fingerprint(o) for o in bpy.data.objects} == {
        name: row["fingerprint"] for name, row in protected["objects"].items()
    }
    print("CLM241_BASELINE_PROTECTED", len(protected["objects"]), flush=True)
    export_private("before")
    source = bpy.data.objects[SOURCE]
    original_visibility = source.hide_render
    mesh = bpy.data.meshes.new_from_object(
        source.evaluated_get(bpy.context.evaluated_depsgraph_get())
    )
    original_vertices = len(mesh.vertices)
    sites = json.loads((ROOT / "result/blender/site_geometry.json").read_text())
    building = next(b for b in sites["buildings"] if b["code"] == "CLM")
    points = [Vector(building["rings"][0][i]) for i in (5, 4, 3, 2, 1)]
    tangents = [(b - a).normalized() for a, b in itertools.pairwise(points)]
    normals = [Vector((t.y, -t.x)) for t in tangents]
    miters = [normals[0]]
    for a, b in itertools.pairwise(normals):
        bisector = (a + b).normalized()
        miters.append(bisector / bisector.dot(a))
    miters.append(normals[-1])
    face_path = [point + miter * 0.375 for point, miter in zip(points, miters)]
    lengths = [(b - a).length for a, b in itertools.pairwise(face_path)]
    cumulative = [0]
    for length in lengths:
        cumulative.append(cumulative[-1] + length)
    origin = source.matrix_world.translation.xy
    projections = []
    for index, (a, b) in enumerate(itertools.pairwise(face_path)):
        tangent = (b - a).normalized()
        distance = max(0, min((origin - a).dot(tangent), lengths[index]))
        projections.append(
            ((origin - a - tangent * distance).length, cumulative[index] + distance)
        )
    anchor = min(projections)[1]
    x_scale = source.matrix_world.to_3x3().col[0].length
    depth_scale = source.matrix_world.to_3x3().col[2].length
    # Split faces at actual frontage joins before bending, so no triangle takes
    # a shortcut through the convex supporting stone.
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6)
    for joint in cumulative[1:-1]:
        local_x = (joint - anchor) / x_scale
        bmesh.ops.bisect_plane(
            bm,
            geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
            plane_co=(local_x, 0, 0),
            plane_no=(1, 0, 0),
            clear_inner=False,
            clear_outer=False,
            dist=1e-7,
        )
    bm.to_mesh(mesh)
    bm.free()
    minimum_depth = min(v.co.z for v in mesh.vertices)
    original_height_range = [
        min((source.matrix_world @ v.co).z for v in mesh.vertices),
        max((source.matrix_world @ v.co).z for v in mesh.vertices),
    ]
    for vertex in mesh.vertices:
        local = vertex.co.copy()
        distance = anchor + local.x * x_scale
        assert 0 < distance < cumulative[-1]
        index = next(i for i in range(len(lengths)) if distance <= cumulative[i + 1])
        tangent = (face_path[index + 1] - face_path[index]).normalized()
        point = face_path[index] + tangent * (distance - cumulative[index])
        clearance = 0.001 + (local.z - minimum_depth) * depth_scale
        xy = point + normals[index] * clearance
        z = (source.matrix_world @ local).z
        vertex.co = (xy.x, xy.y, z)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    assert all(edge.is_manifold for edge in bm.edges)
    bm.to_mesh(mesh)
    bm.free()
    mesh.name = ADDED
    replacement = bpy.data.objects.new(ADDED, mesh)
    bpy.data.collections["CLM_EXTERIOR"].objects.link(replacement)
    replacement["originalObject"] = SOURCE
    replacement["webGeometrySource"] = SOURCE
    replacement["body"] = source.data.body
    replacement["scope"] = (
        "Original glyphs follow existing convex frieze;1mm back clearance and retained12mm font thickness are display estimates, not engraving measurements"
    )
    source.hide_render = True
    source.hide_set(True)
    update_scene()
    contact = verifier.verify_contact(replacement)
    assert abs(min(v.co.z for v in mesh.vertices) - original_height_range[0]) < 0.000002
    assert abs(max(v.co.z for v in mesh.vertices) - original_height_range[1]) < 0.000002
    export_private("after")
    source.hide_render = original_visibility
    assert all(
        object_fingerprint(bpy.data.objects[name]) == row["fingerprint"]
        for name, row in protected["objects"].items()
    )
    component = OUT / "component.blend"
    bpy.data.libraries.write(
        str(component), {replacement}, fake_user=True, compress=True
    )
    audit = {
        "version": 241,
        "code": "CLM",
        "baselineSha256": BASE_SHA,
        "componentPath": str(component.relative_to(ROOT)),
        "componentSha256": sha(component),
        "destinationCollection": "CLM_EXTERIOR",
        "addedObjects": [ADDED],
        "archivedObjects": [SOURCE],
        "addedFingerprints": {ADDED: object_fingerprint(replacement)},
        "replacementNormals": {ADDED: normal_record(mesh)},
        "replacementMaterialBindings": {ADDED: [m.name for m in mesh.materials]},
        "originalGlyphVertices": original_vertices,
        "finalVertices": len(mesh.vertices),
        "triangles": sum(len(p.vertices) - 2 for p in mesh.polygons),
        "contact": contact,
        "anchorPathDistance": anchor,
        "frontPath": [list(p) for p in face_path],
        "scope": "Conform the existing school-name inscription to its convex stone frieze, preserving wording, original font contours, size, height and material. Stone, glass, rooms and other buildings remain unchanged.",
        "evidence": [
            {
                "url": "https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Property-and-Space/LSE-Property-Handbook.pdf",
                "page": 18,
                "local": "data/documents/property_handbook.pdf",
                "sha256": sha(ROOT / "data/documents/property_handbook.pdf"),
                "supports": "School-name inscription follows curved entablature above paired columns",
                "pdfCreated": "2025-10-08",
                "photographCaptureDate": "unknown",
            }
        ],
        "limitations": [
            "Existing font contour, inscription extent and stroke depth remain authored estimates.",
            "No current2026 survey or exact engraving reconstruction.",
            "Unseen elevations and complete building interiors remain incomplete.",
        ],
    }
    write(OUT / "audit.json", audit)
    assert sha(BASE) == BASE_SHA
    print("CLM241_COMPONENT_READY", contact, flush=True)


if __name__ == "__main__":
    main()
