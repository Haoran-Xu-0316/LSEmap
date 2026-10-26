"""Combine reviewed park and MAR components into one protected campus snapshot."""
import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import integrate

BASE_SHA = 'f55f5975ea5e4d755f0c883bc64965b928a3d03add666c598a9b7e987bb70c2d'
COMPONENTS = [
    ('LANDSCAPE', 'park267', '03_PUBLIC_REALM'),
    ('MAR', 'mar269', 'MAR_PUBLIC_INTERIOR_study'),
]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def accepted_components():
    records = {}
    for code, name, owner in COMPONENTS:
        folder = ROOT / 'result/blender' / name
        audit = json.loads((folder / 'audit.json').read_text())
        proof_path = folder / 'fresh-process-verification.json'
        proof = json.loads(proof_path.read_text())
        accepted = json.loads((folder / 'acceptance.json').read_text())
        assert audit['baselineSha256'] == BASE_SHA, code
        assert audit['destinationCollection'] == owner, code
        assert proof['freshBlenderProcess'], code
        if code == 'MAR':
            assert proof['status'] == 'passed-bounded-candidate-only'
            assert proof['candidateOnly'] and not proof['fullHeightShaftAcceptance']
            assert proof['actualMeshProof']['threeFloorBoresOpen']
            assert accepted['scopeOnlySecondFloorLayers']
            assert not accepted['fullHeightShaftAcceptance']
        else:
            assert proof['status'] == 'passed', code
        assert accepted['status'] == 'accepted_for_bounded_integration', code
        assert accepted['verificationSha256'] == sha(proof_path), code
        assert accepted['componentSha256'] == audit['componentSha256'] == sha(ROOT / audit['componentPath']), code
        assert accepted['views'], code
        for path, digest in accepted['views'].items():
            assert sha(folder / path) == digest, path
        records[name] = audit
    return records


def main():
    base = ROOT / 'result/blender/LSE_campus_detailed_v263.blend'
    assert sha(base) == BASE_SHA
    accepted_components()
    bpy.context.preferences.filepaths.save_version = 0
    integrate(
        base=base,
        destination=ROOT / 'result/blender/LSE_campus_detailed_v269.blend',
        proof=ROOT / 'result/blender/stage269', version=269,
        baseline_proof=ROOT / 'result/blender/stage263',
        reports=[(code, f'result/blender/{name}/audit.json', owner)
                 for code, name, owner in COMPONENTS],
        scope='One archived western Lincoln Inn Fields hedge and independently registered MAR second-floor lift openings only; retained upper shaft boundaries remain uncoordinated. Keep all retained architecture, material graphs and35detached room studies. Mapped positions and historical built drawings are not a current site survey; unverified whole-floor interiors remain incomplete.',
    )
    path = ROOT / 'result/blender/stage269/building-refinement.json'
    record = json.loads(path.read_text())
    previous = json.loads((ROOT / 'result/blender/stage263/building-refinement.json').read_text())
    for key in ['libraryNativeViewRouting', 'librarySourceArchiveScene']:
        record[key] = previous[key]
    path.write_text(json.dumps(record, indent=2) + '\n')


if __name__ == '__main__':
    main()
