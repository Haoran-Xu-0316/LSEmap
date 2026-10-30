"""Independent actual-mesh, UV, frame-contact and glazing checks for OLD283.

Load279and the separate component in a fresh Blender process. No geometry is
constructed here. CPU syntax/source checks alone are not native acceptance.
"""

import collections
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v279.blend"
SHA = "b03a0caec932c50e0c7d8ad2a725a43b80eb38abee716f1d1c2d30cde767982c"
OUT = ROOT / "result/blender/old283"
OWNER = "OLD_EXTERIOR"
SOURCE = "OLD_V112_entry_D5_windows85_casements"
NEW = "OLD283_Houghton_two_outer_ground_five_row_casements"
FRAME = "OLD_V112_entry_D5_portal79_Window_sash_frames"
GLASS = "OLDGLASS217_GLASS181_OLD_V112_entry_D5_portal79_Window_glazing"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_axes():
    record = json.loads(
        (ROOT / "result/blender/stage52/old-houghton-audit.json").read_text()
    )
    return tuple(Vector(record[k]) for k in ("origin", "right", "outward"))


def source_point(x, depth, z, axes):
    origin, right, outward = axes
    return origin + right * x + outward * depth + Vector((0, 0, z))


def local(point, axes):
    origin, right, outward = axes
    delta = point - origin
    return Vector((delta.dot(right), delta.dot(outward), point.z))


def groups(mesh):
    adjacency = [set() for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        adjacency[a].add(b)
        adjacency[b].add(a)
    unseen, result = set(range(len(mesh.vertices))), []
    while unseen:
        seed = unseen.pop()
        group, stack = [seed], [seed]
        while stack:
            for other in adjacency[stack.pop()] & unseen:
                unseen.remove(other)
                group.append(other)
                stack.append(other)
        result.append(sorted(group))
    return result


def describe(obj, axes):
    records = []
    for group in groups(obj.data):
        selected = set(group)
        faces = [f for f in obj.data.polygons if set(f.vertices) <= selected]
        assert len(group) == 8 and len(faces) == 6
        edges, directed = collections.Counter(), collections.Counter()
        centre = sum((obj.data.vertices[i].co for i in group), Vector()) / len(group)
        volume = 0.0
        for face in faces:
            ring = list(face.vertices)
            points = [obj.data.vertices[i].co - centre for i in ring]
            volume += sum(
                points[0].dot(points[i].cross(points[i + 1])) / 6
                for i in range(1, len(points) - 1)
            )
            for a, b in zip(ring, ring[1:] + ring[:1], strict=True):
                edges[tuple(sorted((a, b)))] += 1
                directed[(a, b)] += 1
        assert len(edges) == 12 and set(edges.values()) == {2}
        assert all(count == directed[(b, a)] for (a, b), count in directed.items())
        assert volume > 0
        points = [local(obj.data.vertices[i].co, axes) for i in group]
        lo = [min(p[i] for p in points) for i in range(3)]
        hi = [max(p[i] for p in points) for i in range(3)]
        records.append(
            {
                "vertices": group,
                "faces": faces,
                "low": lo,
                "high": hi,
                "centre": [(a + b) / 2 for a, b in zip(lo, hi, strict=True)],
                "size": [b - a for a, b in zip(lo, hi, strict=True)],
                "volume": volume * obj.matrix_world.to_3x3().determinant(),
            }
        )
    assert sum(len(r["faces"]) for r in records) == len(obj.data.polygons)
    return records


def ground_parts(records):
    windows = []
    for x in (-6.7, 6.7):
        parts = [
            r
            for r in records
            if abs(r["centre"][0] - x) < 0.5 and 1.2 < r["centre"][2] < 4.0
        ]
        horizontal = sorted(
            (r for r in parts if r["size"][0] > 1.2 and r["size"][2] < 0.08),
            key=lambda r: r["centre"][2],
        )
        vertical = sorted(
            (r for r in parts if r["size"][2] > 2.5 and r["size"][0] < 0.06),
            key=lambda r: r["centre"][0],
        )
        # Side verticals are slightly more than0.36m from the window centre.
        assert len(vertical) == 3
        assert len(horizontal) in (3, 4)
        windows.append(
            {
                "centreX": x,
                "bottom": 1.275,
                "height": 2.65,
                "width": 1.44,
                "horizontal": horizontal,
                "vertical": vertical,
            }
        )
    return windows


def face_signature(obj, face):
    corners = []
    for loop in face.loop_indices:
        point = obj.data.vertices[obj.data.loops[loop].vertex_index].co
        corners.append(
            (
                tuple(point),
                tuple((uv.name, tuple(uv.data[loop].uv)) for uv in obj.data.uv_layers),
            )
        )
    return (
        face.material_index,
        face.use_smooth,
        min(tuple(corners[i:] + corners[:i]) for i in range(len(corners))),
    )


def actual_tree(objects):
    vertices, faces, owners = [], [], []
    dependency_graph = bpy.context.evaluated_depsgraph_get()
    for obj in objects:
        evaluated = obj.evaluated_get(dependency_graph)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        start = len(vertices)
        vertices.extend(evaluated.matrix_world @ v.co for v in mesh.vertices)
        for triangle in mesh.loop_triangles:
            faces.append(tuple(start + i for i in triangle.vertices))
            owners.append(obj.name)
        evaluated.to_mesh_clear()
    assert faces
    return BVHTree.FromPolygons(vertices, faces, all_triangles=True), owners


def geometry_proof(audit):
    sys.path.insert(0, str(ROOT / "web/tools"))
    from integrate_exterior_round194 import object_fingerprint

    source, obj = bpy.data.objects[SOURCE], bpy.data.objects[NEW]
    assert source.hide_render and not obj.hide_render and not obj.modifiers
    assert object_fingerprint(source) == audit["sourceFingerprint"]
    assert object_fingerprint(obj) == audit["addedFingerprints"][NEW]
    assert source.matrix_world == obj.matrix_world
    assert sorted(c.name for c in obj.users_collection) == [OWNER]
    assert [m.name for m in obj.data.materials] == [
        m.name for m in source.data.materials
    ]
    assert [uv.name for uv in obj.data.uv_layers] == [
        uv.name for uv in source.data.uv_layers
    ]
    axes = source_axes()
    old, new = describe(source, axes), describe(obj, axes)
    assert len(old) == 84 and len(new) == 86
    old_windows, new_windows = ground_parts(old), ground_parts(new)
    old_changed = {
        i
        for window in old_windows
        for row in window["horizontal"]
        for i in row["vertices"]
    }
    new_changed = {
        i
        for window in new_windows
        for row in window["horizontal"]
        for i in row["vertices"]
    }
    old_kept = [f for f in source.data.polygons if not set(f.vertices) & old_changed]
    new_kept = [f for f in obj.data.polygons if not set(f.vertices) & new_changed]
    assert len(old_kept) == len(new_kept) == 468
    assert collections.Counter(
        face_signature(source, f) for f in old_kept
    ) == collections.Counter(face_signature(obj, f) for f in new_kept)
    # For moved rails, compare the exact profile and corner UVs after removing
    # their intended vertical translation. This includes material face slots.
    moved_profile_checks = 0
    for left, right in zip(old_windows, new_windows, strict=True):
        assert len(left["horizontal"]) == 3 and len(right["horizontal"]) == 4
        for j, row in enumerate(right["horizontal"], 1):
            template = left["horizontal"][-1] if j == 3 else left["horizontal"][0]
            assert (
                max(
                    abs(a - b)
                    for a, b in zip(row["size"], template["size"], strict=True)
                )
                < 0.00003
            )
            for face, original in zip(row["faces"], template["faces"], strict=True):
                assert (
                    face.material_index == original.material_index
                    and face.use_smooth == original.use_smooth
                )
                for uv in obj.data.uv_layers:
                    original_uv = source.data.uv_layers[uv.name]
                    assert [tuple(uv.data[i].uv) for i in face.loop_indices] == [
                        tuple(original_uv.data[i].uv) for i in original.loop_indices
                    ]
            moved_profile_checks += 1
    actual_frame, _ = actual_tree([bpy.data.objects[FRAME]])
    objects = [
        o
        for o in bpy.data.collections[OWNER].all_objects
        if o.type == "MESH" and not o.hide_render
    ]
    all_surfaces, owners = actual_tree(objects)
    normal = (
        source.matrix_world.to_3x3().inverted().transposed() @ axes[2]
    ).normalized()
    right = (source.matrix_world.to_3x3() @ axes[1]).normalized()

    def world(x, depth, z):
        return source.matrix_world @ source_point(x, depth, z, axes)

    first_hits, frame_contacts, windows = [], [], []
    for window in new_windows:
        x, width, bottom, height = (
            window["centreX"],
            window["width"],
            window["bottom"],
            window["height"],
        )
        rows = window["horizontal"]
        fractions = [(r["centre"][2] - bottom) / height for r in rows]
        assert max(abs(f - (i + 1) / 5) for i, f in enumerate(fractions)) < 0.00001
        for j, row in enumerate(rows):
            assert abs(row["size"][2] - (0.065 if j == 2 else 0.025)) < 0.00002
            assert abs(row["centre"][1] - 0.145) < 0.00002
            for sign in (-1, 1):
                end = world(
                    x + sign * (width / 2 - 0.06), row["centre"][1], row["centre"][2]
                )
                hit, _, _, distance = actual_frame.ray_cast(
                    end - right * sign * 0.03, right * sign, 0.12
                )
                assert hit is not None, (
                    "missing-finite-rail-frame-contact",
                    x,
                    row["centre"][2],
                    sign,
                )
                frame_contacts.append(distance)
        # Sample all actual pane centres against every active OLD mesh. A pass
        # requires the retained glass to be first, excluding opaque cover-ups.
        for column in range(4):
            for row in range(5):
                px = x - width / 2 + width * (column + 0.5) / 4
                pz = bottom + height * (row + 0.5) / 5
                origin = world(px, 0.145, pz) + normal * 1.5
                hit, _, index, distance = all_surfaces.ray_cast(origin, -normal, 3.0)
                name = owners[index] if index is not None else None
                assert name == GLASS, (
                    "pane-first-hit-not-retained-glass",
                    x,
                    column,
                    row,
                    name,
                )
                assert hit is not None and distance > 1.5
                first_hits.append(
                    {
                        "windowCentreX": x,
                        "column": column + 1,
                        "row": row + 1,
                        "firstSurface": name,
                        "distanceM": distance,
                    }
                )
        windows.append(
            {
                "centreX": x,
                "columns": 4,
                "rows": 5,
                "horizontalFractions": fractions,
                "closedPositiveMemberVolumesM3": [
                    r["volume"] for r in rows + window["vertical"]
                ],
            }
        )
    assert len(first_hits) == 40 and len(frame_contacts) == 16
    old_triangles = sum(len(f.vertices) - 2 for f in source.data.polygons)
    new_triangles = sum(len(f.vertices) - 2 for f in obj.data.polygons)
    assert new_triangles == 1032 and new_triangles - old_triangles == 24
    return {
        "status": "passed-bounded-two-ground-window-grid",
        "actualWindows": windows,
        "closedPositiveSolids": len(new),
        "unchangedNativeMembers": 78,
        "unchangedFacesWithExactCoordinatesUVsAndSlots": 468,
        "translatedProfilesWithExactNativeUVs": moved_profile_checks,
        "actualNativeUVLayers": [uv.name for uv in obj.data.uv_layers],
        "retainedGlassObject": GLASS,
        "retainedOuterFrameObject": FRAME,
        "actualRetainedGlassFirstHitCount": len(first_hits),
        "actualRetainedGlassFirstHits": first_hits,
        "actualFiniteRailOuterFrameContacts": len(frame_contacts),
        "contactRayDistancesM": [min(frame_contacts), max(frame_contacts)],
        "triangles": new_triangles,
        "netTrianglesAdded": new_triangles - old_triangles,
        "materialsAdded": 0,
        "sourcePhotoTextureAdded": False,
        "wholeBuildingExteriorAccepted": False,
    }


def main():
    sys.path.insert(0, str(ROOT / "web/tools"))
    import refine_old283 as author
    from integrate_exterior_round194 import object_fingerprint, update_scene

    audit = json.loads((OUT / "audit.json").read_text())
    assert sha(BASE) == SHA and audit["baselineSha256"] == SHA
    assert sha(ROOT / audit["componentPath"]) == audit["componentSha256"]
    assert sha(ROOT / audit["sourceEvidence"]) == audit["sourceEvidenceSha256"]
    assert all(
        sha(ROOT / path) == value for path, value in audit["sourceHashes"].items()
    )
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / audit["componentPath"]))
    assert set(bpy.data.objects.keys()) == {NEW}
    author.evaluate_component_scene("fresh-process")
    assert object_fingerprint(bpy.data.objects[NEW]) == audit["addedFingerprints"][NEW]
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = author.capture()
    author.apply_component(audit, before["materials"])
    protected = author.protection(before, archived=True)
    proof = geometry_proof(audit)
    assert (
        sha(BASE) == SHA
        and sha(ROOT / audit["componentPath"]) == audit["componentSha256"]
    )
    result = {
        "status": "passed-bounded-candidate",
        "freshBlenderProcess": True,
        "baselineSha256": SHA,
        "componentSha256": audit["componentSha256"],
        "protection": protected,
        "actualMeshProof": proof,
        "wholeNativeSaved": False,
    }
    (OUT / "fresh-process-verification.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print("OLD283_FRESH_VERIFIED", audit["componentSha256"], flush=True)


if __name__ == "__main__":
    main()
