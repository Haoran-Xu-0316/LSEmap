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


def set_layer_hidden(obj, hidden):
    """Apply viewport visibility only to the view layers that own the object.

    Independent room studies intentionally do not belong to the campus layer.
    Render visibility remains global; editor visibility is local to each layer.
    """
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            if obj.name in layer.objects:
                obj.hide_set(hidden, view_layer=layer)


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


def component_destination(report, default_collection):
    """Create isolated rooms or a public assembly shared with the campus."""
    name = report.get('destinationCollection', default_collection)
    spec = report.get('collectionSpec')
    if not spec:
        return bpy.data.collections[name]
    assert spec['kind'] in {'independent-room', 'public-interior'}, 'Unsupported authored collection kind'
    assert spec['name'] == name == report['targetCollection'], 'Authored collection identity mismatch'
    assert name not in bpy.data.collections and spec['scene'] not in bpy.data.scenes, 'Authored collection identity already exists'
    collection = bpy.data.collections.new(name)
    collection['roomSample'] = spec['kind'] == 'independent-room'
    collection['publicInteriorStudy'] = spec['kind'] == 'public-interior'
    if report.get('space'):
        collection['roomCode'] = report['space']['label']
        collection['authoringRecord'] = json.dumps(report['space'], ensure_ascii=False)
    scene = bpy.data.scenes.new(spec['scene'])
    scene.collection.children.link(collection)
    if spec['kind'] == 'public-interior':
        bpy.data.scenes['00_CAMPUS_COMPLETE'].collection.children.link(collection)
    return collection


def verify_saved_model(destination=DESTINATION, proof=PROOF):
    record = json.loads((proof / 'building-refinement.json').read_text())
    bpy.ops.wm.open_mainfile(filepath=str(destination))
    update_scene()
    baseline = json.loads((proof / 'baseline-state.json').read_text())
    for name, expected in baseline['fingerprints'].items():
        assert object_fingerprint(bpy.data.objects[name]) == expected, name
        assert bpy.data.objects[name].hide_render == (True if name in record['archivedObjects']
                                                     else baseline['visibility'][name]), name
    for name, expected in record['addedFingerprints'].items():
        assert object_fingerprint(bpy.data.objects[name]) == expected, name
        assert not bpy.data.objects[name].hide_render, name
    assert set(bpy.data.objects) == {bpy.data.objects[name] for name in baseline['fingerprints']} | {
        bpy.data.objects[name] for name in record['addedObjects']}
    for room in record.get('independentRooms', []):
        collection = bpy.data.collections[room['collection']]
        assert set(obj.name for obj in collection.all_objects) == set(room['objects'])
        assert collection.name in bpy.data.scenes[room['scene']].collection.children
        assert not any(name in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects for name in room['objects']), 'Independent room leaked into campus'
    for public in record.get('publicInteriors', []):
        collection = bpy.data.collections[public['collection']]
        assert set(obj.name for obj in collection.all_objects) == set(public['objects']) | set(public['sharedObjects'])
        assert collection.name in bpy.data.scenes[public['scene']].collection.children
        assert collection.name in bpy.data.scenes['00_CAMPUS_COMPLETE'].collection.children
        assert all(name in bpy.data.collections[public['exteriorCollection']].objects for name in public['exteriorObjects'])
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    assert digest == record['sourceModelSha256']
    result = dict(sourceModelSha256=digest, originalsVerified=len(baseline['fingerprints']),
                  addedObjectsVerified=len(record['addedObjects']), originalGeometryUVsAndBindingsPreserved=True,
                  listedVisibilityOnly=True, completeModelReopened=True)
    (proof / 'reopened-verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(f"EXTERIOR{record['version']}_REOPENED", len(record['addedObjects']), flush=True)


def accepted_fingerprints(proof, source_sha):
    """Read the preceding accepted snapshot, independently of a new process."""
    previous = json.loads((proof / 'building-refinement.json').read_text())
    assert previous['sourceModelSha256'] == source_sha, 'Accepted native identity mismatch'
    expected = json.loads((proof / 'baseline-state.json').read_text())['fingerprints']
    expected.update(previous['addedFingerprints'])
    return expected


def integrate(base=BASE, destination=DESTINATION, proof=PROOF, reports=REPORTS,
              version=194, scope='OLD exterior stone map, CBG coating and glazing, corrected road normals and two walking joins',
              baseline_proof=None):
    proof.mkdir(parents=True, exist_ok=True)
    assert not destination.exists(), 'Do not overwrite an accepted full campus'
    baseline_sha = hashlib.sha256(base.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(base))
    update_scene()
    before = {obj.name: object_fingerprint(obj) for obj in bpy.data.objects}
    if baseline_proof is not None:
        expected = accepted_fingerprints(baseline_proof, baseline_sha)
        mismatches = sorted(name for name in set(expected) | set(before)
                            if expected.get(name) != before.get(name))
        assert not mismatches, 'Loaded source differs from prior accepted geometry: ' + str(mismatches[:20])
    visibility = {obj.name: obj.hide_render for obj in bpy.data.objects}
    (proof / 'baseline-state.json').write_text(json.dumps(dict(fingerprints=before, visibility=visibility)) + '\n')
    # Building-wide edits must not hide detached room studies that happen to
    # share a building prefix. Room components may change their own collection.
    metadata = json.loads((ROOT / 'web/tools/building-metadata.json').read_text())
    room_owners = {}
    for room in metadata['spaces']:
        collection = bpy.data.collections.get(room['collection'])
        if collection:
            for obj in collection.all_objects:
                room_owners.setdefault(obj.name, set()).add(collection.name)
    added, archived, changes, independent_rooms, public_interiors = [], [], [], [], []
    for code, report_path, default_collection in reports:
        report = json.loads((ROOT / report_path).read_text())
        source_sha = report.get('baselineSha256', report.get('sourceModelSha256'))
        assert source_sha == baseline_sha, code
        path = ROOT / report.get('component', report.get('componentPath'))
        assert hashlib.sha256(path.read_bytes()).hexdigest() == report['componentSha256'], code
        names = report['addedObjects']
        assert len(names) == len(set(names)) and not set(names) & set(before), code
        assert not set(report['archivedObjects']) & set(archived), 'Overlapping component ownership'
        destination_collection = component_destination(report, default_collection)
        room_conflicts = [name for name in report['archivedObjects']
                          if name in room_owners and destination_collection.name not in room_owners[name]]
        assert not room_conflicts, 'Building component would alter an independent room: ' + str(room_conflicts)
        spec = report.get('collectionSpec')
        is_public = bool(spec and spec['kind'] == 'public-interior')
        shared = report.get('sharedObjects', [])
        exterior_names = report.get('exteriorObjects', [])
        public_names = report.get('publicObjects', names if is_public else [])
        assert len(shared) == len(set(shared)) and len(exterior_names) == len(set(exterior_names)), code
        assert set(shared) <= set(before) and not set(shared) & set(report['archivedObjects']), code
        assert all(not visibility[name] and name not in room_owners for name in shared), 'Cannot repurpose archived or detached-room objects'
        assert set(exterior_names) <= set(names), code
        assert len(public_names) == len(set(public_names)) and set(public_names) <= set(names), code
        assert not is_public or set(public_names) | set(exterior_names) == set(names), 'Every public component object needs an explicit display owner'
        assert is_public or not (shared or exterior_names), 'Shared source ownership requires an explicit public-interior collection'
        if spec and spec['kind'] == 'independent-room':
            independent_rooms.append(dict(collection=destination_collection.name, scene=spec['scene'], objects=list(names)))
        if is_public:
            exterior_collection = bpy.data.collections[code + '_EXTERIOR']
            for name in shared:
                destination_collection.objects.link(bpy.data.objects[name])
            public_interiors.append(dict(collection=destination_collection.name, scene=spec['scene'], objects=list(public_names),
                                         sharedObjects=list(shared), exteriorCollection=exterior_collection.name, exteriorObjects=list(exterior_names)))
        with bpy.data.libraries.load(str(path), link=False) as (source, target):
            assert set(names) <= set(source.objects)
            target.objects = list(names)
        for obj in target.objects:
            assert obj and obj.parent is None and not obj.constraints, code
            # A replacement may deliberately reuse accepted source materials.
            # Blender append can suffix identical material names; bind explicit
            # identities before recording the complete-model fingerprint.
            bindings = report.get('replacementMaterialBindings', {}).get(obj.name)
            if bindings is not None:
                assert obj.type == 'MESH' and len(obj.data.materials) == len(bindings), obj.name
                for index, material_name in enumerate(bindings):
                    assert material_name in bpy.data.materials, material_name
                    obj.data.materials[index] = bpy.data.materials[material_name]
            source_name = obj.get('originalObject')
            if source_name:
                assert source_name in before, source_name
                original = bpy.data.objects[source_name]
                obj['webGeometrySource'] = geometry_policy_name(original)
                collections = list(original.users_collection)
            else:
                collections = [destination_collection]
            # Registered whole-building assemblies carry explicit exterior or
            # public-interior ownership. The native alias still supplies the
            # accepted geometry policy, but must not relocate a new floor or stair.
            authored_collection = obj.get('destinationCollection')
            if authored_collection:
                assert authored_collection in bpy.data.collections, authored_collection
                collections = [bpy.data.collections[authored_collection]]
            if is_public:
                # A public component owns its whole circulation assembly, while
                # the explicit shell subset also belongs to the shared exterior.
                # Reuse original source objects through declared memberships.
                assert not authored_collection or authored_collection in {destination_collection.name, exterior_collection.name}, obj.name
                collections = [destination_collection] if obj.name in public_names else []
                if obj.name in exterior_names:
                    collections.append(exterior_collection)
            for collection in collections:
                if obj.name not in collection.objects:
                    collection.objects.link(obj)
            obj.hide_render = False
            added.append(obj.name)
        update_scene()
        for name in names:
            set_layer_hidden(bpy.data.objects[name], False)
        for name in report['archivedObjects']:
            assert name in before and not visibility[name], name
            bpy.data.objects[name].hide_render = True
            set_layer_hidden(bpy.data.objects[name], True)
            archived.append(name)
        changes.append(dict(code=code, report=report_path, componentSha256=report['componentSha256'],
                            addedObjects=names, archivedObjects=report['archivedObjects'], sharedObjects=list(shared), exteriorObjects=list(exterior_names), publicObjects=list(public_names)))
    update_scene()
    assert all(object_fingerprint(bpy.data.objects[name]) == fingerprint for name, fingerprint in before.items())
    assert set(bpy.data.objects.keys()) - set(before) == set(added)
    new_state = {name: object_fingerprint(bpy.data.objects[name]) for name in added}
    # Compression changes storage only; the saved model is reopened and checked.
    bpy.ops.wm.save_as_mainfile(filepath=str(destination), compress=True)
    record = dict(version=version, baselineSha256=baseline_sha,
                  sourceModelSha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
                  changes=changes, addedObjects=added, archivedObjects=archived, changedObjects=[],
                  addedFingerprints=new_state, allUnrelatedMeshesPreserved=True, independentRooms=independent_rooms, publicInteriors=public_interiors,
                  scope=scope,
                  limitations='Retained estimated building geometry and interior studies remain incomplete; no claim of an as-built survey.')
    (proof / 'building-refinement.json').write_text(json.dumps(record, indent=2) + '\n')
    verify_saved_model(destination=destination, proof=proof)
    print(f'EXTERIOR{version}_INTEGRATED', len(added), len(archived), destination.stat().st_size, flush=True)


if __name__ == '__main__':
    integrate()
