"""Reopen complete193 and verify paint-only changes and whole-scene preservation."""
from pathlib import Path
import hashlib,json,sys
import bpy
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'web/tools'))
from refine_architectural_glass import shape_signature
from refine_old_lettering185 import font_signature
from refine_rooms import geometry_signatures
from refine_old_painted_frames import apply_old_painted_frames,material_state,SOURCES,PREFIX,ROUGHNESS
BASE=ROOT/'result/blender/LSE_campus_detailed_v192.blend'
MODEL=ROOT/'result/blender/LSE_campus_detailed_v193.blend'
REPORT=ROOT/'result/blender/stage193'
proof=json.loads((REPORT/'building-refinement.json').read_text());change=proof['changes'][0]
snapshot=REPORT/'baseline-state.json'
def materials():
    return {m.name:material_state(m) for m in bpy.data.materials if m.use_nodes and m.node_tree.nodes.get('Principled BSDF')}
if BASE.exists():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==proof['baselineSha256']
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    baseline=dict(baselineSha256=proof['baselineSha256'],collections={c.name:sorted(o.name for o in c.objects)for c in bpy.data.collections},materials=materials())
    snapshot.write_text(json.dumps(baseline,indent=2)+'\n')
else:
    baseline=json.loads(snapshot.read_text());assert baseline['baselineSha256']==proof['baselineSha256']
assert hashlib.sha256(MODEL.read_bytes()).hexdigest()==proof['sourceModelSha256']
bpy.ops.wm.open_mainfile(filepath=str(MODEL))
for scene in bpy.data.scenes:
    for layer in scene.view_layers:layer.update()
assert geometry_signatures()==proof['geometrySignatures']
assert all(shape_signature(bpy.data.objects[n])==v for n,v in proof['originalShapesAndUVs'].items())
assert all(font_signature(bpy.data.objects[n])==v for n,v in proof['originalFonts'].items())
assert all(bpy.data.objects[n].hide_render==v for n,v in proof['visibility'].items())
assert {c.name:sorted(o.name for o in c.objects)for c in bpy.data.collections}==baseline['collections']
assert len(change['changedObjects'])==20 and len(change['bindings'])==20 and change['materialCount']==12
current=materials();assert set(current)==set(baseline['materials'])|{PREFIX+n for n in SOURCES}
assert all(current[n]==v for n,v in baseline['materials'].items())
for name in SOURCES:
    old,new=current[name],current[PREFIX+name]
    assert old==change['originalSourceMaterials'][name]
    assert old['diffuse']==new['diffuse'] and old['opacity']==new['opacity'] and old['closedGlazing']==new['closedGlazing']
    for socket,value in old['inputs'].items():
        if socket=='Metallic':assert new['inputs'][socket]==0
        elif socket=='Roughness':assert abs(new['inputs'][socket]-ROUGHNESS)<1e-6
        else:assert new['inputs'][socket]==value,(name,socket)
for binding in change['bindings']:
    assert bpy.data.objects[binding['object']].data.materials[binding['slot']].name==binding['material']
assert apply_old_painted_frames()['alreadyApplied']
assert not bpy.data.libraries and not any(i.source=='FILE' and not i.packed_file for i in bpy.data.images)
result=dict(version=193,savedSceneReopened=True,sourceModelSha256=proof['sourceModelSha256'],allShapesUVFontsPreserved=True,collectionsVisibilityPreserved=True,allOriginalMaterialInputsPreserved=True,unrelatedBindingsPreserved=True,onlyPaintMetallicAndRoughnessChanged=True,idempotent=True,paintObjects=20,paintMaterials=12,objects=len(bpy.data.objects))
(REPORT/'reopened-verification.json').write_text(json.dumps(result,indent=2)+'\n');print('OLD193_FULL_MODEL_VERIFIED',20,12,flush=True)
