"""Replace four known street-level simplifications in the v19 campus study.
Run in Blender. No survey accuracy is claimed; archived photos establish forms.
All replaced objects are explicit transfer entries, with untouched components copied.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import sys
import bpy
import bmesh
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, Facade, materials
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage20/exteriors';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v19.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.view_layer.update()
profiles={p['code']:p for p in json.loads((ROOT/'result/blender/stage05/infill-geometry.json').read_text())}
refs={r['code']:r['reference'] for r in json.loads((ROOT/'result/blender/stage16/review/references.json').read_text())}
originals=list(bpy.data.objects);replaced={c:[] for c in ['KSW','50L','51L','SAR']};added={c:[] for c in replaced};groups={c:{} for c in replaced}

def digest(objects):
 h=hashlib.sha256()
 for o in sorted(objects,key=lambda o:o.name):
  h.update(o.name.encode());h.update(array.array('f',[x for row in o.matrix_world for x in row]).tobytes())
  if o.type=='MESH':
   a=array.array('f',[0])*(len(o.data.vertices)*3);o.data.vertices.foreach_get('co',a);h.update(a.tobytes())
 return h.hexdigest()
protected=[o for o in originals if not any(c.name in [code+'_EXTERIOR' for code in replaced] for c in o.users_collection)]
protected_before=digest(protected)
colors={'stone':(.60,.56,.46),'pale':(.72,.69,.60),'brick':(.36,.115,.062),'darkbrick':(.20,.057,.035),'glass':(.075,.135,.15),'metal':(.038,.051,.047),'wood':(.22,.115,.05),'bronze':(.48,.32,.10),'joint':(.32,.30,.26)}
for key,color in colors.items():
 m=bpy.data.materials.new('EXT20_'+key);m.use_nodes=True;m.diffuse_color=(*color,1);s=m.node_tree.nodes['Principled BSDF'];s.inputs['Base Color'].default_value=m.diffuse_color;s.inputs['Roughness'].default_value=.30 if key in ['glass','bronze'] else .73
 if key in ['brick','darkbrick']:
  ns=m.node_tree.nodes;links=m.node_tree.links;uv=ns.new('ShaderNodeTexCoord');t=ns.new('ShaderNodeTexBrick');t.inputs['Scale'].default_value=1;t.inputs['Brick Width'].default_value=.225;t.inputs['Row Height'].default_value=.078;t.inputs['Mortar Size'].default_value=.003
  t.inputs['Color1'].default_value=(*color,1);t.inputs['Color2'].default_value=(*(x*.8 for x in color),1);t.inputs['Mortar'].default_value=(.21,.18,.13,1);links.new(uv.outputs['UV'],t.inputs['Vector']);links.new(t.outputs['Color'],s.inputs['Base Color'])
 materials[key]=m

def facade(code,index=None):
 p=profiles[code];w=next(w for w in p['walls'] if w['index']==index) if index is not None else next(w for w in p['walls'] if w['front'])
 return Facade(p,w,groups[code])

def components(o):
 mesh=o.data;parent=list(range(len(mesh.vertices)))
 def find(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 for e in mesh.edges:
  a,b=map(find,e.vertices);parent[a]=b
 buckets={}
 for v in mesh.vertices:buckets.setdefault(find(v.index),[]).append(v.index)
 return buckets.values()

def replace_parts(code,predicate,whole_names=()):
 """Remove disconnected old solids locally, retaining other elevations and floors."""
 for o in list(bpy.data.collections[code+'_EXTERIOR'].objects):
  if o.name.startswith(code+'_V20_EXT_'):continue
  whole=o.name in whole_names
  selected=[]
  if not whole and o.type=='MESH':
   for ids in components(o):
    points=[o.matrix_world@o.data.vertices[i].co for i in ids]
    if predicate(o,points):selected.extend(ids)
  if not whole and not selected:continue
  oldname=o.name;replaced[code].append(oldname)
  if not whole and len(selected)<len(o.data.vertices):
   copy=o.copy();copy.data=o.data.copy();copy.name=code+'_V20_EXT_retained_'+oldname.removeprefix(code+'_')
   bm=bmesh.new();bm.from_mesh(copy.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.verts[i] for i in selected],context='VERTS');bm.to_mesh(copy.data);bm.free()
   bpy.data.collections[code+'_EXTERIOR'].objects.link(copy);added[code].append(copy)
  bpy.data.objects.remove(o,do_unlink=True)

def local_bounds(f,points):
 xy=[Vector((p.x,p.y))-Vector(f.wall['p']) for p in points]
 return min(p.dot(f.u) for p in xy),max(p.dot(f.u) for p in xy),min(p.dot(f.n) for p in xy),max(p.dot(f.n) for p in xy),min(p.z for p in points),max(p.z for p in points)

def curve(f,family,mat,points,radius=.025):
 g=f.group(family,mat);verts=[]
 pts=[Vector(f.point(*p)) for p in points]
 for i,p in enumerate(pts):
  tangent=(pts[min(i+1,len(pts)-1)]-pts[max(0,i-1)]).normalized();a=tangent.cross(Vector((0,0,1)))
  if a.length<.001:a=tangent.cross(Vector((1,0,0)))
  a.normalize();b=tangent.cross(a).normalized()
  verts.extend(tuple(p+radius*(a*math.cos(j*math.tau/8)+b*math.sin(j*math.tau/8))) for j in range(8))
 g.add(verts,[(i*8+j,i*8+(j+1)%8,(i+1)*8+(j+1)%8,(i+1)*8+j) for i in range(len(pts)-1) for j in range(8)])

def fan(f,x,z,r,mat='glass',depth=-.16):
 points=[f.point(x,z,depth)]+[f.point(x+r*math.cos(i*math.pi/40),z+r*math.sin(i*math.pi/40),depth) for i in range(41)]
 f.group('arched_fanlight',mat).add(points,[(0,i+1,i+2) for i in range(40)])

def arch_wall(f,x,width,spring,top,pitch,mat):
 r=width/2
 for side in [-1,1]:f.box('solid_opening_piers',mat,x+side*(pitch+width)/4,top/2,(pitch-width)/2,top,.34,-.16)
 outline=[(x-r,top),(x+r,top)]+[(x+r*math.cos(i*math.pi/40),spring+r*math.sin(i*math.pi/40)) for i in range(41)]
 n=len(outline);verts=[f.point(xx,zz,d) for d in [-.33,.01] for xx,zz in outline]
 f.group('curved_opening_spandrel',mat).add(verts,[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)])

def window(f,x,width,spring,top,pitch,mat,grille=False):
 low=.34;r=width/2
 arch_wall(f,x,width,spring,top,pitch,mat)
 f.box('window_base',mat,x,low/2,width,low,.34,-.16)
 f.box('recessed_window_glass','glass',x,(spring+low)/2,width,spring-low,.035,-.18);fan(f,x,spring,r)
 f.arch('arched_window_frame','metal',x,spring,r-.035,.052,.025)
 for side in [-1,1]:f.box('window_frame','metal',x+side*(r-.025),(spring+low)/2,.052,spring-low,.12,-.025)
 for z in [low,spring,1.13,1.87]:
  if z<spring+.01:f.box('window_transom','metal',x,z,width,.044,.10,-.015)
 f.box('window_mullion','metal',x,(low+spring+r)/2,.035,spring+r-low,.09,.01)
 for side in [-1,1]:
  xx=x+side*width*.25
  hi=spring+math.sqrt(r*r-(width*.25)**2)
  f.box('window_fine_bar','metal',xx,(low+hi)/2,.025,hi-low,.08,.025)
 if grille:
  for j in range(9):f.box('lower_iron_grille','metal',x-width*.46+j*width*.92/8,.72,.025,.85,.04,.14)
  for z in [.30,1.10]:f.box('lower_grille_rail','metal',x,z,width,.045,.065,.14)

# 50L: remove the brick plug above the rectangular door and build a real fanlight.
p=next(p for p in json.loads((ROOT/'result/blender/stage08/coopers-geometry.json').read_text())['profiles'] if p['code']=='50L')
a,b=map(Vector,[p['ring'][5],p['ring'][0]]);u=(b-a).normalized();n=Vector((u.y,-u.x))
if n.dot((a+b)/2-Vector(p['center']))<0:n=-n
f50=Facade(p,{'p':a,'q':b,'length':(b-a).length,'outward':n},groups['50L']);count=max(2,round(f50.length/2.8));pitch=f50.length/count;x50=(count-.5)*pitch;w50=min(1.55,pitch*.72)
def fifty(o,points):
 a,b,d,e,lo,hi=local_bounds(f50,points)
 return 'masonry_above' in o.name and abs((a+b)/2-x50)<.05 and lo<3.0 and hi<3.9
replace_parts('50L',fifty,['50L_D5_door_wood','50L_D5_window_frame_stone','50L_D5_sash_rail_wood'])
f50.box('aligned_timber_door','wood',x50,1.39,w50,2.62,.04,-.17)
for side in [-1,1]:f50.box('aligned_door_jamb','stone',x50+side*w50/2,1.39,.085,2.62,.16,-.01)
for z in [.08,1.39,2.70]:f50.box('aligned_door_rail','wood',x50,z,w50,.06,.13,-.01)
spring=2.70;r=w50/2
# Full width bay spandrel is restored only outside the new opening.
for side in [-1,1]:f50.box('fanlight_side_spandrel','stone',x50+side*(pitch+w50)/4,(2.80+3.80)/2,(pitch-w50)/2,1.0,.30,-.12)
for i in range(40):
 xx=x50-r+(i+.5)*w50/40;bottom=spring+math.sqrt(max(0,r*r-(xx-x50)**2))
 f50.box('fanlight_curved_spandrel','stone',xx,(bottom+3.80)/2,w50/40+.002,3.80-bottom,.30,-.12)
fan(f50,x50,spring,r,'glass',-.15)
f50.arch('inner_fanlight_bead','wood',x50,spring,r-.035,.038,-.02)
f50.box('fanlight_transom','wood',x50,spring,w50,.065,.12,-.015)
for angle in [math.pi/4,math.pi/2,3*math.pi/4]:curve(f50,'fanlight_radial_bar','bronze',[(x50,spring,-.03),(x50+(r-.06)*math.cos(angle),spring+(r-.06)*math.sin(angle),-.03)],.014)

# SAR: replace the entire front street-storey rectangular system, keeping upper floors.
fs=facade('SAR');height=profiles['SAR']['height']/profiles['SAR']['floors'];count=max(1,round(fs.length/profiles['SAR']['pitch']));pitch=fs.length/count
old_entry=[o.name for o in bpy.data.collections['SAR_EXTERIOR'].objects if any(s in o.name for s in ['entrance_','door_','threshold','name_board']) or o.type=='FONT']
def sardinia(o,points):
 a,b,d,e,lo,hi=local_bounds(fs,points)
 return abs((d+e)/2)<.5 and -.05<(a+b)/2<fs.length+.05 and hi<height+.005
replace_parts('SAR',sardinia,old_entry)
for j in range(count):
 x=(j+.5)*pitch;width=pitch*.61;spring=2.55
 if j==count-2:
  arch_wall(fs,x,width,spring,height-.02,pitch,'brick');fs.box('entry_door','wood',x,1.36,width,2.64,.065,-.17);fan(fs,x,spring,width/2)
  for sign in [-1,1]:
   fs.box('door_glazing','glass',x+sign*width*.235,1.70,width*.39,1.30,.035,-.12)
   fs.box('door_pull','bronze',x+sign*.10,1.17,.03,.34,.10,.015)
  fs.box('entry_canopy','stone',x,3.30,width+.65,.13,1.05,.42)
  for sign in [-1,1]:fs.box('door_stone_jamb','stone',x+sign*(width/2+.09),1.58,.18,3.15,.40,-.035)
 else:window(fs,x,width,spring,height-.02,pitch,'brick',True)
 # Recessed rustication is applied to piers only, not over glazing.
 for z in [.35,.78,1.21,1.64,2.07,2.50,2.93,3.36]:
  for side in [-1,1]:fs.box('pier_rustication','darkbrick',x+side*(pitch+width)/4,z,(pitch-width)/2-.025,.018,.020,.025)
fs.box('street_base','metal',fs.length/2,.08,fs.length,.16,.39,-.04)

# 51L: move the false middle-of-wall entrance into the actual chamfered corner.
faces51=[facade('51L',i) for i in [1,2,3]];floor51=profiles['51L']['height']/profiles['51L']['floors']
old_entry=[o.name for o in bpy.data.collections['51L_EXTERIOR'].objects if any(s in o.name for s in ['entrance_','door_','threshold','arched_portal','portal_','name_board']) or o.type=='FONT']
def lincolns(o,points):
 if 'cornices' in o.name:
  a,b,d,e,lo,hi=local_bounds(faces51[1],points)
  return abs((d+e)/2)<.5 and .1<(a+b)/2<faces51[1].length-.1 and hi<floor51+.15
 if max(p.z for p in points)>floor51+.005:return False
 for f in faces51:
  a,b,d,e,lo,hi=local_bounds(f,points)
  if abs((d+e)/2)<.50 and -.1<(a+b)/2<f.length+.1:return True
 return False
replace_parts('51L',lincolns,old_entry)
for f in [faces51[0],faces51[2]]:
 count=max(1,round(f.length/profiles['51L']['pitch']));pitch=f.length/count
 for j in range(count):
  x=(j+.5)*pitch;window(f,x,pitch*.58,2.30,floor51-.02,pitch,'pale')
  # Radial stone arch voussoirs, with narrow bed joints.
  r=pitch*.29
  for i in range(13):
   a=(i+.035)*math.pi/13;b=(i+.965)*math.pi/13
   f.group('stone_arch_voussoirs','stone').add([f.point(x+rr*math.cos(t),2.30+rr*math.sin(t),dep) for dep in [.015,.13] for rr,t in [(r,a),(r,b),(r+.22,b),(r+.22,a)]],[(0,1,2,3),(4,7,6,5),(0,4,5,1),(3,2,6,7),(1,5,6,2),(0,3,7,4)])
  for z in [.37,.81,1.25,1.69,2.13,2.57,3.01]:
   for side in [-1,1]:f.box('stone_bed_joints','joint',x+side*(pitch+pitch*.58)/4,z,pitch*.21-.025,.015,.012,.018)
corner=faces51[1];xc=corner.length/2;doorw=1.45
for side in [-1,1]:
 corner.box('corner_portal_pier','stone',xc+side*(doorw/2+.20),1.52,.40,3.04,.47,-.03)
 corner.box('portal_pilaster','pale',xc+side*(doorw/2+.20),1.62,.23,2.55,.14,.22)
 corner.box('portal_capital','pale',xc+side*(doorw/2+.20),2.92,.46,.17,.59,.06)
 corner.box('portal_base','pale',xc+side*(doorw/2+.20),.20,.45,.30,.57,.06)
corner.box('door_recess','metal',xc,1.47,doorw,2.94,.045,-.24)
for side in [-1,1]:
 xx=xc+side*doorw/4;corner.box('oak_door_leaf','wood',xx,1.43,doorw*.48,2.72,.09,-.17)
 corner.box('door_glazed_panel','glass',xx,1.94,doorw*.34,1.19,.022,-.111)
 corner.box('door_lower_panel','wood',xx,.67,doorw*.34,.83,.035,-.10)
 for dx in [-doorw*.17,doorw*.17]:corner.box('door_panel_reed','bronze',xx+dx,.67,.020,.84,.028,-.075)
 corner.box('door_handle','bronze',xc+side*.095,1.20,.030,.36,.08,-.045)
corner.box('portal_entablature','stone',xc,3.13,corner.length+.18,.32,.56,.035)
# Broken segmental pediment, flat tympanum and scroll consoles from corner photograph.
corner.box('pediment_tympanum','stone',xc,3.44,1.57,.52,.29,-.10)
for side in [-1,1]:
 curve(corner,'segmental_pediment','pale',[(xc+side*1.12*math.cos(a),3.12+.80*math.sin(a),.13) for a in [(.08+.40*i/30)*math.pi for i in range(31)]],.075)
 curve(corner,'pediment_scroll','pale',[(xc+side*(.99+.14*math.exp(-t*.20)*math.cos(t)),3.25+.14*math.exp(-t*.20)*math.sin(t),.20) for t in [i*math.pi/12 for i in range(37)]],.043)
corner.box('pediment_keystone','pale',xc,3.43,.22,.64,.44,.05)
corner.box('stone_threshold','stone',xc,.075,doorw+.25,.15,.72,.12)

# KSW: close the artificial portal gaps and replace sphere-based carving with shallow scrollwork.
path=json.loads((ROOT/'result/blender/stage03/clm_ksw/build_report.json').read_text())['geometry']['KSW']['frontage_path'];a,b=map(Vector,path);u=(b-a).normalized();n=Vector((-u.y,u.x))
fk=Facade({'code':'KSW'},{'p':a,'q':b,'length':(b-a).length,'outward':n},groups['KSW']);xk=fk.length/2
names=['KSW_D3_entrance_rusticated_quoins','KSW_D3_door_portal_entablature','KSW_D3_portal_dropped_keystone','KSW_D3_portal_oval_cartouche','KSW_D3_portal_leaf_relief']
replace_parts('KSW',lambda o,p:False,names)
# Pier cores guarantee no daylight through joints; face blocks use 15mm recesses.
for side in [-1,1]:
 xx=xk+side*1.14
 fk.box('portal_continuous_pier','stone',xx,1.92,.52,3.56,.40,.065)
 for j in range(8):fk.box('portal_ashlar_course','pale',xx,.36+j*.445,.56 if j%2 else .64,.430,.49,.10)
 fk.box('pier_moulded_base','pale',xx,.27,.72,.20,.60,.10)
 fk.box('pier_capital','pale',xx,3.63,.79,.17,.65,.11)
for z,w,h,dep in [(3.78,3.10,.18,.65),(3.93,3.26,.12,.74),(4.12,3.18,.25,.42),(4.31,3.43,.10,.77)]:fk.box('continuous_entablature','pale',xk,z,w,h,dep,.10)
fk.box('portal_inner_lintel','stone',xk,3.58,1.93,.20,.39,.02)
# Tapered stone key with coherent profile, not separated floating blocks.
g=fk.group('dropped_keystone','stone');poly=[(-.20,3.59),(.20,3.59),(.31,4.31),(-.31,4.31)]
g.add([fk.point(xk+x,z,d) for d in [.12,.43] for x,z in poly],[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)])
fk.box('frieze_continuous_backing','stone',xk,4.64,3.25,.92,.30,-.15)
fk.box('carved_frieze_backing','stone',xk,4.52,2.68,.43,.23,.035)
# Elliptical, shallow cartouche with concentric moulded edge.
for scale,radius in [(1,.035),(.78,.018)]:curve(fk,'cartouche_moulding','pale',[(xk+.22*scale*math.cos(t),4.54+.25*scale*math.sin(t),.205) for t in [i*math.tau/48 for i in range(49)]],radius)
for side in [-1,1]:
 curve(fk,'foliate_scroll','pale',[(xk+side*(.36+.70*t),4.49+.14*math.sin(t*math.pi),.20) for t in [i/32 for i in range(33)]],.045)
 for j in range(5):
  xx=xk+side*(.44+j*.135);zz=4.50+.12*math.sin((j+.5)*math.pi/6)
  # Individual tapered leaf-shaped reliefs, with a central vein.
  verts=[fk.point(xx,zz,.20),fk.point(xx+side*.15,zz+.14,.22),fk.point(xx+side*.24,zz+.12,.20),fk.point(xx+side*.11,zz-.035,.24)]
  fk.group('carved_leaf_relief','pale').add(verts,[(0,1,3),(1,2,3)])

# Material-family batches make an explicit, small transfer list.
for code in groups:
 for family,g in groups[code].items():
  g.name=code+'_V20_EXT_'+family;o=g.finish();
  if 'curved_opening_spandrel' in family:o.modifiers.clear()
  o['scope']='Archive-informed street geometry; dimensions estimated';added[code].append(o)
 bpy.context.view_layer.update()
 for o in added[code]:assert len(o.data.vertices)>0 and all(math.isfinite(v) for p in o.data.vertices for v in p.co)
assert digest(protected)==protected_before

# Dedicated rendered views show true openings and relocated entrance in context.
views=[('50L',f50,x50,2.0,7.0),('SAR',fs,fs.length/2,2.7,fs.length*.9),('51L',corner,xc,2.5,7.5),('KSW',fk,xk,2.6,9.0)]
for code,f,x,z,dist in views:
 scene=bpy.data.scenes.new(code+'_V20_EXT_REVIEW');scene.collection.children.link(bpy.data.collections[code+'_EXTERIOR'])
 world=bpy.data.worlds.new(code+'_V20_EXT_WORLD');world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.68,.73,.8,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65;scene.world=world
 camera=bpy.data.objects.new(code+'_V20_EXT_CAMERA',bpy.data.cameras.new(code+'_V20_EXT_CAMERA'));scene.collection.objects.link(camera);scene.camera=camera
 target=Vector(f.point(x,z,0));camera.location=f.point(x+.55,z+1.0,dist);camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.lens=43
 light=bpy.data.objects.new(code+'_V20_EXT_LIGHT',bpy.data.lights.new(code+'_V20_EXT_LIGHT','AREA'));scene.collection.objects.link(light);light.location=f.point(x-3,9,5);light.rotation_euler=(target-light.location).to_track_quat('-Z','Y').to_euler();light.data.energy=1500;light.data.size=7
 scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True;scene.render.resolution_x=1400;scene.render.resolution_y=1050;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/(code.lower()+'-street.png'));bpy.context.window.scene=scene;bpy.context.view_layer.update()
 assert all(o.visible_get() and not o.hide_render for o in added[code]);bpy.ops.render.render(write_still=True)

changes={'50L':['Removed the solid brick plug over the doorway.','Constructed an actual semicircular fanlight, curved spandrel and radial bars.'], '51L':['Removed the false doorway from the middle of the front wall.','Rebuilt street-level stone arches on both exposed street elevations.','Built timber doors and a broken segmental pediment on the existing GIS chamfer.'], 'SAR':['Replaced front street-storey rectangular openings with recessed arched windows.','Added lower iron grilles, rusticated brick piers and a recessed side entrance.'], 'KSW':['Replaced separated entrance blocks with continuous pier cores and narrow-joint ashlar.','Rebuilt coherent entablature and tapered keystone.','Replaced coarse spherical ornaments with shallow cartouche mouldings and foliate scroll relief.']}
limitations={'50L':'Dimensions and exact decorative profiles are estimated; upper/rear fabric is unchanged.', '51L':'GIS chamfer fixes location, but portal height, arch widths and carved relief remain photo-informed estimates.', 'SAR':'Oblique photograph establishes arched street character; repeated bay count, entrance placement and exact dimensions remain estimates.', 'KSW':'Carved relief is a geometric interpretation rather than a scan. Other original upper-storey and rear approximations remain.'}
records=[{'code':c,'status':'rebuilt-street-form','changes':changes[c],'sources':[refs[c]],'limitations':[limitations[c],'No full interior or surveyed as-built claim.'],'addedObjects':[{'name':o.name,'collection':c+'_EXTERIOR'} for o in added[c]],'replacedObjects':replaced[c],'replacementReasons':{name:('Rebuilt portal solids and relief to remove open joints.' if c=='KSW' else 'Removed door-head blockage and aligned door joinery with the arch spring.' if c=='50L' else 'Removed old generic entry or street-level rectangular component; retained unaffected components in a renamed copy.') for name in replaced[c]}} for c in replaced]
for code,f,x,z,dist in views:
 record=next(r for r in records if r['code']==code)
 record['reviewCamera']={'position':list(f.point(x+.55,z+1.0,dist)),'target':list(f.point(x,z,0)),'lensMm':43}
 record['reviewRender']='result/blender/stage20/exteriors/'+code.lower()+'-street.png'
 record['detailView']={'label':'拱窗细节' if code=='SAR' else '入口细节','position':list(f.point(x+.55,z+1.0,dist)),'target':list(f.point(x,z,0)),'fov':50}
# Exterior contact-sheet audit: these are explicit outstanding limits, not completion claims.
audit={
 '61A':'Provisional tenancy attribution; tower silhouette and roof composition remain simplified.',
 '35L':'Indicative construction boundary only; archive photographs cannot establish the current workstage.',
 'CKK':'Existing external glazing and stone bays retained; no exterior gallery view was available for independent pixel inspection.',
 'LRB':'Existing external glazing retained; no exterior gallery view was available for independent pixel inspection.',
 'MAR':'Recent entrance work retained; roof massing and unobserved elevations remain simplified.',
 'SAW':'Folded brick screen and entry structure retained; roof equipment and opaque window appearance remain approximate.',
 'CBG':'Curtain wall, fins and atrium retained; unseen roof equipment and detailed glazing properties remain approximate.',
 'OLD':'Entrance and dormers retained; large rear roof volumes and relief sculpture remain simplified.',
 'SAL':'Street gables and lanterns retained; rear roofs and exact carved ornament remain unverified.',
 'CLM':'Street colonnade and portal retained; roof depth and rear elevations remain estimates.',
 'CON':'Portal retained; repeated upper bays and rear courtyard roof remain estimates.',
 'COL':'Corner and street portals retained; mansard and upper repetition remain estimates.',
 'COW':'Dormers, chimneys and chamfered entrance retained; unseen party roof geometry is estimated.',
 'KGS':'Canted bays and lead dome retained; broad roof deck and side elevation are estimated.',
 'LAK':'Street bays and dormers retained; dormer scale and unobserved roofing remain estimates.',
 'LCH':'Detailed entrance retained; large blank rear roof mass remains simplified.',
 '49L':'Shutters and corner canopy retained; roof deck and unseen elevations remain estimates.',
 '5LF':'Street frontage retained; roof is an estimated plane behind its visible parapets.',
 'PAR':'Photographed gable and roof composition retained; rear spaces remain unverified.',
 'POR':'Chamfered shopfront retained; upper and rear geometry remains approximate.',
 'SHF':'Simple repeated frontage retained; oblique photographic coverage is insufficient for full elevation reconstruction.',
 'PEA':'Canopy retained; upper window rhythm and broad roof remain approximate.',
 'PEL':'Curved envelope retained; exact panel dimensions and rooftop detail remain unverified.',
 'PAN':'Ribbon glazing and entrance retained; repeated upper bands and roof details remain estimates.',
 'FAW':'Ribbon glazing and entrance retained; repeated upper bands and roof details remain estimates.',
 'STC':'Detailed street entry retained; roof deck and unobserved rear elevations remain approximate.'}
# No unsupported edits are made to the other codes.
for code in refs:
 if code in replaced:continue
 records.append({'code':code,'status':'reviewed-existing-scope','changes':[],'sources':[refs[code]],'limitations':[audit.get(code,'Existing exterior study retained; unseen elevations and dimensions remain estimates.'),'No full interior or surveyed as-built claim.'],'addedObjects':[],'replacedObjects':[]})
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];assert digest(protected)==protected_before
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'refined.blend'))
(OUT/'manifest.json').write_text(json.dumps({'baseline':'result/blender/LSE_campus_detailed_v19.blend','protectedGeometryUnchanged':True,'protectedGeometrySha256':protected_before,'buildings':records},indent=2)+'\n')
print('EXTERIOR_REBUILD_COMPLETE',[(c,len(replaced[c]),len(added[c])) for c in replaced],flush=True)
