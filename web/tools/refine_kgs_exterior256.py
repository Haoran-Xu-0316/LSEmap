"""Place the original King's Chambers lettering on its photographed shallow arc.

Only the accepted inscription is copied. Its evaluated glyph contours and gold
finish survive, with a bounded photo-estimated uniform scale and rigid rotation
of each glyph. The existing opaque green mosaic and every other source remain
unchanged. Fixed Blender project paths; no shared release files are written.
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
OUT = ROOT / "result/blender/kgs256"
BASE = ROOT / "result/blender/LSE_campus_detailed_v255.blend"
SHA = "bcb85b059475971cc0e684597d2cc8e5081d47302e669e17d48a923ea44fb3ad"
SOURCE = "KGS_D5_sign.001"
NUMBER_SOURCE = "KGS_D5_sign.002"
NUMBER_ADDED = "KGS256_seated_portal_numbers"
SUPPORT = "KGS_D5_arched_fanlight_green"
ADDED = "KGS256_curved_portal_inscription"
COLLECTION = "KGS_EXTERIOR"
SCALE = 1.45
CLEARANCE = 0.001
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import (
    object_fingerprint,
    set_layer_hidden,
    update_scene,
)
from refine_col_finish252 import sha


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n")


def capture():
    spec = importlib.util.spec_from_file_location(
        "kgs256_protection", ROOT / "web/tests/verify_campus241.py"
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
    assert all(after["materials"][n] == r for n, r in before["materials"].items())
    assert (
        after["rooms"] == before["rooms"]
        and after["campusRooms"] == before["campusRooms"]
    )
    assert len(before["rooms"]) == 35


def glyph_ranges(mesh, expected=14):
    """Merge projected contour components into original, separated glyph spans."""
    neighbors = [set() for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        neighbors[a].add(b)
        neighbors[b].add(a)
    remaining = set(range(len(mesh.vertices)))
    ranges = []
    while remaining:
        seed = remaining.pop()
        stack = [seed]
        ids = [seed]
        while stack:
            for n in neighbors[stack.pop()]:
                if n in remaining:
                    remaining.remove(n)
                    ids.append(n)
                    stack.append(n)
        xs = [mesh.vertices[i].co.x for i in ids]
        ranges.append([min(xs), max(xs)])
    merged = []
    for lo, hi in sorted(ranges):
        if merged and lo <= merged[-1][1] + 1e-6:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([lo, hi])
    assert len(merged) == expected, merged
    return merged


def export_private(label):
    states = {
        o.data: o.data.resolution_u
        for o in bpy.data.objects
        if o.type in {"FONT", "CURVE"}
    }
    for data, res in states.items():
        data.resolution_u = min(res, 4)
    update_scene()
    tree = ast.parse((ROOT / "web/tools/export_scene.py").read_text())
    wanted = {
        "source_geometry_name",
        "surface_descriptor",
        "web_material",
        "clip_below_ground",
        "clone_group",
        "export_scene",
    }
    definitions = [
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in wanted
    ]
    assert len(definitions) == len(wanted)
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
    exec(  # noqa: S102 - Named trusted functions from the production exporter.
        compile(
            ast.Module(body=definitions, type_ignores=[]),
            "trusted-production-export-functions",
            "exec",
        ),
        ns,
    )
    scene = bpy.data.scenes.new("KGS256_PRIVATE_" + label)
    ns["clone_group"](list(bpy.data.collections[COLLECTION].all_objects), "KGS", scene)
    ns["export_scene"](scene, label + ".glb")
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.scenes.remove(scene)
    for data, res in states.items():
        data.resolution_u = res
    update_scene()


def main():
    assert sha(BASE) == SHA
    OUT.mkdir(parents=True, exist_ok=True)
    assert not (OUT / "component.blend").exists(), (
        "Review existing component before replacement"
    )
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    bpy.context.preferences.filepaths.save_version = 0
    before = capture()
    write("protected-source-state.json", before)
    original = bpy.data.objects[SOURCE]
    support = bpy.data.objects[SUPPORT]
    assert original.type == "FONT" and original.data.body == "KING'S CHAMBERS"
    assert not original.hide_render and not support.hide_render
    support_shader = next(
        n
        for n in support.data.materials[0].node_tree.nodes
        if n.type == "BSDF_PRINCIPLED"
    )
    assert (
        support_shader.inputs["Alpha"].default_value == 1
        and support_shader.inputs["Transmission Weight"].default_value == 0
    )
    export_private("before")
    # The original text frame supplies right/up/outward; do not infer a new wall.
    inverse = original.matrix_world.inverted()
    support_local = [
        inverse @ (support.matrix_world @ v.co) for v in support.data.vertices
    ]
    support_depth = sum(p.z for p in support_local) / len(support_local)
    assert max(p.z for p in support_local) - min(p.z for p in support_local) < 1e-5
    native_resolution = original.data.resolution_u
    original.data.resolution_u = min(native_resolution, 4)
    update_scene()
    mesh = bpy.data.meshes.new_from_object(
        original.evaluated_get(bpy.context.evaluated_depsgraph_get())
    )
    original.data.resolution_u = native_resolution
    update_scene()
    original_mesh_coordinates = [list(v.co) for v in mesh.vertices]
    original_mesh_triangles = sum(len(f.vertices) - 2 for f in mesh.polygons)
    spans = glyph_ranges(mesh)
    width = max(v.co.x for v in mesh.vertices) - min(v.co.x for v in mesh.vertices)
    center = (
        max(v.co.x for v in mesh.vertices) + min(v.co.x for v in mesh.vertices)
    ) / 2
    radius = (width * SCALE) ** 2 / (8 * (width * SCALE * 0.10)) + (
        width * SCALE * 0.10
    ) / 2
    old_min_depth = min(v.co.z for v in mesh.vertices)
    records = []
    for index, (lo, hi) in enumerate(spans):
        cx = (lo + hi) / 2
        anchor = (cx - center) * SCALE
        theta = math.asin(anchor / radius)
        lift = radius - math.sqrt(radius * radius - anchor * anchor)
        rotation = Matrix.Rotation(theta, 3, "Z")
        ids = [
            v.index
            for v in mesh.vertices
            if lo - 1e-6 <= original_mesh_coordinates[v.index][0] <= hi + 1e-6
        ]
        for i in ids:
            v = mesh.vertices[i]
            p = Vector(original_mesh_coordinates[i])
            xy = rotation @ Vector(((p.x - cx) * SCALE, p.y * SCALE, 0))
            v.co = (
                center + anchor + xy.x,
                lift + xy.y,
                support_depth + CLEARANCE + (p.z - old_min_depth),
            )
        records.append(
            {
                "index": index,
                "sourceXRange": [lo, hi],
                "sourceCenterX": cx,
                "angleRadians": theta,
                "anchorX": center + anchor,
                "baselineLift": lift,
                "vertexIndices": ids,
            }
        )
    mesh.update()
    mesh.calc_loop_triangles()
    # One actual filled front triangle per glyph avoids letter counters/holes.
    for row in records:
        ids = set(row["vertexIndices"])
        candidates = [
            t
            for t in mesh.loop_triangles
            if set(t.vertices) <= ids and t.normal.z > 0.99
        ]
        assert candidates
        triangle = max(candidates, key=lambda t: t.area)
        point = sum((mesh.vertices[i].co for i in triangle.vertices), Vector()) / 3
        world = original.matrix_world @ point
        normal = (original.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
        row["frontTriangleVertexIndices"] = list(triangle.vertices)
        row["worldFrontTriangleCentroid"] = list(world)
        row["worldOutwardNormal"] = list(normal)
        row["worldProbeOrigin"] = list(world + normal * 0.025)
    mesh.update()
    obj = bpy.data.objects.new(ADDED, mesh)
    obj.matrix_world = original.matrix_world.copy()
    bpy.data.collections[COLLECTION].objects.link(obj)
    obj["originalObject"] = SOURCE
    obj["webGeometrySource"] = SOURCE
    obj["body"] = original.data.body
    obj["destinationCollection"] = COLLECTION
    obj["scope"] = (
        "Retained glyph contours rigidly rotated on a photo-estimated shallow arc; original gold finish and mosaic unchanged"
    )
    # Record source-boundary proof in the actual portal frame, not world AABB.
    xs = [p.x for p in support_local]
    ys = [p.y for p in support_local]
    ox = (min(xs) + max(xs)) / 2
    spring = min(ys)
    r = (max(xs) - min(xs)) / 2
    assigned_indices = [i for row in records for i in row["vertexIndices"]]
    assert sorted(assigned_indices) == list(range(len(mesh.vertices))), (
        "Glyph groups must partition original vertices"
    )
    clear = []
    failures = []
    for v in mesh.vertices:
        clear.append(r - math.hypot(v.co.x - ox, v.co.y - spring))
        if not (v.co.y > spring + 0.05 and clear[-1] > 0.05):
            failures.append(
                {
                    "index": v.index,
                    "coordinate": list(v.co),
                    "bottomClearance": v.co.y - spring,
                    "circleClearance": clear[-1],
                }
            )
    write(
        "layout-diagnostic.json",
        {
            "builderSha256": sha(Path(__file__)),
            "supportCenterX": ox,
            "supportSpringY": spring,
            "supportRadius": r,
            "supportLocalBounds": [
                [min(p[i] for p in support_local), max(p[i] for p in support_local)]
                for i in range(3)
            ],
            "glyphGroups": records,
            "failures": failures,
            "minimumCircleClearance": min(clear),
            "verticesAssignedOnce": True,
        },
    )
    assert not failures, failures[:3]
    # Door numbers have the same inherited 144mm gap. Preserve their complete
    # curve and in-plane placement, correcting only normal seating.
    number_source = bpy.data.objects[NUMBER_SOURCE]
    assert number_source.type == "FONT" and number_source.data.body == "29     31"
    assert not number_source.hide_render
    number_resolution = number_source.data.resolution_u
    number_source.data.resolution_u = min(number_resolution, 4)
    update_scene()
    number_mesh = bpy.data.meshes.new_from_object(
        number_source.evaluated_get(bpy.context.evaluated_depsgraph_get())
    )
    number_source.data.resolution_u = number_resolution
    update_scene()
    number_inverse = number_source.matrix_world.inverted()
    number_support = [
        number_inverse @ (support.matrix_world @ v.co) for v in support.data.vertices
    ]
    number_depth = sum(p.z for p in number_support) / len(number_support)
    number_back = min(v.co.z for v in number_mesh.vertices)
    number_shift = number_depth + CLEARANCE - number_back
    assert abs(number_shift + 0.143) < 1e-5
    number_obj = number_source.copy()
    number_obj.data = number_source.data.copy()
    number_obj.name = NUMBER_ADDED
    number_obj.matrix_world = number_source.matrix_world.copy()
    number_normal = (
        number_source.matrix_world.to_3x3() @ Vector((0, 0, 1))
    ).normalized()
    number_obj.matrix_world.translation += number_normal * number_shift
    number_obj["originalObject"] = NUMBER_SOURCE
    number_obj["webGeometrySource"] = NUMBER_SOURCE
    number_obj["body"] = number_source.data.body
    number_obj["destinationCollection"] = COLLECTION
    bpy.data.collections[COLLECTION].objects.link(number_obj)
    update_scene()
    number_mesh.calc_loop_triangles()
    number_records = []
    for index, (lo, hi) in enumerate(glyph_ranges(number_mesh, expected=4)):
        ids = {
            v.index for v in number_mesh.vertices if lo - 1e-6 <= v.co.x <= hi + 1e-6
        }
        candidates = [
            t
            for t in number_mesh.loop_triangles
            if set(t.vertices) <= ids and t.normal.z > 0.99
        ]
        triangle = max(candidates, key=lambda t: t.area)
        point = (
            sum((number_mesh.vertices[i].co for i in triangle.vertices), Vector()) / 3
        )
        world = number_obj.matrix_world @ point
        number_records.append(
            {
                "index": index,
                "frontTriangleVertexIndices": list(triangle.vertices),
                "worldFrontTriangleCentroid": list(world),
                "worldOutwardNormal": list(number_normal),
                "worldProbeOrigin": list(world + number_normal * 0.025),
            }
        )
    number_report = {
        "source": NUMBER_SOURCE,
        "added": NUMBER_ADDED,
        "body": number_source.data.body,
        "sourceNativeResolution": number_resolution,
        "sourceProductionResolution": min(number_resolution, 4),
        "normalShiftMetres": number_shift,
        "sourceMatrix": [list(r) for r in number_source.matrix_world],
        "replacementMatrix": [list(r) for r in number_obj.matrix_world],
        "oldBackClearanceMetres": number_back - number_depth,
        "newBackClearanceMetres": CLEARANCE,
        "productionVertices": len(number_mesh.vertices),
        "productionTriangles": sum(len(f.vertices) - 2 for f in number_mesh.polygons),
        "triangleDelta": 0,
        "samples": number_records,
        "curveParametersUnchanged": True,
    }
    number_source.hide_render = True
    set_layer_hidden(number_source, True)
    original.hide_render = True
    set_layer_hidden(original, True)
    update_scene()
    after = capture()
    protect(before, after)
    assert set(after["objects"]) - set(before["objects"]) == {ADDED, NUMBER_ADDED}
    component = OUT / "component.blend"
    bpy.data.libraries.write(
        str(component), {obj, number_obj}, fake_user=True, compress=True
    )
    photo = (
        ROOT
        / "data/建筑图片/KGS_King_s Chambers/01_建筑实拍/small_buildings_round3_small3_007.jpg"
    )
    write(
        "audit.json",
        {
            "version": 256,
            "code": "KGS",
            "baselineSha256": SHA,
            "componentPath": str(component.relative_to(ROOT)),
            "componentSha256": sha(component),
            "destinationCollection": COLLECTION,
            "targetCollection": COLLECTION,
            "addedObjects": [ADDED, NUMBER_ADDED],
            "archivedObjects": [SOURCE, NUMBER_SOURCE],
            "changedObjects": [],
            "addedFingerprints": {
                ADDED: object_fingerprint(obj),
                NUMBER_ADDED: object_fingerprint(number_obj),
            },
            "replacementMaterialBindings": {
                ADDED: [m.name for m in mesh.materials],
                NUMBER_ADDED: [m.name for m in number_obj.data.materials],
            },
            "replacementFontBindings": {
                NUMBER_ADDED: {
                    field: getattr(number_source.data, field).name
                    for field in [
                        "font",
                        "font_bold",
                        "font_italic",
                        "font_bold_italic",
                    ]
                }
            },
            "numbers": number_report,
            "body": original.data.body,
            "glyphs": records,
            "uniformScale": SCALE,
            "sourceProductionCoordinates": original_mesh_coordinates,
            "curveResolution": {
                "native": native_resolution,
                "production": min(native_resolution, 4),
            },
            "geometryBudget": {
                "sourceProductionVertices": len(mesh.vertices),
                "replacementVertices": len(mesh.vertices),
                "sourceProductionTriangles": original_mesh_triangles,
                "replacementTriangles": sum(len(f.vertices) - 2 for f in mesh.polygons),
                "triangleDelta": 0,
            },
            "radiusMetres": radius,
            "sourceWidthMetres": width,
            "support": SUPPORT,
            "supportLocalDepth": support_depth,
            "originalBackClearanceMetres": old_min_depth - support_depth,
            "newBackClearanceMetres": CLEARANCE,
            "minimumCircleBoundaryClearanceMetres": min(clear),
            "oldTextUnchangedExceptArchive": True,
            "noDuplicateVisibleText": len(
                [
                    o
                    for o in bpy.data.objects
                    if not o.hide_render
                    and (
                        (o.type == "FONT" and o.data.body == original.data.body)
                        or o.get("body") == original.data.body
                    )
                ]
            )
            == 1,
            "scope": "Portal name inscription arc/scale and normal seating of name/numbers only. Number glyphs/size/in-plane layout, opaque green mosaic, stone, glazing, cupola and rooms retained.",
            "sources": [
                {
                    "path": str(photo.relative_to(ROOT)),
                    "sha256": sha(photo),
                    "url": "https://www.geograph.org.uk/photo/2726416",
                    "captureDate": "2011-12-10",
                    "supports": "Inscription descends toward centre with rotated outer letters; inscription occupies a larger share of green mosaic width than inherited straight line.",
                }
            ],
            "limitations": [
                "2011photograph is historical; no2026 refurbishment completion inferred.",
                "Scale1.45, shallow-arc radius and1mm seating clearance are bounded presentation estimates, not photogrammetric measurements.",
                "Source glyph contours at production resolution4 are retained, not a newly traced accurate historic typeface. Native resolution remains unchanged in the archived original.",
                "Source numbers remain at original size and in-plane placement; only their normal gap is corrected. No unseen facade or room layout correction.",
            ],
        },
    )
    export_private("after")
    assert sha(BASE) == SHA
    print("KGS256_COMPONENT_READY", sha(component), flush=True)


if __name__ == "__main__":
    main()
