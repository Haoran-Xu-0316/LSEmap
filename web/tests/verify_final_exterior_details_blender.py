"""Independently reopen the accepted campus and check merged candidate identity."""
from pathlib import Path
import array, hashlib, json, math, re
import bpy
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage116'
p=ROOT/'result/blender/LSE_campus_detailed_v116.blend'
audit=json.loads((OUT/'integration-audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(p))
for scene in bpy.data.scenes:
    for layer in scene.view_layers: layer.update()
def fingerprint(o, normalize_material_names=False):
    h=hashlib.sha256(str([list(r) for r in o.matrix_world]).encode())
    if o.type=='MESH':
        vertices=array.array('f',[0])*(len(o.data.vertices)*3);loops=array.array('i',[0])*len(o.data.loops)
        o.data.vertices.foreach_get('co',vertices);o.data.loops.foreach_get('vertex_index',loops)
        h.update(vertices.tobytes());h.update(loops.tobytes())
    h.update(str([re.sub(r'\.\d{3}$','',m.name) if normalize_material_names and m else m.name if m else None for m in getattr(o.data,'materials',[])]).encode())
    return h.hexdigest()
for name,value in audit['originalFingerprints'].items():
    assert fingerprint(bpy.data.objects[name])==value,name
    assert bpy.data.objects[name].hide_render==(True if name in audit['archivedObjects'] else audit['originalVisibility'][name]),name
for sub,candidate,audit_name in [('old','OLD_fan_stair_candidate.blend','old-candidate-audit.json'),('ground','LSE_globe_color_candidate.blend','ground-final-audit.json')]:
    names=json.loads((OUT/sub/audit_name).read_text())['addedObjects']
    expected={name:fingerprint(bpy.data.objects[name],True) for name in names}
    with bpy.data.libraries.load(str(OUT/sub/candidate),link=False) as (source,target): target.objects=list(names)
    comparison=bpy.data.scenes.new('VERIFY_'+sub)
    for obj in target.objects: comparison.collection.objects.link(obj)
    for layer in comparison.view_layers: layer.update()
    for obj,name in zip(target.objects,names):
        assert fingerprint(obj,True)==expected[name], (name, [list(row) for row in obj.matrix_world], [m.name for m in obj.data.materials])
globe=bpy.data.objects['SITE_V116_Globe_photographed_Australia_fill']
image=next(n.image for n in globe.data.materials[0].node_tree.nodes if n.type=='TEX_IMAGE')
texture=json.loads((OUT/'ground/texture-verification.json').read_text())
hash_value=hashlib.sha256(bytes(image.packed_file.data)).hexdigest()
assert hash_value=='e0d369ffc2d351fd9949ca75b0c1cb3a9f482d6847032bca7424696b4cc36600'
result={'version':116,'retainedObjects':len(audit['originalFingerprints']),'originalGeometryRetained':True,
        'candidateIdentityRetained':True,'sourceModelSha256':hashlib.sha256(p.read_bytes()).hexdigest(),
        'globeImage':image.name,'globeImageSha256':hash_value}
(OUT/'saved-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print('FINAL_DETAILS_SAVED_VERIFICATION_PASSED',flush=True)
