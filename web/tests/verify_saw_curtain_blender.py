"""Inspect saved SAW panes against the inherited folded masonry boundaries."""
from pathlib import Path
import array,hashlib,json,math
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage82'
a=json.loads((OUT/'saw-curtain-audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v82.blend'))
def fingerprint(o):
 h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
 if o.type=='MESH':
  h.update(array.array('f',[c for v in o.data.vertices for c in v.co]).tobytes())
  h.update(array.array('i',[l.vertex_index for l in o.data.loops]).tobytes())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode())
 return h.hexdigest()
assert all(fingerprint(bpy.data.objects[n])==v for n,v in a['baselineFingerprint'].items())
for n in a['hiddenObjects']:assert bpy.data.objects[n].hide_render
assert set(bpy.data.objects.keys())-set(a['baselineFingerprint'])==set(a['addedObjects'])
vertices=0
for r in a['facades']:
 o=bpy.data.objects['SAW_D5_curtain82_'+r['family']+'_panes'];p=Vector(r['p']);u=Vector(r['u']);n=Vector(r['n'])
 knots=r['headKnots']
 for v in o.data.vertices:
  pos=o.matrix_world@v.co;delta=pos-p;x=delta.dot(u);z=pos.z
  assert -.001<=x<=r['length']+.001 and z>=-.001
  left,right=next((left,right)for left,right in zip(knots,knots[1:])if x<=right[0]+.001)
  h=left[1]+(right[1]-left[1])*(x-left[0])/(right[0]-left[0])
  assert z<=h+.002,(r['family'],x,z,h)
  assert -.331<=delta.dot(n)<=-.304
  vertices+=1
 bm=bmesh.new();bm.from_mesh(o.data);assert bm.calc_volume(signed=True)>0;bm.free()
for n in a['addedObjects']:
 o=bpy.data.objects[n]
 assert not o.hide_render and all(math.isfinite(x)for v in o.data.vertices for x in v.co)
 assert all(p.area>1e-8 for p in o.data.polygons)
a['savedMeasurements']={'originalGeometryAndMaterialsUnchanged':True,'facadeCount':len(a['facades']),'paneCount':sum(r['panes']for r in a['facades']),'clippedPaneVertices':vertices,'newMeshObjects':len(a['addedObjects'])}
(OUT/'saw-curtain-audit.json').write_text(json.dumps(a,indent=2)+'\n')
print('SAVED_SAW_CURTAIN_VERIFIED',a['savedMeasurements'],flush=True)
