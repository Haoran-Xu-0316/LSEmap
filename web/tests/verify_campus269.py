"""Independently reopen the full campus and verify the bounded269 components."""
import importlib.util
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
sys.dont_write_bytecode = True
from integrate_campus269 import BASE_SHA, accepted_components, sha
from integrate_exterior_round194 import object_fingerprint, update_scene


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def capture_source():
    helper = load_module('campus269_source_state', 'web/tests/verify_campus241.py')
    helper.BASE_SHA = BASE_SHA
    state = helper.capture_source()
    state['visibility'] = {o.name: [o.hide_render, o.hide_viewport, o.hide_get()]
                           for o in bpy.data.objects}
    return state


def surface_probes(audits):
    probes = []
    for key, audit in audits.items():
        code = 'LANDSCAPE' if key == 'park267' else 'MAR'
        for name in audit['addedObjects']:
            obj = bpy.data.objects[name]
            if obj.type != 'MESH':
                continue
            mesh = obj.data
            mesh.calc_loop_triangles()
            points = [obj.matrix_world @ v.co for v in mesh.vertices]
            tree = BVHTree.FromPolygons(points, [tuple(t.vertices) for t in mesh.loop_triangles], all_triangles=True)
            samples = []
            for face in list(mesh.polygons)[::max(1, len(mesh.polygons) // 16)]:
                centre = sum((points[i] for i in face.vertices), Vector()) / len(face.vertices)
                normal = (obj.matrix_world.to_3x3().inverted().transposed() @ face.normal).normalized()
                origin = centre + normal * .03
                hit = tree.ray_cast(origin, -normal, .061)
                if hit[0] is not None and abs(hit[3] - .03) < .0001:
                    samples.append({'code': code, 'object': name, 'origin': list(origin),
                                    'direction': list(-normal), 'distance': hit[3],
                                    'materials': [m.name for m in mesh.materials]})
            assert samples, name
            probes.extend(samples)
    return probes


def main():
    out = ROOT / 'result/blender/stage269'
    record = json.loads((out / 'building-refinement.json').read_text())
    base = ROOT / 'result/blender/LSE_campus_detailed_v263.blend'
    current = ROOT / 'result/blender/LSE_campus_detailed_v269.blend'
    assert sha(base) == BASE_SHA == record['baselineSha256']
    current_sha = sha(current)
    assert current_sha == record['sourceModelSha256']
    audits = accepted_components()
    added = set().union(*(set(a['addedObjects']) for a in audits.values()))
    archived = set().union(*(set(a['archivedObjects']) for a in audits.values()))
    assert set(record['addedObjects']) == added and set(record['archivedObjects']) == archived
    assert record['changedObjects'] == []
    bpy.ops.wm.open_mainfile(filepath=str(base))
    update_scene()
    before = capture_source()
    assert len(before['objects']) == 8748 and len(before['materials']) == 2355
    bpy.ops.wm.open_mainfile(filepath=str(current))
    update_scene()
    after = capture_source()
    for name, value in before['objects'].items():
        expected = dict(value)
        if name in archived:
            expected['hidden'] = True
        assert after['objects'][name] == expected, name
    for name, value in before['visibility'].items():
        assert after['visibility'][name] == ([True, value[1], True] if name in archived else value), name
    assert set(after['objects']) == set(before['objects']) | added
    expected_materials = {n: v for a in audits.values() for n, v in a.get('newMaterialGraphs', {}).items()}
    assert after['materials'] == before['materials'] | expected_materials
    assert after['rooms'] == before['rooms'] and len(after['rooms']) == 35
    assert after['campusRooms'] == before['campusRooms']
    for audit in audits.values():
        for name in audit['addedObjects']:
            obj = bpy.data.objects[name]
            assert not obj.hide_render
            assert object_fingerprint(obj) == audit['addedFingerprints'][name] == record['addedFingerprints'][name]
            assert [m.name for m in obj.data.materials] == audit['replacementMaterialBindings'][name]
    park = load_module('campus269_park_geometry', 'web/tests/verify_park_hedge267.py')
    mar = load_module('campus269_mar_geometry', 'web/tests/verify_mar269.py')
    proofs = {'park267': park.geometry_proof(audits['park267']),
              'mar269': mar.geometry_proof(audits['mar269'])}
    probes = surface_probes(audits)
    (out / 'production-probes.json').write_text(json.dumps(probes, indent=2) + '\n')
    assert capture_source() == after
    assert sha(base) == BASE_SHA and sha(current) == current_sha
    result = {'status': 'passed', 'freshBlenderProcess': True,
              'baselineSha256': BASE_SHA, 'sourceModelSha256': current_sha,
              'originalObjectsProtected': 8748, 'originalMaterialsProtected': 2355,
              'roomMembershipsProtected': 35, 'allOriginalGeometryNormalsUVsOwnersPropertiesModifiersPreserved': True,
              'onlyDeclaredVisibilityChanges': sorted(archived), 'actualGeometryProofs': proofs,
              'productionProbes': len(probes), 'completeCampusSavedAndReopened': True}
    (out / 'independent-verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print('CAMPUS269_INDEPENDENTLY_VERIFIED', current_sha, flush=True)


if __name__ == '__main__':
    main()
