"""Fresh complete-campus verification, including retained rooms and street rays."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import bpy

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/stage279"


def main():
    sys.path.insert(0, str(ROOT / "web/tools"))
    import integrate_campus279 as config
    from integrate_exterior_round194 import object_fingerprint, update_scene

    prior_verifier = config.load_module(
        "campus279_preservation", "web/tests/verify_campus275.py"
    )
    capture = lambda: prior_verifier.capture_source(config)
    audit = config.accepted_component()
    record = json.loads((OUT / "building-refinement.json").read_text())
    manifest = json.loads((OUT / "accepted-components.json").read_text())
    digest = config.sha(config.DESTINATION)
    assert config.sha(config.BASE) == config.BASE_SHA == manifest["baselineSha256"]
    assert digest == manifest["sourceModelSha256"] == record["sourceModelSha256"]
    assert manifest["rootAcceptanceSha256"] == config.ACCEPTANCE_SHA
    assert manifest["authoringScriptSha256"] == config.sha(
        ROOT / "web/tools/integrate_campus279.py"
    )
    assert manifest["verificationScriptSha256"] == config.sha(Path(__file__))
    added, archived = set(audit["addedObjects"]), set(audit["archivedObjects"])
    assert added == set(record["addedObjects"]) and archived == set(
        record["archivedObjects"]
    )
    assert record["changedObjects"] == []
    previous = json.loads(
        (ROOT / "result/blender/stage275/building-refinement.json").read_text()
    )
    for key in ("libraryNativeViewRouting", "librarySourceArchiveScene"):
        assert record[key] == previous[key]
    bpy.ops.wm.open_mainfile(filepath=str(config.BASE))
    update_scene()
    before = capture()
    assert len(before["objects"]) == 8770 and len(before["materials"]) == 2355
    images = sorted(i.name for i in bpy.data.images)
    bpy.ops.wm.open_mainfile(filepath=str(config.DESTINATION))
    update_scene()
    after = capture()
    for name, value in before["objects"].items():
        expected = dict(value)
        if name in archived:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
        expected_visibility = (
            [True, before["visibility"][name][1], True]
            if name in archived
            else before["visibility"][name]
        )
        assert after["visibility"][name] == expected_visibility, name
    assert set(after["objects"]) == set(before["objects"]) | added
    assert after["materials"] == before["materials"] | audit["newMaterialGraphs"]
    assert after["rooms"] == before["rooms"] and len(after["rooms"]) == 35
    assert after["campusRooms"] == before["campusRooms"]
    assert sorted(i.name for i in bpy.data.images) == images
    for name in added:
        obj = bpy.data.objects[name]
        assert (
            not obj.hide_render
            and object_fingerprint(obj)
            == audit["addedFingerprints"][name]
            == record["addedFingerprints"][name]
        )
        assert [m.name for m in obj.data.materials] == audit[
            "replacementMaterialBindings"
        ][name]
    verifier = config.load_module(
        "campus279_street_geometry", "web/tests/verify_lindsey277.py"
    )
    actual = verifier.geometry_proof(audit)
    probe_config = SimpleNamespace(
        COMPONENTS=[SimpleNamespace(code="CONTEXT", folder="street277")]
    )
    probes = prior_verifier.surface_probes(probe_config, {"street277": audit})
    assert probes and capture() == after
    assert (
        config.sha(config.BASE) == config.BASE_SHA
        and config.sha(config.DESTINATION) == digest
    )
    (OUT / "production-probes.json").write_text(json.dumps(probes, indent=2) + "\n")
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
        "actualGeometryProofs": {"street277": actual},
        "productionProbes": len(probes),
        "completeCampusSavedAndReopened": True,
        "unlistedComponentsExcluded": True,
        "wholeBuildingCompletionClaimed": False,
    }
    (OUT / "independent-verification.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("CAMPUS279_INDEPENDENTLY_VERIFIED", digest, flush=True)


if __name__ == "__main__":
    main()
