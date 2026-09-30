"""Restore the photo-guided library perimeter mansard and roof windows.
Run in Blender Text Editor. Geometry is an architectural estimate, not a survey;
2001 project imagery does not verify present mechanical plant arrangements.
"""
from pathlib import Path
import bpy,bmesh,json,math,array,hashlib,sys,subprocess
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage60';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v59.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];collection=bpy.data.collections['LRB_EXTERIOR']
site=json.loads((ROOT/'result/blender/site_geometry.json').read_text());building=next(b for b in site['buildings']if b['code']=='LRB');ring=[Vector(p)for p in building['rings'][0]];center=Vector(building['center'])
def fingerprint(obj):
 h=hashlib.sha256(str([list(r)for r in obj.matrix_world]).encode())
 if obj.type=='MESH':h.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes());h.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
 return h.hexdigest()
before={o.name:fingerprint(o)for o in bpy.data.objects};eaves=23;rise=2.8;setback=3.0
deck=bpy.data.objects['LRB_roof_deck_around_atrium'];hole_before=[]
for vertex in deck.data.vertices:
 p=vertex.co
 if not any((Vector(p.xy)-v).length<.01 for v in ring):hole_before.append([p.x,p.y])
(OUT/'roof-void.json').write_text(json.dumps(hole_before))
subprocess.run(['/opt/anaconda3/envs/MachineLearning/bin/python',str(ROOT/'web/tools/prepare_library_mansard_geometry.py')],check=True)
roof_geometry=json.loads((OUT/'roof-geometry.json').read_text())
vertices=[p for triangle in roof_geometry['deckTriangles']for p in triangle];faces=[(i,i+1,i+2)for i in range(0,len(vertices),3)]
mesh=bpy.data.meshes.new('LRB_V60_inset_deck');mesh.from_pydata(vertices,[],faces);mesh.update();deck.data=mesh
deck.data.update();lead=bpy.data.materials.new('LRB_V60_roof_deck_lead');lead.use_nodes=True;lead.diffuse_color=(.43,.45,.445,1);shader=lead.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=lead.diffuse_color;shader.inputs['Roughness'].default_value=.75;deck.data.materials.clear();deck.data.materials.append(lead)
assert roof_geometry['holeArea']>200
shifted=[]
for name in ['LRB_V31_sliced_dome_shell','LRB_V31_north_aperture_glass','LRB_V31_dome_standing_seams_and_frame']:
 obj=bpy.data.objects[name]
 for v in obj.data.vertices:v.co.z+=rise
 obj.data.update();shifted.append(name)
materials.clear()
for key,color,rough in [('slate',(.20,.22,.225),.8),('stone',(.64,.635,.59),.8),('frame',(.68,.69,.66),.55),('glass',(.12,.16,.16),.18),('lining',(.70,.70,.67),.85),('aperture_steel',(.22,.245,.25),.45)]:
 m=bpy.data.materials.new('LRB_V60_'+key);m.use_nodes=True;m.diffuse_color=(*color,1);p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=m.diffuse_color;p.inputs['Roughness'].default_value=rough;materials[key]=m
batches={}
def batch(key):
 if key not in batches:batches[key]=Geometry('LRB','mansard60_'+key,key)
 return batches[key]
# The inset deck connects to the retained cornice through a continuous sloping ring.
for triangle in roof_geometry['roofTriangles']:batch('slate').add(triangle,[(0,1,2)])
# Dormers on the two photographed public faces; bay centres follow the existing
# facade rhythm. Counts and projection depths remain estimated from the aerial.
dormers=[]
for edge,count in [(1,12),(13,12)]:
 a,b=ring[edge],ring[(edge+1)%len(ring)];direction=(b-a).normalized();normal=Vector((-direction.y,direction.x));length=(b-a).length;angle=math.atan2(direction.y,direction.x)
 def point(x,d,z):return (*((a+direction*x)+normal*d),z)
 def box(key,x,d,z,w,t,h):batch(key).box(point(x,d,z),(w,t,h),angle)
 for j in range(count):
  x=(j+.5)*length/count;lo=23.55;hi=25.05;width=1.15;front=-.36;back=-2.9
  box('glass',x,front-.055,(lo+hi)/2,width,.035,hi-lo)
  for sign in [-1,1]:
   box('stone',x+sign*(width/2+.09),front-.15,(lo+hi)/2,.16,.36,hi-lo+.22)
   batch('slate').add([point(x+sign*(width/2+.17),d,z)for d,z in [(front,lo-.10),(front,hi+.2),(back,25.8),(back,25.3)]],[(0,1,2,3)] if sign==1 else [(0,3,2,1)])
  for z in [lo,hi]:box('frame',x,front,z,width,.12,.055)
  for fraction in [-1/6,1/6]:box('frame',x+width*fraction,front,(lo+hi)/2,.025,.10,hi-lo)
  for fraction in [1/3,2/3]:box('frame',x,front,lo+(hi-lo)*fraction,width,.10,.025)
  box('stone',x,front+.03,lo-.13,width+.4,.48,.17)
  # A shallow triangular dressed head projects in front of the mansard slope.
  outline=[(-.77,hi+.12),(.77,hi+.12),(0,hi+.75)]
  vertices=[point(x+dx,d,z)for d in [front-.10,front+.16]for dx,z in outline]
  batch('stone').add(vertices,[(0,1,2),(3,5,4),(0,3,4,1),(1,4,5,2),(2,5,3,0)])
  for sign in [-1,1]:
   vertices=[point(x+sign*.77,front,hi+.20),point(x+sign*.77,back,25.8),point(x,back,26.2),point(x,front,hi+.75)]
   batch('slate').add(vertices,[(0,3,2,1)] if sign==1 else [(0,1,2,3)])
  dormers.append({'edge':edge,'center':x,'low':lo,'high':hi,'width':width})
# Extend the existing circular lightwell to the raised deck without closing its void.
dome=bpy.data.objects['LRB_V31_sliced_dome_shell'];points=[dome.matrix_world@v.co for v in dome.data.vertices];cx=(min(p.x for p in points)+max(p.x for p in points))/2;cy=(min(p.y for p in points)+max(p.y for p in points))/2;radius=9.8
for i in range(128):
 a,b=i*2*math.pi/128,(i+1)*2*math.pi/128
 vertices=[(cx+r*math.cos(t),cy+r*math.sin(t),z)for r in [radius,radius+.12]for z,t in [(eaves,a),(eaves,b),(eaves+rise,b),(eaves+rise,a)]]
 batch('lining').add(vertices,[(0,3,2,1),(4,5,6,7),(3,7,6,2)])
# Replace the former five vertical bars with the photographed triangular grid.
aperture=bpy.data.objects['LRB_V31_north_aperture_glass'];aperture_origin=aperture.matrix_world@aperture.data.vertices[0].co
u=Vector((1,0,0));v=Vector((0,-1,1)).normalized();plane_normal=u.cross(v)
boundary=[aperture.matrix_world@p.co-aperture_origin for p in list(aperture.data.vertices)[1:]]
polygon=[Vector((p.dot(u),p.dot(v)))for p in boundary]
seams=bpy.data.objects['LRB_V31_dome_standing_seams_and_frame'];bm=bmesh.new();bm.from_mesh(seams.data);seen=set();remove=[];old_grid_count=0
for seed in list(bm.verts):
 if seed in seen:continue
 component=[];stack=[seed];seen.add(seed)
 while stack:
  vertex=stack.pop();component.append(vertex)
  for edge in vertex.link_edges:
   other=edge.other_vert(vertex)
   if other not in seen:seen.add(other);stack.append(other)
 points=[seams.matrix_world@p.co-aperture_origin for p in component]
 if len(points)==12 and max(p.dot(v)for p in points)-min(p.dot(v)for p in points)>3 and max(p.x for p in points)-min(p.x for p in points)<.12 and all(abs(p.dot(plane_normal))<.06 for p in points):
  remove.extend(component);old_grid_count+=1
assert old_grid_count==5,old_grid_count
bmesh.ops.delete(bm,geom=remove,context='VERTS');bm.to_mesh(seams.data);bm.free();seams.data.update()
grid_lines=[]
def tube(a,b):
 axis=(b-a).normalized();radial=plane_normal.cross(axis).normalized();offset=plane_normal
 vertices=[p+.055*(radial*math.cos(i*math.pi/3)+offset*math.sin(i*math.pi/3))for p in [a,b]for i in range(6)]
 faces=[(i,(i+1)%6,(i+1)%6+6,i+6)for i in range(6)]+[tuple(reversed(range(6))),tuple(range(6,12))]
 batch('aperture_steel').add(vertices,faces)
for family,direction in enumerate([Vector((1,0)),Vector((.5,math.sqrt(3)/2)),Vector((-.5,math.sqrt(3)/2))]):
 normal=Vector((-direction.y,direction.x));projections=[p.dot(normal)for p in polygon]
 for step in range(math.ceil(min(projections)/2.1),math.floor(max(projections)/2.1)+1):
  offset=step*2.1;intersections=[]
  for a,b in zip(polygon,polygon[1:]+polygon[:1]):
   da,db=a.dot(normal)-offset,b.dot(normal)-offset
   if (da<=0<db)or(db<=0<da):intersections.append(a+(b-a)*da/(da-db))
  if len(intersections)!=2:continue
  a,b=intersections
  if (b-a).length<.3:continue
  tube(aperture_origin+u*a.x+v*a.y,aperture_origin+u*b.x+v*b.y)
  grid_lines.append({'family':family,'endpoints':[list(a),list(b)]})
added=[]
for g in batches.values():
 obj=g.finish();obj['sharedInteriorRoof']=True;obj['source_status']='Project-era mansard and roof windows, dimensions and counts estimated';added.append(obj.name)
 for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
changed=[name for name,h in before.items()if fingerprint(bpy.data.objects[name])!=h];assert set(changed)==set([deck.name]+shifted),changed
for filename in ['room-studies.json','room-spaces.json','building-review.json']:(OUT/filename).write_bytes((ROOT/'result/blender/stage59'/filename).read_bytes())
audit={'version':60,'baseline':59,'changedExisting':changed,'changedOtherObjects':[n for n in changed if not n.startswith('LRB_')],'added':added,'roofTriangleCount':len(roof_geometry['roofTriangles']),'roofRegionAreas':{k:roof_geometry[k] for k in ['holeArea','bandArea','deckArea','outerArea']},'holeXYBefore':hole_before,'dormers':dormers,'dormerRoofFaces':len(dormers)*2,'removedVerticalGridBars':old_grid_count,'triangularGridLines':grid_lines,'eaves':eaves,'deckHeight':eaves+rise,'domeRise':rise,'roofSetback':setback,'reference':'data/建筑图片/LRB_Lionel Robbins Building_Library/01_建筑实拍/library_round5_library_round5_LRB_5ea4100c9303.jpg','sourcePage':'https://tyrensakt.com/projects/lse-library/','limitations':['2001 project imagery, photograph date not stated','Perimeter roof rise, setback, dormer count and dimensions estimated; not a surveyed restoration','Present heat-pump plant, rear elevations and complete interior layouts remain unverified']}
(OUT/'library-mansard-audit.json').write_text(json.dumps(audit,indent=2)+'\n');bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v60.blend'));print('LIBRARY_MANSARD_SAVED',len(dormers),changed)
