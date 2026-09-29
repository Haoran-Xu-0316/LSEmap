"""Remove unsupported generic stacks from the LRB ground-floor study.

Run in Blender's Text Editor. Keeps the floor-guide-derived furniture and all
other floors unchanged. This does not calibrate the model's absolute levels.
"""
from pathlib import Path
import array
import hashlib
import json
import bpy
import bmesh

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage36'
OUT.mkdir(parents=True, exist_ok=True)
SOURCE = ROOT / 'result/blender/LSE_campus_detailed_v35.blend'
DESTINATION = OUT / 'library-ground-candidate.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))

def fingerprint(obj):
    digest = hashlib.sha256()
    digest.update(array.array('f', [v for row in obj.matrix_world for v in row]).tobytes())
    for values, typecode in [([v for vertex in obj.data.vertices for v in vertex.co], 'f'),
                             ([loop.vertex_index for loop in obj.data.loops], 'i'),
                             ([face.material_index for face in obj.data.polygons], 'i')]:
        digest.update(array.array(typecode, values).tobytes())
    return digest.hexdigest()

before = {obj.name: fingerprint(obj) for obj in bpy.data.objects if obj.type == 'MESH'}
collection = bpy.data.collections['LRB_PUBLIC_INTERIOR_study']
prefixes = ('LRB_shelf_end_panels', 'LRB_shelf_boards', 'LRB_reference_book_spines')
changes = []
for obj in collection.all_objects:
    if obj.type != 'MESH' or not obj.name.startswith(prefixes):
        continue
    # Legacy batches contain G/1/2/3 together. Select only complete G components.
    heights = {v.index: (obj.matrix_world @ v.co).z for v in obj.data.vertices}
    removed = {i for i, z in heights.items() if 4.30 <= z < 7.0}
    if not removed:
        continue
    assert all(not(set(face.vertices) & removed) or set(face.vertices) <= removed
               for face in obj.data.polygons), 'Selection would cut through a component'
    retained_before = [(tuple(v.co), v.index) for v in obj.data.vertices if v.index not in removed]
    old_count = len(obj.data.vertices)
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    mesh.verts.ensure_lookup_table()
    bmesh.ops.delete(mesh, geom=[mesh.verts[i] for i in removed], context='VERTS')
    mesh.to_mesh(obj.data)
    mesh.free()
    obj.data.update()
    # Compare coordinates without relying on reindexed vertices.
    assert sorted(tuple(v.co) for v in obj.data.vertices) == sorted(p for p, _ in retained_before)
    assert all((obj.matrix_world @ v.co).z >= 8.3 for v in obj.data.vertices)
    obj['groundZoneCorrection'] = 'Removed generic G stacks: official floor guide identifies learning and service zones'
    changes.append({'name':obj.name,'removedVertices':len(removed),
                    'retainedVertices':len(obj.data.vertices),'originalVertices':old_count})
assert len(changes) == 7, changes
assert sum(item['removedVertices'] for item in changes) == (40 + 120 + 3000) * 8
changed = {item['name'] for item in changes}
after = {obj.name: fingerprint(obj) for obj in bpy.data.objects if obj.type == 'MESH'}
assert set(before) == set(after)
assert all(before[name] == after[name] for name in before if name not in changed)
bpy.ops.wm.save_as_mainfile(filepath=str(DESTINATION))
audit = {
    'baseline':str(SOURCE.relative_to(ROOT)), 'candidate':str(DESTINATION.relative_to(ROOT)),
    'sourceUrl':'https://www.lse.ac.uk/asset-library/information/library-floor-plans-pdf.pdf',
    'sourcePath':'data/documents/library_floor_plans.pdf', 'sourcePage':3,
    'sourceChecked':'2026-09-29',
    'sourceSha256':hashlib.sha256((ROOT/'data/documents/library_floor_plans.pdf').read_bytes()).hexdigest(),
    'change':'Removed 20 legacy generic stack modules from the model G layer; retained plan-derived learning furniture',
    'changedMeshes':changes, 'unchangedMeshes':len(before)-len(changed),
    'checks':['No partially cut mesh component','Every retained shelf vertex unchanged',
              'All unselected meshes unchanged, including exterior, atrium, plan-derived furniture and other buildings'],
    'limitations':['G remains at estimated Z4.32 and LG at Z0.32; vertical calibration unresolved',
                   'Atrium position differs from diagram fit; not a surveyed reconstruction',
                   'Remaining legacy reading desks are estimated; service counters and enclosed rooms incomplete'],
    'publication':'Native candidate only; web assets still edition35 pending integrated structural review',
}
(OUT/'library-ground-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
print('LIBRARY_GROUND_CORRECTED', len(changes), 'batches;', len(before)-len(changed), 'meshes unchanged')
