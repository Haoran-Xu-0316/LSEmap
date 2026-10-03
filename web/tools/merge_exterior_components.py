"""Merge independently verified audited CKK curved wing pediment component into the current campus.

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
OUT=ROOT/'result/blender/stage131';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v130.blend'
CURRENT=ROOT/'result/blender/LSE_campus_detailed_v131.blend'
COMPONENTS=[('CKK','ckk_pediment_next','ckk-pediment-component.blend')]
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
        if mat.name.startswith(('CKK_NEXT_',)) and mat.users==int(mat.use_fake_user):
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
    assert all(name.startswith((code+'_NEXT_', code+'_GLAZING_NEXT_', code+'_FRAME_NEXT_')) for name in audit['ownedObjects'])
    assert all(name.startswith(code+'_') for name in audit['archivedObjects'])
    assert not set(audit['ownedObjects'])&set(bpy.data.objects.keys())
    with bpy.data.libraries.load(str(path),link=False) as (source,target):
        assert set(audit['ownedObjects'])<=set(source.objects)
        target.objects=list(audit['ownedObjects'])
    destinations={}
    for record in audit.get('collections',[]):
        collection=bpy.data.collections.get(record['name'])
        if not collection:collection=bpy.data.collections.new(record['name'])
        scene=bpy.data.scenes.get('STUDY_'+record['name'])
        if not scene:
            scene=bpy.data.scenes.new('STUDY_'+record['name']);scene.collection.children.link(collection)
        for name in record['ownedObjects']:destinations[name]=(collection,scene)
    for obj in target.objects:
        assert obj is not None
        if obj.name in destinations:
            collection,scene=destinations[obj.name];bpy.context.window.scene=scene
        else:
            collection=bpy.data.collections[code+'_EXTERIOR'];bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
        collection.objects.link(obj)
        obj.hide_render=False;obj.hide_viewport=False;obj.hide_set(False)
    # Restore unchanged component slots to their existing local material IDs.
    for obj in target.objects:
        for index,mat in enumerate(list(obj.data.materials)):
            if mat:
                existing=bpy.data.materials.get(mat.name.rsplit('.',1)[0]) if mat.name[-4:-3]=='.' else None
                # Previously accepted materials can already carry NEXT prefixes.
                # Reuse an identical native ID; keep intentionally new finishes.
                if existing:
                    def signature(material):
                        shader=material.node_tree.nodes.get('Principled BSDF') if material.use_nodes else None
                        values=[]
                        for key in ('Base Color','Metallic','Roughness','Alpha','IOR','Transmission Weight'):
                            value=shader.inputs[key].default_value if shader and key in shader.inputs else None
                            values.append(tuple(value) if hasattr(value,'__len__') else value)
                        return (tuple(material.diffuse_color),tuple(values),sorted((key,str(value)) for key,value in material.items()))
                    if signature(mat)==signature(existing):obj.data.materials[index]=existing
    pairs={c['replacement']:c['original'] for c in audit.get('changes',[])}
    pairs.update({'PAR_NEXT_'+name.removeprefix('PAR_'):name for name in audit.get('replacementSlots',{})})
    for name,original_name in pairs.items():
        obj=bpy.data.objects[name];old=bpy.data.objects[original_name]
        for index,mat in enumerate(list(obj.data.materials)):
            if mat and not mat.name.startswith(code+'_NEXT_') and index<len(old.data.materials):
                obj.data.materials[index]=old.data.materials[index]
    # Separate audited component families for exact browser-scale parity checks.
    component_materials={}
    for obj in target.objects:
        for index,mat in enumerate(list(obj.data.materials)):
            if mat:
                if mat.name not in component_materials:
                    copied=mat.copy();copied.name=code+'_NEXT_'+mat.name
                    component_materials[mat.name]=copied
                obj.data.materials[index]=component_materials[mat.name]
    for name in audit['archivedObjects']:
        bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
    archived.extend(audit['archivedObjects']);owned.extend(audit['ownedObjects'])
    components.append({'code':code,'source':str(path.relative_to(ROOT)),'sha256':component_sha,'objects':len(target.objects)})
for scene in bpy.data.scenes:
    for layer in scene.view_layers:layer.update()
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
mismatches=[n for n,value in original.items() if fingerprint(bpy.data.objects[n])!=value]
assert not mismatches,mismatches
assert all([bpy.data.objects[n].hide_render,bpy.data.objects[n].hide_viewport,bpy.data.objects[n].hide_get()]==value for n,value in visibility.items() if n not in archived)
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
bpy.ops.wm.save_as_mainfile(filepath=str(CURRENT))
bpy.ops.wm.open_mainfile(filepath=str(CURRENT))
for scene in bpy.data.scenes:
    for layer in scene.view_layers:layer.update()
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
mismatches=[n for n,value in original.items() if fingerprint(bpy.data.objects[n])!=value]
assert not mismatches,mismatches
assert all(bpy.data.objects[n].hide_render for n in archived)
assert all(not bpy.data.objects[n].hide_render for n in owned)
assert rebuilding or hashlib.sha256(BASE.read_bytes()).hexdigest()==base_sha
proof={'version':131,'sourceModelSha256':hashlib.sha256(CURRENT.read_bytes()).hexdigest(),'baselineSha256':base_sha,'originalGeometryRetained':True,'unrelatedVisibilityPreserved':True,'retainedOriginalObjects':len(original),'archivedObjects':archived,'archivedVisibility':{n:visibility[n] for n in archived},'ownedObjects':owned,'components':components,'ownedMaterialNames':{code:sorted({mat.name for name in owned if name.startswith(code+'_') for mat in bpy.data.objects[name].data.materials if mat}) for code,_,_ in COMPONENTS},'savedSceneReopened':True}
(OUT/'saved-verification.json').write_text(json.dumps(proof,indent=2)+'\n')
print('EXTERIOR_COMPONENTS_SAVED_AND_REOPENED',len(original),len(owned),flush=True)
