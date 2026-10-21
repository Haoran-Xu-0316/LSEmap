"""Restore SHF's photographed right-hand blind panel, not a pair of windows.

Run in Blender with fixed project paths. Only two inherited facade apertures
are filled; no floor, roof, glass optics, lighting or unseen elevation is inferred.
The old window assemblies remain hidden archives in the native component.
"""

import importlib.util
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v254.blend"
SHA = "47db5d164487cc7d5f87c4c6f0df47b4800238cb16e650ce1325e6db99f97140"
OUT = ROOT / "result/blender/shf255"
PREFIX = "SHF255_"
COLLECTION = "SHF_EXTERIOR"
FRAME = json.loads((ROOT / "result/blender/shf_exterior148/audit.json").read_text())[
    "registration"
]
ORIGIN, RIGHT, OUTSIDE = [Vector(FRAME[k]) for k in ("origin", "right", "outward")]
WIDTH = FRAME["frontLength"] / 4 * 0.69
CENTRE = FRAME["centres"][3]
HOLES = [
    (CENTRE - WIDTH / 2, CENTRE + WIDTH / 2, z - h / 2, z + h / 2)
    for z, h in [(1.2, 1.2), (4.3, 2.2)]
]
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from facade_geometry import Geometry, materials
from integrate_exterior_round194 import (
    geometry_policy_name,
    object_fingerprint,
    set_layer_hidden,
    update_scene,
)
from refine_col_finish252 import sha


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n")


def capture():
    spec = importlib.util.spec_from_file_location(
        "shf255_protection", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = SHA
    return helper.capture_source()


def local(point):
    delta = point - ORIGIN
    return delta.dot(RIGHT), delta.dot(OUTSIDE), point.z


def world(x, d, z):
    return ORIGIN + RIGHT * x + OUTSIDE * d + Vector((0, 0, z))


def islands(mesh):
    adjacency = [set() for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        adjacency[a].add(b)
        adjacency[b].add(a)
    pending = set(range(len(adjacency)))
    while pending:
        first = pending.pop()
        component = {first}
        stack = [first]
        while stack:
            for neighbour in adjacency[stack.pop()] & pending:
                pending.remove(neighbour)
                component.add(neighbour)
                stack.append(neighbour)
        yield component


def face_record(obj, face):
    """Retained topology, UV, split normals and binding, independent of indices."""
    return {
        "vertices": [list(obj.data.vertices[k].co) for k in face.vertices],
        "normal": [round(v, 6) for v in face.normal],
        "corners": [
            [round(v, 6) for v in obj.data.corner_normals[k].vector]
            for k in face.loop_indices
        ],
        "uv": {
            layer.name: [list(layer.data[k].uv) for k in face.loop_indices]
            for layer in obj.data.uv_layers
        },
        "material": obj.data.materials[face.material_index].name,
        "smooth": face.use_smooth,
    }


def target_islands(obj):
    if not any(
        token in obj.name
        for token in ("_window_", "_paired_stiles_", "_overlight_transoms_")
    ):
        return []
    selected = []
    for part in islands(obj.data):
        points = [local(obj.matrix_world @ obj.data.vertices[k].co) for k in part]
        centre = [sum(p[a] for p in points) / len(points) for a in range(3)]
        if (
            abs(centre[0] - CENTRE) < WIDTH / 2 + 0.2
            and 0.35 < centre[2] < 5.5
            and -0.4 < centre[1] < 0.25
        ):
            assert all(
                CENTRE - WIDTH / 2 - 0.25 < p[0] < CENTRE + WIDTH / 2 + 0.25
                and 0.35 < p[2] < 5.6
                and -0.5 < p[1] < 0.35
                for p in points
            ), obj.name
            selected.append(part)
    return selected


def trim(source, removed_vertices):
    keep = [p for p in source.data.polygons if not set(p.vertices) & removed_vertices]
    assert len(keep) < len(source.data.polygons) and keep
    expected = [face_record(source, p) for p in keep]
    used = sorted({k for p in keep for k in p.vertices})
    mapping = {old: new for new, old in enumerate(used)}
    mesh = bpy.data.meshes.new(PREFIX + source.name)
    mesh.from_pydata(
        [source.data.vertices[k].co for k in used],
        [],
        [tuple(mapping[k] for k in p.vertices) for p in keep],
    )
    for material in source.data.materials:
        mesh.materials.append(material)
    for layer in source.data.uv_layers:
        new = mesh.uv_layers.new(name=layer.name)
        new.active_render = layer.active_render
        for face, old in zip(mesh.polygons, keep):
            for dst, src in zip(face.loop_indices, old.loop_indices):
                new.data[dst].uv = layer.data[src].uv
    if source.data.uv_layers.active:
        mesh.uv_layers.active = mesh.uv_layers[source.data.uv_layers.active.name]
    for face, old in zip(mesh.polygons, keep):
        face.material_index = old.material_index
        face.use_smooth = old.use_smooth
    mesh.update()
    if source.data.has_custom_normals:
        mesh.normals_split_custom_set(
            [source.data.corner_normals[k].vector for p in keep for k in p.loop_indices]
        )
    obj = source.copy()
    obj.data = mesh
    obj.name = PREFIX + source.name
    obj["originalObject"] = source.name
    obj["webGeometrySource"] = geometry_policy_name(source)
    obj["destinationCollection"] = COLLECTION
    bpy.data.collections[COLLECTION].objects.link(obj)
    assert [face_record(obj, p) for p in mesh.polygons] == expected, source.name
    return obj, {
        "source": source.name,
        "retainedFaces": len(keep),
        "removedFaces": len(source.data.polygons) - len(keep),
        "retainedFaceRecords": expected,
    }


def tree(objects):
    vertices, faces, owners = [], [], []
    for obj in objects:
        if obj.type != "MESH" or obj.hide_render:
            continue
        start = len(vertices)
        vertices.extend(obj.matrix_world @ v.co for v in obj.data.vertices)
        faces.extend(tuple(start + k for k in p.vertices) for p in obj.data.polygons)
        owners.extend([obj.name] * len(obj.data.polygons))
    return BVHTree.FromPolygons(vertices, faces), owners


def probes(objects):
    bvh, owners = tree(objects)
    result = []
    for x0, x1, z0, z1 in HOLES:
        for u in [0.2, 0.5, 0.8]:
            for v in [0.2, 0.5, 0.8]:
                point = world(x0 + (x1 - x0) * u, 0.5, z0 + (z1 - z0) * v)
                hit = bvh.ray_cast(point, -OUTSIDE, 1)
                result.append(
                    {
                        "x": x0 + (x1 - x0) * u,
                        "z": z0 + (z1 - z0) * v,
                        "object": owners[hit[2]] if hit[2] is not None else None,
                        "depth": local(hit[0])[1] if hit[0] is not None else None,
                    }
                )
    return result


def check_protection(before, after, archived):
    for name, row in before["objects"].items():
        expected = dict(row)
        if name in archived:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
    assert before["materials"] == after["materials"]
    assert before["rooms"] == after["rooms"]
    assert before["campusRooms"] == after["campusRooms"]


def main():
    assert sha(BASE) == SHA
    OUT.mkdir(parents=True, exist_ok=True)
    assert not (OUT / "component.blend").exists(), (
        "Review the previous candidate before replacing"
    )
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.preferences.filepaths.save_version = 0
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    update_scene()
    before = capture()
    write("protected-source-state.json", before)
    collection = bpy.data.collections[COLLECTION]
    sources = {
        o.name: target_islands(o)
        for o in collection.all_objects
        if o.type == "MESH" and not o.hide_render
    }
    sources = {name: parts for name, parts in sources.items() if parts}
    assert len(sources) == 6, sources.keys()
    assert any("window_glass" in name for name in sources)
    # Actual source apertures must be open through the inherited .30m wall;
    # never add a coplanar white patch on top of an already solid white wall.
    opaque = [o for o in collection.all_objects if o.name not in sources]
    before_hits = probes(opaque)
    assert all(p["object"] is None for p in before_hits), before_hits
    owned, geometry = [], []
    for name, parts in sources.items():
        obj, record = trim(bpy.data.objects[name], set().union(*parts))
        record["removedIslands"] = len(parts)
        owned.append(obj)
        geometry.append(record)
        source = bpy.data.objects[name]
        source.hide_render = True
        set_layer_hidden(source, True)
    materials.clear()
    materials["white"] = bpy.data.materials["SHF_V50_white"]
    patch = Geometry("SHF", "blind255", "white")
    patch.name = PREFIX + "photographed_blind_wall"
    import math

    angle = math.atan2(RIGHT.y, RIGHT.x)
    for x0, x1, z0, z1 in HOLES:
        patch.box(
            world((x0 + x1) / 2, -0.18, (z0 + z1) / 2), (x1 - x0, 0.30, z1 - z0), angle
        )
    wall = patch.finish()
    # The construction-edge bevel on the two exact infills would open seams.
    wall.modifiers.clear()
    wall["referenceScope"] = (
        "Only fill inherited false window holes, front -.03m and rear -.33m; no wall overlay"
    )
    owned.append(wall)
    relief = Geometry("SHF", "blind255_relief", "white")
    relief.name = PREFIX + "blind_panel_relief"
    left, right = CENTRE - WIDTH / 2 - 0.10, CENTRE + WIDTH / 2 + 0.10
    bottom, top = 1.95, 5.45
    for x in [left, right]:
        relief.box(
            world(x, -0.005, (bottom + top) / 2), (0.055, 0.05, top - bottom), angle
        )
    for z in [bottom, 2.61, 4.18, top]:
        relief.box(world(CENTRE, -0.005, z), (right - left + 0.055, 0.05, 0.055), angle)
    panel = relief.finish()
    panel.modifiers.clear()
    panel["referenceScope"] = (
        "Photo-supported rectangular blind field with two intermediate rails; profile and panel coordinates estimated within inherited bay"
    )
    owned.append(panel)
    update_scene()
    after_hits = probes(collection.all_objects)
    assert all(p["object"] in {wall.name, panel.name} for p in after_hits), after_hits
    after = capture()
    check_protection(before, after, sources)
    component = OUT / "component.blend"
    bpy.data.libraries.write(str(component), set(owned), fake_user=True, compress=True)
    photos = [
        ROOT / "data/建筑图片/SHF_Sheffield Street/01_建筑实拍" / name
        for name in [
            "exteriors_lse_estate_027.jpg",
            "small_round5_SHF_handbook-000.png",
        ]
    ]
    write(
        "audit.json",
        {
            "version": 255,
            "building": "SHF",
            "baseline": str(BASE.relative_to(ROOT)),
            "baselineSha256": SHA,
            "componentPath": str(component.relative_to(ROOT)),
            "componentSha256": sha(component),
            "addedObjects": [o.name for o in owned],
            "archivedObjects": list(sources),
            "changedObjects": [],
            "addedFingerprints": {o.name: object_fingerprint(o) for o in owned},
            "replacementMaterialBindings": {
                o.name: [m.name for m in o.data.materials] for o in owned
            },
            "targetCollection": COLLECTION,
            "destinationCollection": COLLECTION,
            "registration": FRAME,
            "removedFalseWindowHoles": HOLES,
            "retainedGeometry": geometry,
            "beforeOpaqueOpeningProbes": before_hits,
            "afterBlindWallProbes": after_hits,
            "sources": [
                {
                    "path": str(p.relative_to(ROOT)),
                    "sha256": sha(p),
                    "captureDate": "unknown",
                    "supports": "Two photographs show the rightmost lower bay as a blind white panel, not windows",
                }
                for p in photos
            ],
            "sourceURLs": [
                "https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate",
                "https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Property-and-Space/LSE-Property-Handbook.pdf",
            ],
            "limitations": [
                "Photograph capture dates unknown; handbook edition2025/26 does not date the image.",
                "Facade dimensions, relief depths and trim positions remain estimates. No measured drawing or current survey is claimed.",
                "Other window panes, normals, UVs, glass optics, brick finish, roof and unseen elevations are retained.",
            ],
            "status": "saved_awaiting_independent_reopen_and_visual_review",
        },
    )
    assert sha(BASE) == SHA
    print("SHF255_COMPONENT_SAVED", len(owned), list(sources), flush=True)


if __name__ == "__main__":
    main()
