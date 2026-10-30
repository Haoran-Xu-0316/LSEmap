"""Integrate only the reviewed OLD window and MAR Ground components.

The unresolved SAW roof candidate is excluded. Fixed project paths are suitable
for Blender's Text Editor. Every original asset remains in the native archive.
"""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v279.blend"
BASE_SHA = "b03a0caec932c50e0c7d8ad2a725a43b80eb38abee716f1d1c2d30cde767982c"
DESTINATION = ROOT / "result/blender/LSE_campus_detailed_v283.blend"
OUT = ROOT / "result/blender/stage283"
ACCEPTANCE = OUT / "root-review.json"
ACCEPTANCE_SHA = "0dd9eeb72ecb2aa34ed155cea440982ea98312d04b7badb4f325c320aaeca6ab"
COMPONENTS = [
    SimpleNamespace(
        code="OLD", folder="old283", owner="OLD_EXTERIOR", added=1, archived=1
    ),
    SimpleNamespace(
        code="MAR",
        folder="mar283",
        owner="MAR_PUBLIC_INTERIOR_study",
        added=5,
        archived=4,
    ),
]


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
    assert sha(BASE) == BASE_SHA
    assert sha(ACCEPTANCE) == ACCEPTANCE_SHA
    review = json.loads(ACCEPTANCE.read_text())
    assert review["status"] == "accepted-for-bounded-integration"
    assert review["baselineSha256"] == BASE_SHA
    assert review["excludedCandidates"] == ["saw276"]
    audits = {}
    for component in COMPONENTS:
        folder = ROOT / "result/blender" / component.folder
        audit = json.loads((folder / "audit.json").read_text())
        proof_path = folder / "fresh-process-verification.json"
        proof = json.loads(proof_path.read_text())
        decision = review["components"][component.folder]
        assert audit["baselineSha256"] == proof["baselineSha256"] == BASE_SHA
        assert (
            sha(ROOT / audit["componentPath"])
            == audit["componentSha256"]
            == proof["componentSha256"]
            == decision["componentSha256"]
        )
        assert sha(proof_path) == decision["freshProofSha256"]
        assert proof["freshBlenderProcess"]
        if component.code == "OLD":
            assert proof["status"] == "passed-bounded-candidate"
            assert proof["protection"]["roomMemberships"] == 35
            script_proof = audit
        else:
            assert proof["status"] == "passed-fresh-ground-only-MAR283-component"
            assert proof["roomMembershipsProtected"] == 35
            script_proof = proof
        assert len(audit["addedObjects"]) == component.added
        assert len(audit["archivedObjects"]) == component.archived
        assert audit["changedObjects"] == [] and audit["newMaterials"] == 0
        assert all(sha(ROOT / p) == h for p, h in audit["sourceHashes"].items())
        assert (
            sha(ROOT / f"web/tools/refine_{component.folder}.py")
            == script_proof["authoringScriptSha256"]
        )
        assert (
            sha(ROOT / f"web/tests/verify_{component.folder}.py")
            == script_proof["verificationScriptSha256"]
        )
        assert decision["views"] and all(
            sha(ROOT / p) == h for p, h in decision["views"].items()
        )
        audits[component.folder] = audit
    return audits


def main():
    sys.path.insert(0, str(ROOT / "web/tools"))
    from integrate_exterior_round194 import integrate

    accepted_components()
    integrate(
        base=BASE,
        destination=DESTINATION,
        proof=OUT,
        version=283,
        baseline_proof=ROOT / "result/blender/stage279",
        reports=[
            (s.code, f"result/blender/{s.folder}/audit.json", s.owner)
            for s in COMPONENTS
        ],
        scope="OLD two Houghton ground-window grids; MAR Ground lift walls, ceiling apertures and local service/sill clearance.",
    )
    record_path = OUT / "building-refinement.json"
    record = json.loads(record_path.read_text())
    prior = json.loads(
        (ROOT / "result/blender/stage279/building-refinement.json").read_text()
    )
    for key in ("libraryNativeViewRouting", "librarySourceArchiveScene"):
        record[key] = prior[key]
    record_path.write_text(json.dumps(record, indent=2) + "\n")
    manifest = {
        "version": 283,
        "baselineSha256": BASE_SHA,
        "sourceModelSha256": record["sourceModelSha256"],
        "rootAcceptanceSha256": ACCEPTANCE_SHA,
        "components": [vars(s) for s in COMPONENTS],
        "excludedCandidates": ["saw276"],
        "authoringScriptSha256": sha(Path(__file__)),
        "verificationScriptSha256": sha(ROOT / "web/tests/verify_campus283.py"),
    }
    (OUT / "accepted-components.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("CAMPUS283_INTEGRATED", manifest["sourceModelSha256"], flush=True)


if __name__ == "__main__":
    main()
