"""Refine SAR's photographed street facade from the saved campus.
Run in Blender Text Editor. Openings, floor levels and footprint remain estimates;
stone surrounds, segmental hoods, school fascia and red brick are photo-guided.
"""
from pathlib import Path
import array,hashlib,json,math,shutil,sys
import bpy,bmesh
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage102';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,Facade,materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v101.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
profile=next(p for p in json.loads((ROOT/'result/blender/stage05/infill-geometry.json').read_text()) if p['code']=='SAR')
facade=Facade(profile,profile['walls'][profile['front']],{})
collection=bpy.data.collections['SAR_EXTERIOR'];height=profile['height']/profile['floors'];count=round(facade.length/profile['pitch']);pitch=facade.length/count;width=pitch*.58
u=Vector((*facade.u,0));n=Vector((*facade.n,0))
def fingerprint(o):
 h=hashlib.sha256(str([list(r) for r in o.matrix_world]).encode())
 if o.type=='MESH':
  h.update(array.array('f',[c for v in o.data.vertices for c in v.co]).tobytes());h.update(array.array('i',[l.vertex_index for l in o.data.loops]).tobytes())
 if o.type=='FONT':h.update(str((o.data.body,o.data.size,o.data.font.name,o.data.extrude)).encode())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode());return h.hexdigest()
before={o.name:fingerprint(o) for o in bpy.data.objects}
materials.clear()
for key,color,rough,metal in [('stone',(.55,.53,.48),.86,0),('letters',(.045,.05,.046),.54,.15)]:
 m=bpy.data.materials.new('SAR_V102_'+key);m.use_nodes=True;m.diffuse_color=(*color,1)
 p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=m.diffuse_color;p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;materials[key]=m
copies=[];brick_materials={}
for old in list(collection.all_objects):
 if old.hide_render or old.type!='MESH':continue
 slots=[i for i,m in enumerate(old.data.materials) if m.name in ['INFILL_red','INFILL_red.001','EXT20_brick']]
 if not slots:continue
 new=old.copy();new.data=old.data.copy();new.name='SAR_V102_'+old.name.removeprefix('SAR_');collection.objects.link(new)
 for i in slots:
  source=old.data.materials[i]
  if source.name not in brick_materials:
   m=source.copy();m.name='SAR_V102_red_brick_'+source.name;m.diffuse_color=(.42,.11,.075,1)
   nodes=m.node_tree.nodes;nodes.clear();out=nodes.new('ShaderNodeOutputMaterial');p=nodes.new('ShaderNodeBsdfPrincipled');p.inputs['Roughness'].default_value=.87
   uv=nodes.new('ShaderNodeTexCoord');brick=nodes.new('ShaderNodeTexBrick');brick.inputs['Color1'].default_value=(.42,.11,.075,1);brick.inputs['Color2'].default_value=(.32,.078,.055,1);brick.inputs['Mortar'].default_value=(.24,.18,.145,1);brick.inputs['Scale'].default_value=1;brick.inputs['Brick Width'].default_value=.225;brick.inputs['Row Height'].default_value=.075;brick.inputs['Mortar Size'].default_value=.006
   links=m.node_tree.links;links.new(uv.outputs['UV'],brick.inputs['Vector']);links.new(brick.outputs['Color'],p.inputs['Base Color']);links.new(p.outputs['BSDF'],out.inputs['Surface']);m['siteDetail']=True;brick_materials[source.name]=m
  new.data.materials[i]=brick_materials[source.name]
 old.hide_render=True;old.hide_set(True);new.hide_render=False;new.hide_set(False);copies.append({'source':old.name,'copy':new.name})
# Replace only internal first-floor sash members, preserving every other part.
partials=[];lo=height+.82;hi=2*height-.62;origin=Vector(facade.point(0,0,0))
materials['sash']=bpy.data.materials['INFILL_frame.001']
for suffix,expected in [('sash_rails_frame',8),('sash_verticals_frame',8),('sash_fine_bars_frame',16)]:
 old=bpy.data.objects['SAR_V20_EXT_retained_D5_'+suffix];new=old.copy();new.data=old.data.copy();new.name='SAR_V102_retained_'+suffix;collection.objects.link(new)
 bm=bmesh.new();bm.from_mesh(new.data);seen=set();delete=[];removed=0
 for v in list(bm.verts):
  if v in seen:continue
  stack=[v];seen.add(v);component=[]
  while stack:
   q=stack.pop();component.append(q)
   for e in q.link_edges:
    other=e.other_vert(q)
    if other not in seen:seen.add(other);stack.append(other)
  ps=[new.matrix_world@v.co-origin for v in component]
  xs=[p.dot(u) for p in ps];ds=[p.dot(n) for p in ps];zs=[p.z for p in ps]
  cx=(min(xs)+max(xs))/2;cz=(min(zs)+max(zs))/2
  if 0<cx<facade.length and abs(sum(ds)/len(ds))<.16 and lo+.1<cz<hi-.1:
   delete.extend(component);removed+=1
 assert removed==expected,(suffix,removed)
 bmesh.ops.delete(bm,geom=delete,context='VERTS');bm.to_mesh(new.data);bm.free()
 old.hide_render=True;old.hide_set(True);new.hide_render=False;new.hide_set(False)
 partials.append({'source':old.name,'copy':new.name,'removedComponents':removed,'retainedVertices':[list(v.co) for v in new.data.vertices]})
for j in range(count):
 x=(j+.5)*pitch
 for part in [.25,.5,.75]:facade.box('first_floor_sashes','sash',x+width*(part-.5),(lo+hi)/2,.04,hi-lo,.10,.015)
 for part in [1/3,2/3]:facade.box('first_floor_sashes','sash',x,lo+(hi-lo)*part,width,.04,.10,.015)
# The three central upper levels have dressed stone surrounds in the street photo.
windows=[]
for floor in [2,3,4]:
 for j in range(count):
  x=(j+.5)*pitch;lo=floor*height+.82;hi=(floor+1)*height-.62
  for side in [-1,1]:facade.box('stone_architraves','stone',x+side*(width/2+.055),(lo+hi)/2,.11,hi-lo+.22,.16,.07)
  facade.box('stone_architraves','stone',x,hi+.08,width+.32,.16,.20,.09)
  facade.box('stone_architraves','stone',x,lo-.10,width+.38,.18,.32,.15)
  if floor==2:
   # A shallow segmental head, carried on paired simple stone corbels.
   facade.box('window_hood_base','stone',x,hi+.22,width+.55,.15,.28,.14)
   radius=width*.86;spring=hi-.54
   for i in range(24):
    a=math.pi*.23+math.pi*.54*i/24;b=math.pi*.23+math.pi*.54*(i+1)/24
    verts=[facade.point(x+r*math.cos(t),spring+r*math.sin(t),d) for d in [.14,.29] for r,t in [(radius,a),(radius,b),(radius+.10,b),(radius+.10,a)]]
    facade.group('segmental_window_hoods','stone').add(verts,[(0,1,2,3),(4,7,6,5),(0,4,5,1),(3,2,6,7),(1,5,6,2),(0,3,7,4)])
   for side in [-1,1]:facade.box('window_hood_corbels','stone',x+side*(width/2+.12),hi+.02,.17,.25,.24,.14)
  windows.append({'floor':floor,'bay':j,'center':x,'lower':lo,'upper':hi})
# Broad fascia below the retained dentilled cornice, clear of the first-floor glazing.
course=height*2;facade.box('school_name_fascia','stone',facade.length/2,course-.37,facade.length,.48,.24,.13)
added=[]
for g in facade.groups.values():
 o=g.finish();o.name='SAR_V102_'+o.name.removeprefix('SAR_D5_')
 for modifier in list(o.modifiers):o.modifiers.remove(modifier)
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free();added.append(o.name)
curve=bpy.data.curves.new('SAR_V102_school_name_curve','FONT');curve.body='The London School of Economics and Political Science';curve.align_x='CENTER';curve.size=.30;curve.extrude=.004
curve.font=next(f for f in bpy.data.fonts if f.filepath.endswith('/Arial.ttf'));curve.materials.append(materials['letters'])
obj=bpy.data.objects.new('SAR_V102_school_name',curve);collection.objects.link(obj)
right=-u;up=Vector((0,0,1));obj.matrix_world=Matrix(((right.x,up.x,n.x,0),(right.y,up.y,n.y,0),(right.z,up.z,n.z,0),(0,0,0,1)));obj.matrix_world.translation=Vector(facade.point(facade.length/2,course-.44,.258));added.append(obj.name)
bpy.context.view_layer.update();assert obj.dimensions.length>0
assert all(fingerprint(bpy.data.objects[k])==v for k,v in before.items())
for name in ['room-studies.json','room-spaces.json','building-review.json']:shutil.copyfile(ROOT/'result/blender/stage101'/name,OUT/name)
if not (OUT/'catalogue-before.json').exists():shutil.copyfile(ROOT/'web/public/models/catalogue.json',OUT/'catalogue-before.json')
assert json.loads((OUT/'catalogue-before.json').read_text())['version']=='101'
audit={'version':102,'baseline':101,'originalFingerprints':before,'copies':copies,'partialCopies':partials,'addedObjects':added,'windows':windows,'frontLength':facade.length,'course':course,'axis':list(u),'normal':list(n),'origin':facade.point(0,0,0),'references':['data/建筑图片/SAR_Sardinia House/01_建筑实拍/exteriors_lse_estate_025.jpg','data/建筑图片/SAR_Sardinia House/01_建筑实拍/campus_photos_round2_SAR_geograph_5974706_01.jpg'],'scope':'Photographed stone window surrounds, segmental hoods, school-name fascia and a local red-brick finish; retained estimated openings, floor count and footprint','limits':['Tree-obscured bays use repeated estimated profiles; pediment order and fine carving unverified','Roof, attic and rear elevations remain unresolved','Colours and dimensions are photographic estimates; interiors unchanged']}
(OUT/'sardinia-facade-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v102.blend'))
print('SARDINIA_FACADE_SAVED',len(windows),len(copies),len(added))
