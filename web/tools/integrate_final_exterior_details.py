"""Merge independently checked OLD steps and globe colour into current MAR.
Run in Blender Text Editor. Archive originals in the scene, never overwrite
original meshes or materials. Keep only one accepted full campus after review.
"""
from pathlib import Path
import array, hashlib, json
import bpy
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage116'
BASE=ROOT/'result/blender/LSE_campus_detailed_v115.blend'
def update():
    for scene in bpy.data.scenes:
        for layer in scene.view_layers: layer.update()
def fingerprint(obj):
    h=hashlib.sha256(str([list(r) for r in obj.matrix_world]).encode())
    if obj.type=='MESH':
        vertices=array.array('f',[0])*(len(obj.data.vertices)*3)
        loops=array.array('i',[0])*len(obj.data.loops)
        obj.data.vertices.foreach_get('co',vertices);obj.data.loops.foreach_get('vertex_index',loops)
        h.update(vertices.tobytes());h.update(loops.tobytes())
    h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return h.hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(BASE));update()
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
before={o.name:fingerprint(o) for o in bpy.data.objects}
visibility={o.name:o.hide_render for o in bpy.data.objects}
jobs=[('old/old-candidate-audit.json','old/OLD_fan_stair_candidate.blend','OLD_EXTERIOR'),
      ('ground/ground-final-audit.json','ground/LSE_globe_color_candidate.blend','00_SITE')]
added=[];archived=[]
for audit_path,candidate_path,collection_name in jobs:
    audit=json.loads((OUT/audit_path).read_text())
    names=audit['addedObjects'];assert not set(names)&set(before)
    with bpy.data.libraries.load(str(OUT/candidate_path),link=False) as (source,target):
        assert set(names)<=set(source.objects)
        target.objects=names
    for obj in target.objects:
        assert obj and obj.parent is None and not obj.constraints
        bpy.data.collections[collection_name].objects.link(obj)
        obj.hide_render=False;obj.hide_set(False);added.append(obj.name)
    for name in audit['archivedObjects']:
        assert not visibility[name]
        bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
        archived.append(name)
update()
assert all(fingerprint(bpy.data.objects[n])==value for n,value in before.items())
assert all(bpy.data.objects[n].hide_render==(True if n in archived else state) for n,state in visibility.items())
assert set(bpy.data.objects.keys())-set(before)==set(added)
assert len(added)==3 and len(archived)==2
path=ROOT/'result/blender/LSE_campus_detailed_v116.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(path))
audit={'version':116,'baseline':115,'originalFingerprints':before,'originalVisibility':visibility,
       'addedObjects':added,'archivedObjects':archived,'sourceModelSha256':hashlib.sha256(path.read_bytes()).hexdigest(),
       'scope':'Retained MAR north fissure correction, OLD approach steps and Australia map fill'}
(OUT/'integration-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print('FINAL_EXTERIOR_DETAILS_INTEGRATED',len(added),flush=True)
