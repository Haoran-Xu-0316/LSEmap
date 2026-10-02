"""Refine SAL's two photographed front tower roofs and arched lanterns.
Run in Blender Text Editor. Existing tower placement and endpoints are retained;
curvature, joinery and optical finish are photographic estimates, not a survey.
"""
from pathlib import Path
import array,hashlib,json,math,shutil,sys
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage101';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v100.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
def fingerprint(o):
 h=hashlib.sha256(str([list(r) for r in o.matrix_world]).encode())
 if o.type=='MESH':
  h.update(array.array('f',[c for v in o.data.vertices for c in v.co]).tobytes());h.update(array.array('i',[l.vertex_index for l in o.data.loops]).tobytes())
 if o.type=='FONT':h.update(str((o.data.body,o.data.size,o.data.font.name,o.data.extrude)).encode())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode());return h.hexdigest()
def components(o):
 bm=bmesh.new();bm.from_mesh(o.data);seen=set();groups=[]
 for v in bm.verts:
  if v in seen:continue
  todo=[v];seen.add(v);group=[]
  while todo:
   p=todo.pop();group.append(o.matrix_world@p.co)
   for e in p.link_edges:
    q=e.other_vert(p)
    if q not in seen:seen.add(q);todo.append(q)
  groups.append(group)
 bm.free();return groups
before={o.name:fingerprint(o) for o in bpy.data.objects}
roof=bpy.data.objects['SAL_Tower_slate_hipped_roofs']
a=math.radians(24.35);u=Vector((-math.cos(a),-math.sin(a),0));n=Vector((-math.sin(a),math.cos(a),0))
towers=[]
for ps in components(roof):
 xs=[p.dot(u) for p in ps];ys=[p.dot(n) for p in ps];zs=[p.z for p in ps]
 center=u*((min(xs)+max(xs))/2)+n*((min(ys)+max(ys))/2)
 towers.append({'center':list(center),'base':min(zs),'top':max(zs),'width':max(xs)-min(xs),'depth':max(ys)-min(ys)})
assert len(towers)==2
materials.clear()
materials['slate']=roof.data.materials[0]
materials['metal']=bpy.data.materials['SAL_Dark_painted_iron']
glass=bpy.data.materials['SAL_Recessed_reflective_glazing'].copy();glass.name='SAL_V101_lantern_glass';glass['webOpacity']=.58
glass.diffuse_color=(.085,.12,.14,1);shader=glass.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=glass.diffuse_color;shader.inputs['Roughness'].default_value=.22;shader.inputs['Transmission Weight'].default_value=.4
materials['glass']=glass
batches={}
def batch(key):
 if key not in batches:batches[key]=Geometry('SAL','tower101_'+key,key)
 return batches[key]
def point(t,x,y,z):return Vector(t['center'])+u*x+n*y+Vector((0,0,z))
def box(t,key,x,y,z,w,d,h):batch(key).box(point(t,x,y,z),(w,d,h),math.atan2(u.y,u.x))
def loft(t,key,rows):
 # Continuous square bell profile, closed at both ends.
 vs=[point(t,x*w,y*d,z) for z,w,d in rows for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]]
 fs=[(3,2,1,0),tuple(range(len(vs)-4,len(vs)))]
 for i in range(len(rows)-1):
  for j in range(4):fs.append((4*i+j,4*i+(j+1)%4,4*(i+1)+(j+1)%4,4*(i+1)+j))
 batch(key).add(vs,fs)
def prism(t,key,outline,axis,offset,thickness):
 # axis points across one lantern face; offset locates it on the square perimeter.
 vs=[Vector(t['center'])+axis*x+offset+Vector((0,0,z))+axis.cross(Vector((0,0,1))).normalized()*d for d in [-thickness/2,thickness/2] for x,z in outline]
 k=len(outline);fs=[tuple(reversed(range(k))),tuple(range(k,2*k))]+[(j,(j+1)%k,(j+1)%k+k,j+k) for j in range(k)]
 batch(key).add(vs,fs)
old_names=['SAL_Tower_slate_hipped_roofs','SAL_Tower_lantern_cornices','SAL_Tower_lantern_glass','SAL_Tower_lantern_frames','SAL_Tower_lantern_cornices.001','SAL_Tower_lantern_caps']
for name in old_names:
 o=bpy.data.objects[name];assert not o.hide_render;o.hide_render=True;o.hide_set(True)
for t in towers:
 z0,z1=t['base'],t['top'];w,d=t['width']/2,t['depth']/2
 rows=[]
 for i in range(25):
  f=i/24;blend=(1-f)**1.45
  rows.append((z0+(z1-z0)*f,1.175+(w-1.175)*blend,1.175+(d-1.175)*blend))
 loft(t,'slate',rows)
 # Dark layered base and projecting upper cornice replace the former stone box.
 for z,size,h in [(z1+.035,2.72,.07),(z1+.12,2.52,.10),(z1+.245,2.34,.15),(z1+2.08,2.50,.10),(z1+2.18,2.70,.10)]:box(t,'metal',0,0,z,size,size,h)
 base=z1+.30;spring=base+.90;radius=.87
 outline=[(-radius,base),(radius,base),(radius,spring)]+[(radius*math.cos(i*math.pi/16),spring+radius*math.sin(i*math.pi/16)) for i in range(1,17)]
 for axis,offset in [(u,n*1.055),(-u,-n*1.055),(n,-u*1.055),(-n,u*1.055)]:
  prism(t,'glass',outline,axis,offset,.035)
  # Each face has a true curved arch head and thin subdividing bars.
  for i in range(24):
   a0,a1=i*math.pi/24,(i+1)*math.pi/24
   path=[(r*math.cos(a),spring+r*math.sin(a)) for r,a in [(radius,a0),(radius,a1),(radius+.08,a1),(radius+.08,a0)]]
   prism(t,'metal',path,axis,offset,.10)
  for x in [-.91,-.29,.29,.91]:
   top=spring+math.sqrt(max(0,radius**2-min(abs(x),radius)**2))
   prism(t,'metal',[(x-.035,base),(x+.035,base),(x+.035,top),(x-.035,top)],axis,offset,.10)
  for z in [base+.55,spring]:prism(t,'metal',[(-radius,z-.025),(radius,z-.025),(radius,z+.025),(-radius,z+.025)],axis,offset,.10)
 for x in [-1.055,1.055]:
  for y in [-1.055,1.055]:box(t,'metal',x,y,base+.9,.15,.15,1.85)
 # Slightly curved shallow cap preserves the existing crown height and finial.
 loft(t,'slate',[(z1+2.15+1.2*f,.35+(1.35-.35)*(1-f)**1.3,.35+(1.35-.35)*(1-f)**1.3) for f in [i/16 for i in range(17)]])
added=[]
for g in batches.values():
 o=g.finish();o.name='SAL_V101_'+g.material.name
 for m in list(o.modifiers):o.modifiers.remove(m)
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free();added.append(o.name)
assert all(fingerprint(bpy.data.objects[k])==v for k,v in before.items())
for name in ['room-studies.json','room-spaces.json','building-review.json']:shutil.copyfile(ROOT/'result/blender/stage100'/name,OUT/name)
shutil.copyfile(ROOT/'web/public/models/catalogue.json',OUT/'catalogue-before.json')
audit={'version':101,'baseline':100,'originalFingerprints':before,'hiddenObjects':old_names,'addedObjects':added,'towers':towers,'axis':list(u),'normal':list(n),'reference':'data/建筑图片/SAL_Sir Arthur Lewis Building/01_建筑实拍/library_round5_library_round5_SAL_d0d696021ed0.jpg','referenceUrl':'https://www.jesticowhiles.com/project/lincolns-inn-fields-london-school-of-economics/','captureDate':None,'scope':'Two retained front tower locations and roof endpoints; bell-curved roof slopes, layered dark lantern cornices, four arched glazing faces per tower and fine joinery; other architecture and interiors retained','limits':['Roof profile, lantern joinery and optical finish are photo estimates','Full roof arrangement and rear elevations unresolved','No change or completion claim for whole interiors']}
(OUT/'sal-tower-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v101.blend'))
print('SAL_TOWER_ROOFS_SAVED',len(towers),len(added))
