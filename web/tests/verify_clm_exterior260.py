"""Reopen CLM paired sashes and verify four real pane channels per opening."""

import json
import sys
from collections import Counter
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint, update_scene
from refine_clm_exterior260 import (
    BASE,
    COLLECTION,
    OUT,
    REPLACEMENT,
    SHA,
    capture,
    point,
    registration,
    sha,
)


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


def topology(obj):
    mesh = obj.data
    edges = Counter()
    adjacent = [set() for _ in mesh.vertices]
    for face in mesh.polygons:
        ids = tuple(face.vertices)
        for a, b in zip(ids, ids[1:] + ids[:1]):
            edges[tuple(sorted((a, b)))] += 1
            adjacent[a].add(b)
            adjacent[b].add(a)
    assert set(edges.values()) == {2}
    unseen, groups = set(range(len(mesh.vertices))), []
    while unseen:
        seed = unseen.pop()
        found, queue = {seed}, [seed]
        while queue:
            for other in adjacent[queue.pop()] & unseen:
                unseen.remove(other)
                found.add(other)
                queue.append(other)
        groups.append(found)
    assert len(groups) == 42 and all(len(g) == 8 for g in groups)
    mesh.calc_loop_triangles()
    volumes = []
    for group in groups:
        anchor = mesh.vertices[min(group)].co
        volume = 0
        for triangle in mesh.loop_triangles:
            if triangle.vertices[0] in group:
                a, b, c = [mesh.vertices[i].co - anchor for i in triangle.vertices]
                volume += a.dot(b.cross(c)) / 6
        assert volume > 0
        volumes.append(volume)
    assert len(mesh.loop_triangles) == 504
    return {
        "closedSolids": 42,
        "allEdgesTwoFaces": True,
        "positiveVolumeEach": True,
        "minimumVolume": min(volumes),
        "triangles": 504,
    }


def proof():
    obj = bpy.data.objects[REPLACEMENT]
    frame_tree = tree(obj)
    matches = [
        o
        for o in bpy.data.collections[COLLECTION].all_objects
        if o.type == "MESH"
        and not o.hide_render
        and o.name.endswith("ENVELOPE_tall_split_glass")
    ]
    assert len(matches) == 1, [o.name for o in matches]
    glass_tree = tree(matches[0])
    segments, length = registration()
    pane_rays, bar_rays, infill_rays, former_bar_rays = [], [], [], []
    for bay in range(7):
        centre = (bay + 0.5) * length / 7
        segment = next((s for s in segments if centre <= s[1]), segments[-1])
        normal = Vector((*segment[4], 0))
        for z in [13.84, 17.4]:
            for fraction in [0.125, 0.375, 0.625, 0.875]:
                along = centre - 1.05 + 2.1 * fraction
                normal = Vector(
                    (*next((s for s in segments if along <= s[1]), segments[-1])[4], 0)
                )
                origin = point(segments, along, 1, z)
                glass = glass_tree.ray_cast(origin, -normal, 2)
                assert glass[0] is not None, (bay, z, fraction)
                assert frame_tree.ray_cast(origin, -normal, glass[3])[0] is None
                pane_rays.append(
                    {
                        "bay": bay,
                        "height": z,
                        "fraction": fraction,
                        "glassDistance": glass[3],
                    }
                )
            for fraction in [0.25, 0.5, 0.75]:
                along = centre - 1.05 + 2.1 * fraction
                normal = Vector(
                    (*next((s for s in segments if along <= s[1]), segments[-1])[4], 0)
                )
                hit = frame_tree.ray_cast(point(segments, along, 1, z), -normal, 2)
                assert hit[0] is not None
                # Check the rigid stile frame, including a bay whose centre
                # crosses a GIS corner. Width is measured along one local facet.
                width = 0.065 if fraction == 0.5 else 0.038
                tangent = Vector(
                    (*next((s for s in segments if along <= s[1]), segments[-1])[3], 0)
                )
                ray_origin = point(segments, along, 1, z)
                assert abs(hit[3] - 1.0875) < 5e-5, (bay, z, fraction, hit[3])
                for delta, expected in [(width * 0.45, True), (width * 0.55, False)]:
                    actual = (
                        frame_tree.ray_cast(ray_origin + tangent * delta, -normal, 2)[0]
                        is not None
                    )
                    assert actual == expected, (bay, z, fraction, delta, actual)
                bar_rays.append(
                    {
                        "bay": bay,
                        "height": z,
                        "fraction": fraction,
                        "measuredWidthVerified": width,
                    }
                )
            for fraction in [1 / 3, 2 / 3]:
                along = centre - 1.05 + 2.1 * fraction
                normal = Vector(
                    (*next((s for s in segments if along <= s[1]), segments[-1])[4], 0)
                )
                assert (
                    frame_tree.ray_cast(point(segments, along, 1, z), -normal, 2)[0]
                    is None
                ), (bay, z, fraction)
                former_bar_rays.append({"bay": bay, "height": z, "fraction": fraction})
        for fraction in [0.25, 0.5, 0.75]:
            origin = point(segments, centre - 1.05 + 2.1 * fraction, 1, 15.58)
            assert frame_tree.ray_cast(origin, -normal, 2)[0] is None
            infill_rays.append(
                {"bay": bay, "fraction": fraction, "noNewBarAcrossOpaqueInfill": True}
            )
    return {
        "topology": topology(obj),
        "fourColumnPaneRays": pane_rays,
        "threeStileRays": bar_rays,
        "oldThirdColumnBarsRemoved": former_bar_rays,
        "opaqueInfillClearance": infill_rays,
        "glassObject": matches[0].name,
    }


def main():
    audit = json.loads((OUT / "audit.json").read_text())
    before = json.loads((OUT / "protected-source-state.json").read_text())
    component = ROOT / audit["componentPath"]
    assert sha(BASE) == SHA == audit["baselineSha256"]
    assert sha(component) == audit["componentSha256"]
    assert sha(OUT / "source-review.json") == audit["sourceReviewSha256"]
    review = json.loads((OUT / "source-review.json").read_text())
    assert all(sha(ROOT / r["local"]) == r["sha256"] for r in review["references"])
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    assert capture() == before
    with bpy.data.libraries.load(str(component), link=False) as (_, loaded):
        loaded.objects = list(audit["addedObjects"])
    for obj in loaded.objects:
        bpy.data.collections[COLLECTION].objects.link(obj)
        for index, name in enumerate(audit["replacementMaterialBindings"][obj.name]):
            obj.data.materials[index] = bpy.data.materials[name]
        assert object_fingerprint(obj) == audit["addedFingerprints"][obj.name]
    source = audit["archivedObjects"][0]
    bpy.data.objects[source].hide_render = True
    bpy.data.objects[source].hide_set(True)
    update_scene()
    result = proof()
    after = capture()
    # Appending a component may create duplicate datablock materials even after
    # rebinding;the original graphs must match,while integration cleans unused copies.
    for name, row in before["objects"].items():
        expected = dict(row)
        if name == source:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
    assert all(
        after["materials"][name] == row for name, row in before["materials"].items()
    )
    assert (
        after["rooms"] == before["rooms"]
        and after["campusRooms"] == before["campusRooms"]
    )
    assert len(after["rooms"]) == 35
    assert set(after["objects"]) - set(before["objects"]) == set(audit["addedObjects"])
    assert sha(BASE) == SHA
    (OUT / "verification.json").write_text(
        json.dumps(
            {
                "passed": True,
                "savedComponentReopened": True,
                "componentSha256": sha(component),
                "protectedOriginalObjects": 8731,
                "protectedOriginalMaterials": 2350,
                "protectedRoomStudies": 35,
                "proof": result,
                "wholeBuildingCompletionClaimed": False,
            },
            indent=2,
        )
        + "\n"
    )
    print(
        "CLM260_PAIRED_SASH_REOPEN_VERIFIED",
        len(result["fourColumnPaneRays"]),
        flush=True,
    )


if __name__ == "__main__":
    main()
