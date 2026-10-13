"""Integrate independently verified exterior components into one current campus.

Run in Blender's Text Editor. The baseline is read-only, source objects remain
intact inside the new file, and only listed replacements change visibility.
No command-line arguments, global preferences or external downloads are used.
"""
from pathlib import Path
import array
import hashlib
import json
import bpy

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'result/blender/LSE_campus_detailed_v193.blend'
DESTINATION = ROOT / 'result/blender/LSE_campus_detailed_v194.blend'
PROOF = ROOT / 'result/blender/stage194'
REPORTS = [
    ('OLD', 'result/blender/old-exterior194/building-refinement.json', 'OLD_EXTERIOR'),
    ('CBG', 'result/blender/cbg-exterior194/audit.json', 'CBG_EXTERIOR'),
    ('STREETS', 'result/blender/street-connections194/audit.json', '00_SITE'),
]


def update_scene():
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']


def object_fingerprint(obj):
    digest = hashlib.sha256((obj.type + str([list(row) for row in obj.matrix_world])).encode())
    if obj.type == 'MESH':
        mesh = obj.data
        for values, field, kind, count in [(mesh.vertices, 'co', 'f', 3),
                                           (mesh.loops, 'vertex_index', 'i', 1),
                                           (mesh.polygons, 'material_index', 'i', 1),
                                           (mesh.polygons, 'loop_total', 'i', 1)]:
            buffer = array.array(kind, [0]) * (len(values) * count)
            values.foreach_get(field, buffer)
            digest.update(buffer.tobytes())
        for layer in mesh.uv_layers:
            buffer = array.array('f', [0]) * (len(layer.data) * 2)
            layer.data.foreach_get('uv', buffer)
            digest.update(layer.name.encode() + buffer.tobytes())
        digest.update(str([material.name if material else None for material in mesh.materials]).encode())
    elif obj.type == 'FONT':
        digest.update(str((obj.data.body, obj.data.size, obj.data.extrude, obj.data.align_x,
                           obj.data.align_y, obj.data.font.name)).encode())
    elif obj.type in {'CURVE', 'SURFACE'}:
        for spline in obj.data.splines:
            digest.update(spline.type.encode())
            for point in spline.points:
                digest.update(str(tuple(point.co)).encode())
            for point in spline.bezier_points:
                digest.update(str((tuple(point.co), tuple(point.handle_left), tuple(point.handle_right))).encode())
    return digest.hexdigest()


def geometry_policy_name(obj):
    """A replacement keeps the accepted UV and bevel policy of its source."""
    name = obj.get('webGeometrySource', obj.name)
    if name.startswith('OLD_ENTRANCE192_'):
        name = obj['originalObject']
    if name.startswith('MAR188_trim_'):
        name = name.removeprefix('MAR188_trim_')
        if not name.startswith('MAR'):
            name = 'MAR_' + name
    return name.removeprefix('SAL184_').removeprefix('SAL183_').removeprefix('GLASS181_')


def verify_saved_model():
    record = json.loads((PROOF / 'building-refinement.json').read_text())
    bpy.ops.wm.open_mainfile(filepath=str(DESTINATION))
    update_scene()
    baseline = json.loads((PROOF / 'baseline-state.json').read_text())
    for name, expected in baseline['fingerprints'].items():
        assert object_fingerprint(bpy.data.objects[name]) == expected, name
        assert bpy.data.objects[name].hide_render == (True if name in record['archivedObjects']
                                                     else baseline['visibility'][name]), name
    for name, expected in record['addedFingerprints'].items():
        assert object_fingerprint(bpy.data.objects[name]) == expected, name
        assert not bpy.data.objects[name].hide_render, name
    assert set(bpy.data.objects) == {bpy.data.objects[name] for name in baseline['fingerprints']} | {
        bpy.data.objects[name] for name in record['addedObjects']}
    digest = hashlib.sha256(DESTINATION.read_bytes()).hexdigest()
    assert digest == record['sourceModelSha256']
    result = dict(sourceModelSha256=digest, originalsVerified=len(baseline['fingerprints']),
                  addedObjectsVerified=len(record['addedObjects']), originalGeometryUVsAndBindingsPreserved=True,
                  listedVisibilityOnly=True, completeModelReopened=True)
    (PROOF / 'reopened-verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print('EXTERIOR194_REOPENED', len(record['addedObjects']), flush=True)


def integrate():
    PROOF.mkdir(parents=True, exist_ok=True)
    assert not DESTINATION.exists(), 'Do not overwrite an accepted full campus'
    baseline_sha = hashlib.sha256(BASE.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = {obj.name: object_fingerprint(obj) for obj in bpy.data.objects}
    visibility = {obj.name: obj.hide_render for obj in bpy.data.objects}
    (PROOF / 'baseline-state.json').write_text(json.dumps(dict(fingerprints=before, visibility=visibility)) + '\n')
    added, archived, changes = [], [], []
    for code, report_path, default_collection in REPORTS:
        report = json.loads((ROOT / report_path).read_text())
        source_sha = report.get('baselineSha256', report.get('sourceModelSha256'))
        assert source_sha == baseline_sha, code
        path = ROOT / report.get('component', report.get('componentPath'))
        assert hashlib.sha256(path.read_bytes()).hexdigest() == report['componentSha256'], code
        names = report['addedObjects']
        assert len(names) == len(set(names)) and not set(names) & set(before), code
        assert not set(report['archivedObjects']) & set(archived), 'Overlapping component ownership'
        with bpy.data.libraries.load(str(path), link=False) as (source, target):
            assert set(names) <= set(source.objects)
            target.objects = list(names)
        for obj in target.objects:
            assert obj and obj.parent is None and not obj.constraints, code
            source_name = obj.get('originalObject')
            if source_name:
                assert source_name in before, source_name
                original = bpy.data.objects[source_name]
                obj['webGeometrySource'] = geometry_policy_name(original)
                collections = list(original.users_collection)
            else:
                collections = [bpy.data.collections[report.get('destinationCollection', default_collection)]]
            for collection in collections:
                if obj.name not in collection.objects:
                    collection.objects.link(obj)
            obj.hide_render = False
            obj.hide_set(False)
            added.append(obj.name)
        for name in report['archivedObjects']:
            assert name in before and not visibility[name], name
            bpy.data.objects[name].hide_render = True
            bpy.data.objects[name].hide_set(True)
            archived.append(name)
        changes.append(dict(code=code, report=report_path, componentSha256=report['componentSha256'],
                            addedObjects=names, archivedObjects=report['archivedObjects']))
    update_scene()
    assert all(object_fingerprint(bpy.data.objects[name]) == fingerprint for name, fingerprint in before.items())
    assert set(bpy.data.objects.keys()) - set(before) == set(added)
    new_state = {name: object_fingerprint(bpy.data.objects[name]) for name in added}
    # Compression changes storage only; the saved model is reopened and checked.
    bpy.ops.wm.save_as_mainfile(filepath=str(DESTINATION), compress=True)
    record = dict(version=194, baselineSha256=baseline_sha,
                  sourceModelSha256=hashlib.sha256(DESTINATION.read_bytes()).hexdigest(),
                  changes=changes, addedObjects=added, archivedObjects=archived, changedObjects=[],
                  addedFingerprints=new_state, allUnrelatedMeshesPreserved=True,
                  scope='OLD exterior stone map, CBG coating and glazing, corrected road normals and two walking joins',
                  limitations='Retained estimated building geometry and interior studies remain incomplete; no claim of an as-built survey.')
    (PROOF / 'building-refinement.json').write_text(json.dumps(record, indent=2) + '\n')
    verify_saved_model()
    print('EXTERIOR194_INTEGRATED', len(added), len(archived), DESTINATION.stat().st_size, flush=True)


if __name__ == '__main__':
    integrate()
