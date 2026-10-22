"""Reopen edition258 and verify all originals plus its three bounded components.

Component proof functions operate on this saved complete scene. They never
reopen a component or replace the complete scene with a baseline during checks.
"""

import importlib.util
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_buildings_round258 import COMPONENTS, sha
from integrate_exterior_round194 import object_fingerprint, update_scene
from refine_mar_structure258 import capture, section_proof, volume_contact_proof
from refine_portsmouth_exterior207 import material_fingerprint

BASE_SHA = "5f73b29480de08425d4d8ab3c39aa1e2b9231656f81f1f763ee1ffa200568db9"


def load_verifier(name):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "web/tests" / (name + ".py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_mar_finish(record):
    """Reuse the independent component verifier's actual scene ray trees."""
    helper = load_verifier("verify_mar_finish258")
    material = bpy.data.materials[helper.MATERIAL]
    original = bpy.data.materials[helper.FIN]
    helper.other_material_values_preserved(material, original)
    base = helper.shader(material).inputs["Base Color"]
    background = helper.shader(bpy.data.materials[helper.BACKGROUND]).inputs[
        "Base Color"
    ]
    assert not base.is_linked
    assert all(
        abs(base.default_value[i] - background.default_value[i] * helper.FACTOR) < 1e-7
        for i in range(3)
    )
    assert (
        abs(
            base.default_value[3]
            - helper.shader(original).inputs["Base Color"].default_value[3]
        )
        < 1e-7
    )
    assert all(
        abs(material.diffuse_color[i] - base.default_value[i]) < 1e-7 for i in range(3)
    )
    trees = helper.actual_trees()
    probes = []
    for row in record["records"]:
        obj, source = bpy.data.objects[row["added"]], bpy.data.objects[row["source"]]
        assert helper.mesh_record(obj) == helper.mesh_record(source) == row["mesh"]
        assert (
            helper.normal_record(obj.data)
            == helper.normal_record(source.data)
            == row["normals"]
        )
        assert helper.geometry_groups(obj) == row["groups"]
        assert obj.data.materials[0] == material
        for sample in row["worldFaceProbes"]:
            points = [
                obj.matrix_world @ obj.data.vertices[i].co
                for i in sample["triangleVertexIndices"]
            ]
            center = sum(points, Vector()) / 3
            normal = (points[1] - points[0]).cross(points[2] - points[0]).normalized()
            assert (center - Vector(sample["worldFrontTriangleCentroid"])).length < 1e-6
            assert (normal - Vector(sample["worldOutwardNormal"])).length < 1e-6
            origin = center + normal * 0.035
            assert (origin - Vector(sample["worldProbeOrigin"])).length < 1e-6
            hits = []
            for name, tree in trees:
                hit = tree.ray_cast(origin, -normal, 0.07)
                if hit[0] is not None:
                    hits.append((hit[3], name))
            assert hits
            distance, name = min(hits)
            assert name == obj.name and abs(distance - 0.035) < 0.00002
            probes.append(
                {
                    "object": obj.name,
                    "group": sample["index"],
                    "firstSurface": name,
                    "distance": distance,
                }
            )
    assert len(probes) == 9
    return {
        "geometryUVNormalsAndOtherMaterialValuesPreserved": True,
        "actualCompleteSceneFaceProbes": probes,
    }


def verify_mar_deck(record):
    helper = load_verifier("verify_mar_structure258")
    source = bpy.data.objects[helper.SOURCE]
    replacement = bpy.data.objects[helper.REPLACEMENT]
    section = section_proof(source, replacement)
    contacts = volume_contact_proof(source, replacement)
    assert section == record["sectionProof"]
    assert contacts == record["actualVolumeContactProof"]
    assert source.hide_render and not replacement.hide_render
    mar = next(
        row
        for row in json.loads((ROOT / "web/tools/building-metadata.json").read_text())[
            "buildings"
        ]
        if row["code"] == "MAR"
    )
    exported = mar["interiorAdditionalObjects"]
    assert helper.SOURCE not in exported and helper.REPLACEMENT in exported
    assert "MAR251_third_south_lift_core_walls" in exported
    return {
        "sectionProof": section,
        "actualVolumeContactProof": contacts,
        "explicitInteriorExportUsesSolidReplacement": True,
    }


def component_records():
    records = {}
    for code, name, collection in COMPONENTS:
        folder = ROOT / "result/blender" / name
        audit = json.loads((folder / "audit.json").read_text())
        verified = json.loads((folder / "verification.json").read_text())
        accepted = json.loads((folder / "acceptance.json").read_text())
        assert audit["baselineSha256"] == BASE_SHA
        assert verified["passed"]
        assert accepted["status"] == "accepted_for_bounded_integration"
        assert (
            accepted["componentSha256"]
            == audit["componentSha256"]
            == sha(ROOT / audit["componentPath"])
        )
        assert accepted["verificationSha256"] == sha(folder / "verification.json")
        for image, expected in accepted["views"].items():
            assert sha(folder / image) == expected
        assert audit.get("destinationCollection", collection) == collection, code
        records[name] = audit
    return records


def main():
    folder = ROOT / "result/blender/stage258"
    record = json.loads((folder / "building-refinement.json").read_text())
    baseline = ROOT / "result/blender/LSE_campus_detailed_v257.blend"
    current = ROOT / "result/blender/LSE_campus_detailed_v258.blend"
    assert sha(baseline) == record["baselineSha256"] == BASE_SHA
    current_sha = sha(current)
    assert current_sha == record["sourceModelSha256"]
    audits = component_records()
    expected_added, expected_archived, new_materials = set(), set(), {}
    for audit in audits.values():
        assert not expected_added.intersection(audit["addedObjects"])
        assert not expected_archived.intersection(audit["archivedObjects"])
        expected_added.update(audit["addedObjects"])
        expected_archived.update(audit["archivedObjects"])
        new_materials.update(audit.get("newMaterialGraphs", {}))
    assert set(record["addedObjects"]) == expected_added
    assert set(record["archivedObjects"]) == expected_archived
    assert record["changedObjects"] == []
    bpy.ops.wm.open_mainfile(filepath=str(baseline))
    update_scene()
    before = capture()
    assert len(before["objects"]) == 8695 and len(before["materials"]) == 2349
    bpy.ops.wm.open_mainfile(filepath=str(current))
    update_scene()
    after = capture()
    for name, state in before["objects"].items():
        expected = dict(state)
        if name in expected_archived:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
    for name, state in before["materials"].items():
        assert after["materials"][name] == state, name
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
            bindings = audit.get("replacementMaterialBindings", {}).get(name)
            if bindings is not None:
                assert [m.name if m else None for m in obj.data.materials] == bindings
        for name, fingerprint in audit.get("newMaterialGraphs", {}).items():
            assert material_fingerprint(bpy.data.materials[name]) == fingerprint
    proofs = {
        "mar-finish258": verify_mar_finish(audits["mar-finish258"]),
        "mar258": verify_mar_deck(audits["mar258"]),
        "lrb258": load_verifier("verify_lrb_approach258").proof_geometry(
            audits["lrb258"]
        ),
    }
    # Component proofs may create and delete temporary witness materials, but
    # cannot alter the saved originals, append objects or change room membership.
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
        "auditDerivedAddedObjectCount": len(expected_added),
        "auditDerivedArchivedObjectCount": len(expected_archived),
        "declaredNewMaterialGraphsVerified": sorted(new_materials),
        "componentProofsInReopenedCompleteScene": proofs,
    }
    (folder / "complete-protection.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("CAMPUS258_COMPLETE_PROTECTED", len(before["objects"]), flush=True)


if __name__ == "__main__":
    main()
