"""Verify the saved complete campus and actual upper CLM sash geometry."""

import importlib.util
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_buildings_round261 import BASE_SHA, accepted_components, sha
from integrate_exterior_round194 import object_fingerprint, update_scene
from refine_clm_exterior261 import capture


def main():
    folder = ROOT / "result/blender/stage261"
    record = json.loads((folder / "building-refinement.json").read_text())
    baseline = ROOT / "result/blender/LSE_campus_detailed_v260.blend"
    current = ROOT / "result/blender/LSE_campus_detailed_v261.blend"
    assert sha(baseline) == record["baselineSha256"] == BASE_SHA
    current_sha = sha(current)
    assert current_sha == record["sourceModelSha256"]
    audits = accepted_components()
    expected_added = set().union(*(set(a["addedObjects"]) for a in audits.values()))
    assert set(record["addedObjects"]) == expected_added
    expected_archived = set().union(
        *(set(a["archivedObjects"]) for a in audits.values())
    )
    assert set(record["archivedObjects"]) == expected_archived
    assert record["changedObjects"] == []
    bpy.ops.wm.open_mainfile(filepath=str(baseline))
    update_scene()
    before = capture()
    assert len(before["objects"]) == 8733 and len(before["materials"]) == 2350
    bpy.ops.wm.open_mainfile(filepath=str(current))
    update_scene()
    after = capture()
    for name, state in before["objects"].items():
        expected = dict(state)
        if name in expected_archived:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
    for name, state in before["visibility"].items():
        expected = [True, state[1], True] if name in expected_archived else state
        assert after["visibility"][name] == expected, name
    assert after["materials"] == before["materials"]
    assert after["rooms"] == before["rooms"] and len(after["rooms"]) == 35
    assert after["campusRooms"] == before["campusRooms"]
    assert set(after["objects"]) - set(before["objects"]) == expected_added
    for audit in audits.values():
        for name in audit["addedObjects"]:
            obj = bpy.data.objects[name]
            assert not obj.hide_render
            assert (
                object_fingerprint(obj)
                == audit["addedFingerprints"][name]
                == record["addedFingerprints"][name]
            )
            assert [m.name for m in obj.data.materials] == audit[
                "replacementMaterialBindings"
            ][name]
    from mathutils import Vector
    from refine_clm_exterior261 import (
        MEETING,
        REPLACEMENT,
        point,
        registration,
        source_objects,
        tree,
        upper_parts,
    )

    spec = importlib.util.spec_from_file_location(
        "clm261_geometry", ROOT / "web/tests/verify_clm_exterior261.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    audit = audits["clm261"]
    retained = helper.old_geometry_proof(
        bpy.data.objects[audit["archivedObjects"][0]], bpy.data.objects[MEETING]
    )
    geometry = helper.pane_proof()
    proofs = {"clm261": {"retained": retained, "geometry": geometry}}
    _frames, glass = source_objects()
    segments, length = registration()
    windows = upper_parts(glass)
    probes = []
    for kind, rows in [
        ("pane", geometry["fourColumnChannels"]),
        ("stile", geometry["centralAndFineWidths"]),
    ]:
        for row in rows:
            bay = row["bay"]
            _ids, points, _centre = windows[bay]
            chain = (bay + 0.5) * length / 7
            section = next((s for s in segments if chain <= s[1]), segments[-1])
            tangent = Vector((*section[3], 0))
            width = max(p.dot(tangent) for p in points) - min(
                p.dot(tangent) for p in points
            )
            along = chain + width * (row["fraction"] - 0.5)
            local = next((s for s in segments if along <= s[1]), segments[-1])
            normal = Vector((*local[4], 0))
            origin = point(segments, along, 1, row["height"])
            target = (
                glass
                if kind == "pane"
                else bpy.data.objects[
                    MEETING if row["fraction"] == 0.5 else REPLACEMENT
                ]
            )
            hit = tree(target).ray_cast(origin, -normal, 3)
            assert hit[0] is not None
            probes.append(
                {
                    "code": "CLM",
                    "kind": kind,
                    "origin": list(origin),
                    "direction": list(-normal),
                    "distance": hit[3],
                    "materials": [m.name for m in target.data.materials],
                }
            )
    (folder / "production-probes.json").write_text(json.dumps(probes, indent=2) + "\n")
    assert capture() == after
    assert sha(baseline) == BASE_SHA and sha(current) == current_sha
    result = {
        "completeModelReopened": True,
        "sourceModelSha256": current_sha,
        "baselineSha256": BASE_SHA,
        "originalObjectsProtected": len(before["objects"]),
        "originalMaterialGraphsProtected": len(before["materials"]),
        "roomStudiesProtected": len(after["rooms"]),
        "roomMembersProtected": sum(len(m) for m in after["rooms"].values()),
        "roomMembershipUnchanged": True,
        "campusRoomMembershipUnchanged": True,
        "addedObjects": record["addedObjects"],
        "archivedObjects": record["archivedObjects"],
        "componentProofsInReopenedCompleteScene": proofs,
    }
    (folder / "complete-protection.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("CAMPUS261_COMPLETE_PROTECTED", len(before["objects"]), flush=True)


if __name__ == "__main__":
    main()
