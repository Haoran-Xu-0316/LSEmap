"""Restore the photographed arched Lincoln Chambers title above the number3.

Original Georgia glyph contours are evaluated at production resolution4 and
rigidly arranged on a photo-estimated arc. The original number curve moves down
without shape changes. Both are seated1mm in front of the retained fanlight.
"""

import ast
import importlib.util
import json
import math
import re
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v256.blend"
SHA = "31657c42eb77323d2273bc525ad4db3164fbaa644ddbe6af3b66e44c8679efa1"
OUT = ROOT / "result/blender/lch257"
COLLECTION = "LCH_EXTERIOR"
SOURCE = "LCH_D5_sign.002"
NUMBER_SOURCE = "LCH_D5_sign.001"
SUPPORT = "GLASS181_LCH_NEXT_GLAZING149_porch_fanlights"
ADDED = "LCH257_arched_fanlight_title"
NUMBER_ADDED = "LCH257_lowered_fanlight_number"
CLEARANCE = 0.001
RADIUS = 0.58
ARC_SPAN = math.radians(140)
NUMBER_BASELINE = 2.76
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import (
    object_fingerprint,
    set_layer_hidden,
    update_scene,
)
from refine_col_finish252 import sha
from refine_kgs_exterior256 import glyph_ranges


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n")


def capture():
    spec = importlib.util.spec_from_file_location(
        "lch257_protection", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = SHA
    return helper.capture_source()


def protect(before, after):
    for name, row in before["objects"].items():
        expected = dict(row)
        if name in {SOURCE, NUMBER_SOURCE}:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
    assert all(
        after["materials"][name] == value for name, value in before["materials"].items()
    )
    assert (
        before["rooms"] == after["rooms"]
        and before["campusRooms"] == after["campusRooms"]
    )
    assert len(before["rooms"]) == 35


def evaluated_font(obj):
    resolution = obj.data.resolution_u
    obj.data.resolution_u = min(resolution, 4)
    update_scene()
    mesh = bpy.data.meshes.new_from_object(
        obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    )
    obj.data.resolution_u = resolution
    update_scene()
    return mesh, resolution


def fan_frame(text, support):
    """Select only real front-plane central triangles, excluding angled side fans."""
    inverse = text.matrix_world.inverted()
    vertices = [inverse @ (support.matrix_world @ v.co) for v in support.data.vertices]
    indices = set()
    for face in support.data.polygons:
        pts = [vertices[k] for k in face.vertices]
        normal = (pts[1] - pts[0]).cross(pts[2] - pts[0]).normalized()
        if abs(normal.z) > 0.9999:
            indices.update(face.vertices)
    assert len(indices) == 38, len(indices)
    points = [vertices[k] for k in sorted(indices)]
    assert max(p.z for p in points) - min(p.z for p in points) < 1e-5
    return {
        "centerX": (min(p.x for p in points) + max(p.x for p in points)) / 2,
        "springY": min(p.y for p in points),
        "radius": (max(p.x for p in points) - min(p.x for p in points)) / 2,
        "depth": max(p.z for p in points),
        "centralVertexIndices": sorted(indices),
    }


def glyph_samples(obj, groups):
    obj.data.calc_loop_triangles()
    normal = (obj.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
    for row in groups:
        indices = set(row["vertexIndices"])
        candidates = [
            t
            for t in obj.data.loop_triangles
            if set(t.vertices) <= indices and t.normal.z > 0.99
        ]
        assert candidates, row
        triangle = max(candidates, key=lambda t: t.area)
        point = obj.matrix_world @ (
            sum((obj.data.vertices[k].co for k in triangle.vertices), Vector()) / 3
        )
        row["frontTriangleVertexIndices"] = list(triangle.vertices)
        row["worldFrontTriangleCentroid"] = list(point)
        row["worldOutwardNormal"] = list(normal)
        row["worldProbeOrigin"] = list(point + normal * 0.025)
    return groups


def export_preview():
    states = {
        o.data: o.data.resolution_u
        for o in bpy.data.objects
        if o.type in {"FONT", "CURVE"}
    }
    for data, value in states.items():
        data.resolution_u = min(value, 4)
    update_scene()
    path = ROOT / "web/tools/export_scene.py"
    definitions = ast.parse(path.read_text())
    wanted = {
        "source_geometry_name",
        "surface_descriptor",
        "web_material",
        "clip_below_ground",
        "clone_group",
        "export_scene",
    }
    selected = [
        n
        for n in definitions.body
        if isinstance(n, ast.FunctionDef) and n.name in wanted
    ]
    assert len(selected) == len(wanted)
    ns = {
        "bpy": bpy,
        "bmesh": bmesh,
        "Vector": Vector,
        "re": re,
        "json": json,
        "full_detail": True,
        "material_cache": {},
        "OUTPUT": OUT,
        "depsgraph": bpy.context.evaluated_depsgraph_get(),
    }
    exec(compile(ast.Module(selected, type_ignores=[]), str(path), "exec"), ns)  # noqa: S102
    scene = bpy.data.scenes.new("LCH257_PRIVATE_PREVIEW")
    ns["clone_group"](list(bpy.data.collections[COLLECTION].all_objects), "LCH", scene)
    ns["export_scene"](scene, "preview.glb")
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.scenes.remove(scene)
    for data, value in states.items():
        data.resolution_u = value
    update_scene()


def main():
    assert sha(BASE) == SHA
    assert not (OUT / "component.blend").exists(), (
        "Review existing component before replacing"
    )
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.preferences.filepaths.save_version = 0
    update_scene()
    before = capture()
    write("protected-source-state.json", before)
    original = bpy.data.objects[SOURCE]
    number_source = bpy.data.objects[NUMBER_SOURCE]
    support = bpy.data.objects[SUPPORT]
    assert original.type == number_source.type == "FONT"
    assert original.data.body == "LINCOLN CHAMBERS" and number_source.data.body == "3"
    assert abs(original.matrix_world.translation.z - 2.74) < 1e-5
    assert bpy.data.objects["LCH_D5_sign.003"].data.body == "LINCOLN CHAMBERS"
    assert (
        not original.hide_render
        and not number_source.hide_render
        and not support.hide_render
    )
    frame = fan_frame(original, support)
    mesh, native_resolution = evaluated_font(original)
    coordinates = [list(v.co) for v in mesh.vertices]
    spans = glyph_ranges(mesh, expected=15)
    width = max(p[0] for p in coordinates) - min(p[0] for p in coordinates)
    centre = (max(p[0] for p in coordinates) + min(p[0] for p in coordinates)) / 2
    scale = RADIUS * ARC_SPAN / width
    old_depth = min(p[2] for p in coordinates)
    glyphs = []
    for index, (lo, hi) in enumerate(spans):
        cx = (lo + hi) / 2
        theta = (cx - centre) / width * ARC_SPAN
        anchor_x = frame["centerX"] + RADIUS * math.sin(theta)
        anchor_y = frame["springY"] + RADIUS * math.cos(theta)
        rotation = Matrix.Rotation(-theta, 3, "Z")
        indices = [
            k for k, p in enumerate(coordinates) if lo - 1e-6 <= p[0] <= hi + 1e-6
        ]
        for k in indices:
            p = Vector(coordinates[k])
            q = rotation @ Vector(((p.x - cx) * scale, p.y * scale, 0))
            mesh.vertices[k].co = (
                anchor_x + q.x,
                anchor_y + q.y,
                frame["depth"] + CLEARANCE + p.z - old_depth,
            )
        glyphs.append(
            {
                "index": index,
                "sourceXRange": [lo, hi],
                "sourceCenterX": cx,
                "angleRadians": theta,
                "anchor": [anchor_x, anchor_y],
                "vertexIndices": indices,
            }
        )
    assert sorted(k for row in glyphs for k in row["vertexIndices"]) == list(
        range(len(mesh.vertices))
    )
    mesh.update()
    obj = bpy.data.objects.new(ADDED, mesh)
    obj.matrix_world = original.matrix_world.copy()
    bpy.data.collections[COLLECTION].objects.link(obj)
    for added, source in [(obj, original)]:
        added["originalObject"] = source.name
        added["webGeometrySource"] = source.name
        added["destinationCollection"] = COLLECTION
        added["body"] = source.data.body
    glyph_samples(obj, glyphs)
    circle = [
        frame["radius"]
        - math.hypot(v.co.x - frame["centerX"], v.co.y - frame["springY"])
        for v in mesh.vertices
    ]
    assert min(circle) > 0.03, min(circle)
    number_mesh, number_resolution = evaluated_font(number_source)
    number_frame = fan_frame(number_source, support)
    number_shift = (
        number_frame["depth"] + CLEARANCE - min(v.co.z for v in number_mesh.vertices)
    )
    normal = (number_source.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
    number_obj = number_source.copy()
    number_obj.data = number_source.data.copy()
    number_obj.name = NUMBER_ADDED
    number_obj.matrix_world = number_source.matrix_world.copy()
    number_obj.matrix_world.translation += normal * number_shift + Vector(
        (0, 0, NUMBER_BASELINE - number_source.matrix_world.translation.z)
    )
    number_obj["originalObject"] = NUMBER_SOURCE
    number_obj["webGeometrySource"] = NUMBER_SOURCE
    number_obj["destinationCollection"] = COLLECTION
    bpy.data.collections[COLLECTION].objects.link(number_obj)
    update_scene()
    number_mesh.calc_loop_triangles()
    number_triangle = max(
        (t for t in number_mesh.loop_triangles if t.normal.z > 0.99),
        key=lambda t: t.area,
    )
    number_centroid = number_obj.matrix_world @ (
        sum((number_mesh.vertices[k].co for k in number_triangle.vertices), Vector())
        / 3
    )
    number_report = {
        "samples": [
            {
                "index": 0,
                "frontTriangleVertexIndices": list(number_triangle.vertices),
                "worldFrontTriangleCentroid": list(number_centroid),
                "worldOutwardNormal": list(normal),
                "worldProbeOrigin": list(number_centroid + normal * 0.025),
            }
        ],
        "sourceNativeResolution": number_resolution,
        "sourceProductionResolution": min(number_resolution, 4),
        "sourceMatrix": [list(r) for r in number_source.matrix_world],
        "replacementMatrix": [list(r) for r in number_obj.matrix_world],
        "normalShift": number_shift,
        "worldBaseline": NUMBER_BASELINE,
        "productionCoordinates": [list(v.co) for v in number_mesh.vertices],
    }
    for source in [original, number_source]:
        source.hide_render = True
        set_layer_hidden(source, True)
    update_scene()
    after = capture()
    protect(before, after)
    component = OUT / "component.blend"
    bpy.data.libraries.write(
        str(component), {obj, number_obj}, fake_user=True, compress=True
    )
    candidate = json.loads((OUT / "candidate-plan.json").read_text())
    write(
        "audit.json",
        {
            "version": 257,
            "code": "LCH",
            "baseline": str(BASE.relative_to(ROOT)),
            "baselineSha256": SHA,
            "componentPath": str(component.relative_to(ROOT)),
            "componentSha256": sha(component),
            "targetCollection": COLLECTION,
            "destinationCollection": COLLECTION,
            "addedObjects": [ADDED, NUMBER_ADDED],
            "archivedObjects": [SOURCE, NUMBER_SOURCE],
            "changedObjects": [],
            "addedFingerprints": {
                o.name: object_fingerprint(o) for o in [obj, number_obj]
            },
            "replacementMaterialBindings": {
                o.name: [m.name for m in o.data.materials] for o in [obj, number_obj]
            },
            "replacementFontBindings": {
                NUMBER_ADDED: {
                    key: getattr(number_source.data, key).name
                    for key in ["font", "font_bold", "font_italic", "font_bold_italic"]
                }
            },
            "body": original.data.body,
            "glyphs": glyphs,
            "uniformInPlaneScale": scale,
            "arcRadiusEstimate": RADIUS,
            "arcSpanDegreesEstimate": math.degrees(ARC_SPAN),
            "clearanceMetres": CLEARANCE,
            "fanlightFrame": frame,
            "sourceProductionCoordinates": coordinates,
            "curveResolution": {
                "native": native_resolution,
                "production": min(native_resolution, 4),
            },
            "numbers": number_report,
            "geometryBudget": {
                "sourceVertices": len(coordinates),
                "replacementVertices": len(mesh.vertices),
                "sourceAndReplacementTriangles": sum(
                    len(p.vertices) - 2 for p in mesh.polygons
                ),
                "triangleGrowth": 0,
            },
            "minimumCircleClearance": min(circle),
            "sources": candidate["sources"],
            "otherOriginalFontsPreserved": [
                "LCH_D5_sign.003",
                "LCH_D5_sign.004",
                "LCH_D5_sign.005",
            ],
            "limitations": [
                "Two historical photos establish arched title above3, not2026condition or measured lettering.",
                "Uniform in-plane scale,140degree arc,.58mradius and2.76mnumber baseline are proportional display estimates.",
                "Original glyph outlines, production-resolution topology, UV, materials and curve/font data retained; only two source identities replaced.",
                "Actual fanlight front supplies letter back clearance about1mm. Glass and wood geometry/optics, other wording and35rooms are unchanged.",
                "Unreadable lower address text not invented.",
            ],
            "status": "saved_awaiting_independent_reopen_and_production_review",
        },
    )
    export_preview()
    protect(before, capture())
    assert sha(BASE) == SHA
    print("LCH257_TITLE_COMPONENT_SAVED", sha(component), flush=True)


if __name__ == "__main__":
    main()
