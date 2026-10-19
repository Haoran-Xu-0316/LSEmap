"""Integrate the photographed OLD portal grille into the complete campus.

COL's registered source facade remains private pending roof coordination.
"""

import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
from integrate_exterior_round194 import integrate


def main():
    folder = ROOT / "result/blender/old-exterior249"
    audit = json.loads((folder / "audit.json").read_text())
    acceptance = json.loads((folder / "acceptance.json").read_text())
    proof_path = folder / "verification.json"
    proof = json.loads(proof_path.read_text())
    assert acceptance["componentSha256"] == audit["componentSha256"]
    assert (
        hashlib.sha256(proof_path.read_bytes()).hexdigest()
        == acceptance["savedProofSha256"]
    )
    assert proof["savedComponentReopened"] and proof["triangles"] == 24
    assert (
        proof["originalObjectsUnchanged"] == 8636
        and proof["originalMaterialGraphsUnchanged"] == 2341
    )
    assert proof["protectedRooms"] == 35 and proof["closedManifoldSolids"] == 2
    assert not audit["archivedObjects"] and not audit["changedObjects"]
    bpy.context.preferences.filepaths.save_version = 0
    integrate(
        base=ROOT / "result/blender/LSE_campus_detailed_v248.blend",
        destination=ROOT / "result/blender/LSE_campus_detailed_v249.blend",
        proof=ROOT / "result/blender/stage249",
        version=249,
        baseline_proof=ROOT / "result/blender/stage248",
        reports=[("OLD", "result/blender/old-exterior249/audit.json", "OLD_EXTERIOR")],
        scope="Restore the photographed two horizontal grille rails above OLD entrance doors. Original frames, glass, artwork, materials, buildings, roads and35room studies remain intact. Rail section and setback are estimates. COL registration stays private pending whole-building roof coordination.",
    )
    path = ROOT / "result/blender/stage249/building-refinement.json"
    record = json.loads(path.read_text())
    prior = json.loads(
        (ROOT / "result/blender/stage248/building-refinement.json").read_text()
    )
    for key in ["libraryNativeViewRouting", "librarySourceArchiveScene"]:
        record[key] = prior[key]
    path.write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    main()
