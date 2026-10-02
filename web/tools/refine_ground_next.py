"""Complete a private globe paving candidate from native edition113.
Run in Blender's Text Editor after preparing stage114/ground/paving-plan.json.
This script neither exports website assets nor changes the shared baseline.
"""
from pathlib import Path
import array
import hashlib
import json
import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage114/ground'
BASELINE = ROOT / 'result/blender/LSE_campus_detailed_v113.blend'
CANDIDATE = OUT / 'LSE_ground_candidate.blend'
bpy.ops.wm.open_mainfile(filepath=str(BASELINE))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()

def fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        digest.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i', [loop.vertex_index for loop in obj.data.loops]).tobytes())
        digest.update(str([m.name if m else None for m in obj.data.materials]).encode())
    return digest.hexdigest()

before = {obj.name: fingerprint(obj) for obj in bpy.data.objects}
plan = json.loads((OUT / 'paving-plan.json').read_text())
assert plan['buildingOverlap'] < 1e-8
collection = bpy.data.collections['00_SITE']
materials = [bpy.data.materials['SITE_V47_grout']]
materials += [bpy.data.materials[f'SITE_V47_slab_{index}'] for index in range(5)]
vertices, faces, indices = [], [], []

def add(triangles, height, material_index):
    for triangle in triangles:
        start = len(vertices)
        points = [(p[0], p[1], height) for p in triangle]
        # Ensure the world-space top surface faces upward.
        cross = (points[1][0]-points[0][0])*(points[2][1]-points[0][1])-(points[1][1]-points[0][1])*(points[2][0]-points[0][0])
        vertices.extend(points)
        faces.append((start, start+1, start+2) if cross > 0 else (start, start+2, start+1))
        indices.append(material_index)

add(plan['base'], .0502, 0)
for tile in plan['tiles']:
    add(tile['triangles'], .0515, tile['shade']+1)
mesh = bpy.data.meshes.new('SITE_V114_Globe_continuous_paving')
mesh.from_pydata(vertices, [], faces)
for material in materials:
    mesh.materials.append(material)
for face, material_index in zip(mesh.polygons, indices):
    face.material_index = material_index
mesh.update()
assert all(face.normal.z > .999 for face in mesh.polygons)
obj = bpy.data.objects.new(mesh.name, mesh)
collection.objects.link(obj)
obj['scope'] = plan['scope']
obj['paverCount'] = len(plan['tiles'])
# Preserve the original inlay mesh and lift an owned copy above the new paving.
original = bpy.data.objects['SITE_V48_globe_concentric_inlays']
replacement = original.copy()
replacement.data = original.data.copy()
replacement.name = 'SITE_V114_Globe_concentric_inlays'
collection.objects.link(replacement)
replacement.location.z += .0015
original.hide_render = True
original.hide_set(True)
for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()
changed = [name for name, digest in before.items() if fingerprint(bpy.data.objects[name]) != digest]
assert not changed, changed
bpy.ops.wm.save_as_mainfile(filepath=str(CANDIDATE))
audit = {
    'baseline': 113,
    'candidate': str(CANDIDATE),
    'baselineSha256': hashlib.sha256(BASELINE.read_bytes()).hexdigest(),
    'changedExistingGeometry': changed,
    'originalObjectsRetained': len(before),
    'addedObjects': [obj.name, replacement.name],
    'archivedObjects': [original.name],
    'pavers': len(plan['tiles']),
    'area': plan['area'],
    'buildingOverlapArea': plan['buildingOverlap'],
    'upwardSurfaceNormals': True,
    'globeGeometryAndMaterialRetained': True,
    'limitations': [
        'Paving course sizes, circular completion boundary and material are photo-estimated.',
        'Existing globe position, country colors and compass heading retained; not an exact artwork facsimile.',
        'Candidate requires isolated visual and saved-file checks before integration.',
        'No complete roads, bars, interiors or current2026 condition claim.',
    ],
}
(OUT / 'ground-candidate-audit.json').write_text(json.dumps(audit, indent=2)+'\n')
print('GROUND_CANDIDATE_SAVED', len(plan['tiles']), plan['area'])
