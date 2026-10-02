"""Merge reviewed MAR, CLM and ground candidates without replacing the scene.
Run in Blender Text Editor. Preserve all baseline geometry; archive only sources
listed by the independently reopened candidate audits.
"""
from pathlib import Path
import array,hashlib,json,re,shutil
import bpy
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage114'
BASE=ROOT/'result/blender/LSE_campus_detailed_v113.blend'
def fingerprint(obj):
    digest=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type=='MESH':
        vertices=array.array('f',[0])*(len(obj.data.vertices)*3)
        indices=array.array('i',[0])*len(obj.data.loops)
        obj.data.vertices.foreach_get('co',vertices)
        obj.data.loops.foreach_get('vertex_index',indices)
        digest.update(vertices.tobytes());digest.update(indices.tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return digest.hexdigest()
def update_layers():
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:layer.update()
bpy.ops.wm.open_mainfile(filepath=str(BASE));update_layers()
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
before={o.name:fingerprint(o) for o in bpy.data.objects}
visibility={o.name:o.hide_render for o in bpy.data.objects}
mar=json.loads((OUT/'mar/mar-upper-screen-audit.json').read_text())
clm=json.loads((OUT/'historic/historic-candidate-audit.json').read_text())
ground=json.loads((OUT/'ground/ground-candidate-audit.json').read_text())
jobs=[('MAR',ROOT/mar['candidate'],mar['addedObjects'],mar['archivedObjects'],'MAR_EXTERIOR'),
      ('CLM',OUT/'historic/CLM_tall_windows_candidate.blend',clm['addedObjects']+[x['copy'] for x in clm['replacements']],[x['source'] for x in clm['replacements']],'CLM_EXTERIOR'),
      ('SITE',Path(ground['candidate']),ground['addedObjects'],ground['archivedObjects'],'00_SITE')]
added=[];archived=[];candidate_hashes={}
for code,path,names,sources,collection_name in jobs:
    assert not set(names)&set(before)
    baseline_materials={m.name:m for m in bpy.data.materials}
    with bpy.data.libraries.load(str(path),link=False) as (source,target):
        assert set(names)<=set(source.objects)
        target.objects=names
    collection=bpy.data.collections[collection_name]
    for obj in target.objects:
        assert obj and obj.parent is None and not obj.constraints
        for index,material in enumerate(obj.data.materials):
            canonical=re.sub(r'\.\d{3}$','',material.name)
            original=baseline_materials.get(canonical)
            if original and original!=material:
                assert tuple(material.diffuse_color)==tuple(original.diffuse_color),(material.name,canonical)
                obj.data.materials[index]=original
        collection.objects.link(obj);obj.hide_render=False;obj.hide_set(False)
        added.append(obj.name)
    for name in sources:
        assert not visibility[name],name
        bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
        archived.append(name)
    candidate_hashes[code]=hashlib.sha256(path.read_bytes()).hexdigest()
update_layers()
assert all(fingerprint(bpy.data.objects[name])==digest for name,digest in before.items())
assert all(bpy.data.objects[n].hide_render==(True if n in archived else state) for n,state in visibility.items())
assert set(bpy.data.objects.keys())-set(before)==set(added)
assert len(added)==34 and len(archived)==22
for filename in ['room-studies.json','building-review.json']:
    shutil.copyfile(ROOT/'result/blender/stage113'/filename,OUT/filename)
audit={'baseline':113,'edition':114,'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),
       'originalFingerprints':before,'originalVisibility':visibility,'addedObjects':added,
       'archivedObjects':archived,'candidateHashes':candidate_hashes,
       'scope':'MAR upper screen, CLM middle tall-window band and continuous globe paving only',
       'limitations':['MAR central north recess and lower screen remain inaccurate','CLM figure relief still missing','Globe country colours unchanged','Full interiors and other building corrections remain incomplete']}
(OUT/'integration-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v114.blend'))
print('EXTERIOR_CANDIDATES_INTEGRATED',len(added),len(archived),flush=True)
