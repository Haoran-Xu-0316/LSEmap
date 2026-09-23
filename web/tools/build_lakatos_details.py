"""Refine Lakatos' two evidenced public elevations; preserve all other buildings.
Run inside Blender. Roof depths, bays and unseen surfaces remain estimates.
"""
from pathlib import Path
import array, hashlib, json, math, sys
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, Facade, materials
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage13/lakatos';OUT.mkdir(parents=True,exist_ok=True)
profile=next(p for p in json.loads((ROOT/'result/blender/stage05/infill-geometry.json').read_text()) if p['code']=='LAK')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v12.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
collection=bpy.data.collections['LAK_EXTERIOR']
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
colors={'brick':(.38,.13,.064),'stone':(.61,.56,.43),'frame':(.72,.71,.62),'glass':(.080,.145,.16),'metal':(.065,.075,.062),'slate':(.115,.135,.14),'timber':(.21,.15,.09)}
for name,color in colors.items():
 m=bpy.data.materials.new('LAK13_'+name);m.use_nodes=True;m.diffuse_color=(*color,1)
 shader=m.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=m.diffuse_color;shader.inputs['Roughness'].default_value=.28 if name=='glass' else .77
 if name=='brick':
  nodes,links=m.node_tree.nodes,m.node_tree.links;uv=nodes.new('ShaderNodeTexCoord');brick=nodes.new('ShaderNodeTexBrick')
  for key,value in [('Scale',1),('Brick Width',.225),('Row Height',.078),('Mortar Size',.005)]:brick.inputs[key].default_value=value
  brick.inputs['Color1'].default_value=(*color,1);brick.inputs['Color2'].default_value=(*(v*.78 for v in color),1);brick.inputs['Mortar'].default_value=(.27,.24,.18,1)
  links.new(uv.outputs['UV'],brick.inputs['Vector']);links.new(brick.outputs['Color'],shader.inputs['Base Color'])
 materials[name]=m
groups={};facades=[Facade(profile,w,groups) for w in profile['walls']];front,plaza=facades[:2]

def window(f,x,width,low,high,pitch,z0,z1):
 for side in [-1,1]:f.box('brick_piers','brick',x+side*(pitch+width)/4,(low+high)/2,(pitch-width)/2,high-low,.34,-.17)
 for a,b in [(z0,low),(high,z1)]:f.box('brick_spandrels','brick',x,(a+b)/2,pitch,b-a,.34,-.17)
 f.box('sash_glass','glass',x,(low+high)/2,width,high-low,.04,-.17)
 for side in [-1,1]:f.box('sash_jamb','frame',x+side*width/2,(low+high)/2,.067,high-low,.14,-.018)
 for z in [low,high,(low+high)/2]:f.box('sash_rail','frame',x,z,width,.058,.14,.008)
 for fraction in [-.25,0,.25]:f.box('fine_vertical_bar','frame',x+width*fraction,(low+high)/2,.024,high-low,.07,.035)
 for fraction in [.25,.75]:f.box('fine_horizontal_bar','frame',x,low+(high-low)*fraction,width,.024,.07,.037)
 f.box('projecting_sill','stone',x,low-.075,width+.26,.15,.42,.025)
 for side in [-1,1]:f.box('sill_bracket','stone',x+side*width*.32,low-.23,.17,.23,.28,.035)
 f.box('window_lintel','stone',x,high+.08,width+.10,.16,.26,-.02)
 # Tapered stone key above each square-headed opening.
 f.group('tapered_keystone','stone').add([f.point(x+dx,z,d) for d in [-.02,.15] for dx,z in [(-.085,high+.14),(.085,high+.14),(.16,high+.47),(-.16,high+.47)]],[(0,1,2,3),(4,7,6,5),(0,4,5,1),(3,2,6,7)])

for i,f in enumerate(facades):
 if i not in {0,1}:
  f.box('party_envelope','brick',f.length/2,7.8,f.length,15.6);continue
 bays=3 if i==0 else 7;pitch=f.length/bays
 for low,high,z0,z1 in [(4.85,8.12,4.25,8.65),(9.12,11.20,8.65,11.7),(12.10,14.40,11.7,15.6)]:
  for j in range(bays):window(f,(j+.5)*pitch,1.55 if i==0 else 1.50,low,high,pitch,z0,z1)
 # Ground-floor treatment is deliberately different on the two streets.
 for j in range(bays):
  x=(j+.5)*pitch
  if i==0:
   width=pitch-.36
   f.box('shop_glass','glass',x,2.05,width,3.30,.055,-.18)
   for side in [-1,1]:f.box('shop_pilaster','stone',x+side*pitch/2,2.07,.31,4.14,.44,-.06)
   for z in [.42,1.13,2.08,3.05,3.67]:f.box('shop_horizontal_bar','frame',x,z,width,.052,.10,-.04)
   for k in range(5):f.box('shop_vertical_bar','frame',x+(k-2)*width/5,2.05,.048,3.28,.10,-.035)
   f.box('shop_stone_apron','stone',x,.22,width,.44,.38,-.06)
   f.box('shop_fascia','stone',x,3.97,pitch,.48,.48,-.005)
  else:
   width=1.37;r=width/2;spring=2.47
   for side in [-1,1]:f.box('ground_brick_pier','brick',x+side*(pitch+width)/4,2.125,(pitch-width)/2,4.25,.34,-.17)
   f.box('ground_brick_apron','brick',x,.30,width,.60,.34,-.17)
   f.box('arched_glass_lower','glass',x,(.60+spring)/2,width,spring-.60,.04,-.18)
   f.group('arched_glass_fan','glass').add([f.point(x,spring,-.18)]+[f.point(x+r*math.cos(k*math.pi/32),spring+r*math.sin(k*math.pi/32),-.18) for k in range(33)],[(0,k+1,k+2) for k in range(32)])
   for k in range(32):
    a,b=k*math.pi/32,(k+1)*math.pi/32
    f.group('arched_brick_head','brick').add([f.point(x+r*math.cos(a),spring+r*math.sin(a),0),f.point(x+r*math.cos(b),spring+r*math.sin(b),0),f.point(x+r*math.cos(b),4.25,0),f.point(x+r*math.cos(a),4.25,0)],[(0,1,2,3)])
   f.arch('stone_arch','stone',x,spring,r,.13,.08)
   for sign in [-1,1]:f.box('arched_window_jamb','frame',x+sign*r,(.60+spring)/2,.07,spring-.6,.13,-.015)
   for dx in [-.33,0,.33]:f.box('arched_window_bar','frame',x+dx,(.60+spring)/2,.028,spring-.6,.09,-.01)
   for z in [.60,1.21,1.84,2.47]:f.box('arched_window_rail','frame',x,z,width,.045,.11,.0)
   for k in range(1,6):
    a=k*math.pi/6
    end=Vector((r*.9*math.cos(a),r*.9*math.sin(a)))
    f.group('fanlight_radial','frame').add([f.point(x+dx,spring+dz,d) for d in [-.04,.035] for dx,dz in [(-.012,0),(.012,0),(end.x+.012,end.y),(end.x-.012,end.y)]],[(0,1,2,3),(4,7,6,5)])
   f.box('arched_window_sill','stone',x,.54,width+.20,.13,.39,.035)
 # Continuous cornice and closely spaced dentils under the roof edge.
 for z,h,depth in [(4.23,.12,.50),(15.22,.16,.42),(15.45,.17,.59),(15.66,.12,.75)]:f.box('cornice','stone',f.length/2,z,f.length,h,depth,.06)
 for j in range(round(f.length/.32)):f.box('cornice_dentil','stone',(j+.5)*f.length/round(f.length/.32),15.33,.13,.18,.40,.19)
 # Corners show alternating stone bands in the official street photographs.
 for x in [.20,f.length-.20]:
  for j in range(18):f.box('corner_quoin','stone',x,.50+j*.84,.44 if j%2 else .67,.24,.37,.03)
 for x in [.39,f.length-.39]:
  f.box('rainwater_pipe','metal',x,7.80,.065,15.2,.075,.28)
  for z in [1.5,4.5,8,12,15]:f.box('pipe_bracket','metal',x,z,.14,.04,.13,.23)

# An estimated shallow hipped roof retains the map footprint. Do not transplant
# the historical pediment until its position within the combined street block is proven.
center=Vector(profile['building']['center']);ring=profile['building']['rings'][0]
roof=Geometry('LAK','hipped_slate_roof','slate')
for a,b in zip(ring,ring[1:]+ring[:1]):
 ai=center+(Vector(a)-center)*.68;bi=center+(Vector(b)-center)*.68
 roof.add([(*a,15.72),(*b,15.72),(*bi,17.55),(*ai,17.55)],[(0,1,2,3)])
for triangle in profile['building']['triangles']:
 roof.add([(*(center+(Vector(p)-center)*.68),17.55) for p in triangle],[(0,1,2)])
groups['roof']=roof
# The street photograph supports dormer heads above the cornice; exact depths estimated.
for f,count in [(front,2),(plaza,4)]:
 for j in range(count):
  x=(j+.5)*f.length/count;d=-.55;z=16.30
  f.box('dormer_glass','glass',x,z,.74,.99,.04,d)
  for sign in [-1,1]:f.box('dormer_jamb','stone',x+sign*.43,z,.12,1.22,.65,d-.24)
  for zz in [z-.55,z+.55]:f.box('dormer_rail','frame',x,zz,.91,.10,.17,d+.045)
  f.box('dormer_mullion','frame',x,z,.035,1.1,.12,d+.045)
  for zz in [z-.22,z+.22]:f.box('dormer_glazing_bar','frame',x,zz,.83,.027,.10,d+.05)
  f.box('dormer_cap','slate',x,z+.65,1.14,.12,1.00,d-.26)
for geometry in groups.values():
 obj=geometry.finish()
 if 'arched_brick_head' in obj.name:
  for polygon in obj.data.polygons:
   for index in polygon.loop_indices:
    vertex=obj.data.vertices[obj.data.loops[index].vertex_index].co
    delta=Vector(vertex.xy)-Vector(plaza.wall['p'])
    obj.data.uv_layers.active.data[index].uv=(delta.dot(plaza.u),vertex.z)
 if 'stone_arch' in obj.name:
  for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
bpy.context.view_layer.update();assert protected_geometry()==before
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v13.blend'))
n=(front.n+plaza.n*.55).normalized()
record={'code':'LAK','exteriorDirection':[n.x,.40,-n.y],
 'scope':'Photograph-informed Portugal Street shopfront and John Watkins Plaza arched windows, sash divisions, quoins, cornice and roof study. Heights, bay counts, dormer positions and roof depth estimated. Historical pediment not assigned without firmer location evidence. No verified interior.',
 'reference':profile['reference'],'supportingReference':'data/建筑图片/LAK_Lakatos Building/01_建筑实拍/campus_photos_round3_LRB_LAK_geograph_668683.jpg',
 'protectedGeometrySha256':before,'components':sum(g.parts for g in groups.values()),
 'detailView':{'label':'窗饰细节','position':list(plaza.point(plaza.length*.50,5.0,10)),'target':list(plaza.point(plaza.length*.50,3.4,0)),'fov':45}}
(OUT/'lakatos-manifest.json').write_text(json.dumps({'buildings':[record]},indent=2)+'\n')
print('LAKATOS_REFINEMENT_COMPLETE',record,flush=True)
