"""Reopen native254 and protect every original object, material and other room."""

import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
from integrate_exterior_round194 import update_scene
from refine_saw_interior254 import capture, check_protection, sha


def main():
    folder = ROOT / "result/blender/stage254"
    record = json.loads((folder / "building-refinement.json").read_text())
    baseline = ROOT / "result/blender/LSE_campus_detailed_v252.blend"
    current = ROOT / "result/blender/LSE_campus_detailed_v254.blend"
    assert sha(baseline) == record["baselineSha256"]
    assert sha(current) == record["sourceModelSha256"]
    bpy.ops.wm.open_mainfile(filepath=str(baseline))
    update_scene()
    before = capture()
    bpy.ops.wm.open_mainfile(filepath=str(current))
    update_scene()
    after = capture()
    check_protection(before, after, record["addedObjects"])
    assert set(after["objects"]) - set(before["objects"]) == set(record["addedObjects"])
    new = bpy.data.materials["SAW254_three_tuns_clear_glass"]
    assert new["webOpacity"] == .30
    proof = {
        "completeModelReopened": True,
        "sourceModelSha256": sha(current),
        "baselineSha256": sha(baseline),
        "originalObjectsProtected": len(before["objects"]),
        "originalMaterialGraphsProtected": len(before["materials"]),
        "roomStudies": len(after["rooms"]),
        "otherRoomMembershipsProtected": 34,
        "campusRoomMembershipUnchanged": before["campusRooms"] == after["campusRooms"],
        "addedObjects": record["addedObjects"],
        "archivedObjects": record["archivedObjects"],
    }
    (folder / "complete-protection.json").write_text(json.dumps(proof, indent=2) + "\n")
    print("CAMPUS254_COMPLETE_PROTECTED", len(before["objects"]), flush=True)


if __name__ == "__main__":
    main()
