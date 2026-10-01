"""Rebuild SAW's timber curtain walls inside the existing folded brick boundaries.
Run in Blender Text Editor. Facade locations and section levels are inherited estimates.
"""
from pathlib import Path
import array,hashlib,json,math,shutil,sys
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage82';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v81.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
def fingerprint(o):
 h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
 if o.type=='MESH':
  h.update(array.array('f',[c for v in o.data.vertices for c in v.co]).tobytes())
  h.update(array.array('i',[l.vertex_index for l in o.data.loops]).tobytes())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode())
 return h.hexdigest()
before={o.name:fingerprint(o)for o in bpy.data.objects}
hidden=['SAW_entrance_recessed_glass','SAW_entrance_timber_mullions','SAW_entrance_transoms','SAW_SAW_glazed_notch_return_pierced_wall']
for name in hidden:
 o=bpy.data.objects[name];o.hide_render=True;o.hide_set(True)
materials.clear()
for key,color,rough in [('jatoba',(.23,.105,.05),.48),('glass',(.18,.25,.26),.18),('seal',(.025,.03,.027),.72)]:
 m=bpy.data.materials.new('SAW_V82_'+key);m.use_nodes=True;m.diffuse_color=(*color,1)
 s=m.node_tree.nodes['Principled BSDF'];s.inputs['Base Color'].default_value=(*color,1);s.inputs['Roughness'].default_value=rough
 materials[key]=m
d=json.loads((ROOT/'result/blender/stage02/detail_geometry.json').read_text())
surfaces={s['name']:s for s in d['surfaces']if s['code']=='SAW'}
centre=Vector((*d['saw_center'],0));batches={};records=[]
def batch(family,key):
 if (family,key)not in batches:batches[family,key]=Geometry('SAW','curtain82_'+family,key)
 return batches[family,key]
def clip(poly,limit,value,keep_less):
 result=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  aa=limit(a)-value;bb=limit(b)-value
  ina=aa<=1e-9 if keep_less else aa>=-1e-9
  inb=bb<=1e-9 if keep_less else bb>=-1e-9
  if ina:result.append(a)
  if ina!=inb:
   t=aa/(aa-bb);result.append(tuple(a[i]+t*(b[i]-a[i])for i in range(2)))
 return result
for family in ['north_fold','central_return','south_fold','glazed_notch_return']:
 s=surfaces['SAW_'+family];p=Vector((*s['p'],0));q=Vector((*s['q'],0))
 length=(q-p).length;u=(q-p).normalized();n=Vector((u.y,-u.x,0))
 if ((p+q)*.5-centre).dot(n)<0:n=-n
 angle=math.atan2(u.y,u.x)
 def point(x,z,offset):return p+u*x+n*offset+Vector((0,0,z))
 if family=='north_fold':knots=[(0,7.8),(.61*length,7.8),(length,0)]
 elif family=='central_return':knots=[(0,0),(length,11.5)]
 elif family=='south_fold':knots=[(0,0),(.7*length,8),(length,8)]
 else:knots=[(0,22),(length,24.7)]
 def height(x):
  for (a,ha),(b,hb)in zip(knots,knots[1:]):
   if x<=b+1e-9:return ha+(hb-ha)*(x-a)/(b-a)
  return knots[-1][1]
 levels=[0,3.45,8.1,11.1,14.1,18,21.9,24.7]
 divisions=max(1,round(length/1.2))
 columns=sorted(set([i*length/divisions for i in range(divisions+1)]+[x for x,h in knots]))
 # Subdivide glazing at every column, transom and change in the sloping boundary.
 pane_count=0
 for left,right in zip(columns,columns[1:]):
  slope=(height(right)-height(left))/(right-left);intercept=height(left)-slope*left
  for low,high in zip(levels,levels[1:]):
   poly=[(left+.035,low+.035),(right-.035,low+.035),(right-.035,high-.035),(left+.035,high-.035)]
   poly=clip(poly,lambda v:v[1]-slope*v[0],intercept-.055,True)
   if len(poly)<3:continue
   area=abs(sum(a[0]*b[1]-b[0]*a[1]for a,b in zip(poly,poly[1:]+poly[:1])))/2
   if area<.008:continue
   verts=[point(x,z,off)for off in [-.33,-.305]for x,z in poly];count=len(poly)
   faces=[tuple(range(count-1,-1,-1)),tuple(range(count,2*count))]
   faces += [(i,(i+1)%count,(i+1)%count+count,i+count)for i in range(count)]
   batch(family+'_panes','glass').add(verts,faces);pane_count+=1
 for x in columns:
  h=height(x)
  if h>.12:
   batch(family+'_mullions','jatoba').box(point(x,h/2,-.24),(.105,.18,h),angle)
   batch(family+'_seal','seal').box(point(x,h/2,-.335),(.13,.028,h),angle)
 for z in levels:
  if z==24.7:continue
  for (left,hl),(right,hr)in zip(knots,knots[1:]):
   if max(hl,hr)<=z+.06:continue
   if min(hl,hr)<z+.06:
    cross=left+(right-left)*(z+.06-hl)/(hr-hl)
    if hl<hr:left=cross
    else:right=cross
   if right-left>.08:
    batch(family+'_transoms','jatoba').box(point((left+right)/2,z,-.24),(right-left,.18,.14),angle)
 # Follow the brick soffit with continuous wooden head rails.
 for (left,hl),(right,hr)in zip(knots,knots[1:]):
  a=point(left,hl-.04,-.24);b=point(right,hr-.04,-.24)
  axis=(b-a).normalized();side=n*.085;edge=axis.cross(n).normalized()*.06
  verts=[v+sign1*side+sign2*edge for v in [a,b]for sign1,sign2 in [(-1,-1),(-1,1),(1,1),(1,-1)]]
  batch(family+'_head','jatoba').add(verts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
 records.append({'family':family,'length':length,'columns':columns,'headKnots':knots,'panes':pane_count,'p':list(p),'u':list(u),'n':list(n),'levels':levels})
added=[]
for g in batches.values():
 o=g.finish();bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
 added.append(o.name)
assert all(before[o.name]==fingerprint(o)for o in bpy.data.objects if o.name in before)
for name in ['room-studies.json','room-spaces.json','building-review.json']:shutil.copyfile(ROOT/'result/blender/stage81'/name,OUT/name)
shutil.copyfile(ROOT/'web/public/models/catalogue.json',OUT/'catalogue-before.json')
audit={'version':82,'baseline':81,'hiddenObjects':hidden,'addedObjects':added,'facades':records,'baselineFingerprint':before,
 'referenceUrls':['https://gemjoinery.ie/projects/lse-saw-swee-hock-student-centre/','https://www.photography909.co.uk/saw-swee-hocklse-gallery'],
 'limitations':['Published completion photographs; exact capture dates and 2026 condition unverified','Existing footprint, brick fold silhouette and section levels retained; joinery sizes and spacing estimated','Brick screen layouts, roof silhouette and complete current interiors still require review']}
(OUT/'saw-curtain-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v82.blend'))
print('SAW_TIMBER_CURTAIN_SAVED',len(added),sum(r['panes']for r in records),flush=True)
