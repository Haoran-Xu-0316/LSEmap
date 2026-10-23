"""Reopen CLM261 independently and test actual pane channels and old geometry."""

import json
import sys
from collections import Counter
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
import itertools

from integrate_exterior_round194 import object_fingerprint, update_scene
from refine_clm_exterior261 import (
    BASE,
    CENTRAL_WIDTH,
    COLLECTION,
    MEETING,
    OUT,
    REPLACEMENT,
    SHA,
    SIDE_WIDTH,
    capture,
    groups,
    point,
    registration,
    sha,
    source_objects,
    tree,
    upper_parts,
)


def old_geometry_proof(source, meeting):
    assert source.matrix_world == meeting.matrix_world
    assert len(source.data.vertices) == len(meeting.data.vertices) == 288
    assert [tuple(p.vertices) for p in source.data.polygons] == [
        tuple(p.vertices) for p in meeting.data.polygons
    ]
    assert [p.material_index for p in source.data.polygons] == [
        p.material_index for p in meeting.data.polygons
    ]
    assert [m.name for m in source.data.materials] == [
        m.name for m in meeting.data.materials
    ]
    for old, new in zip(source.data.uv_layers, meeting.data.uv_layers):
        assert old.name == new.name
        assert [tuple(v.uv) for v in old.data] == [tuple(v.uv) for v in new.data]
    selected = {i for ids, _pts, _centre in upper_parts(source) for i in ids}
    untouched = [i for i in range(len(source.data.vertices)) if i not in selected]
    assert len(untouched) == 29 * 8
    for i in untouched:
        assert source.data.vertices[i].co == meeting.data.vertices[i].co
    segments, length = registration()
    widths = []
    _frame, glass = source_objects()
    glass_tree = tree(glass)
    for bay, ((ids, old, centre), (_ids, new, newcentre)) in enumerate(
        zip(upper_parts(source), upper_parts(meeting))
    ):
        chain = (bay + 0.5) * length / 7
        section = next((s for s in segments if chain <= s[1]), segments[-1])
        u, n = Vector((*section[3], 0)), Vector((*section[4], 0))
        centre_change = newcentre - centre
        assert abs(centre_change.dot(u)) < 3e-5 and abs(centre_change.z) < 3e-5
        glasshit = glass_tree.ray_cast(newcentre + n, -n, 2)
        assert glasshit[0] is not None
        actual_offset = (newcentre - glasshit[0]).dot(n)
        assert abs(actual_offset - 0.034) < 0.00006
        if bay == 5:
            assert -0.061 < centre_change.dot(n) < -0.060
        else:
            assert abs(centre_change.dot(n)) < 0.00005
        oldwidth = max(p.dot(u) for p in old) - min(p.dot(u) for p in old)
        newwidth = max(p.dot(u) for p in new) - min(p.dot(u) for p in new)
        assert abs(oldwidth - 0.038) < 4e-5 and abs(newwidth - CENTRAL_WIDTH) < 4e-5
        for i in ids:
            change = (
                meeting.matrix_world @ meeting.data.vertices[i].co
                - source.matrix_world @ source.data.vertices[i].co
            )
            assert (
                abs(change.z) < 1e-7
                and abs(change.dot(n) - centre_change.dot(n)) < 3e-5
            )
        widths.append(
            {
                "bay": bay,
                "sourceWidth": oldwidth,
                "newWidth": newwidth,
                "normalDepthCorrection": centre_change.dot(n),
                "actualOffsetFromGlassFront": actual_offset,
            }
        )
    return {
        "unrelatedSolidsRetainedExactly": 29,
        "allOriginalUVsRetainedExactly": True,
        "onlySelected7WidthsAndGlassRegistrationChanged": widths,
    }


def topology(obj):
    edges = Counter()
    for face in obj.data.polygons:
        ids = tuple(face.vertices)
        for a, b in zip(ids, ids[1:] + ids[:1]):
            edges[tuple(sorted((a, b)))] += 1
    assert set(edges.values()) == {2}
    islands = groups(obj)
    assert len(islands) == 14 and all(len(ids) == 8 for ids in islands)
    obj.data.calc_loop_triangles()
    assert len(obj.data.loop_triangles) == 168
    for ids in islands:
        anchor = obj.data.vertices[ids[0]].co
        volume = 0
        for face in obj.data.loop_triangles:
            if face.vertices[0] not in ids:
                continue
            a, b, c = [obj.data.vertices[i].co - anchor for i in face.vertices]
            volume += a.dot(b.cross(c)) / 6
        assert volume > 0
    return {"closedSolids": 14, "triangles": 168, "positiveVolumes": True}


def pane_proof():
    fine = bpy.data.objects[REPLACEMENT]
    meeting = bpy.data.objects[MEETING]
    _current, glass = source_objects()
    gtree, ftree, mtree = tree(glass), tree(fine), tree(meeting)
    # Derive every unobstructed row interval from the actual retained rail mesh.
    rails = [
        o
        for o in bpy.data.collections[COLLECTION].all_objects
        if o.type == "MESH"
        and not o.hide_render
        and o.name.endswith("D3_window_glazing_bars")
    ]
    assert len(rails) == 1
    railtree = tree(rails[0])
    segments, length = registration()
    panes, barchecks = [], []
    for bay, (_ids, pts, centre) in enumerate(upper_parts(glass)):
        chain = (bay + 0.5) * length / 7
        section = next((s for s in segments if chain <= s[1]), segments[-1])
        u = Vector((*section[3], 0))
        width = max(p.dot(u) for p in pts) - min(p.dot(u) for p in pts)
        cuts = [19.4, 21.66]
        for ids in groups(rails[0]):
            points = [rails[0].matrix_world @ rails[0].data.vertices[i].co for i in ids]
            c = sum(points, Vector()) / len(points)
            if abs((c - centre).dot(u)) < 0.15 and 19.4 < c.z < 21.66:
                cuts.extend([min(p.z for p in points), max(p.z for p in points)])
        cuts = sorted(cuts)
        heights = [(a + b) / 2 for a, b in itertools.pairwise(cuts) if b - a > 0.10]
        assert len(heights) >= 2, (bay, heights)
        for height in heights:
            for fraction in [0.125, 0.375, 0.625, 0.875]:
                along = chain + width * (fraction - 0.5)
                local = next((s for s in segments if along <= s[1]), segments[-1])
                n = Vector((*local[4], 0))
                origin = point(segments, along, 1, height)
                glasshit = gtree.ray_cast(origin, -n, 3)
                assert glasshit[0] is not None
                for t in [ftree, mtree, railtree]:
                    assert t.ray_cast(origin, -n, glasshit[3])[0] is None, (
                        bay,
                        height,
                        fraction,
                    )
                panes.append(
                    {
                        "bay": bay,
                        "height": height,
                        "fraction": fraction,
                        "firstFrameOrGlassSurface": "retainedGlass",
                    }
                )
            for fraction in [0.25, 0.5, 0.75]:
                along = chain + width * (fraction - 0.5)
                local = next((s for s in segments if along <= s[1]), segments[-1])
                n, u = Vector((*local[4], 0)), Vector((*local[3], 0))
                origin = point(segments, along, 1, height)
                target = mtree if fraction == 0.5 else ftree
                hit = target.ray_cast(origin, -n, 3)
                glasshit = gtree.ray_cast(origin, -n, 3)
                assert (
                    hit[0] is not None
                    and glasshit[0] is not None
                    and hit[3] < glasshit[3]
                ), (bay, fraction, height)
                expected = CENTRAL_WIDTH if fraction == 0.5 else SIDE_WIDTH
                for direction in [-1, 1]:
                    for delta, should_hit in [
                        (expected * 0.45, True),
                        (expected * 0.55, False),
                    ]:
                        result = (
                            target.ray_cast(origin + u * delta * direction, -n, 3)[0]
                            is not None
                        )
                        assert result == should_hit, (
                            bay,
                            fraction,
                            height,
                            delta,
                            result,
                        )
                barchecks.append(
                    {
                        "bay": bay,
                        "height": height,
                        "fraction": fraction,
                        "verifiedWidth": expected,
                    }
                )
    return {
        "fourColumnChannels": panes,
        "centralAndFineWidths": barchecks,
        "fineTopology": topology(fine),
    }


def main():
    audit = json.loads((OUT / "audit.json").read_text())
    before = json.loads((OUT / "protected-source-state.json").read_text())
    component = ROOT / audit["componentPath"]
    assert sha(BASE) == SHA == audit["baselineSha256"]
    assert (
        sha(component) == audit["componentSha256"]
        and sha(OUT / "source-review.json") == audit["sourceReviewSha256"]
    )
    assert (
        sha(OUT / "glass-registration-diagnosis.json")
        == audit["glassRegistrationDiagnosisSha256"]
    )
    review = json.loads((OUT / "source-review.json").read_text())
    assert all(sha(ROOT / r["local"]) == r["sha256"] for r in review["references"])
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    assert capture() == before
    source = bpy.data.objects[audit["archivedObjects"][0]]
    with bpy.data.libraries.load(str(component), link=False) as (_library, loaded):
        loaded.objects = list(audit["addedObjects"])
    for obj in loaded.objects:
        bpy.data.collections[COLLECTION].objects.link(obj)
        for index, name in enumerate(audit["replacementMaterialBindings"][obj.name]):
            obj.data.materials[index] = bpy.data.materials[name]
        assert object_fingerprint(obj) == audit["addedFingerprints"][obj.name]
    source.hide_render = True
    source.hide_set(True)
    update_scene()
    retained = old_geometry_proof(source, bpy.data.objects[MEETING])
    proof = pane_proof()
    after = capture()
    for name, row in before["objects"].items():
        expected = dict(row)
        if name == source.name:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
    assert all(
        after["materials"][name] == row for name, row in before["materials"].items()
    )
    for name, row in before["visibility"].items():
        assert after["visibility"][name] == (
            [True, row[1], True] if name == source.name else row
        ), name
    assert (
        before["rooms"] == after["rooms"]
        and before["campusRooms"] == after["campusRooms"]
        and len(after["rooms"]) == 35
    )
    assert set(after["objects"]) - set(before["objects"]) == set(audit["addedObjects"])
    assert sha(BASE) == SHA
    report = {
        "passed": True,
        "savedComponentReopened": True,
        "componentSha256": sha(component),
        "protectedOriginalObjects": len(before["objects"]),
        "protectedOriginalMaterials": len(before["materials"]),
        "protectedRoomStudies": 35,
        "retainedMixedFrameGeometry": retained,
        "proof": proof,
        "wholeBuildingCompletionClaimed": False,
        "roofEdited": False,
    }
    (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "CLM261_UPPER_SASH_REOPEN_VERIFIED",
        len(proof["fourColumnChannels"]),
        flush=True,
    )


if __name__ == "__main__":
    main()
