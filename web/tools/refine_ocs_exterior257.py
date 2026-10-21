"""Recover the photographed four-row upper sashes of the Old Curiosity Shop.

Three source windows contain four horizontal bars each, including an off-centre
meeting rail. Retain one lower bar, the original thicker meeting rail and one
upper bar per window, at quarter/mid/three-quarter height of the existing pane.
No aperture, glass, material, roof, shopfront or room is changed. Fixed paths.
"""

import ast
import importlib.util
import json
import re
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v256.blend"
SHA = "31657c42eb77323d2273bc525ad4db3164fbaa644ddbe6af3b66e44c8679efa1"
OUT = ROOT / "result/blender/ocs257"
SOURCE = "OCS_D3_red_sash_horizontal_bars"
GLASS = "OCS_NEXT_EXTERIOR168_upper_sash_glass"
ADDED = "OCS257_photographed_four_row_sash_bars"
COLLECTION = "OCS_EXTERIOR"
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
        "ocs257_protection", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = SHA
    return helper.capture_source()


def protect(before, after):
    for name, row in before["objects"].items():
        expected = dict(row)
        if name == SOURCE:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
    assert all(after["materials"][n] == v for n, v in before["materials"].items())
    assert (
        after["rooms"] == before["rooms"]
        and after["campusRooms"] == before["campusRooms"]
    )
    assert len(before["rooms"]) == 35


def parts(mesh):
    neighbors = [set() for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        neighbors[a].add(b)
        neighbors[b].add(a)
    remain = set(range(len(mesh.vertices)))
    result = []
    while remain:
        seed = remain.pop()
        todo = [seed]
        ids = {seed}
        while todo:
            for n in neighbors[todo.pop()]:
                if n in remain:
                    remain.remove(n)
                    ids.add(n)
                    todo.append(n)
        result.append(sorted(ids))
    return result


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
    definitions = [
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in wanted
    ]
    assert len(definitions) == len(wanted)
    exec(  # noqa: S102 - Named trusted production export functions.
        compile(
            ast.Module(body=definitions, type_ignores=[]),
            "trusted-production-export-functions",
            "exec",
        ),
        ns,
    )
    scene = bpy.data.scenes.new("OCS257_REVIEW_" + label)
    ns["clone_group"](list(bpy.data.collections[COLLECTION].all_objects), "OCS", scene)
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
        "Review existing component before replacing"
    )
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    bpy.context.preferences.filepaths.save_version = 0
    before = capture()
    write("protected-source-state.json", before)
    source = bpy.data.objects[SOURCE]
    glass = bpy.data.objects[GLASS]
    assert not source.hide_render and not glass.hide_render and not source.modifiers
    assert len(source.data.vertices) == 96 and len(parts(source.data)) == 12
    assert len(glass.data.polygons) == 3
    export_private("before")
    panes = []
    for f in glass.data.polygons:
        points = [glass.matrix_world @ glass.data.vertices[i].co for i in f.vertices]
        panes.append(
            {
                "face": f.index,
                "center": sum(points, Vector()) / len(points),
                "bottom": min(p.z for p in points),
                "top": max(p.z for p in points),
                "normal": (glass.matrix_world.to_3x3() @ f.normal).normalized(),
            }
        )
    groups = {i: [] for i in range(3)}
    for ids in parts(source.data):
        pp = [source.matrix_world @ source.data.vertices[i].co for i in ids]
        center = sum(pp, Vector()) / len(pp)
        index = min(groups, key=lambda j: (panes[j]["center"].xy - center.xy).length)
        assert (panes[index]["center"].xy - center.xy).length < 0.08
        groups[index].append(
            {
                "ids": ids,
                "center": center,
                "height": max(p.z for p in pp) - min(p.z for p in pp),
            }
        )
    inverse_basis = source.matrix_world.to_3x3().inverted()
    retained = []
    windows = []
    for index, rows in groups.items():
        rows.sort(key=lambda r: r["center"].z)
        assert len(rows) == 4
        assert 0.05 < rows[1]["height"] < 0.06 and all(
            0.02 < rows[k]["height"] < 0.024 for k in [0, 2, 3]
        )
        pane = panes[index]
        window = {
            "pane": index,
            "glassBottom": pane["bottom"],
            "glassTop": pane["top"],
            "originalBarCentres": [list(r["center"]) for r in rows],
            "discardedSourceVertexIndices": rows[2]["ids"],
            "bars": [],
        }
        for ordinal, (row, fraction) in enumerate(
            zip([rows[0], rows[1], rows[3]], [0.25, 0.5, 0.75])
        ):
            z = pane["bottom"] + (pane["top"] - pane["bottom"]) * fraction
            delta_z = z - row["center"].z
            delta = inverse_basis @ Vector((0, 0, delta_z))
            entry = {
                "pane": index,
                "ordinal": ordinal,
                "sourceVertexIndices": row["ids"],
                "localTranslation": list(delta),
                "targetCenterZ": z,
                "height": row["height"],
                "targetFraction": fraction,
                "worldOutwardNormal": list(pane["normal"]),
            }
            retained.append(entry)
            window["bars"].append(entry)
        windows.append(window)
    mapping = {}
    vertices = []
    for entry in retained:
        delta = Vector(entry["localTranslation"])
        new = []
        for old in entry["sourceVertexIndices"]:
            mapping[old] = len(vertices)
            new.append(len(vertices))
            vertices.append(source.data.vertices[old].co + delta)
        entry["replacementVertexIndices"] = new
    selected = [
        f for f in source.data.polygons if all(i in mapping for i in f.vertices)
    ]
    mesh = bpy.data.meshes.new(ADDED + "_mesh")
    mesh.from_pydata(
        vertices, [], [tuple(mapping[i] for i in f.vertices) for f in selected]
    )
    mesh.update()
    for m in source.data.materials:
        mesh.materials.append(m)
    for f, old in zip(mesh.polygons, selected):
        f.material_index = old.material_index
        f.use_smooth = old.use_smooth
    for old in source.data.uv_layers:
        new = mesh.uv_layers.new(name=old.name)
        for f, old_face in zip(mesh.polygons, selected):
            for li, old_li in zip(f.loop_indices, old_face.loop_indices):
                new.data[li].uv = old.data[old_li].uv
        new.active_render = old.active_render
    if source.data.uv_layers.active:
        mesh.uv_layers.active = mesh.uv_layers[source.data.uv_layers.active.name]
    obj = source.copy()
    obj.data = mesh
    obj.name = ADDED
    obj["originalObject"] = SOURCE
    obj["webGeometrySource"] = SOURCE
    obj["destinationCollection"] = COLLECTION
    bpy.data.collections[COLLECTION].objects.link(obj)
    update_scene()
    mesh.calc_loop_triangles()
    for row in retained:
        ids = set(row["replacementVertexIndices"])
        normal = Vector(row["worldOutwardNormal"])
        triangles = [
            t
            for t in mesh.loop_triangles
            if set(t.vertices) <= ids
            and (obj.matrix_world.to_3x3() @ t.normal).normalized().dot(normal) > 0.99
        ]
        assert triangles
        t = max(triangles, key=lambda t: t.area)
        center = obj.matrix_world @ (
            sum((mesh.vertices[i].co for i in t.vertices), Vector()) / 3
        )
        row["frontTriangleVertexIndices"] = list(t.vertices)
        row["worldFrontTriangleCentroid"] = list(center)
        row["worldProbeOrigin"] = list(center + normal * 0.025)
    source.hide_render = True
    set_layer_hidden(source, True)
    update_scene()
    protect(before, capture())
    assert (
        len(mesh.vertices) == 72 and len(mesh.polygons) == 54 and len(parts(mesh)) == 9
    )
    component = OUT / "component.blend"
    bpy.data.libraries.write(str(component), {obj}, fake_user=True, compress=True)
    refs = [
        "data/建筑图片/OCS_Old Curiosity Shop/01_建筑实拍/exterior_photos_round4_OCS_sykes_complete_1.png",
        "data/建筑图片/OCS_Old Curiosity Shop/01_建筑实拍/exterior_photos_round4_OCS_ayesa_2.jpg",
    ]
    write(
        "audit.json",
        {
            "version": 257,
            "code": "OCS",
            "baselineSha256": SHA,
            "componentPath": str(component.relative_to(ROOT)),
            "componentSha256": sha(component),
            "destinationCollection": COLLECTION,
            "targetCollection": COLLECTION,
            "addedObjects": [ADDED],
            "archivedObjects": [SOURCE],
            "changedObjects": [],
            "addedFingerprints": {ADDED: object_fingerprint(obj)},
            "replacementMaterialBindings": {ADDED: [m.name for m in mesh.materials]},
            "glass": GLASS,
            "windows": windows,
            "sourceFaceIndices": [f.index for f in selected],
            "geometryBudget": {
                "sourceBars": 12,
                "replacementBars": 9,
                "sourceVertices": 96,
                "replacementVertices": 72,
                "sourceTriangles": sum(
                    len(f.vertices) - 2 for f in source.data.polygons
                ),
                "replacementTriangles": sum(len(f.vertices) - 2 for f in mesh.polygons),
                "newMaterials": 0,
            },
            "sources": [
                {
                    "path": p,
                    "sha256": sha(ROOT / p),
                    "supports": "Completed restoration shows three columns/four rows, central thicker meeting rail and one thin horizontal bar in each sash half; exact dimensions and capture dates unknown.",
                }
                for p in refs
            ],
            "scope": "Three existing upper sash windows only. Retain existing pane apertures, frames, vertical bars, original UVs and paint material; relocate retained horizontal members vertically and remove one extra thin bar in each window.",
            "limitations": [
                "Restoration project photos relate to2021-2023work; no2026survey or current shop layout is inferred.",
                "Quarter-height placement is a source-informed fit to accepted approximate panes, not a measured drawing.",
                "All original meshes/materials remain intact; glass optics/UV/geometry, roof, lettering, shopfront and rooms are unchanged.",
            ],
        },
    )
    export_private("after")
    assert sha(BASE) == SHA
    print("OCS257_COMPONENT_READY", sha(component), flush=True)


if __name__ == "__main__":
    main()
