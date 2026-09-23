"""Refine the photographed 1 Portsmouth Street corner bookshop exterior.
Run inside Blender. Retain the footprint; shop branding is historical photo context.
"""
from pathlib import Path
import array, hashlib, json, math, sys
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, Facade, materials
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage16/portsmouth';OUT.mkdir(parents=True,exist_ok=True)
profile=next(p for p in json.loads((ROOT/'result/blender/stage05/infill-geometry.json').read_text()) if p['code']=='POR')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v15.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
collection=bpy.data.collections['POR_EXTERIOR']
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
colors={'brick':(.25,.185,.12),'redbrick':(.34,.13,.055),'cream':(.63,.59,.47),'frame':(.65,.64,.53),'glass':(.095,.14,.145),'metal':(.065,.08,.069),'gold':(.47,.36,.14),'slate':(.16,.18,.17),'shadow':(.065,.065,.053)}
for name,color in colors.items():
 m=bpy.data.materials.new('POR14_'+name);m.use_nodes=True;m.diffuse_color=(*color,1)
 shader=m.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=m.diffuse_color;shader.inputs['Roughness'].default_value=.26 if name=='glass' else .76
 if name in {'brick','redbrick'}:
  nodes,links=m.node_tree.nodes,m.node_tree.links;uv=nodes.new('ShaderNodeTexCoord');brick=nodes.new('ShaderNodeTexBrick')
  for key,value in [('Scale',1),('Brick Width',.225),('Row Height',.078),('Mortar Size',.005)]:brick.inputs[key].default_value=value
  brick.inputs['Color1'].default_value=(*color,1);brick.inputs['Color2'].default_value=(*(v*.81 for v in color),1);brick.inputs['Mortar'].default_value=(.22,.20,.15,1)
  links.new(uv.outputs['UV'],brick.inputs['Vector']);links.new(brick.outputs['Color'],shader.inputs['Base Color'])
 materials[name]=m
groups={};facades=[Facade(profile,w,groups) for w in profile['walls']];corner=facades[0]

def sash(f,x,pitch,width,low,high,z0,z1):
 for sign in [-1,1]:f.box('upper_brick_pier','brick',x+sign*(pitch+width)/4,(low+high)/2,(pitch-width)/2,high-low,.34,-.17)
 for a,b in [(z0,low),(high,z1)]:f.box('upper_brick_spandrel','brick',x,(a+b)/2,pitch,b-a,.34,-.17)
 f.box('sash_glass','glass',x,(low+high)/2,width,high-low,.04,-.17)
 for sign in [-1,1]:
  f.box('window_surround','cream',x+sign*(width+.10)/2,(low+high)/2,.11,high-low+.20,.21,-.008)
  f.box('sash_jamb','frame',x+sign*width/2,(low+high)/2,.056,high-low,.12,.025)
 for z in [low,high,(low+high)/2]:f.box('sash_rail','frame',x,z,width,.065,.13,.038)
 for dx in [-width/6,width/6]:f.box('fine_glazing_bar','frame',x+dx,(low+high)/2,.023,high-low,.075,.067)
 for fraction in [.25,.75]:f.box('fine_glazing_bar','frame',x,low+(high-low)*fraction,width,.023,.075,.067)
 f.box('window_head','cream',x,high+.07,width+.30,.14,.26,.014)
 f.box('projecting_sill','cream',x,low-.08,width+.33,.16,.40,.055)

for i,f in enumerate(facades):
 if f.wall['party']:
  f.box('party_envelope','brick',f.length/2,7.15,f.length,14.3);continue
 bays=1 if i in {0,6} else 2
 pitch=f.length/bays
 for low,high,z0,z1 in [(4.83,7.18,4.45,7.72),(8.20,10.58,7.72,11.12),(11.62,13.55,11.12,14.30)]:
  for j in range(bays):sash(f,(j+.5)*pitch,pitch,min(1.34,pitch*.58),low,high,z0,z1)
 # Warm red brick strips define the edges of the chamfer and window bays.
 for x in [.095,f.length-.095]:f.box('red_corner_strip','redbrick',x,9.38,.19,9.85,.36,-.145)
 if i==0:continue
 # Ground shop windows with leaded upper lights and a deep grille beneath the display.
 for j in range(bays):
  x=(j+.5)*pitch;width=pitch-.42
  for side in [-1,1]:f.box('shop_stone_pier','cream',x+side*pitch/2,2.17,.34,4.34,.52,-.065)
  f.box('shop_display_glass','glass',x,2.02,width,2.82,.045,-.16)
  for dx in [-width/2,0,width/2]:f.box('shop_frame','frame',x+dx,2.02,.07,2.82,.16,-.025)
  for z in [.61,2.82,3.42]:f.box('shop_frame','frame',x,z,width,.09,.17,-.01)
  for k in range(max(2,round(width/.22))):
   xx=x-width/2+(k+.5)*width/max(2,round(width/.22))
   f.box('fanlight_lead','metal',xx,3.12,.018,.53,.045,.035)
  for z in [2.99,3.18]:f.box('fanlight_lead','metal',x,z,width,.019,.045,.035)
  f.box('grille_recess','shadow',x,.34,width,.53,.05,-.10)
  for k in range(max(3,round(width/.18))):f.box('lower_grille_bar','metal',x-width/2+(k+.5)*width/max(3,round(width/.18)),.34,.03,.52,.07,.025)
  f.box('lower_grille_rail','metal',x,.35,width,.03,.07,.031)
  f.box('shop_sill','cream',x,.66,width+.11,.12,.43,.10)
  f.box('shop_plinth','metal',x,.055,pitch,.11,.40,.03)
 f.box('shop_sign_surround','cream',f.length/2,3.91,f.length,.84,.39,.06)
 f.box('shop_name_panel','metal',f.length/2,3.91,f.length-.45,.44,.05,.276)
 f.label('ALPHA BOOKS',f.length/2,3.79,min(.26,f.length/22),'gold',.31)
 for z,h,d in [(4.34,.13,.47),(4.47,.11,.62),(4.57,.09,.73)]:f.box('shop_cornice','cream',f.length/2,z,f.length,h,d,.06)
 # Metal gutter pipes are separate from the masonry, with visible fixing collars.
 f.box('rain_pipe','metal',f.length-.16,9.5,.065,9.3,.08,.24)
 for z in [5,8,11,13.8]:f.box('pipe_clip','metal',f.length-.16,z,.14,.035,.13,.20)
 # Low coping retains the source's mostly concealed roof.
 f.box('roof_parapet','brick',f.length/2,14.57,f.length,.54,.32,-.14)
 f.box('roof_coping','slate',f.length/2,14.88,f.length,.12,.48,-.10)

# Chamfered corner entrance and the projecting box above it.
x=corner.length/2
for side in [-1,1]:corner.box('corner_entry_pier','cream',x+side*.80,1.95,.60,3.90,.51,-.055)
corner.box('corner_entry_back','metal',x,1.48,1.04,2.91,.055,-.23)
for side in [-1,1]:corner.box('corner_door_surround','frame',x+side*.57,1.52,.14,3.03,.18,-.035)
corner.box('corner_door_lintel','frame',x,3.06,1.29,.15,.20,-.025)
corner.box('door_pull','gold',x-.35,1.32,.035,.39,.07,-.13)
corner.box('door_kickplate','shadow',x,.16,1.0,.25,.04,-.19)
corner.box('entry_step','cream',x,.035,1.54,.07,.55,.09)
corner.box('corner_wall_overdoor','cream',x,3.59,corner.length,.95,.48,-.025)
corner.label('α',x,3.45,.40,'metal',.24)
# Projected fascia volume supported by a shallow taper, rather than a floating box.
corner.box('corner_fascia_box','cream',x,4.50,corner.length+.10,1.0,.99,.25)
corner.group('tapered_fascia_support','cream').add([corner.point(xx,z,d) for z,w,d in [(3.72,corner.length-.44,.20),(4.00,corner.length+.10,.73)] for xx in [x-w/2,x+w/2]],[(0,1,3,2)])
for side in [-1,1]:
 corner.group('fascia_side_support','cream').add([corner.point(x+side*(corner.length-.44)/2,3.72,-.20),corner.point(x+side*(corner.length-.44)/2,3.72,.20),corner.point(x+side*(corner.length+.10)/2,4.00,.73),corner.point(x+side*(corner.length+.10)/2,4.00,-.20)],[(0,1,2,3)])
corner.box('corner_fascia_cap','cream',x,5.03,corner.length+.18,.11,1.09,.25)
corner.box('corner_roof_parapet','brick',x,14.57,corner.length,.54,.32,-.14)
corner.box('corner_roof_coping','slate',x,14.88,corner.length+.10,.12,.49,-.10)
# Street plaques sit on the flanking faces rather than across the entrance.
for index,label,xx in [(1,'PORTSMOUTH',.61),(6,'SHEFFIELD',facades[6].length-.67)]:
 f=facades[index]
 f.box('street_name_plate','cream',xx,5.05,1.12,.43,.055,.065)
 f.label(label,xx,5.06,.096,'metal',.101)
 f.label('STREET WC2',xx,4.91,.073,'metal',.101)
# One subdued roof plane and two stacks; rooftop rails follow visible edge photographs.
roof=Geometry('POR','concealed_roof','slate')
for triangle in profile['building']['triangles']:roof.add([(*p,14.33) for p in triangle],[(0,1,2)])
groups['roof']=roof
for i in [1,5]:
 f=facades[i]
 for xx in [.75,f.length-.75]:
  f.box('brick_stack','brick',xx,15.09,.42,1.54,.54,-.40)
  f.box('stack_coping','slate',xx,15.9,.53,.10,.65,-.40)
 for j in range(max(2,round(f.length/.95))+1):f.box('roof_guard_post','metal',j*f.length/max(2,round(f.length/.95)),15.22,.035,.62,.035,-.13)
 f.box('roof_guard_top','metal',f.length/2,15.52,f.length,.045,.045,-.13)
for geometry in groups.values():geometry.finish()
bpy.context.view_layer.update();assert protected_geometry()==before
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_portsmouth_v16.blend'))
n=corner.n.normalized()
record={'code':'POR','exteriorDirection':[n.x,.40,-n.y],
 'scope':'Photo-informed chamfered corner entrance, projecting fascia, historical bookshop fronts, sash windows, street plaques and roof edge. Footprint retained; heights, openings, hidden roof and ornamental dimensions estimated. Branding reflects the archived photograph, not verified current tenancy.',
 'reference':profile['reference'],'protectedGeometrySha256':before,'components':sum(g.parts for g in groups.values()),
 'detailView':{'label':'转角细节','position':list(corner.point(x,3.80,10)),'target':list(corner.point(x,2.65,0)),'fov':45}}
(OUT/'portsmouth-manifest.json').write_text(json.dumps({'buildings':[record]},indent=2)+'\n')
print('PORTSMOUTH_REFINEMENT_COMPLETE',record,flush=True)
