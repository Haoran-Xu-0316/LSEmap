"""Reopen192 and verify entrance optics plus the complete geometry boundary."""
from pathlib import Path
import hashlib,json,sys
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from refine_architectural_glass import shape_signature
from refine_old_lettering185 import font_signature
from refine_rooms import geometry_signatures
from refine_old_entrance_optics import apply_old_entrance_optics,SOURCE,TARGET,COLOUR,OPACITY
BASE=ROOT/'result/blender/LSE_campus_detailed_v191.blend'
MODEL=ROOT/'result/blender/LSE_campus_detailed_v192.blend'
REPORT=ROOT/'result/blender/stage192'
proof=json.loads((REPORT/'building-refinement.json').read_text())
def optical_state(material):
 values={}
 for socket in material.node_tree.nodes['Principled BSDF'].inputs:
  if not hasattr(socket,'default_value'):continue
  value=socket.default_value
  values[socket.identifier]=list(value) if hasattr(value,'__iter__') else value
 return dict(name=material.name,diffuse=list(material.diffuse_color),opacity=material.get('webOpacity'),inputs=values)
snapshot=REPORT/'baseline-collections.json'
if BASE.exists():
 assert hashlib.sha256(BASE.read_bytes()).hexdigest()==proof['baselineSha256']
 bpy.ops.wm.open_mainfile(filepath=str(BASE))
 collections={c.name:sorted(o.name for o in c.objects) for c in bpy.data.collections}
 original_optics=optical_state(bpy.data.objects[SOURCE].data.materials[0])
 snapshot.write_text(json.dumps(dict(baselineSha256=proof['baselineSha256'],collections=collections,originalOptics=original_optics),indent=2)+'\n')
else:
 baseline=json.loads(snapshot.read_text());assert baseline['baselineSha256']==proof['baselineSha256'];collections=baseline['collections'];original_optics=baseline['originalOptics']
assert hashlib.sha256(MODEL.read_bytes()).hexdigest()==proof['sourceModelSha256']
bpy.ops.wm.open_mainfile(filepath=str(MODEL))
for scene in bpy.data.scenes:
 for layer in scene.view_layers:layer.update()
assert geometry_signatures()==proof['geometrySignatures']
assert all(shape_signature(bpy.data.objects[n])==v for n,v in proof['originalShapesAndUVs'].items())
assert all(font_signature(bpy.data.objects[n])==v for n,v in proof['originalFonts'].items())
assert all(bpy.data.objects[n].hide_render==v for n,v in proof['visibility'].items())
for name,objects in collections.items():
 assert sorted(o.name for o in bpy.data.collections[name].objects if o.name!=TARGET)==objects
old,new=bpy.data.objects[SOURCE],bpy.data.objects[TARGET]
assert old.hide_render and not new.hide_render
assert shape_signature(old)==shape_signature(new)
assert len(new.data.polygons)==8 and len(new.data.vertices)==32
left,right=old.data.materials[0],new.data.materials[0]
assert optical_state(left)==original_optics
assert list(right.diffuse_color)==list(right.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value)
assert all(abs(x-y)<1e-7 for x,y in zip(right.diffuse_color,COLOUR))
assert right['webOpacity']==OPACITY and right.get('webClosedGlazing') is False
for a,b in zip(left.node_tree.nodes['Principled BSDF'].inputs,right.node_tree.nodes['Principled BSDF'].inputs):
 assert a.identifier==b.identifier and a.is_linked==b.is_linked
 if a.name=='Base Color' or not hasattr(a,'default_value'):continue
 x,y=a.default_value,b.default_value
 if hasattr(x,'__iter__'):assert list(x)==list(y)
 else:assert x==y
assert apply_old_entrance_optics()['alreadyApplied']
assert not bpy.data.libraries and not any(i.source=='FILE' and not i.packed_file for i in bpy.data.images)
result=dict(version=192,savedSceneReopened=True,sourceModelSha256=proof['sourceModelSha256'],originalGeometryUVFontsBindingsPreserved=True,collectionsPreserved=True,idempotent=True,entranceGeometryAndUVPreserved=True,unrelatedOpticalInputsPreserved=True,paneCount=8,objects=len(bpy.data.objects))
(REPORT/'reopened-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print('OLD192_FULL_MODEL_VERIFIED',8,flush=True)
