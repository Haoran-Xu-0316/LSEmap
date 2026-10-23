"""Restore paired two-column leaves in seven upper CLM sashes.

2018-04-24 detail photographs support paired two-column leaves. The seven meeting stiles become thicker relative to their fine subdivisions.
Every original mesh and material survives; only the superseded frame display is archived.
New bar sections are photo-guided estimates, not architectural measurements.
Fixed Blender component builder; no full-campus save or command-line options.
"""

import importlib.util
import json
import sys
from pathlib import Path
from statistics import median

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v260.blend"
SHA = "c208a1086482bcc1bf20ec25ccdd9c684a0ea88a4891e5a007439c1076c1eec2"
OUT = ROOT / "result/blender/clm261"
COLLECTION = "CLM_EXTERIOR"
REPLACEMENT = "CLM261_upper_small_sash_fine_verticals"
SIDE_WIDTH = 0.038
CENTRAL_WIDTH = 0.065
MEETING = "CLM261_retained_frames_upper_meeting_stiles"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint, update_scene
from refine_clm_exterior260 import point, registration
from refine_col_finish252 import sha


def capture():
    spec = importlib.util.spec_from_file_location(
        "clm261_protection", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = SHA
    result = helper.capture_source()
    result["visibility"] = {
        o.name: [o.hide_render, o.hide_viewport, o.hide_get()] for o in bpy.data.objects
    }
    return result


def groups(obj):
    adjacent = [set() for _ in obj.data.vertices]
    for edge in obj.data.edges:
        a, b = edge.vertices
        adjacent[a].add(b)
        adjacent[b].add(a)
    unseen = set(range(len(adjacent)))
    result = []
    while unseen:
        seed = min(unseen)
        unseen.remove(seed)
        found, queue = {seed}, [seed]
        while queue:
            for other in adjacent[queue.pop()] & unseen:
                unseen.remove(other)
                found.add(other)
                queue.append(other)
        result.append(sorted(found))
    return result


def upper_parts(obj):
    result = []
    for ids in groups(obj):
        pts = [obj.matrix_world @ obj.data.vertices[i].co for i in ids]
        low, high = min(p.z for p in pts), max(p.z for p in pts)
        if abs(low - 19.4) < 0.001 and abs(high - 21.66) < 0.001:
            result.append((ids, pts, sum(pts, Vector()) / len(pts)))
    return sorted(result, key=lambda row: row[2].x)


def source_objects():
    visible = [
        o
        for o in bpy.data.collections[COLLECTION].all_objects
        if o.type == "MESH" and not o.hide_render
    ]
    mullions = [
        o
        for o in visible
        if (o.name.endswith("D3_window_mullions") or o.name == MEETING)
    ]
    glass = [o for o in visible if o.name.endswith("ENVELOPE_street_glass")]
    assert len(mullions) == len(glass) == 1
    assert len(upper_parts(mullions[0])) == len(upper_parts(glass[0])) == 7
    return mullions[0], glass[0]


def tree(obj):
    mesh = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    data = mesh.to_mesh()
    data.calc_loop_triangles()
    result = BVHTree.FromPolygons(
        [mesh.matrix_world @ v.co for v in data.vertices],
        [tuple(t.vertices) for t in data.loop_triangles],
        all_triangles=True,
    )
    mesh.to_mesh_clear()
    return result


def build():
    source, glass = source_objects()
    segments, length = registration()
    glass_tree = tree(glass)
    diagnosis = json.loads((OUT / "glass-registration-diagnosis.json").read_text())
    assert diagnosis["baselineSha256"] == SHA
    reference_offset = median(
        r["centreOffsetFromGlassFront"] for r in diagnosis["rows"]
    )
    assert abs(reference_offset - 0.034) < 0.00005
    meeting = source.copy()
    meeting.data = source.data.copy()
    meeting.name = MEETING
    meeting.data.name = MEETING + "_mesh"
    bpy.data.collections[COLLECTION].objects.link(meeting)
    meeting["originalObject"] = source.name
    meeting["destinationCollection"] = COLLECTION
    meeting["sourceScope"] = (
        "Only7upper-small-window meeting stiles widened and glass-registered;29other solids and allUVs retained"
    )
    inverse = meeting.matrix_world.inverted()
    vertices, faces, bars = [], [], []
    winding = [
        (0, 4, 6, 2),
        (1, 3, 7, 5),
        (0, 1, 5, 4),
        (2, 6, 7, 3),
        (0, 2, 3, 1),
        (4, 5, 7, 6),
    ]
    for bay, ((_ids, original, centre), (_glass_ids, panes, _gc)) in enumerate(
        zip(upper_parts(source), upper_parts(glass))
    ):
        chain = (bay + 0.5) * length / 7
        segment = next((s for s in segments if chain <= s[1]), segments[-1])
        tangent, normal = Vector((*segment[3], 0)), Vector((*segment[4], 0))
        depths = [(p - centre).dot(normal) for p in original]
        frame_depth = max(depths) - min(depths)
        original_width = max(p.dot(tangent) for p in original) - min(
            p.dot(tangent) for p in original
        )
        assert 0.025 < original_width < 0.045 and 0.06 < frame_depth < 0.09
        glass_width = max(p.dot(tangent) for p in panes) - min(
            p.dot(tangent) for p in panes
        )
        assert 1.65 < glass_width < 1.8
        hit = glass_tree.ray_cast(centre + normal, -normal, 2)
        assert hit[0] is not None
        face_offset = (centre - hit[0]).dot(normal)
        measured = diagnosis["rows"][bay]
        assert (hit[0] - Vector(measured["retainedGlassHit"])).length < 0.00005
        assert abs(face_offset - measured["centreOffsetFromGlassFront"]) < 0.00005
        depth_shift = reference_offset - face_offset
        assert abs(depth_shift) < 0.00005 if bay != 5 else -0.061 < depth_shift < -0.060
        for index in _ids:
            old = source.matrix_world @ source.data.vertices[index].co
            scaled = (
                old
                + tangent
                * (old - centre).dot(tangent)
                * (CENTRAL_WIDTH / original_width - 1)
                + normal * depth_shift
            )
            meeting.data.vertices[index].co = inverse @ scaled
        for fraction in [0.25, 0.75]:
            along = chain + glass_width * (fraction - 0.5)
            local = next((s for s in segments if along <= s[1]), segments[-1])
            u, n = Vector((*local[3], 0)), Vector((*local[4], 0))
            ray_origin = point(segments, along, 1, centre.z)
            surface = glass_tree.ray_cast(ray_origin, -n, 3)
            assert surface[0] is not None, (bay, fraction)
            anchor = surface[0] + n * reference_offset
            low, high = min(p.z for p in original), max(p.z for p in original)
            offset = len(vertices)
            vertices.extend(
                anchor
                + u * x * SIDE_WIDTH / 2
                + n * y * frame_depth / 2
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
            faces.extend(tuple(offset + i for i in face) for face in winding)
            bars.append(
                {
                    "bay": bay,
                    "fraction": fraction,
                    "chainage": along,
                    "width": SIDE_WIDTH,
                    "depth": frame_depth,
                    "low": low,
                    "high": high,
                    "centre": list(anchor),
                    "normal": list(n),
                    "right": list(u),
                    "retainedCentralWidth": original_width,
                    "frontOffsetFromActualGlass": reference_offset,
                    "originalCentralFrontOffset": face_offset,
                    "centralDepthCorrection": depth_shift,
                    "nativePaneProjectedWidth": glass_width,
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
        uv.data[loop.index].uv = mesh.vertices[loop.vertex_index].co.xy
    mesh.update()
    obj = bpy.data.objects.new(REPLACEMENT, mesh)
    bpy.data.collections[COLLECTION].objects.link(obj)
    obj["destinationCollection"] = COLLECTION
    obj["sourceScope"] = (
        "Four glass columns within each of seven upper small sashes; central meeting stiles and every original surface retained"
    )
    obj["dimensionsEstimated"] = True
    meeting.data.update()
    source.hide_render = True
    source.hide_set(True)
    return obj, meeting, source.name, bars


def main():
    assert sha(BASE) == SHA
    OUT.mkdir(parents=True, exist_ok=True)
    assert not (OUT / "component.blend").exists(), (
        "Review existing component before replacement"
    )
    review = json.loads((OUT / "source-review.json").read_text())
    assert all(sha(ROOT / r["local"]) == r["sha256"] for r in review["references"])
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = capture()
    obj, meeting, archived, bars = build()
    update_scene()
    after = capture()
    for name, row in before["objects"].items():
        expected = dict(row)
        if name == archived:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
    assert after["materials"] == before["materials"]
    for name, row in before["visibility"].items():
        expected = [True, row[1], True] if name == archived else row
        assert after["visibility"][name] == expected, name
    assert (
        before["rooms"] == after["rooms"]
        and before["campusRooms"] == after["campusRooms"]
    )
    assert len(before["rooms"]) == 35
    component = OUT / "component.blend"
    bpy.data.libraries.write(
        str(component), {obj, meeting}, fake_user=True, compress=True
    )
    report = {
        "version": 261,
        "building": "CLM",
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": SHA,
        "componentPath": str(component.relative_to(ROOT)),
        "componentSha256": sha(component),
        "destinationCollection": COLLECTION,
        "targetCollection": COLLECTION,
        "addedObjects": [obj.name, meeting.name],
        "archivedObjects": [archived],
        "changedObjects": [],
        "addedFingerprints": {o.name: object_fingerprint(o) for o in [obj, meeting]},
        "replacementMaterialBindings": {
            o.name: [m.name for m in o.data.materials] for o in [obj, meeting]
        },
        "newMaterials": [],
        "newMaterialGraphs": {},
        "retainNewMaterials": True,
        "bars": bars,
        "sourceReviewSha256": sha(OUT / "source-review.json"),
        "glassRegistrationDiagnosisSha256": sha(
            OUT / "glass-registration-diagnosis.json"
        ),
        "addedTriangles": 600,
        "removedDisplayTriangles": 432,
        "netTriangleChange": 168,
        "protectedOriginalObjects": len(before["objects"]),
        "protectedOriginalMaterials": len(before["materials"]),
        "scope": "Thicken7upper-small-window central meeting stiles to0.065m,register the detached curved-bay central stile against its actual glass and add14fine0.038m divisions. Archive original mixed frame display;retain all29unrelated frame solids verbatim, every original object/material, horizontal rails, roofs and35independent room studies.",
        "limitations": review["limitations"],
    }
    (OUT / "protected-source-state.json").write_text(
        json.dumps(before, indent=2) + "\n"
    )
    (OUT / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
    assert sha(BASE) == SHA
    print("CLM261_UPPER_SASH_COMPONENT_SAVED", len(bars), flush=True)


if __name__ == "__main__":
    main()
