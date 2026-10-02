"""Independently reopen the merged scene and check geometry and clear openings."""
from pathlib import Path
import array,hashlib,json,math
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage114'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v114.blend'))
for scene in bpy.data.scenes:
 for layer in scene.view_layers:layer.update()
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
integration=json.loads((OUT/'integration-audit.json').read_text())
def fingerprint(obj):
 h=hashlib.sha256(str([list(r)for r in obj.matrix_world]).encode())
 if obj.type=='MESH':
  vertices=array.array('f',[0])*(len(obj.data.vertices)*3);indices=array.array('i',[0])*len(obj.data.loops)
  obj.data.vertices.foreach_get('co',vertices);obj.data.loops.foreach_get('vertex_index',indices)
  h.update(vertices.tobytes());h.update(indices.tobytes())
 h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode());return h.hexdigest()
assert all(fingerprint(bpy.data.objects[n])==v for n,v in integration['originalFingerprints'].items())
assert all(bpy.data.objects[n].hide_render==(True if n in integration['archivedObjects']else v) for n,v in integration['originalVisibility'].items())
for name in integration['addedObjects']:
 obj=bpy.data.objects[name];assert not obj.hide_render and obj.parent is None
 assert all(math.isfinite(c) for v in obj.data.vertices for c in v.co),name
mar=json.loads((OUT/'mar/mar-upper-screen-audit.json').read_text())
for name in mar['addedObjects']:
 assert len(bpy.data.objects[name].data.vertices)==38*8,name
 assert bpy.data.objects[name] in list(bpy.data.collections['MAR_EXTERIOR'].objects)
audit=json.loads((OUT/'historic/historic-candidate-audit.json').read_text())
collection=bpy.data.collections['CLM_EXTERIOR']
site=json.loads((ROOT/'result/blender/site_geometry.json').read_text());r=next(b for b in site['buildings'] if b['code']=='CLM');ring=r['rings'][0];points=[Vector(ring[i]) for i in (5,4,3,2,1)];center=Vector(r['center']);segments=[];distance=0
for a,b in zip(points,points[1:]):
 u=(b-a).normalized();n=Vector((u.y,-u.x))
 if n.dot((a+b)/2-center)<0:n=-n
 length=(b-a).length;segments.append((distance,distance+length,a,u,n));distance+=length
vertices=[];polygons=[]
for obj in collection.all_objects:
 if obj.type!='MESH' or obj.hide_render:continue
 # Glass, metal bars and the retained dark lining are intentional window layers.
 if not any('stone' in m.name.lower() or 'portland' in m.name.lower() for m in obj.data.materials if m):continue
 offset=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
 polygons.extend(tuple(offset+i for i in p.vertices) for p in obj.data.polygons)
bvh=BVHTree.FromPolygons(vertices,polygons)
probes=[]
for window in audit['windows']:
 start,end,a,u,n=next(s for s in segments if window['s']<=s[1]);xy=a+u*(window['s']-start);normal=Vector((n.x,n.y,0))
 for height in [13.5,15.5,17.5]:
  for lateral in [-.86,0,.86]:
   origin=Vector((xy.x+u.x*lateral,xy.y+u.y*lateral,height))+normal*2
   hit=bvh.ray_cast(origin,-normal,2.24)
   assert hit[0] is None,(window['bay'],height,lateral,hit[3])
   probes.append({'bay':window['bay'],'height':height,'lateral':lateral,'clear':True})
assert len(probes)==63
assert len(audit['windows'])==7
for record in audit['replacements']:
 source=bpy.data.objects[record['source']];assert source.hide_render
 assert record['copy'] in collection.objects

clm_probes=len(probes)
obj=bpy.data.objects['SITE_V114_Globe_continuous_paving']
assert obj.name in bpy.data.collections['00_SITE'].objects
verts=[obj.matrix_world@v.co for v in obj.data.vertices]
bvh=BVHTree.FromPolygons(verts,[list(f.vertices)for f in obj.data.polygons],all_triangles=True)
assert all(f.normal.z>.999 for f in obj.data.polygons)
count=0
for radius in [.5,1.5,2.5,3.4]:
 for i in range(24):
  a=math.tau*i/24
  point,n,index,d=bvh.ray_cast(Vector((-48.9262+radius*math.cos(a),-20.3711+radius*math.sin(a),1)),Vector((0,0,-1)))
  assert point is not None and .05019<=point.z<=.05151
  count+=1
ring=bpy.data.objects['SITE_V114_Globe_concentric_inlays']
clearance=min((ring.matrix_world@v.co).z for v in ring.data.vertices)-max(v.z for v in verts)
assert clearance>.0019
proof={'version':114,'originalGeometryRetained':True,'retainedObjects':len(integration['originalFingerprints']),
 'marFins':38,'marHammerheads':38,'clmTallWindows':7,'clearClmWindowProbes':clm_probes,
 'groundCoverageProbes':count,'ringClearanceMetres':clearance,'addedObjects':len(integration['addedObjects']),
 'archivedObjects':len(integration['archivedObjects']),'sourceModelSha256':hashlib.sha256((ROOT/'result/blender/LSE_campus_detailed_v114.blend').read_bytes()).hexdigest()}
(OUT/'saved-verification.json').write_text(json.dumps(proof,indent=2)+'\n')
print('MERGED_EXTERIORS_SAVED_VERIFIED',clm_probes,count,flush=True)
