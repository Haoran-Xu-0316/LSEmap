"""Rebuild Parish Hall's photographed street composition, preserving version 09.

Run inside Blender. Source photos inform geometry but are not embedded. The OSM
footprint stays fixed; roof heights and unseen elevations remain estimates.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import sys
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, Facade, materials
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage10/parish'
data=json.loads((OUT/'parish-geometry.json').read_text())
profile=data['profile'];wall=data['front']
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v09.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
collection=bpy.data.collections['PAR_EXTERIOR']
def protected_geometry():
 digest=hashlib.sha256();excluded=set(collection.all_objects)
 for obj in sorted(bpy.data.objects,key=lambda o:o.name):
  if obj.type!='MESH' or obj in excluded:continue
  digest.update(obj.name.encode());digest.update(array.array('f',[v for row in obj.matrix_world for v in row]).tobytes())
  coordinates=array.array('f',[0])*(len(obj.data.vertices)*3);obj.data.vertices.foreach_get('co',coordinates);digest.update(coordinates.tobytes())
 return digest.hexdigest()
before=protected_geometry()
for obj in list(collection.all_objects):bpy.data.objects.remove(obj,do_unlink=True)
materials.clear()
colors={'brick':(.38,.135,.068),'archbrick':(.28,.075,.031),'tile':(.34,.095,.048),
        'stone':(.59,.56,.46),'frame':(.74,.72,.63),'glass':(.070,.105,.105),
        'metal':(.035,.043,.04),'timber':(.10,.058,.034),'lead':(.34,.36,.35),'red':(.60,.016,.026)}
for name,color in colors.items():
 m=bpy.data.materials.new('PAR10_'+name);m.use_nodes=True;m.diffuse_color=(*color,1)
 nodes,links=m.node_tree.nodes,m.node_tree.links;shader=nodes['Principled BSDF']
 shader.inputs['Base Color'].default_value=m.diffuse_color;shader.inputs['Roughness'].default_value=.25 if name=='glass' else .77
 if name in {'brick','tile'}:
  uv=nodes.new('ShaderNodeTexCoord');brick=nodes.new('ShaderNodeTexBrick')
  for key,value in [('Scale',1),('Brick Width',.24 if name=='tile' else .225),('Row Height',.11 if name=='tile' else .078),('Mortar Size',.003 if name=='tile' else .005)]:brick.inputs[key].default_value=value
  brick.inputs['Color1'].default_value=(*color,1);brick.inputs['Color2'].default_value=(*(v*.79 for v in color),1);brick.inputs['Mortar'].default_value=(.18,.12,.075,1) if name=='tile' else (.30,.27,.20,1)
  links.new(uv.outputs['UV'],brick.inputs['Vector']);links.new(brick.outputs['Color'],shader.inputs['Base Color'])
 materials[name]=m
groups={};front=Facade(profile,wall,groups);L=front.length;split=data['entryStart'];entry_x=(split+L)/2

def beam(name,material,points,radius=.04):
 points=[Vector(front.point(x,z,d)) for x,z,d in points];vertices=[]
 for i,p in enumerate(points):
  tangent=(points[min(i+1,len(points)-1)]-points[max(i-1,0)]).normalized();axis=tangent.cross(Vector((0,0,1)))
  if axis.length<.001:axis=tangent.cross(Vector((1,0,0)))
  axis.normalize();other=tangent.cross(axis).normalized()
  vertices.extend(tuple(p+radius*(axis*math.cos(j*math.tau/8)+other*math.sin(j*math.tau/8))) for j in range(8))
 faces=[(i*8+j,i*8+(j+1)%8,(i+1)*8+(j+1)%8,(i+1)*8+j) for i in range(len(points)-1) for j in range(8)]
 front.group(name,material).add(vertices,faces)

def window(f,x,bottom,top,width,pitch,z0,z1):
 for sign in [-1,1]:f.box('masonry_pier','brick',x+sign*(pitch+width)/4,(bottom+top)/2,(pitch-width)/2,top-bottom,.36,-.17)
 for low,high in [(z0,bottom),(top,z1)]:f.box('masonry_spandrel','brick',x,(low+high)/2,pitch,high-low,.36,-.17)
 f.box('recessed_glass','glass',x,(bottom+top)/2,width,top-bottom,.04,-.19)
 for sign in [-1,1]:f.box('window_jamb','frame',x+sign*width/2,(bottom+top)/2,.075,top-bottom,.14,-.025)
 for z in [bottom,top,bottom+(top-bottom)*.55]:f.box('window_rail','frame',x,z,width,.065,.14,-.015)
 for fraction in [-.25,0,.25]:f.box('glazing_bar','frame',x+width*fraction,(bottom+top)/2,.029,top-bottom,.08,.01)
 if top-bottom>1.5:
  for fraction in [.26,.77]:f.box('glazing_bar','frame',x,bottom+(top-bottom)*fraction,width,.026,.08,.01)
 f.box('stone_lintel','stone',x,top+.10,width+.28,.21,.38,.035)
 f.box('stone_sill','stone',x,bottom-.07,width+.30,.14,.46,.06)

# Four window groups in the main wing: basement, tall main windows, short attic windows.
pitch=split/4
for i in range(4):
 x=(i+.5)*pitch
 window(front,x,.12,1.15,2.12,pitch,0,1.65)
 window(front,x,2.8,5.15,2.10,pitch,1.65,6.55)
 window(front,x,7.0,8.25,2.20,pitch,6.55,8.8)
 front.arch('brick_relieving_arch','archbrick',x,5.26,1.10,.23,.12)
 for j in range(6):front.box('sill_corbel','archbrick',x+(j-2.5)*.30,2.61,.16,.20,.32,.06)
for z,thickness in [(1.6,.12),(6.58,.15),(8.63,.20)]:front.box('front_stone_course','stone',split/2,z,split,thickness,.42,.04)

# The entrance is the low end bay seen at the left of the street photograph.
# Two separate glazed portals flank a masonry pier; there is no false arch-shaped door.
for i in range(2):
 x=split+1.20+i*2.25
 for side in [-1,1]:front.box('portal_brick_pier','brick',x+side*(2.25+1.54)/4,1.8,(2.25-1.54)/2,3.6,.36,-.17)
 front.box('portal_fanlight','glass',x,3.17,1.54,.68,.045,-.17)
 for dx in [-.77,-.25,.25,.77]:front.box('fanlight_mullion','frame',x+dx,3.17,.042,.68,.10,-.025)
 front.box('portal_threshold','stone',x,.025,1.65,.05,.52,.1)
 front.box('portal_lower_glass','glass',x,1.45,1.46,2.72,.07,.015)
 for sign in [-1,1]:front.box('portal_metal_jamb','metal',x+sign*.75,1.70,.09,3.35,.18,.075)
 front.box('portal_door_rail','metal',x,2.87,1.55,.08,.17,.10)
 beam('door_handle','metal',[(x-.53,1.0,.15),(x-.53,1.6,.15)],.025)
front.box('hall_tympanum','brick',entry_x,4.60,4.70,2.1,.36,-.17)
front.group('entrance_gable','brick').add([front.point(split,5.62,.02),front.point(L,5.62,.02),front.point(entry_x,6.98,.02)],[(0,1,2)])
for offset in [0,.15]:beam('gable_stone_coping','stone',[(split-.06,5.64+offset,.14),(entry_x,7.02+offset,.14),(L+.06,5.64+offset,.14)],.095)
# Brick voussoirs of a pointed arch, built from paired circular arcs.
half=1.95;rise=1.85;spring=3.72;c=(rise*rise-half*half)/(2*half);radius=half+c
for side in [-1,1]:
 angle_end=math.atan2(rise,-c)
 for j in range(28):
  angles=[math.pi+(angle_end-math.pi)*j/28,math.pi+(angle_end-math.pi)*(j+1)/28]
  vertices=[front.point(entry_x+side*(c+r*math.cos(a)),spring+r*math.sin(a),d) for d in [.03,.21] for r,a in [(radius,angles[0]),(radius,angles[1]),(radius+.25,angles[1]),(radius+.25,angles[0])]]
  front.group('pointed_brick_arch','archbrick').add(vertices,[(0,1,2,3),(4,7,6,5),(0,4,5,1),(3,2,6,7),(1,5,6,2),(0,3,7,4)])
front.box('inscribed_lintel','stone',entry_x,3.55,4.70,.32,.45,.10)
front.label('ST CLEMENT DANES PARISH HOUSE',entry_x,3.49,.137,'timber',.331)
front.box('stone_cross_stem','stone',entry_x,4.70,.13,.85,.08,.07)
front.box('stone_cross_arm','stone',entry_x,4.89,.54,.12,.08,.07)
for x in [split+.25,L-.27]:
 front.box('entry_red_marker','red',x,2.30,.30,.42,.12,.075)
 front.label('LSE',x,2.20,.145,'frame',.14)
 front.box('entry_call_panel','metal',x,1.98,.16,.32,.10,.075)
for x in [split+.39,entry_x,L-.40]:front.box('portal_stone_capital','stone',x,2.65,.35,.16,.44,.03)

# Split side walls at the change in eaves height; keep the low wing low.
def local_xy(point):
 delta=Vector(point)-Vector(wall['p'])
 return delta.dot(front.u),delta.dot(front.n)
for w in profile['walls']:
 if w['front']:continue
 pa,pb=local_xy(w['p']),local_xy(w['q']);cuts=[0,1]
 if (pa[0]-split)*(pb[0]-split)<0:cuts.append((split-pa[0])/(pb[0]-pa[0]))
 cuts.sort()
 for ta,tb in zip(cuts,cuts[1:]):
  p=[w['p'][i]+ta*(w['q'][i]-w['p'][i]) for i in range(2)]
  q=[w['p'][i]+tb*(w['q'][i]-w['p'][i]) for i in range(2)]
  length=math.dist(p,q)
  if length<.01:continue
  f=Facade(profile,{'p':p,'q':q,'length':length,'outward':w['outward']},groups)
  low_wing=(local_xy(p)[0]+local_xy(q)[0])/2>=split
  height=5.9 if low_wing else 8.8
  if length<2:f.box('short_return','brick',length/2,height/2,length,height);continue
  count=max(1,round(length/3.2));bay=length/count
  floors=[(.15,1.15,0,1.65),(2.8,5.15,1.65,5.9 if low_wing else 6.55)]
  if not low_wing:floors.append((7.0,8.25,6.55,8.8))
  for i in range(count):
   for low,high,z0,z1 in floors:window(f,(i+.5)*bay,low,high,min(1.60,bay*.60),bay,z0,z1)

# Clipped roof planes avoid extending the roof over neighbouring footprints.
def roof_height(depth,kind):
 rise=1.55 if kind=='entry' else 4.2
 peak=7.45 if kind=='entry' else 13.0
 rear_depth=abs(min(p[1] for p in data['localRing']))-5
 return peak-(depth+5.0)*rise/5 if depth>=-5 else peak-(-depth-5.0)*rise/rear_depth
roof=Geometry('PAR','tiled_roof','tile')
for part in data['roofParts']:
 for triangle in part['triangles']:roof.add([front.point(x,roof_height(d,part['kind']),d) for x,d in triangle],[(0,1,2)])
groups['roof']=roof
# Close the outer roof edges with gable masonry and retain the stepped entry volume.
ring=data['localRing']
for a,b in zip(ring,ring[1:]+ring[:1]):
 if abs(a[1])<.05 and abs(b[1])<.05:continue
 crossings=[0,1]
 if (a[1]+5)*(b[1]+5)<0:crossings.append((-5-a[1])/(b[1]-a[1]))
 if (a[0]-split)*(b[0]-split)<0:crossings.append((split-a[0])/(b[0]-a[0]))
 for t0,t1 in zip(sorted(crossings),sorted(crossings)[1:]):
  points=[(a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])) for t in [t0,t1]]
  kind='entry' if sum(p[0] for p in points)/2>=split else 'main'
  eaves=5.9 if kind=='entry' else 8.8
  front.group('rear_roof_gable','brick').add([front.point(x,eaves,d) for x,d in points]+[front.point(x,roof_height(d,kind),d) for x,d in reversed(points)],[(0,1,2,3)])
# Close the main wing's exposed gable above the adjoining low roof.
seam_back=-10.14
for d0,d1 in [(0,-5),(-5,seam_back)]:
 front.group('stepped_wing_gable','brick').add([front.point(split,roof_height(d,'entry'),d) for d in [d0,d1]]+[front.point(split,roof_height(d,'main'),d) for d in [d1,d0]],[(0,1,2,3)])
beam('main_roof_ridge','tile',[(.2,13.02,-5),(split-.1,13.02,-5)],.115)
beam('front_gutter','metal',[(0,8.81,.12),(split,8.81,.12)],.07)
beam('entry_gutter','metal',[(split,5.91,.12),(L,5.91,.12)],.06)
for x in [.22,split/2,split-.22]:
 beam('rainwater_pipe','metal',[(x,.12,.22),(x,7.7,.22),(x,8.1,.12),(x,8.78,.12)],.06)
 for z in [1,3.5,6.0,8.0]:front.box('pipe_clip','metal',x,z,.19,.055,.15,.15)
# Four small timber dormers align with the four street window groups.
for i in range(4):
 x=(i+.5)*pitch;z=10.9;depth=-2.6
 front.box('dormer_glass','glass',x,z+.34,.75,.52,.06,depth+.02)
 for sign in [-1,1]:
  front.box('dormer_frame','timber',x+sign*.43,z+.36,.10,.75,.18,depth+.06)
  front.box('dormer_cheek','timber',x+sign*.46,z+.35,.10,1.1,1.14,depth-.49)
 for dz in [0,.72]:front.box('dormer_rail','timber',x,z+dz,.98,.09,.20,depth+.07)
 front.box('dormer_mullion','timber',x,z+.36,.05,.70,.12,depth+.07)
 for side in [-1,1]:
  front.group('dormer_pitched_roof','tile').add([front.point(x,z+1.36,depth+.20),front.point(x+side*.70,z+.76,depth+.20),front.point(x+side*.70,z+.76,depth-1.25),front.point(x,z+1.36,depth-1.25)],[(0,1,2,3)])
 beam('dormer_bargeboard','timber',[(x-.72,z+.75,depth+.22),(x,z+1.4,depth+.22),(x+.72,z+.75,depth+.22)],.08)
# Roof shoulders and two distinctive tall stacks follow the photographed silhouette.
for x in [.10,split-.10]:
 beam('roof_stone_verge','stone',[(x,8.85,0),(x,13.08,-5)],.14)
 front.box('chimney_stack','brick',x,12.95,.78,4.45,.72,-4.8)
 for z,width in [(14.48,.88),(14.70,1.0),(14.94,1.12)]:front.box('chimney_corbel','archbrick',x,z,width,.18,.88,-4.8)
 for dx in [-.22,.22]:beam('chimney_pot','archbrick',[(x+dx,15.0,-4.8),(x+dx,15.47,-4.8)],.11)
# Street railings screen the exposed basement windows; repeated bars share one mesh.
rail_start=.12;rail_end=split-.15
for i in range(int((rail_end-rail_start)/.22)+1):
 x=rail_start+i*.22
 beam('basement_railing','metal',[(x,.03,1.00),(x,1.57,1.00)],.018)
for z in [.18,1.35,1.54]:beam('basement_rail','metal',[(rail_start,z,1.00),(rail_end,z,1.00)],.027)
for i in range(9):beam('rail_support','metal',[(rail_start+(rail_end-rail_start)*i/8,.02,1.00),(rail_start+(rail_end-rail_start)*i/8,1.62,1.00)],.035)
for geometry in groups.values():
 obj=geometry.finish()
 if geometry is roof:
  # Continuous roof coordinates keep tile courses parallel to the eaves across triangles.
  for face in obj.data.polygons:
   for index in face.loop_indices:
    vertex=obj.data.vertices[obj.data.loops[index].vertex_index].co
    x,d=local_xy(vertex.xy)
    obj.data.uv_layers.active.data[index].uv=(x,d*1.25)
bpy.context.view_layer.update()
assert protected_geometry()==before,'Geometry outside Parish Hall changed'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v10.blend'))
record={'code':'PAR','exteriorDirection':[front.n.x,.5,-front.n.y],
 'scope':'Photo-informed low entrance hall, four-bay street elevation and pitched tile roof. Footprint retained; heights, roof depths, ornamental profiles and unseen elevations estimated. No verified interior.',
 'reference':profile['reference'],'supportingReference':'data/建筑图片/PAR_Parish Hall/01_建筑实拍/small_round5_PAR-001.jpg',
 'components':sum(g.parts for g in groups.values()),'protectedGeometrySha256':before,
 'detailView':{'label':'入口细节','position':list(front.point(entry_x,3.8,15)),'target':list(front.point(entry_x,3.1,0)),'fov':46}}
(OUT/'parish-manifest.json').write_text(json.dumps({'buildings':[record]},indent=2)+'\n')
print('PARISH_REFINEMENT_COMPLETE',record,flush=True)
