"""Reopen the saved scene and verify isolated architectural glass bindings."""
from pathlib import Path
import hashlib,json,sys
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from refine_rooms import geometry_signatures
from refine_architectural_glass import apply_architectural_glass,shape_signature,LEGACY,ATRIA
from refine_dielectric_glazing166 import apply_dielectric_glazing,finish_state
from refine_saw_exterior166 import apply_saw_exterior166
from refine_pan_faw_exterior166 import apply_pan_faw_exterior
from refine_cbg_exterior166 import apply_cbg_exterior166
REPORT=ROOT/'result/blender/stage166'
MODEL=ROOT/'result/blender/LSE_campus_detailed_v166.blend'
proof=json.loads((REPORT/'building-refinement.json').read_text())
assert hashlib.sha256(MODEL.read_bytes()).hexdigest()==proof['sourceModelSha256']
bpy.ops.wm.open_mainfile(filepath=str(MODEL))
for scene in bpy.data.scenes:
 for layer in scene.view_layers:layer.update()
assert geometry_signatures()==proof['geometrySignatures']
for refiner in (apply_dielectric_glazing,apply_saw_exterior166,apply_pan_faw_exterior,apply_cbg_exterior166):
 assert refiner()['alreadyApplied']
assert geometry_signatures()==proof['geometrySignatures']
assert {o.name:o.hide_render for o in bpy.data.objects}==proof['visibility']
for name,digest in proof['originalShapesAndUVs'].items():
 assert shape_signature(bpy.data.objects[name])==digest
for binding in proof['changes'][0]['bindings']:
 obj=bpy.data.objects[binding['object']]
 assert shape_signature(obj)==binding['shapeSignature']
 mat=obj.data.materials[binding['slot']];assert mat.name==binding['material']
 assert finish_state(mat)=={**proof['changes'][0]['originalSourceMaterials'][binding['sourceMaterial']],'metallic':0.0}
for name,state in proof['changes'][0]['originalSourceMaterials'].items():
 source=bpy.data.materials.get(name)
 if source:assert finish_state(source)==state
change=json.loads((ROOT/'result/blender/stage164/building-refinement.json').read_text())['changes'][0]
for binding in change['bindings']:
 obj=bpy.data.objects[binding['object']];assert shape_signature(obj)==binding['shapeSignature']
 assert obj.data.materials[0].name==binding['material']
 node=obj.data.materials[0].node_tree.nodes['Principled BSDF'];assert node.inputs['Metallic'].default_value==0
 if obj.name in LEGACY:
  original=change['originalSourceMaterials'][binding['sourceMaterial']]
  assert list(node.inputs['Base Color'].default_value)==original['color']
  assert float(node.inputs['Roughness'].default_value)==original['roughness']
  assert float(node.inputs['Transmission Weight'].default_value)==original['transmission']
  assert obj.data.materials[0].get('webOpacity')==original['webOpacity']
 else:assert obj.data.materials[0].get('webOpacity')==.16
unused_sources=[]
legacy_sources={b['sourceMaterial']for b in change['bindings']if b['object']in LEGACY}
for name,state in change['originalSourceMaterials'].items():
 source=bpy.data.materials.get(name)
 if source is None:
  # Blender omits an unreferenced copied finish on save; shared sources must survive.
  assert name in legacy_sources
  assert not any(name==m.name for obj in bpy.data.objects for m in getattr(obj.data,'materials',[])if m)
  unused_sources.append(name);continue
 node=source.node_tree.nodes['Principled BSDF']
 assert list(node.inputs['Base Color'].default_value)==state['color']
 assert float(node.inputs['Metallic'].default_value)==state['metallic']
 assert float(node.inputs['Roughness'].default_value)==state['roughness']
 assert float(node.inputs['Transmission Weight'].default_value)==state['transmission']
 assert source.get('webOpacity')==state['webOpacity']
assert not bpy.data.libraries
assert not any(i.source=='FILE'and not i.packed_file for i in bpy.data.images)
(REPORT/'reopened-verification.json').write_text(json.dumps({'version':166,'sourceModelSha256':proof['sourceModelSha256'],'savedSceneReopened':True,'allMeshSignaturesVerified':True,'allOriginalShapesAndUVsPreserved':True,'dielectricBindingsVerified':len(proof['changes'][0]['bindings']),'idempotent':True,'originalSharedMaterialsPreserved':True,'glassBindingsVerified':len(change['bindings']),'externalDependencies':False,'archivedObjects':proof['archivedObjects']},indent=2)+'\n')
print('BUILDINGS166_REOPENED_VERIFIED')
