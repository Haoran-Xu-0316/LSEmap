"""Model SAW's two roof terraces, fitted PV field and high brick flues.
Run in Blender Text Editor. Historical photos guide form; placements are estimates.
"""
from pathlib import Path
import array,hashlib,json,math,shutil,sys
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage83'
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v82.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
plan=json.loads((OUT/'roof-plan.json').read_text())
def fingerprint(o):
 h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
 if o.type=='MESH':
  h.update(array.array('f',[c for v in o.data.vertices for c in v.co]).tobytes())
  h.update(array.array('i',[l.vertex_index for l in o.data.loops]).tobytes())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode())
 return h.hexdigest()
before={o.name:fingerprint(o)for o in bpy.data.objects}
hidden=['SAW_folded_roof_planes','SAW_roof_PV_modules']
for n in hidden:
 o=bpy.data.objects[n];o.hide_render=True;o.hide_set(True)
materials.clear()
for key,color,rough,metal in [('pv_sheet',(.095,.135,.17),.3,.25),('metal',(.38,.42,.43),.48,.55),
 ('deck',(.42,.37,.28),.84,0),('sedum',(.23,.27,.15),.95,0),('rail',(.05,.06,.053),.5,.45),('glass',(.18,.25,.26),.18,0)]:
 m=bpy.data.materials.new('SAW_V83_'+key);m.use_nodes=True;m.diffuse_color=(*color,1)
 shader=m.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=(*color,1)
 shader.inputs['Roughness'].default_value=rough;shader.inputs['Metallic'].default_value=metal
 materials[key]=m
for key,old in [('roof','D2_roof'),('brick','D2_brick_palette26_SAW'),('timber','SAW_V82_jatoba')]:
 m=bpy.data.materials[old].copy();m.name='SAW_V83_'+key;materials[key]=m
batches={}
def batch(family,key):
 if (family,key)not in batches:batches[family,key]=Geometry('SAW','roof83_'+family,key)
 return batches[family,key]
def polygon(family,key,points):
 batch(family,key).add(points,[tuple(range(len(points)))])
def beam(family,key,a,b,width=.07,depth=None):
 a,b=Vector(a),Vector(b);axis=(b-a).normalized();side=axis.cross(Vector((0,0,1)))
 if side.length<.01:side=Vector((1,0,0))
 else:side.normalize()
 normal=axis.cross(side).normalized();side*=width/2;normal*=(depth or width)/2
 v=[p+i*side+j*normal for p in [a,b]for i,j in [(-1,-1),(-1,1),(1,1),(1,-1)]]
 batch(family,key).add(v,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
for tri in plan['roofTriangles']:polygon('metal_fields','roof',tri)
for module in plan['panels']:
 p=module['corners'];polygon('pv_modules','pv_sheet',p)
 for a,b in zip(p,p[1:]+p[:1]):beam('pv_frames','metal',a,b,.027)
for family,key,z in [('upper_terrace','deck',plan['upperLevel']),('green_roof','sedum',plan['greenLevel'])]:
 xy=plan['upperTerrace' if family=='upper_terrace' else 'greenRoof']
 polygon(family,key,[(*p,z)for p in xy])
 for a,b in zip(xy,xy[1:]+xy[:1]):
  beam(family+'_fascia','metal',(*a,z),(*b,z),.12,.20)
# The curtain wall below the terrace; fixed published fifth/sixth-floor datums.
a,b=map(lambda v:Vector((*v,0)),plan['upperTerrace'][:2]);axis=(b-a).normalized();length=(b-a).length
low,high=plan['greenLevel'],plan['upperLevel'];divisions=round(length/1.2)
for i in range(divisions):
 x=a+(b-a)*i/divisions;y=a+(b-a)*(i+1)/divisions
 polygon('lower_roof_glazing','glass',[(x.x,x.y,low),(y.x,y.y,low),(y.x,y.y,high),(x.x,x.y,high)])
for i in range(divisions+1):
 p=a+(b-a)*i/divisions;beam('lower_mullions','timber',(*p[:2],low),(*p[:2],high),.11,.16)
for z in [low,high]:beam('lower_transoms','timber',(*a[:2],z),(*b[:2],z),.12)
# Rear glazing meets the existing metal roof along the west edge of the terrace.
def roof_height(x,y):
 for tri in plan['sourceRoofTriangles']:
  p,q,r=map(Vector,tri);v=q-p;w=r-p;det=v.x*w.y-v.y*w.x
  s=((x-p.x)*w.y-(y-p.y)*w.x)/det;t=(v.x*(y-p.y)-v.y*(x-p.x))/det
  if s>=-1e-5 and t>=-1e-5 and s+t<=1.00001:return p.z+s*v.z+t*w.z
 raise ValueError((x,y))
a,b=map(lambda v:Vector((*v,0)),[plan['upperTerrace'][3],plan['upperTerrace'][2]])
for i in range(divisions):
 x=a+(b-a)*i/divisions;y=a+(b-a)*(i+1)/divisions
 hx,hy=roof_height(x.x,x.y),roof_height(y.x,y.y)
 assert min(hx,hy)>high
 polygon('upper_roof_glazing','glass',[(x.x,x.y,high),(y.x,y.y,high),(y.x,y.y,hy),(x.x,x.y,hx)])
for i in range(divisions+1):
 p=a+(b-a)*i/divisions;beam('upper_mullions','timber',(*p[:2],high),(*p[:2],roof_height(p.x,p.y)),.11,.16)
# Fixed perimeter guardrails, not inferred seating or movable furniture.
for family,xy,z in [('upper',plan['upperTerrace'][:2],high),('green',plan['greenRoof']+[plan['greenRoof'][0]],low)]:
 for a,b in zip(xy,xy[1:]):
  a,b=Vector((*a,z)),Vector((*b,z));beam(family+'_rail_top','rail',a+Vector((0,0,1.05)),b+Vector((0,0,1.05)),.05)
  for i in range(max(1,round((b-a).length/.22))+1):
   count=max(1,round((b-a).length/.22));p=a+(b-a)*i/count
   beam(family+'_rail_pickets','rail',p,p+Vector((0,0,1.05)),.018)
for stack in plan['chimneys']:
 x,y=stack['centre'];z=(stack['base']+stack['top'])/2
 batch('chimneys','brick').box((x,y,z),(*stack['size'],stack['top']-stack['base']),stack['angle'])
 batch('flue_capping','metal').box((x,y,stack['top']+.025),(stack['size'][0]+.08,stack['size'][1]+.08,.05),stack['angle'])
added=[]
for g in batches.values():
 o=g.finish();bm=bmesh.new();bm.from_mesh(o.data)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 if any(o.name.endswith('_'+name)for name in ['metal_fields','pv_modules','upper_terrace','green_roof']):
  bm.normal_update()
  for face in bm.faces:
   if face.normal.z<0:face.normal_flip()
 bm.to_mesh(o.data);bm.free();added.append(o.name)
assert all(before[o.name]==fingerprint(o)for o in bpy.data.objects if o.name in before)
for name in ['room-studies.json','room-spaces.json','building-review.json']:shutil.copyfile(ROOT/'result/blender/stage82'/name,OUT/name)
shutil.copyfile(ROOT/'web/public/models/catalogue.json',OUT/'catalogue-before.json')
audit={'version':83,'baseline':82,'addedObjects':added,'hiddenObjects':hidden,'baselineFingerprint':before,
 'plan':plan,'referenceUrls':['https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/development-projects/saw/breeam'],
 'photo':'data/collections/saw-roof-2026/lse-roof.jpg','photoSha256':hashlib.sha256((ROOT/'data/collections/saw-roof-2026/lse-roof.jpg').read_bytes()).hexdigest(),
 'limitations':plan['limits']}
(OUT/'saw-roof-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v83.blend'))
print('SAW_PHOTO_ROOF_SAVED',len(added),flush=True)
