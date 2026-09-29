"""Sweep Clement House cornices along its existing convex GIS frontage.

Run in Blender's Text Editor. Existing profile dimensions remain estimates;
this corrects chord-shaped connections, without inventing facade dimensions.
"""
from pathlib import Path
import array
import hashlib
import json
import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage40'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v39.blend'))

def fingerprint(obj):
    digest = hashlib.sha256(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
    digest.update(array.array('i', [loop.vertex_index for loop in obj.data.loops]).tobytes())
    return digest.hexdigest()

before = {o.name: fingerprint(o) for o in bpy.data.objects if o.type == 'MESH'}
site = json.loads((ROOT / 'result/blender/site_geometry.json').read_text())
building = next(b for b in site['buildings'] if b['code'] == 'CLM')
ring = building['rings'][0]
points = [Vector(ring[i]) for i in (5, 4, 3, 2, 1)]
centre = Vector(building['center'])
normals = []
for start, end in zip(points, points[1:]):
    tangent = (end - start).normalized()
    normal = Vector((tangent.y, -tangent.x))
    if normal.dot((start + end) / 2 - centre) < 0:
        normal.negate()
    normals.append(normal)
miters = [normals[0]]
for left, right in zip(normals, normals[1:]):
    direction = (left + right).normalized()
    miters.append(direction / direction.dot(left))
miters.append(normals[-1])

profiles = {
    'CLM_D3_main_colonnade_entablature': [(8.17, .13, .70, .23), (8.46, .13, .49, .39), (8.75, .13, .70, .18)],
    'CLM_D3_upper_floor_stringcourses': [(z, .08, .29, .13) for z in (8.9, 12.2, 15.5, 18.8)],
    'CLM_D3_strong_upper_entablature': [(22.07, .09, .44, .18), (22.32, .09, .61, .26), (22.59, .09, .83, .18), (22.77, .09, .64, .13)],
}

def export_review(name):
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    for obj in bpy.context.scene.objects:
        obj.select_set(False)
    for obj in bpy.data.collections['CLM_EXTERIOR'].all_objects:
        obj.hide_set(False)
        obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(OUT / name), export_format='GLB', use_selection=True, use_active_scene=True, export_cameras=False, export_lights=False)

export_review('cornices-before.glb')
for name, bands in profiles.items():
    obj = bpy.data.objects[name]
    vertices, faces = [], []
    for z, depth, width, height in bands:
        offset = len(vertices)
        for point, miter in zip(points, miters):
            for d, zz in [(depth-width/2,z-height/2),(depth+width/2,z-height/2),(depth+width/2,z+height/2),(depth-width/2,z+height/2)]:
                xy = point + miter * d
                vertices.append(obj.matrix_world.inverted() @ Vector((xy.x, xy.y, zz)))
        faces.append(tuple(offset + i for i in (3,2,1,0)))
        for section in range(len(points)-1):
            a, b = offset + section*4, offset + (section+1)*4
            for side in range(4):
                next_side = (side+1)%4
                faces.append((a+side,a+next_side,b+next_side,b+side))
        faces.append(tuple(offset+(len(points)-1)*4+i for i in range(4)))
    mesh = bpy.data.meshes.new(name + '_curved')
    mesh.from_pydata(vertices, [], faces)
    for material in obj.data.materials:
        mesh.materials.append(material)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    assert all(edge.is_manifold for edge in bm.edges), name
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj.data = mesh
    obj['profile_scope'] = 'Existing estimated profile swept along four GIS frontage segments with shared miter joints'

changed = [o.name for o in bpy.data.objects if o.type == 'MESH' and fingerprint(o) != before[o.name]]
assert set(changed) == set(profiles)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'clement-cornices-candidate.blend'))
export_review('cornices-after.glb')
(OUT / 'cornice-audit.json').write_text(json.dumps({
    'baseline': 'LSE_campus_detailed_v39.blend', 'changed': changed,
    'unchangedMeshes': len(before)-len(changed), 'profileCount': sum(map(len, profiles.values())),
    'frontageSegments': len(normals), 'closedManifoldProfiles': True,
    'reference': 'https://historicengland.org.uk/listing/the-list/list-entry/1066494',
    'basis': 'Convex Aldwych frontage and sharply profiled entablature; existing GIS path and estimated profile sizes retained',
    'limitations': ['No new survey dimensions', 'Roof plant and rear envelope still unresolved'],
    'publication': 'Native candidate; not integrated into public web assets'
}, ensure_ascii=False, indent=2)+'\n')
print('CORNICES_REFINED', changed)
