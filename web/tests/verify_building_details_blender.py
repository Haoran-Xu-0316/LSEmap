"""Reopen the saved scene and verify isolated architectural glass bindings."""
from pathlib import Path
import hashlib,json,sys
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from refine_rooms import geometry_signatures
from refine_architectural_glass import apply_architectural_glass,shape_signature,LEGACY,ATRIA
REPORT=ROOT/'result/blender/stage164'
MODEL=ROOT/'result/blender/LSE_campus_detailed_v164.blend'
proof=json.loads((REPORT/'building-refinement.json').read_text())
assert hashlib.sha256(MODEL.read_bytes()).hexdigest()==proof['sourceModelSha256']
bpy.ops.wm.open_mainfile(filepath=str(MODEL))
for scene in bpy.data.scenes:
 for layer in scene.view_layers:layer.update()
assert geometry_signatures()==proof['geometrySignatures']
assert apply_architectural_glass()['alreadyApplied']
assert geometry_signatures()==proof['geometrySignatures']
change=proof['changes'][0]
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
(REPORT/'reopened-verification.json').write_text(json.dumps({'version':164,'sourceModelSha256':proof['sourceModelSha256'],'savedSceneReopened':True,'allMeshSignaturesVerified':True,'allShapesAndUVsPreserved':True,'originalSharedMaterialsPreserved':True,'bindingsVerified':len(change['bindings']),'externalDependencies':False,'discardedUnreferencedSourceMaterials':unused_sources},indent=2)+'\n')
print('BUILDINGS164_REOPENED_VERIFIED')
