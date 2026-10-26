"""Integrate explicitly accepted components into a new protected campus275 file.

Fixed269baseline. Only OLD, MAR and CBG are currently accepted and listed. To add another
component, root must append a ComponentSpec with its reviewed scope and pinned
component/fresh-proof hashes; an unlisted or unverified SAW is never inferred.
Run main() in Blender. No source/public model or metadata is overwritten.
"""

import hashlib
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v269.blend"
BASE_SHA = "a44026d64bb57cea159a44b1fa96b7b9be13e7d4af034f57d09beb62480ef21b"
DESTINATION = ROOT / "result/blender/LSE_campus_detailed_v275.blend"
OUT = ROOT / "result/blender/stage275"


@dataclass(frozen=True)
class ComponentSpec:
    code: str
    folder: str
    owner: str
    component_sha256: str
    fresh_proof_sha256: str
    fresh_status: str
    verifier: str
    verifier_sha256: str
    accepted_scope: str


# Append only components explicitly accepted by root after fresh verification.
# Keep each component's own verifier; do not extend OLD's bounded acceptance.
COMPONENTS = (
    ComponentSpec(
        code="OLD",
        folder="old270",
        owner="OLD_EXTERIOR",
        component_sha256="b58245f31bb5fc97c39807968f4fb71b549a553a8e36e9b78aa65668e9211d4b",
        fresh_proof_sha256="9b83b32d69af8e3a0e5a79116a7a5d6098211f96c4ed01fe1797d53c9652a1d2",
        fresh_status="passed-bounded-candidate",
        verifier="web/tests/verify_old270.py",
        verifier_sha256="1b39a43c6b5e5d12ddea4025cc73f65e5062f69cbdf26f976ccf3c0ccfa2eb46",
        accepted_scope="Four ordinary lower Clare grids:6columns8rows. Upper28native members, original glazing and opening extents retained. Dimensions remain photo estimates.",
    ),
    ComponentSpec(
        code="MAR",
        folder="mar273",
        owner="MAR_PUBLIC_INTERIOR_study",
        component_sha256="e2c7a8d78ec6842477f7a776d57e1fb11b6716e362f68cb97942ab2895c37f84",
        fresh_proof_sha256="660f8744d76eaf6aa9c56841e3475995f9bae1c60ac457b2d014ccc7cee51229",
        fresh_status="passed-bounded-four-shaft-two-floor-component",
        verifier="web/tests/verify_mar273.py",
        verifier_sha256="53ea452313d516710ece9493a42d7f3d2e1703c3f82413239114bb52faf1e8ae",
        accepted_scope="Four source-identified main-core shafts coordinated across Second and Third, including the previously filled fourth shaft. Retain21.9mplate and all detached room studies. Vertical datums and door-heads remain estimates; no whole-height shaft claim.",
    ),
    ComponentSpec(
        code="CBG",
        folder="cbg274",
        owner="CBG_EXTERIOR",
        component_sha256="c51df241d5541d0f96dd84f4c304e7d6e0679a32efe504dd1c1a0db120994b4e",
        fresh_proof_sha256="a00622196702699fb63b166447fbb9b3cfa736ea45efc3512b1a204914fb8725",
        fresh_status="passed-bounded-candidate",
        verifier="web/tests/verify_cbg274.py",
        verifier_sha256="1528d3014910db2088f10d2eedc40dfd3398a092d15879c774e763e801037fdb",
        accepted_scope="Upper two courtyard storeys return shade/infill to the photographed G4 boundary; restore two single clear panes without changing the red/orange finish or main framing. Whole-facade fin spacing remains estimated.",
    ),
)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def accepted_components():
    assert COMPONENTS and len({s.folder for s in COMPONENTS}) == len(COMPONENTS)
    audits, added, archived = {}, set(), set()
    for spec in COMPONENTS:
        folder = ROOT / "result/blender" / spec.folder
        audit = json.loads((folder / "audit.json").read_text())
        proof_path = folder / "fresh-process-verification.json"
        proof = json.loads(proof_path.read_text())
        acceptance = json.loads((folder / "acceptance.json").read_text())
        assert acceptance["status"] == "accepted_for_bounded_integration"
        assert acceptance["componentSha256"] == spec.component_sha256
        assert acceptance["verificationSha256"] == sha(proof_path)
        assert acceptance["views"]
        for view, digest in acceptance["views"].items():
            assert sha(ROOT / "result/blender" / view) == digest, view
        assert (
            len(spec.component_sha256)
            == len(spec.fresh_proof_sha256)
            == len(spec.verifier_sha256)
            == 64
        )
        assert spec.accepted_scope and sha(proof_path) == spec.fresh_proof_sha256
        assert audit["baselineSha256"] == proof["baselineSha256"] == BASE_SHA
        assert proof["freshBlenderProcess"] and proof["status"] == spec.fresh_status
        assert proof["status"].startswith("passed")
        assert audit["destinationCollection"] == spec.owner
        assert (
            sha(ROOT / audit["componentPath"])
            == audit["componentSha256"]
            == proof["componentSha256"]
            == spec.component_sha256
        )
        if audit.get("sourcePlan"):
            assert sha(ROOT / audit["sourcePlan"]) == audit["sourcePlanSha256"]
        assert all(sha(ROOT / p) == h for p, h in audit.get("sourceHashes", {}).items())
        assert sha(ROOT / spec.verifier) == spec.verifier_sha256
        # Preserve the build-time identity when a formatting-only review precedes
        # fresh verification; bind the runner actually used by the fresh proof.
        recorded_verifier = proof.get(
            "verificationScriptSha256", audit.get("verificationScriptSha256")
        )
        if recorded_verifier:
            assert recorded_verifier == spec.verifier_sha256
        assert audit["changedObjects"] == []
        names, hidden = set(audit["addedObjects"]), set(audit["archivedObjects"])
        assert len(names) == len(audit["addedObjects"]) and len(hidden) == len(
            audit["archivedObjects"]
        )
        assert not names & added and not hidden & archived and not names & hidden
        added |= names
        archived |= hidden
        if spec.code == "OLD":
            actual = proof["actualMeshProof"]
            assert len(actual["actualWindows"]) == 4
            assert all(
                w["rows"] == 8 and w["columns"] == 6 for w in actual["actualWindows"]
            )
            assert actual["upperNativeMembersExact"] == 28
            assert actual["upperNativeFacesCoordinatesUVsMaterialsExact"] == 168
            assert actual["unobstructedActualGlassPaneRays"] == 192
            assert actual["actualNativeOuterFrameContacts"] == 96
            assert actual["materialsAdded"] == actual["imagesAdded"] == 0
        audits[spec.folder] = audit
    assert not added & archived
    return audits


def main():
    sys.path.insert(0, str(ROOT / "web/tools"))
    from integrate_exterior_round194 import integrate

    assert sha(BASE) == BASE_SHA
    audits = accepted_components()
    integration_manifest = {
        "version": 275,
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": BASE_SHA,
        "destination": str(DESTINATION.relative_to(ROOT)),
        "components": [vars(spec) for spec in COMPONENTS],
        "componentHashes": {name: a["componentSha256"] for name, a in audits.items()},
        "unlistedComponentsExcluded": True,
        "authoringScriptSha256": sha(Path(__file__)),
        "verificationScriptSha256": sha(ROOT / "web/tests/verify_campus275.py"),
    }
    integrate(
        base=BASE,
        destination=DESTINATION,
        proof=OUT,
        version=275,
        baseline_proof=ROOT / "result/blender/stage269",
        reports=[
            (spec.code, f"result/blender/{spec.folder}/audit.json", spec.owner)
            for spec in COMPONENTS
        ],
        scope="; ".join(spec.accepted_scope for spec in COMPONENTS),
    )
    record_path = OUT / "building-refinement.json"
    record = json.loads(record_path.read_text())
    previous = json.loads(
        (ROOT / "result/blender/stage269/building-refinement.json").read_text()
    )
    for key in ("libraryNativeViewRouting", "librarySourceArchiveScene"):
        record[key] = previous[key]
    record_path.write_text(json.dumps(record, indent=2) + "\n")
    integration_manifest["sourceModelSha256"] = record["sourceModelSha256"]
    (OUT / "accepted-components.json").write_text(
        json.dumps(integration_manifest, indent=2) + "\n"
    )
    print(
        "CAMPUS275_INTEGRATED", sorted(audits), record["sourceModelSha256"], flush=True
    )


if __name__ == "__main__":
    main()
