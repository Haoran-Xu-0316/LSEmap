"""Read-only OLD216 exterior review on the accepted native source."""
from pathlib import Path
import hashlib,json,sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'result/blender/LSE_campus_detailed_v215.blend'
SHA='b6c726056d7e98dc229e1ac2dc1d01e7be35eb1835a28cd7a6bb88155a9c1a11'
OUT=ROOT/'result/blender/old-exterior216'
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import object_fingerprint

def run():
 assert hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE))
 bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 for s in bpy.data.scenes:
  for l in s.view_layers:l.update()
 frame=json.loads((ROOT/'result/blender/stage52/old-houghton-audit.json').read_text())
 origin,right,normal=[Vector(frame[k])for k in ['origin','right','outward']]
 rows=[]
 for obj in bpy.data.collections['OLD_EXTERIOR'].all_objects:
  if obj.hide_render:continue
  pts=[obj.matrix_world@v.co-origin for v in obj.data.vertices] if obj.type=='MESH' else [obj.matrix_world@Vector(p)-origin for p in obj.bound_box]
  local=[(p.dot(right),p.dot(normal),p.z)for p in pts]
  rows.append(dict(name=obj.name,type=obj.type,materials=[m.name if m else None for m in getattr(obj.data,'materials',[])],bounds=[[min(p[i]for p in local)for i in range(3)],[max(p[i]for p in local)for i in range(3)]],vertices=len(obj.data.vertices)if obj.type=='MESH' else None))
 (OUT/'inventory.json').write_text(json.dumps(dict(baselineSha256=SHA,objects=rows),indent=2)+'\n')
 if (OUT/'clare-relief-rays.json').exists():
  print('OLD216_EXACT_INVENTORY_DONE',len(rows),flush=True)
  return
 # Probe whether existing figure surfaces actually clear the retained facade.
 frame=json.loads((ROOT/'result/blender/stage49/old-clare-audit.json').read_text())
 origin,right,normal=[Vector(frame[k])for k in ['origin','right','outward']]
 vertices,faces,owners=[],[],[]
 for obj in bpy.data.collections['OLD_EXTERIOR'].all_objects:
  if obj.type!='MESH' or obj.hide_render:continue
  n=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
  faces.extend(tuple(n+i for i in p.vertices)for p in obj.data.polygons);owners.extend([obj.name]*len(obj.data.polygons))
 tree=BVHTree.FromPolygons(vertices,faces)
 parts=[]
 for obj in bpy.data.collections['OLD_EXTERIOR'].all_objects:
  if obj.hide_render or not('clare89_pose' in obj.name or obj.name=='OLD194_STONE_OLD_CLARE165_retained_facade_stone'):continue
  points=[obj.matrix_world@v.co-origin for v in obj.data.vertices]
  coords=[(p.dot(right),p.dot(normal),p.z)for p in points]
  probes=[]
  if 'clare89_pose' in obj.name:
   for face_index in range(0,len(obj.data.polygons),max(1,len(obj.data.polygons)//150)):
    face=obj.data.polygons[face_index]
    target=obj.matrix_world@face.center
    hit=tree.ray_cast(target+normal*2,-normal,4)
    probes.append(dict(firstSurface=owners[hit[2]]if hit[2]is not None else None,distance=hit[3],target=list(target)))
  parts.append(dict(name=obj.name,bounds=[[min(p[i]for p in coords)for i in range(3)],[max(p[i]for p in coords)for i in range(3)]],probeCount=len(probes),visibleOwn=sum(p['firstSurface']==obj.name for p in probes),probes=probes))
 (OUT/'clare-relief-rays.json').write_text(json.dumps(parts,indent=2)+'\n')
 # Reuse the previous neutral review rig without any native save.
 from refine_old_exterior194 import render_comparison
 import refine_old_exterior194
 refine_old_exterior194.OUT=OUT
 if not (OUT/'current-houghton.png').exists():render_comparison('current',[])
 print('OLD216_REVIEW_DONE',len(rows),flush=True)
if __name__=='__main__':run()
