"""Reopen and verify the current editable foliage refinement in Blender."""
from pathlib import Path
from array import array
import hashlib
import json
import bpy
ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / 'result/blender/LSE_campus_detailed_v157.blend'
REPORT = ROOT / 'result/blender/stage157'
proof = json.loads((REPORT / 'vegetation-shading.json').read_text())
assert hashlib.sha256(MODEL.read_bytes()).hexdigest() == proof['sourceModelSha256']
bpy.ops.wm.open_mainfile(filepath=str(MODEL))
assert len(bpy.data.objects) == proof['objects']
for record in proof['changedObjects']:
    mesh = bpy.data.objects[record['object']].data
    assert len(mesh.vertices) == record['vertices'] and len(mesh.polygons) == record['faces']
    assert all(p.use_smooth for p in mesh.polygons)
    points = array('f', [0.0]) * (len(mesh.vertices) * 3)
    mesh.vertices.foreach_get('co', points)
    loops = array('i', [0]) * len(mesh.loops)
    mesh.loops.foreach_get('vertex_index', loops)
    assert hashlib.sha256(points.tobytes() + loops.tobytes()).hexdigest() == record['geometrySha256']
assert not bpy.data.libraries
assert not any(image.source == 'FILE' and not image.packed_file for image in bpy.data.images)
(REPORT / 'reopened-verification.json').write_text(json.dumps({'sourceModelSha256': proof['sourceModelSha256'], 'savedSceneReopened': True, 'geometryVerified': True, 'smoothNormalsVerified': True, 'objects': len(bpy.data.objects), 'externalDependencies': False}, indent=2) + '\n')
print('ENVIRONMENT157_REOPENED_VERIFIED', len(bpy.data.objects))
