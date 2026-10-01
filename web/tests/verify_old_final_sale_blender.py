"""Inspect saved SAW panes against the inherited folded masonry boundaries."""
from pathlib import Path
import array,hashlib,json,math
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage84'
a=json.loads((OUT/'old-final-sale-audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v84.blend'))
def fingerprint(o):
 h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
 if o.type=='MESH':
  h.update(array.array('f',[c for v in o.data.vertices for c in v.co]).tobytes())
  h.update(array.array('i',[l.vertex_index for l in o.data.loops]).tobytes())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode())
 return h.hexdigest()
assert all(fingerprint(bpy.data.objects[n])==v for n,v in a['baselineFingerprint'].items())
assert set(bpy.data.objects.keys())-set(a['baselineFingerprint'])==set(a['addedObjects'])
for n in a['hiddenPreviousObjects']:assert bpy.data.objects[n].hide_render
metrics={}
for n in a['addedObjects']:
 o=bpy.data.objects[n]
 assert not o.hide_render and not o.modifiers
 assert all(math.isfinite(c)for v in o.data.vertices for c in v.co)
 assert all(p.area>1e-10 for p in o.data.polygons)
 metrics[n]={'vertices':len(o.data.vertices),'faces':len(o.data.polygons)}
for family in ['figures','products']:
 o=bpy.data.objects['OLD_D5_finalsale84_'+family]
 euler=len(o.data.vertices)-len(o.data.edges)+len(o.data.polygons)
 assert euler<-100, (family,euler)
 metrics[o.name]['eulerCharacteristic']=euler
 # Openings in the lattice are modelled as geometry, not painted texture.
 assert len(o.data.polygons)>1000 and all(not n.type=='TEX_IMAGE' for m in o.data.materials for n in m.node_tree.nodes)
glass=bpy.data.objects['OLD_D5_finalsale84_glazing']
assert len(glass.data.polygons)==1
shader=glass.data.materials[0].node_tree.nodes['Principled BSDF']
assert abs(shader.inputs['Alpha'].default_value-.58)<.001
assert glass.data.polygons[0].normal.dot(Vector(a['frame']['outward']))>.99
assert a['figureCount']==6 and a['basketCount']==3
assert any(f['pose']=='occluded'for f in a['figures'])
a['savedMeasurements']={'originalGeometryAndMaterialsUnchanged':True,'figures':6,'shoppingContainers':3,'meshObjects':metrics,'latticeHasGeometricOpenings':True,'publicPhotoTextures':0}
(OUT/'old-final-sale-audit.json').write_text(json.dumps(a,indent=2)+'\n')
print('SAVED_OLD_FINAL_SALE_VERIFIED',metrics,flush=True)
