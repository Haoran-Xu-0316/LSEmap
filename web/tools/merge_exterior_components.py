"""Merge independently verified KGS and PAR components into the SAR campus.

Run in Blender Text Editor. Originals retain their geometry and material slots;
only the audited exterior display objects are archived. Reopen the saved result
and verify it before publishing browser exports.
"""
from pathlib import Path
import array
import hashlib
import json
import bpy
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage120';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v119.blend'
CURRENT=ROOT/'result/blender/LSE_campus_detailed_v120.blend'
COMPONENTS=[('KGS','kgs_next','kings-chambers-component.blend'),('PAR','par_next','parish-exterior-component.blend')]
def fingerprint(obj):
    h=hashlib.sha256(str([list(r) for r in obj.matrix_world]).encode())
    if obj.type=='MESH':
        v=array.array('f',[0])*(len(obj.data.vertices)*3);i=array.array('i',[0])*len(obj.data.loops)
        obj.data.vertices.foreach_get('co',v);obj.data.loops.foreach_get('vertex_index',i)
        h.update(v.tobytes());h.update(i.tobytes())
        indices=array.array('i',[0])*len(obj.data.polygons)
        obj.data.polygons.foreach_get('material_index',indices);h.update(indices.tobytes())
        for layer in obj.data.uv_layers:
            uvs=array.array('f',[0])*(len(layer.data)*2)
            layer.data.foreach_get('uv',uvs);h.update(uvs.tobytes())
    h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return h.hexdigest()
rebuilding=not BASE.exists()
source=CURRENT if rebuilding else BASE
base_sha=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source))
if rebuilding:
    previous=json.loads((OUT/'saved-verification.json').read_text())
    for name in previous['ownedObjects']:
        obj=bpy.data.objects[name];data=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
        data.use_fake_user=False
        if not data.users:bpy.data.meshes.remove(data)
    for name,state in previous['archivedVisibility'].items():
        obj=bpy.data.objects[name];obj.hide_render,obj.hide_viewport=state[:2];obj.hide_set(state[2])
    for mat in list(bpy.data.materials):
        if mat.name.startswith(('KGS_NEXT_','PAR_NEXT_')) and mat.users==int(mat.use_fake_user):
            mat.use_fake_user=False;bpy.data.materials.remove(mat)

for scene in bpy.data.scenes:
    for layer in scene.view_layers:layer.update()
original={o.name:fingerprint(o) for o in bpy.data.objects}
visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()] for o in bpy.data.objects}
archived=[];owned=[];components=[]
for code,folder,filename in COMPONENTS:
    directory=ROOT/'result/blender'/folder
    audit=json.loads((directory/'audit.json').read_text())
    proof=json.loads((directory/'verification.json').read_text())
    assert rebuilding or audit['baselineSha256']==base_sha
    path=directory/filename
    component_sha=hashlib.sha256(path.read_bytes()).hexdigest()
    assert component_sha==proof['componentSha256']
    assert all(name.startswith(code+'_NEXT_') for name in audit['ownedObjects'])
    assert all(name.startswith(code+'_') for name in audit['archivedObjects'])
    assert not set(audit['ownedObjects'])&set(bpy.data.objects.keys())
    with bpy.data.libraries.load(str(path),link=False) as (source,target):
        assert set(audit['ownedObjects'])<=set(source.objects)
        target.objects=list(audit['ownedObjects'])
    for obj in target.objects:
        assert obj is not None
        bpy.data.collections[code+'_EXTERIOR'].objects.link(obj)
        obj.hide_render=False;obj.hide_viewport=False;obj.hide_set(False)
    # Restore unchanged component slots to their existing local material IDs.
    pairs={c['replacement']:c['original'] for c in audit.get('changes',[])}
    pairs.update({'PAR_NEXT_'+name.removeprefix('PAR_'):name for name in audit.get('replacementSlots',{})})
    for name,original_name in pairs.items():
        obj=bpy.data.objects[name];old=bpy.data.objects[original_name]
        for index,mat in enumerate(list(obj.data.materials)):
            if mat and not mat.name.startswith(code+'_NEXT_') and index<len(old.data.materials):
                obj.data.materials[index]=old.data.materials[index]
    for name in audit['archivedObjects']:
        bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
    archived.extend(audit['archivedObjects']);owned.extend(audit['ownedObjects'])
    components.append({'code':code,'source':str(path.relative_to(ROOT)),'sha256':component_sha,'objects':len(target.objects)})
for scene in bpy.data.scenes:
    for layer in scene.view_layers:layer.update()
mismatches=[n for n,value in original.items() if fingerprint(bpy.data.objects[n])!=value]
assert not mismatches,mismatches
assert all([bpy.data.objects[n].hide_render,bpy.data.objects[n].hide_viewport,bpy.data.objects[n].hide_get()]==value for n,value in visibility.items() if n not in archived)
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
bpy.ops.wm.save_as_mainfile(filepath=str(CURRENT))
bpy.ops.wm.open_mainfile(filepath=str(CURRENT))
for scene in bpy.data.scenes:
    for layer in scene.view_layers:layer.update()
mismatches=[n for n,value in original.items() if fingerprint(bpy.data.objects[n])!=value]
assert not mismatches,mismatches
assert all(bpy.data.objects[n].hide_render for n in archived)
assert all(not bpy.data.objects[n].hide_render for n in owned)
assert rebuilding or hashlib.sha256(BASE.read_bytes()).hexdigest()==base_sha
proof={'version':120,'sourceModelSha256':hashlib.sha256(CURRENT.read_bytes()).hexdigest(),'baselineSha256':base_sha,'originalGeometryRetained':True,'unrelatedVisibilityPreserved':True,'retainedOriginalObjects':len(original),'archivedObjects':archived,'archivedVisibility':{n:visibility[n] for n in archived},'ownedObjects':owned,'components':components,'savedSceneReopened':True}
(OUT/'saved-verification.json').write_text(json.dumps(proof,indent=2)+'\n')
print('EXTERIOR_COMPONENTS_SAVED_AND_REOPENED',len(original),len(owned),flush=True)
