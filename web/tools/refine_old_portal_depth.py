"""Refine OLD entrance stone projection and glazing from the private user photo.
Run in Blender Text Editor. Reuses the saved campus; all originals stay archived.
Stone offsets and glass finish are photo estimates, not survey measurements.
"""
from pathlib import Path
import array, hashlib, json, shutil
import bpy, bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage97'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v96.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
frame = json.loads((ROOT / 'result/blender/stage52/old-houghton-audit.json').read_text())
origin, right, outward = [Vector(frame[k]) for k in ['origin', 'right', 'outward']]
collection = bpy.data.collections['OLD_EXTERIOR']

def fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        digest.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i', [l.vertex_index for l in obj.data.loops]).tobytes())
    if obj.type == 'FONT':
        digest.update(obj.data.body.encode())
    digest.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return digest.hexdigest()

before = {o.name: fingerprint(o) for o in bpy.data.objects}
records = []

def owned_copy(name):
    source = bpy.data.objects[name]
    assert not source.hide_render, name
    copy = source.copy()
    copy.data = source.data.copy()
    copy.name = 'OLD_V97_' + name.removeprefix('OLD_')
    collection.objects.link(copy)
    source.hide_render = True
    source.hide_set(True)
    copy.hide_render = False
    copy.hide_set(False)
    records.append({'source': name, 'copy': copy.name})
    return source, copy

# Existing wall blocks have a front plane around depth .225m. The former entry
# blocks extended to .685m, producing a deep staircase of protruding stone.
# Keep block widths, heights and joints, with a shallow dressed front projection.
for name, low, high in [('OLD_Entrance_rusticated_blocks', .210, .270),
                        ('OLD_Corner_rusticated_quoins', .145, .275)]:
    source, copy = owned_copy(name)
    depths = [(source.matrix_world @ v.co - origin).dot(outward) for v in source.data.vertices]
    a, b = min(depths), max(depths)
    inverse = copy.matrix_world.inverted()
    for vertex in copy.data.vertices:
        point = copy.matrix_world @ vertex.co
        depth = (point - origin).dot(outward)
        target = low + (depth - a) * (high - low) / (b - a)
        vertex.co = inverse @ (point + outward * (target - depth))
    for modifier in copy.modifiers:
        if modifier.type == 'BEVEL':
            modifier.width = min(modifier.width, .008)
    records[-1].update({'oldDepth': [a, b], 'newDepth': [low, high]})

# Fill the support behind the shallow courses. The former deeply projecting
# blocks covered a missing wall strip; thinning them must not expose those gaps.
mesh = bpy.data.meshes.new('OLD_V97_entry_pier_backing_mesh')
bm = bmesh.new()
for center in [-4.51, 4.51]:
    result = bmesh.ops.create_cube(bm, size=1)
    for vertex in result['verts']:
        x, depth, height = vertex.co
        vertex.co = origin + right * (center + x * 1.10) + outward * (-.01 + depth * .48) + Vector((0, 0, 2.745 + height * 4.11))
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
bm.to_mesh(mesh); bm.free()
backing = bpy.data.objects.new('OLD_V97_entry_pier_backing', mesh)
collection.objects.link(backing)
mesh.materials.append(bpy.data.objects['OLD_Entrance_rusticated_blocks'].data.materials[0])

# Move plaques and raised lettering with their revised support, rather than
# leaving signs hovering at their old exaggerated stone projection.
for name, shift in [('OLD_LSE_entrance_signs', -.415),
                    ('OLD_LSE_entry_sign', -.415),
                    ('OLD_LSE_entry_sign.001', -.415),
                    ('OLD_Old_Building_name', -.614),
                    ('OLD_Old_Building_name.001', -.614)]:
    source, copy = owned_copy(name)
    copy.matrix_world.translation += outward * shift
    records[-1]['translationDepth'] = shift

# Only entrance door panes receive this finish. Other blue-framed windows and
# the artwork backing retain their existing material. No interior layout added.
source, copy = owned_copy('OLD_D5_entry65_glass')
material = source.data.materials[0].copy()
material.name = 'OLD_V97_entry_glass'
material.diffuse_color = (.29, .325, .315, 1)
shader = next(n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
shader.inputs['Base Color'].default_value = material.diffuse_color
shader.inputs['Roughness'].default_value = .17
shader.inputs['Metallic'].default_value = .04
shader.inputs['Transmission Weight'].default_value = .55
material['webOpacity'] = .46
copy.data.materials[0] = material
records[-1]['material'] = material.name
for filename in ['room-studies.json', 'room-spaces.json', 'building-review.json']:
    shutil.copyfile(ROOT / 'result/blender/stage96' / filename, OUT / filename)
assert all(fingerprint(bpy.data.objects[n]) == h for n, h in before.items())
audit = {'version': 97, 'baseline': 96, 'frame': frame, 'originalFingerprints': before,
         'copies': records, 'addedObjects': [backing.name], 'reference': 'data/collections/old-user-reference/houghton-user-entrance-20261001.png',
         'receivedDate': '2026-10-01', 'captureDate': None,
         'scope': 'Shallow stone courses and mounted entry plaques; neutral reflective semi-transparent entrance panes. Original geometry archived; no photo textures or speculative interior layout.',
         'limits': ['Stone depths and glazing finish estimated from photograph',
                    'Artwork mesh silhouettes, whole roof, unseen elevations and full interiors unresolved']}
(OUT / 'old-portal-depth-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v97.blend'))
print('OLD_PORTAL_DEPTH_SAVED', len(records))
