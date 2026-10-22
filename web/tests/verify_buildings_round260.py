"""Verify the saved complete campus and actual CLM window and KSW supported approach geometry."""

import importlib.util
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_buildings_round260 import BASE_SHA, accepted_components, sha
from integrate_exterior_round194 import object_fingerprint, update_scene
from refine_clm_exterior260 import capture


def main():
    folder = ROOT / "result/blender/stage260"
    record = json.loads((folder / "building-refinement.json").read_text())
    baseline = ROOT / "result/blender/LSE_campus_detailed_v259.blend"
    current = ROOT / "result/blender/LSE_campus_detailed_v260.blend"
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
    assert len(before["objects"]) == 8731 and len(before["materials"]) == 2350
    bpy.ops.wm.open_mainfile(filepath=str(current))
    update_scene()
    after = capture()
    for name, state in before["objects"].items():
        expected = dict(state)
        if name in expected_archived:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
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
    proofs = {}
    modules = {}
    for code, name in [("CLM", "clm260"), ("KSW", "ksw260")]:
        spec = importlib.util.spec_from_file_location(
            name + "_geometry",
            ROOT / "web/tests" / ("verify_" + code.lower() + "_exterior260.py"),
        )
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        modules[code] = helper
        proofs[name] = (
            helper.proof() if code == "CLM" else helper.proof_geometry(audits[name])
        )
    # Save actual native surface controls for the independent compiled viewer.
    from mathutils import Vector

    probes = []
    helper = modules["CLM"]
    audit = audits["clm260"]
    obj = bpy.data.objects[audit["addedObjects"][0]]
    segments, length = helper.registration()
    material = audit["replacementMaterialBindings"][obj.name][0]
    for index, bar in enumerate(audit["bars"]):
        outward = Vector(
            (*next((v for v in segments if bar["along"] <= v[1]), segments[-1])[4], 0)
        )
        face = max(
            list(obj.data.polygons)[index * 6 : index * 6 + 6],
            key=lambda f: f.normal.dot(outward),
        )
        normal = (obj.matrix_world.to_3x3() @ face.normal).normalized()
        assert normal.dot(outward) > 0.999
        center = sum(
            (obj.matrix_world @ obj.data.vertices[i].co for i in face.vertices),
            Vector(),
        ) / len(face.vertices)
        probes.append(
            {
                "code": "CLM",
                "kind": "stile",
                "origin": list(center + normal * 0.03),
                "direction": list(-normal),
                "distance": 0.03,
                "materials": [material],
            }
        )
    glass = bpy.data.objects[proofs["clm260"]["glassObject"]]
    for row in proofs["clm260"]["fourColumnPaneRays"]:
        along = (row["bay"] + 0.5) * length / 7 - 1.05 + 2.1 * row["fraction"]
        normal = Vector(
            (*next((v for v in segments if along <= v[1]), segments[-1])[4], 0)
        )
        probes.append(
            {
                "code": "CLM",
                "kind": "pane",
                "origin": list(helper.point(segments, along, 1, row["height"])),
                "direction": list(-normal),
                "distance": row["glassDistance"],
                "materials": [m.name for m in glass.data.materials],
            }
        )
    audit = audits["ksw260"]
    material = audit["replacementMaterialBindings"][audit["addedObjects"][0]][0]
    for row in proofs["ksw260"]["actualTreadLandingRays"]:
        point = Vector(row["point"])
        probes.append(
            {
                "code": "KSW",
                "kind": "tread",
                "origin": list(point + Vector((0, 0, 0.03))),
                "direction": [0, 0, -1],
                "distance": 0.03,
                "materials": [material],
            }
        )
    for row in proofs["ksw260"]["actualGroundSupport"]["actualStepBottomContactRays"]:
        point = Vector(row["stepUnderside"])
        probes.append(
            {
                "code": "KSW",
                "kind": "underside",
                "origin": list(point - Vector((0, 0, 0.03))),
                "direction": [0, 0, 1],
                "distance": 0.03,
                "materials": [material],
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
    print("CAMPUS260_COMPLETE_PROTECTED", len(before["objects"]), flush=True)


if __name__ == "__main__":
    main()
