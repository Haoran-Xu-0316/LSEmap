"""Independently reopen OLD arch finish and verify shape, normals and scope."""
from pathlib import Path
import array, hashlib, json, math
import bpy
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'result/blender/stage103'
audit = json.loads((OUT/'old-arch-finish-audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v103.blend'))

def fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        digest.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return digest.hexdigest()
for name,value in audit['originalFingerprints'].items():
    assert fingerprint(bpy.data.objects[name]) == value, name
assert set(bpy.data.objects.keys()) - set(audit['originalFingerprints']) == {audit['copy']}
source, copy = [bpy.data.objects[audit[k]] for k in ['source','copy']]
assert source.hide_render and not copy.hide_render
assert source.matrix_world == copy.matrix_world
assert [tuple(v.co) for v in source.data.vertices] == [tuple(v.co) for v in copy.data.vertices]
assert [tuple(p.vertices) for p in source.data.polygons] == [tuple(p.vertices) for p in copy.data.polygons]
assert copy.data.has_custom_normals
origin,right,outward = [Vector(audit['frame'][k]) for k in ['origin','right','outward']]
changed = 0
for index in audit['curvedFaces']:
    face = copy.data.polygons[index]
    assert face.use_smooth
    for loop in face.loop_indices:
        point = copy.matrix_world @ copy.data.vertices[copy.data.loops[loop].vertex_index].co
        x,z = (point-origin).dot(right), point.z-origin.z-4.8
        r = math.hypot(x,z); t = max(.002,min(1,(r-2.90)/1.30))
        expected = (outward-(right*(x/r)+Vector((0,0,z/r)))*(.85*.65/1.30*t**(-.35))).normalized()
        actual = (copy.matrix_world.to_3x3().inverted().transposed() @ copy.data.corner_normals[loop].vector).normalized()
        assert actual.dot(expected) > .9998, (index, actual.dot(expected))
        if actual.dot(source.data.corner_normals[loop].vector) < .9998: changed += 1
assert changed > 500, changed
assert len(audit['curvedFaces']) == 240
for segment,faces in audit['segments'].items():
    assert len({copy.data.polygons[i].material_index for i in faces}) == 1
assert len(copy.data.materials) == 5
for index,material in enumerate(copy.data.materials):
    assert material['siteDetail']
    assert not any(n.type == 'TEX_IMAGE' for n in material.node_tree.nodes)
    shader = next(n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    assert abs(shader.inputs['Roughness'].default_value-.88)<1e-6
    noise = next(n for n in material.node_tree.nodes if n.type == 'TEX_NOISE')
    assert noise.inputs['Scale'].default_value == 3.5
    for a,b in zip(material.diffuse_color[:3],source.data.materials[0].diffuse_color[:3]):
        assert abs(a-b*audit['materialFactors'][index]) < 1e-6
    assert shader.inputs['Normal'].is_linked
measurements = {'originalObjectsUnchanged':True,'identicalGeometry':True,'smoothCurvedFaces':240,
                'verifiedNormalCorners':changed,'consistentStoneColours':True,'photoTextures':0,'sharedMaterialCount':5}
audit['savedMeasurements'] = measurements
(OUT/'old-arch-finish-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print('SAVED_OLD_ARCH_FINISH_VERIFIED',measurements,flush=True)
