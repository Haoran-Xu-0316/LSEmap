"""Reopen edition255 and protect original architecture, material graphs and rooms."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
from integrate_exterior_round194 import update_scene
from refine_shf_exterior255 import capture, sha


def main():
    folder = ROOT / "result/blender/stage255"
    record = json.loads((folder / "building-refinement.json").read_text())
    baseline = ROOT / "result/blender/LSE_campus_detailed_v254.blend"
    current = ROOT / "result/blender/LSE_campus_detailed_v255.blend"
    assert sha(baseline) == record["baselineSha256"]
    assert sha(current) == record["sourceModelSha256"]
    bpy.ops.wm.open_mainfile(filepath=str(baseline))
    update_scene()
    before = capture()
    bpy.ops.wm.open_mainfile(filepath=str(current))
    update_scene()
    after = capture()
    for name, state in before["objects"].items():
        expected = dict(state)
        if name in record["archivedObjects"]:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
    for name, state in before["materials"].items():
        assert after["materials"][name] == state, name
    assert after["rooms"] == before["rooms"] and len(after["rooms"]) == 35
    assert after["campusRooms"] == before["campusRooms"]
    assert set(after["objects"]) - set(before["objects"]) == set(record["addedObjects"])
    cow = json.loads((ROOT / "result/blender/cow255/audit.json").read_text())
    head = bpy.data.objects[cow["addedObjects"][1]]
    policy = cow["headBevel"]
    weights = [
        value.value for value in head.data.attributes[policy["weightAttribute"]].data
    ]
    assert weights == policy["weights"]
    assert (
        hashlib.sha256(json.dumps(weights).encode()).hexdigest()
        == policy["weightsSha256"]
    )
    assert head.modifiers[0].limit_method == "WEIGHT"
    assert abs(head.modifiers[0].width - policy["width"]) < 1e-8
    assert (
        sum(value == 0 for value in weights)
        == len(cow["cancelledInternalBevelEdges"])
        == 32
    )
    result = {
        "completeModelReopened": True,
        "sourceModelSha256": sha(current),
        "baselineSha256": sha(baseline),
        "originalObjectsProtected": len(before["objects"]),
        "originalMaterialGraphsProtected": len(before["materials"]),
        "roomStudiesProtected": len(after["rooms"]),
        "roomMembersProtected": sum(len(m) for m in after["rooms"].values()),
        "roomMembershipUnchanged": True,
        "headWeightAttributeVerified": True,
        "internalHeadBevelEdgesCancelled": 32,
        "campusRoomMembershipUnchanged": True,
        "addedObjects": record["addedObjects"],
        "archivedObjects": record["archivedObjects"],
    }
    (folder / "complete-protection.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("CAMPUS255_COMPLETE_PROTECTED", len(before["objects"]), flush=True)


if __name__ == "__main__":
    main()
