"""Reopen edition256 and protect original architecture, material graphs and rooms."""

import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
from integrate_exterior_round194 import update_scene
from refine_shf_exterior255 import capture, sha


def main():
    folder = ROOT / "result/blender/stage256"
    record = json.loads((folder / "building-refinement.json").read_text())
    baseline = ROOT / "result/blender/LSE_campus_detailed_v255.blend"
    current = ROOT / "result/blender/LSE_campus_detailed_v256.blend"
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
    kgs = json.loads((ROOT / "result/blender/kgs256/audit.json").read_text())
    for name, bindings in kgs["replacementFontBindings"].items():
        text = bpy.data.objects[name]
        original = bpy.data.objects[text["originalObject"]]
        assert text.type == original.type == "FONT"
        for role, font_name in bindings.items():
            assert getattr(text.data, role) == getattr(original.data, role)
            assert getattr(text.data, role) == bpy.data.fonts[font_name]
    result = {
        "completeModelReopened": True,
        "seatedNumbersRetainOriginalFontIdentities": True,
        "sourceModelSha256": sha(current),
        "baselineSha256": sha(baseline),
        "originalObjectsProtected": len(before["objects"]),
        "originalMaterialGraphsProtected": len(before["materials"]),
        "roomStudiesProtected": len(after["rooms"]),
        "roomMembersProtected": sum(len(m) for m in after["rooms"].values()),
        "roomMembershipUnchanged": True,
        "campusRoomMembershipUnchanged": True,
        "addedObjects": record["addedObjects"],
        "archivedObjects": record["archivedObjects"],
    }
    (folder / "complete-protection.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("CAMPUS256_COMPLETE_PROTECTED", len(before["objects"]), flush=True)


if __name__ == "__main__":
    main()
