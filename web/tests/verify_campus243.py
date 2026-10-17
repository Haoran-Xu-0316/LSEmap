"""Verify the complete saved243 native against every accepted242 source member."""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/stage243"
MODEL = ROOT / "result/blender/LSE_campus_detailed_v243.blend"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint, update_scene


def main():
    protected = json.loads((OUT / "protected-source-state.json").read_text())
    record = json.loads((OUT / "building-refinement.json").read_text())
    audit = json.loads(
        (ROOT / "result/blender/houghton-footway243/audit.json").read_text()
    )
    digest = hashlib.sha256(MODEL.read_bytes()).hexdigest()
    assert digest == record["sourceModelSha256"]
    assert record["baselineSha256"] == protected["baselineSha256"]
    assert record["archivedObjects"] == audit["archivedObjects"]
    assert record["changedObjects"] == []
    assert record["addedObjects"] == audit["addedObjects"]
    bpy.ops.wm.open_mainfile(filepath=str(MODEL))
    update_scene()
    spec = importlib.util.spec_from_file_location(
        "capture_native_state", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = protected["baselineSha256"]
    current = helper.capture_source()
    assert set(current["objects"]) == set(protected["objects"]) | set(
        audit["addedObjects"]
    )
    for name, expected in protected["objects"].items():
        expected = dict(expected)
        if name in audit["archivedObjects"]:
            expected["hidden"] = True
        assert current["objects"][name] == expected, name
    for name, expected in protected["materials"].items():
        assert current["materials"][name] == expected, name
    assert current["rooms"] == protected["rooms"]
    assert current["campusRooms"] == protected["campusRooms"]
    assert len(current["rooms"]) == 35
    for name in audit["addedObjects"]:
        obj = bpy.data.objects[name]
        assert object_fingerprint(obj) == audit["addedFingerprints"][name]
        assert (
            not obj.hide_render
            and not obj.parent
            and not obj.modifiers
            and not obj.constraints
        )
        assert [c.name for c in obj.users_collection] == ["00_SITE"]
        if name == "SITE243_Houghton_paving_support":
            assert all(v.co.z < 0.024 for v in obj.data.vertices)
        assert all("SITE243_Houghton_graded" not in o.name for o in bpy.data.objects)
    result = {
        "completeNativeReopened": True,
        "sourceModelSha256": digest,
        "originalObjectsVerified": len(protected["objects"]),
        "originalMaterialGraphsVerified": len(protected["materials"]),
        "allOriginalGeometryNormalsUVsModifiersPropertiesAndOwnersPreserved": True,
        "onlyListedOriginalVisibilityChanged": True,
        "protectedRooms": len(protected["rooms"]),
        "protectedRoomMembers": sum(map(len, protected["rooms"].values())),
        "addedObjectsVerified": len(audit["addedObjects"]),
        "gradeCandidateExcluded": True,
        "scope": audit["scope"],
    }
    (OUT / "native-verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        "CAMPUS243_VERIFIED",
        result["originalObjectsVerified"],
        len(audit["addedObjects"]),
        flush=True,
    )


if __name__ == "__main__":
    main()
