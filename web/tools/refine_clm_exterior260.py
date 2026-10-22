"""Restore four-column paired sashes in CLM's seven tall window openings.

The2018 high-resolution exterior photograph supports a strong central meeting
stile and one finer subdivision per leaf. Existing window bounds,horizontal
rails,glass,opaque infill,materials and rooms are retained. Dimensions remain
photo-guided estimates. Open in Blender's editor; fixed project paths only.
"""

import importlib.util
import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v259.blend"
SHA = "b304b1fe4f519a6aafd3df15dcf9235ca25a99f3bd699e99a14beaab410c7e8e"
OUT = ROOT / "result/blender/clm260"
COLLECTION = "CLM_EXTERIOR"
REPLACEMENT = "CLM260_tall_paired_sash_verticals"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
import itertools

from integrate_exterior_round194 import object_fingerprint, update_scene
from refine_col_finish252 import sha


def capture():
    spec = importlib.util.spec_from_file_location(
        "clm260_protection", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = SHA
    return helper.capture_source()


def registration():
    site = json.loads((ROOT / "result/blender/site_geometry.json").read_text())
    record = next(b for b in site["buildings"] if b["code"] == "CLM")
    points = [Vector(record["rings"][0][i]) for i in (5, 4, 3, 2, 1)]
    centre = Vector(record["center"])
    segments, length = [], 0
    for a, b in itertools.pairwise(points):
        tangent = (b - a).normalized()
        normal = Vector((tangent.y, -tangent.x))
        if normal.dot((a + b) / 2 - centre) < 0:
            normal = -normal
        size = (b - a).length
        segments.append((length, length + size, a, tangent, normal))
        length += size
    return segments, length


def point(segments, along, depth, height):
    start, _end, origin, tangent, normal = next(
        (s for s in segments if along <= s[1]), segments[-1]
    )
    xy = origin + tangent * (along - start) + normal * depth
    return Vector((xy.x, xy.y, height))


def visible_source():
    matches = [
        o
        for o in bpy.data.collections[COLLECTION].all_objects
        if o.type == "MESH"
        and not o.hide_render
        and o.name.endswith("tall114_metal_mullions")
    ]
    assert len(matches) == 1, [o.name for o in matches]
    return matches[0]


def check_protection(before, after, source):
    for name, row in before["objects"].items():
        expected = dict(row)
        if name == source:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
    assert after["materials"] == before["materials"]
    assert (
        after["rooms"] == before["rooms"]
        and after["campusRooms"] == before["campusRooms"]
    )
    assert len(before["rooms"]) == 35


def build_verticals(source):
    segments, length = registration()
    vertices, faces, bars = [], [], []
    for bay in range(7):
        centre = (bay + 0.5) * length / 7
        for low, high in [(12.8, 15.37), (15.79, 18.36)]:
            for fraction, width in [(0.25, 0.038), (0.5, 0.065), (0.75, 0.038)]:
                along = centre - 1.05 + 2.1 * fraction
                offset = len(vertices)
                segment = next(
                    (item for item in segments if along <= item[1]), segments[-1]
                )
                tangent = Vector((*segment[3], 0))
                normal = Vector((*segment[4], 0))
                anchor = point(segments, along, -0.125, (low + high) / 2)
                # Each physical stile is a rigid rectangle. Mapping its corners
                # independently across a GIS offset-curve corner pinches width.
                vertices.extend(
                    anchor
                    + tangent * x * width / 2
                    + normal * y * 0.075 / 2
                    + Vector((0, 0, z * (high - low) / 2))
                    for x, y, z in [
                        (-1, -1, -1),
                        (-1, -1, 1),
                        (-1, 1, -1),
                        (-1, 1, 1),
                        (1, -1, -1),
                        (1, -1, 1),
                        (1, 1, -1),
                        (1, 1, 1),
                    ]
                )
                faces.extend(
                    tuple(offset + i for i in face)
                    for face in [
                        (0, 4, 6, 2),
                        (1, 3, 7, 5),
                        (0, 1, 5, 4),
                        (2, 6, 7, 3),
                        (0, 2, 3, 1),
                        (4, 5, 7, 6),
                    ]
                )
                bars.append(
                    {
                        "bay": bay,
                        "fraction": fraction,
                        "width": width,
                        "low": low,
                        "high": high,
                        "along": along,
                    }
                )
    mesh = bpy.data.meshes.new(REPLACEMENT + "_mesh")
    mesh.from_pydata(vertices, [], faces)
    for material in source.data.materials:
        mesh.materials.append(material)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    uv = mesh.uv_layers.new(name="Metric")
    for loop in mesh.loops:
        p = mesh.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = p.xy
    mesh.update()
    obj = bpy.data.objects.new(REPLACEMENT, mesh)
    bpy.data.collections[COLLECTION].objects.link(obj)
    obj["originalObject"] = source.name
    obj["destinationCollection"] = COLLECTION
    obj["sourceScope"] = (
        "Seven photo-supported paired two-column sashes; existing glass,outer frames,horizontal rails and opaque infill retained"
    )
    return obj, bars


def main():
    assert sha(BASE) == SHA
    assert not (OUT / "component.blend").exists(), (
        "Review existing component before replacing"
    )
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = capture()
    assert len(before["objects"]) == 8731 and len(before["materials"]) == 2350
    source = visible_source()
    assert len(source.data.vertices) == 112
    obj, bars = build_verticals(source)
    source.hide_render = True
    source.hide_set(True)
    update_scene()
    check_protection(before, capture(), source.name)
    component = OUT / "component.blend"
    bpy.data.libraries.write(str(component), {obj}, fake_user=True, compress=True)
    report = {
        "version": 260,
        "building": "CLM",
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": SHA,
        "componentPath": str(component.relative_to(ROOT)),
        "componentSha256": sha(component),
        "destinationCollection": COLLECTION,
        "targetCollection": COLLECTION,
        "addedObjects": [obj.name],
        "archivedObjects": [source.name],
        "changedObjects": [],
        "addedFingerprints": {obj.name: object_fingerprint(obj)},
        "replacementMaterialBindings": {obj.name: [m.name for m in obj.data.materials]},
        "newMaterials": [],
        "newMaterialGraphs": {},
        "retainNewMaterials": True,
        "bars": bars,
        "sourceReviewSha256": sha(OUT / "source-review.json"),
        "addedTriangles": 504,
        "removedDisplayTriangles": 168,
        "netTriangleChange": 336,
        "sourceFingerprint": object_fingerprint(source),
        "scope": "Change seven tall windows from three columns to paired two-column leaves,split at existing opaque spandrels. Reuse accepted dark painted-frame finish;retain every original object and material.",
        "limitations": [
            "2018and2023photos,not a current2026survey.",
            "Bar thicknesses and retained window/grid dimensions remain estimates.",
            "Horizontal rail count and heights retained;opening mechanisms,upper small sashes,rear elevations and full interiors remain unresolved.",
        ],
    }
    (OUT / "protected-source-state.json").write_text(
        json.dumps(before, indent=2) + "\n"
    )
    (OUT / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
    assert sha(BASE) == SHA
    print("CLM260_PAIRED_SASH_COMPONENT_SAVED", len(bars), flush=True)


if __name__ == "__main__":
    main()
