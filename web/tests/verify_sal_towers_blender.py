"""Reopen SAL roof refinement and measure curved profiles and arched panes."""
from pathlib import Path
import array,hashlib,json
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage101'
audit=json.loads((OUT/'sal-tower-audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v101.blend'))
def fingerprint(obj):
    h=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type=='MESH':
        h.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
        h.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
    if obj.type=='FONT':h.update(str((obj.data.body,obj.data.size,obj.data.font.name,obj.data.extrude)).encode())
    h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return h.hexdigest()

for name,digest in audit['originalFingerprints'].items():assert fingerprint(bpy.data.objects[name])==digest,name
assert set(o.name for o in bpy.data.objects)-set(audit['originalFingerprints'])==set(audit['addedObjects'])
for name in audit['hiddenObjects']:assert bpy.data.objects[name].hide_render
u,n=[Vector(audit[k]) for k in ['axis','normal']]
counts={};roofs=[]
for name in audit['addedObjects']:
 o=bpy.data.objects[name];assert not o.hide_render
 bm=bmesh.new();bm.from_mesh(o.data);assert all(e.is_manifold for e in bm.edges),name
 assert bm.calc_volume()>0,name
 seen=set();parts=[]
 for v in bm.verts:
  if v in seen:continue
  todo=[v];seen.add(v);ps=[]
  while todo:
   p=todo.pop();ps.append(o.matrix_world@p.co)
   for e in p.link_edges:
    q=e.other_vert(p)
    if q not in seen:seen.add(q);todo.append(q)
  parts.append(ps)
 counts[name]=len(parts)
 if 'slate' in name.lower():roofs=parts
 if 'glass' in name.lower():
  assert len(parts)==8
  for ps in parts:
   zs=sorted(set(round(p.z,4) for p in ps));assert len(zs)>=10
   assert 1.7<max(zs)-min(zs)<1.9
 bm.free()
assert len(roofs)==4
for tower in audit['towers']:
 center=Vector(tower['center']);roof=min(roofs,key=lambda ps:((sum(ps,Vector())/len(ps))-center-Vector((0,0,(tower['base']+tower['top'])/2))).length)
 assert abs(min(p.z for p in roof)-tower['base'])<.0001
 assert abs(max(p.z for p in roof)-tower['top'])<.0001
 bottom=[p for p in roof if abs(p.z-tower['base'])<.0001]
 assert abs(sum((p-center).dot(u) for p in bottom)/len(bottom))<.0001
 assert abs(max((p-center).dot(u) for p in bottom)-tower['width']/2)<.0001
 midz=(tower['base']+tower['top'])/2
 middle=[p for p in roof if abs(p.z-midz)<.0001]
 assert middle
 top=[p for p in roof if abs(p.z-tower['top'])<.0001]
 straight=(max((p-center).dot(u) for p in bottom)+max((p-center).dot(u) for p in top))/2
 assert max((p-center).dot(u) for p in middle)<straight-.1
material=bpy.data.materials['SAL_V101_lantern_glass'];assert abs(material['webOpacity']-.58)<1e-6
audit['savedMeasurements']={'originalObjectsUnchanged':True,'twoRoofEndpointsRetained':True,'bellCurvatureVerified':True,'eightArchedPanes':True,'closedPositiveVolumeMeshes':True,'components':counts}
(OUT/'sal-tower-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print('SAVED_SAL_TOWERS_VERIFIED',len(audit['towers']),counts)
