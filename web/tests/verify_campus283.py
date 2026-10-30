"""Fresh native verification for the bounded OLD/MAR campus integration."""

import json
import sys
from pathlib import Path

import bpy

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
import integrate_campus283 as config
from integrate_exterior_round194 import object_fingerprint, update_scene


def main():
    out = config.OUT
    audits = config.accepted_components()
    record = json.loads((out / "building-refinement.json").read_text())
    manifest = json.loads((out / "accepted-components.json").read_text())
    digest = config.sha(config.DESTINATION)
    assert digest == record["sourceModelSha256"] == manifest["sourceModelSha256"]
    assert record["baselineSha256"] == manifest["baselineSha256"] == config.BASE_SHA
    assert manifest["rootAcceptanceSha256"] == config.ACCEPTANCE_SHA
    assert manifest["components"] == [vars(s) for s in config.COMPONENTS]
    assert manifest["excludedCandidates"] == ["saw276"]
    assert manifest["authoringScriptSha256"] == config.sha(
        ROOT / "web/tools/integrate_campus283.py"
    )
    assert manifest["verificationScriptSha256"] == config.sha(Path(__file__))
    added = set().union(*(set(a["addedObjects"]) for a in audits.values()))
    archived = set().union(*(set(a["archivedObjects"]) for a in audits.values()))
    assert added == set(record["addedObjects"]) and archived == set(
        record["archivedObjects"]
    )
    assert record["changedObjects"] == []
    prior_record = json.loads(
        (ROOT / "result/blender/stage279/building-refinement.json").read_text()
    )
    for key in ("libraryNativeViewRouting", "librarySourceArchiveScene"):
        assert record[key] == prior_record[key]
    helper = config.load_module(
        "campus283_preservation", "web/tests/verify_campus275.py"
    )
    capture = lambda: helper.capture_source(config)
    bpy.ops.wm.open_mainfile(filepath=str(config.BASE))
    update_scene()
    before = capture()
    assert len(before["objects"]) == 8774 and len(before["materials"]) == 2357
    images = sorted(i.name for i in bpy.data.images)
    bpy.ops.wm.open_mainfile(filepath=str(config.DESTINATION))
    update_scene()
    after = capture()
    for name, original in before["objects"].items():
        expected = dict(original)
        if name in archived:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
        expected_visibility = list(before["visibility"][name])
        if name in archived:
            expected_visibility[0] = expected_visibility[2] = True
        assert after["visibility"][name] == expected_visibility, name
    assert set(after["objects"]) == set(before["objects"]) | added
    for key in ("materials", "rooms", "campusRooms"):
        assert after[key] == before[key], key
    assert (
        len(after["rooms"]) == 35 and sorted(i.name for i in bpy.data.images) == images
    )
    actual = {}
    for spec in config.COMPONENTS:
        audit = audits[spec.folder]
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
        verifier = config.load_module(
            f"campus283_{spec.folder}_geometry", f"web/tests/verify_{spec.folder}.py"
        )
        actual[spec.folder] = verifier.geometry_proof(audit)
    probes = helper.surface_probes(config, audits)
    probes += json.loads(
        (ROOT / "result/blender/stage279/production-probes.json").read_text()
    )
    for probe in probes:
        obj = bpy.data.objects[probe["object"]]
        probe["webGeometrySource"] = obj.get("webGeometrySource", obj.name)
    assert capture() == after and config.sha(config.DESTINATION) == digest
    (out / "production-probes.json").write_text(json.dumps(probes, indent=2) + "\n")
    result = {
        "status": "passed-bounded-integration",
        "freshBlenderProcess": True,
        "baselineSha256": config.BASE_SHA,
        "sourceModelSha256": digest,
        "originalObjectsProtected": len(before["objects"]),
        "originalMaterialsProtected": len(before["materials"]),
        "roomMembershipsProtected": len(before["rooms"]),
        "allOriginalGeometryNormalsUVsOwnersPropertiesModifiersPreserved": True,
        "onlyDeclaredVisibilityChanges": sorted(archived),
        "actualGeometryProofs": actual,
        "productionProbes": len(probes),
        "completeCampusSavedAndReopened": True,
        "unlistedComponentsExcluded": True,
        "wholeBuildingCompletionClaimed": False,
    }
    (out / "independent-verification.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("CAMPUS283_INDEPENDENTLY_VERIFIED", digest, flush=True)


if __name__ == "__main__":
    main()
