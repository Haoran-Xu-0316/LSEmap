"""Reopen the complete campus and protect materials, room ownership and sources."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
sys.path.insert(0, str(ROOT / "web/tests"))
from integrate_exterior_round194 import update_scene
from verify_campus241 import capture_source


def main():
    folder = ROOT / "result/blender/stage252"
    record = json.loads((folder / "building-refinement.json").read_text())
    baseline = ROOT / "result/blender/LSE_campus_detailed_v251.blend"
    current = ROOT / "result/blender/LSE_campus_detailed_v252.blend"
    assert hashlib.sha256(baseline.read_bytes()).hexdigest() == record["baselineSha256"]
    assert hashlib.sha256(current.read_bytes()).hexdigest() == record["sourceModelSha256"]
    bpy.ops.wm.open_mainfile(filepath=str(baseline))
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    update_scene()
    before = capture_source()
    bpy.ops.wm.open_mainfile(filepath=str(current))
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    update_scene()
    after = capture_source()
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
    proof = {
        "completeModelReopened": True,
        "sourceModelSha256": record["sourceModelSha256"],
        "baselineSha256": record["baselineSha256"],
        "originalObjectsProtected": len(before["objects"]),
        "originalMaterialGraphsProtected": len(before["materials"]),
        "protectedRooms": len(after["rooms"]),
        "protectedRoomMembers": sum(len(members) for members in after["rooms"].values()),
        "roomCampusMembershipUnchanged": True,
        "addedObjects": record["addedObjects"],
        "archivedObjects": record["archivedObjects"],
    }
    (folder / "complete-protection.json").write_text(json.dumps(proof, indent=2) + "\n")
    print("CAMPUS252_COMPLETE_PROTECTED", len(before["objects"]), len(before["materials"]), flush=True)


if __name__ == "__main__":
    main()
