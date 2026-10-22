"""Verify the saved complete campus and actual Houghton sill/window geometry."""

import importlib.util
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_buildings_round259 import BASE_SHA, accepted_components, sha
from integrate_exterior_round194 import object_fingerprint, update_scene
from refine_old_exterior259 import capture


def main():
    folder = ROOT / "result/blender/stage259"
    record = json.loads((folder / "building-refinement.json").read_text())
    baseline = ROOT / "result/blender/LSE_campus_detailed_v258.blend"
    current = ROOT / "result/blender/LSE_campus_detailed_v259.blend"
    assert sha(baseline) == record["baselineSha256"] == BASE_SHA
    current_sha = sha(current)
    assert current_sha == record["sourceModelSha256"]
    audits = accepted_components()
    expected_added = set().union(*(set(a["addedObjects"]) for a in audits.values()))
    assert set(record["addedObjects"]) == expected_added
    assert record["archivedObjects"] == record["changedObjects"] == []
    bpy.ops.wm.open_mainfile(filepath=str(baseline))
    update_scene()
    before = capture()
    assert len(before["objects"]) == 8728 and len(before["materials"]) == 2350
    bpy.ops.wm.open_mainfile(filepath=str(current))
    update_scene()
    after = capture()
    assert all(
        after["objects"][name] == state for name, state in before["objects"].items()
    )
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
    spec = importlib.util.spec_from_file_location(
        "old259_geometry", ROOT / "web/tests/verify_old_exterior259.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    geometry = helper.proof_geometry(audits["old259"])
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
        "archivedObjects": [],
        "componentProofsInReopenedCompleteScene": {"old259": geometry},
    }
    (folder / "complete-protection.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("CAMPUS259_COMPLETE_PROTECTED", len(before["objects"]), flush=True)


if __name__ == "__main__":
    main()
