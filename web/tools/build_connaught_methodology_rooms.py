"""Build two bounded CON Methodology samples from the January2026 LSE newsletter.

Open in Blender Text Editor. The photographs show the autumn2025 refurbishment;
they do not supply a floor plan. Dimensions, furniture positions and ceiling
service routes are estimates. Existing rooms and the full campus stay untouched.
"""
from pathlib import Path
import array, hashlib, json, math, sys
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/con_methodology_next';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v123.blend'
if not BASE.exists():
    BASE=max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
bpy.ops.wm.open_mainfile(filepath=str(BASE))
# Rebuild only this builder's samples when old full snapshots have been removed.
previous=json.loads((OUT/'audit.json').read_text()) if (OUT/'audit.json').exists() else None
# A legacy component audit may predate the separately added acoustic mesh.
# Remove this builder-owned addition before rebuilding both room collections.
acoustic = bpy.data.objects.get('CON_ACOUSTICS161_tea_panel_joints')
if acoustic:
    assert all(c.name == 'CON_TEA_ROOM_study' for c in acoustic.users_collection)
    mesh = acoustic.data
    bpy.data.objects.remove(acoustic, do_unlink=True)
    if not mesh.users: bpy.data.meshes.remove(mesh)
if previous:
    for name in previous['ownedObjects']:
        obj=bpy.data.objects.get(name)
        if obj:
            mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True);mesh.use_fake_user=False
            if not mesh.users:bpy.data.meshes.remove(mesh)
    for record in previous.get('collections',[]):
        collection=bpy.data.collections.get(record['name'])
        if collection:
            assert not collection.objects,'Do not delete a collection containing unrelated objects'
            bpy.data.collections.remove(collection)
    for mat in list(bpy.data.materials):
        if mat.name.startswith(('CON_NEXT_', 'CON_ACOUSTICS161_')) and mat.users==int(mat.use_fake_user):
            mat.use_fake_user=False;bpy.data.materials.remove(mat)
for scene in bpy.data.scenes:
    for layer in scene.view_layers:layer.update()
def fingerprint(obj):
    digest=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type=='MESH':
        for data,field,kind,width in ((obj.data.vertices,'co','f',3),(obj.data.loops,'vertex_index','i',1),(obj.data.polygons,'material_index','i',1)):
            values=array.array(kind,[0])*(len(data)*width);data.foreach_get(field,values);digest.update(values.tobytes())
        for layer in obj.data.uv_layers:
            values=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);digest.update(values.tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return digest.hexdigest()
original={obj.name:fingerprint(obj) for obj in bpy.data.objects}
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,materials
palette={'white':(.88,.89,.85),'floor':(.72,.72,.69),'carpet':(.21,.22,.225),
 'cream':(.69,.66,.56),'wood':(.52,.34,.17),'tablewood':(.75,.57,.30),
 'cyan':(.36,.57,.59),'blue':(.15,.32,.40),'yellow':(.83,.55,.035),
 'orange':(.63,.16,.045),'metal':(.40,.44,.45),'dark':(.045,.055,.055),
 'leaf':(.07,.19,.085),'leaflight':(.17,.30,.10),'pot':(.17,.17,.15),
 'glass':(.44,.59,.61),'light':(.96,.96,.91)}
materials.clear()
for key,color in palette.items():
    mat=bpy.data.materials.new('CON_NEXT_METHOD_'+key);mat.use_nodes=True;mat.diffuse_color=(*color,1)
    shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=(*color,1);shader.inputs['Roughness'].default_value=.68
    if key=='metal':shader.inputs['Metallic'].default_value=.65;shader.inputs['Roughness'].default_value=.42
    if key=='glass':shader.inputs['Metallic'].default_value=.1;shader.inputs['Roughness'].default_value=.2
    if key=='light':shader.inputs['Emission Color'].default_value=(*color,1);shader.inputs['Emission Strength'].default_value=.4
    materials[key]=mat
collections=[];room_records=[];owned=[]
def start_room(identifier,collection_name,label,width,depth):
    global collection,groups,prefix
    assert bpy.data.collections.get(collection_name) is None,'Do not overwrite an existing study'
    collection=bpy.data.collections.new(collection_name);collection['roomSample']=True;collection['roomLabel']=label
    scene=bpy.data.scenes.new('REVIEW_'+identifier);scene.collection.children.link(collection);bpy.context.window.scene=scene
    collections.append(collection);groups={};prefix='CON_NEXT_'+identifier.replace('-','_')+'_'
    scope='依据LSE2026年1月简报中2025年秋翻新空间照片建立的局部样本。尺寸、家具位置和不可见构造估算，未连接为完整楼层。'
    room_records.append({'id':identifier,'code':'CON','collection':collection_name,'label':label,'scope':scope,
      'gallery':identifier+'-interior','interiorStudy':{'kind':'room-sample','label':label,'scope':scope},
      'interiorView':{'position':([width*1.2,width*.85,depth*1.25] if identifier=='con-methodology' else [.4,3.4,6.8]),'target':([0,1.05,0] if identifier=='con-methodology' else [0,1.10,0]),'fov':(48 if identifier=='con-methodology' else 50)}})
    return scene

def group(family,material):
    key=(family,material)
    if key not in groups:
        geometry=Geometry('CON',family,material);geometry.collection=collection;geometry.name=prefix+family+'_'+material;groups[key]=geometry
    return groups[key]
def box(family,material,point,size,angle=0):group(family,material).box(point,size,angle)
def tube(family,material,a,b,radius=.02,sides=12):
    a,b=Vector(a),Vector(b);axis=(b-a).normalized();u=axis.cross(Vector((0,0,1)))
    if u.length<.01:u=axis.cross(Vector((0,1,0)))
    u.normalize();v=axis.cross(u)
    points=[p+radius*(u*math.cos(i*math.tau/sides)+v*math.sin(i*math.tau/sides)) for p in [a,b] for i in range(sides)]
    group(family,material).add(points,[tuple(reversed(range(sides))),tuple(range(sides,2*sides))]+[(i,(i+1)%sides,(i+1)%sides+sides,i+sides) for i in range(sides)])
def round_table(x,y,radius=.46):
    tube('round_table_top','tablewood',(x,y,.73),(x,y,.77),radius,32)
    tube('table_pedestal','metal',(x,y,.035),(x,y,.73),.04)
    tube('table_base','metal',(x,y,.02),(x,y,.045),radius*.48,20)
def chair(x,y,angle,soft=False):
    c,s=math.cos(angle),math.sin(angle)
    def point(dx,dy,z):return(x+c*dx-s*dy,y+s*dx+c*dy,z)
    size=.65 if soft else .45;material='cream' if soft else 'orange'
    box('seat',material,point(0,0,.45),(size,size*.86,.14 if soft else .055),angle)
    box('seat_back',material,point(0,.29 if soft else .20,.78),(size,.14 if soft else .06,.50 if soft else .38),angle)
    if soft:
        for sign in [-1,1]:box('padded_arm',material,point(sign*.33,0,.64),(.12,.64,.34),angle)
    for dx in [-size*.40,size*.40]:
        for dy in [-size*.32,size*.32]:tube('seat_leg','dark',point(dx,dy,.025),point(dx*.9,dy*.9,.42),.024)
def plant(x,y,height=1.35):
    tube('planter','pot',(x,y,0),(x,y,.32),.20,20)
    for index in range(7):
        angle=index*math.tau/7;length=height*(.70+.04*index)
        end=Vector((x+math.cos(angle)*.26,y+math.sin(angle)*.26,length))
        tube('plant_stem','leaf',(x,y,.25),end,.009,6)
        for level in [.58,.83]:
            stem=Vector((x,y,.25)).lerp(end,level)
            tip=stem+Vector((math.cos(angle)*.38,math.sin(angle)*.38,.08))
            lateral=Vector((-math.sin(angle)*.09,math.cos(angle)*.09,0))
            group('plant_leaf','leaflight' if index%2 else 'leaf').add([stem,stem.lerp(tip,.46)+lateral,tip,stem.lerp(tip,.46)-lateral],[(0,1,2,3)])
def finish_room(scene,name):
    for geometry in groups.values():
        obj=geometry.finish();obj['scope']='Photographed2025 refurbished local sample; dimensions estimated'
        if any(key in obj.name for key in ['seat','padded','table_top']):
            for modifier in obj.modifiers:
                if modifier.type=='BEVEL':modifier.width=.035;modifier.segments=3
        owned.append(obj)
def render_room(scene,name):
    # Review only, not part of exported room collections.
    world=bpy.data.worlds.new(name);world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.75,.78,.80,1);world.node_tree.nodes['Background'].inputs[1].default_value=.65;scene.world=world
    light=bpy.data.lights.new(name,'AREA');light.energy=1300;light.shape='DISK';light.size=8
    lamp=bpy.data.objects.new(name+'_light',light);scene.collection.objects.link(lamp);lamp.location=(1,-3,7)
    target=Vector((0,0,1.0));camera_data=bpy.data.cameras.new(name);camera=bpy.data.objects.new(name+'_camera',camera_data);scene.collection.objects.link(camera)
    camera.location=(-10,-13,10);camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.type='ORTHO';camera_data.ortho_scale=15 if 'learning' in name else 7;scene.camera=camera
    scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
    scene.render.resolution_x=1400;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.render.filepath=str(OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True)

scene=start_room('con-methodology','CON_METHOD_ROOM_study','CON一层学习区2025',10.8,7.6)
box('floor','floor',(0,0,-.06),(10.8,7.6,.12));box('circulation_carpet','carpet',(0,-.05,.007),(10.7,1.6,.014))
box('cyan_acoustic_wall','cyan',(-5.25,1.95,1.4),(.12,3.65,2.8))
box('rear_wall','white',(0,3.76,1.4),(10.8,.12,2.8))
box('rear_glazed_partition','glass',(-2.9,3.67,1.42),(4.2,.025,2.70))
for x in [-5.03,-3.63,-2.23,-.77]:box('partition_mullion','dark',(x,3.63,1.42),(.04,.06,2.75))
for z in [.04,2.78]:box('partition_rail','dark',(-2.9,3.63,z),(4.25,.06,.045))
for y in [.45,1.22,1.99,2.76]:box('panel_joint','blue',(-5.18,y,1.4),(.012,.008,2.75))
# Two photographed timber screens define open seating zones; no inferred floor connectivity.
for x,y,length,angle in [(-1.15,1.28,2.1,0),(-2.18,2.15,1.8,math.pi/2)]:
    # Open framing and slats, without any solid infill.
    for z in [.05,2.75]:box('screen_rail','wood',(x,y,z),(length,.09,.08),angle)
    if angle==0:
        # The photographed front screen is diagonal lattice; its return uses vertical slats.
        for slope in [-1,1]:
            for index in range(-6,19):
                intercept=index*.22
                lo=max(-length/2,.09-intercept) if slope==1 else max(-length/2,intercept-2.70)
                hi=min(length/2,2.70-intercept) if slope==1 else min(length/2,intercept-.09)
                if hi-lo>.02:
                    tube('diagonal_screen','wood',(x+lo,y+slope*.013,slope*lo+intercept),(x+hi,y+slope*.013,slope*hi+intercept),.016,4)
    else:
        for i in range(int(length/.11)):
            offset=-length/2+(i+.5)*.11
            box('screen_slat','wood',(x+math.cos(angle)*offset,y+math.sin(angle)*offset,1.4),(.042,.075,2.75),angle)
for x,y,angle in [(-4.0,-2.25,0),(-2.35,-2.25,.28),(-1.25,-3.10,2.6),(.05,1.05,0),(.05,2.55,math.pi)]:chair(x,y,angle,True)
for x,y in [(-3,-2.4),(.85,1.85),(3.55,2.3)]:round_table(x,y)
for x,y,angle in [(1.4,1.85,math.pi/2),(.9,2.75,math.pi),(3.0,2.3,-math.pi/2),(3.55,3.05,math.pi),(4.20,2.3,math.pi/2),(3.55,1.58,0)]:chair(x,y,angle)
for x,y,height in [(-4.9,-1.6,1.55),(-2.5,.6,1.30),(4.8,-2.4,1.85),(4.65,3.25,1.25)]:plant(x,y,height)
# Exposed services are a cropped approximate arrangement, not a surveyed MEP plan.
for y in [-2.5,1.0]:box('ceiling_duct','metal',(0,y,2.98),(10.5,.34,.22))
for x in [-3.8,-.6,3.2]:
    tube('ceiling_pipe','white',(x,-3.7,3.10),(x,3.7,3.10),.028)
    for y in [-1.8,2.0]:
        tube('light_suspension','metal',(x,y,2.88),(x,y,2.55),.008)
        box('linear_light','light',(x,y,2.53),(1.65,.07,.06))
finish_room(scene,'methodology-learning')

scene=start_room('con-tea-point','CON_TEA_ROOM_study','CON一层茶水间2025',3.8,4.9)
box('floor','floor',(0,0,-.06),(3.8,4.9,.12));box('rear_wall','white',(0,2.40,1.45),(3.8,.1,2.9));box('side_wall','white',(1.85,0,1.45),(.1,4.9,2.9))
box('base_cabinet','blue',(-1.47,.60,.43),(.68,2.65,.86));box('counter','white',(-1.47,.60,.91),(.75,2.72,.08))
box('upper_cabinet','blue',(-1.57,.62,2.0),(.45,2.65,.72))
for y in [-.18,.62,1.43]:
    for z in [.43,2.0]:box('cabinet_door_joint','dark',(-1.109 if z<1 else -1.338,y,z),(.008,.008,.73))
box('sink','metal',(-1.43,.4,.958),(.40,.48,.015));tube('tap','metal',(-1.68,.4,.95),(-1.68,.4,1.19),.016);tube('tap_spout','metal',(-1.68,.4,1.19),(-1.49,.4,1.19),.016)
box('coffee_machine','dark',(-1.47,1.32,1.12),(.3,.34,.35))
box('rear_window','glass',(0,2.33,1.65),(2.65,.025,1.1))
for x in [-1.36,-.45,.45,1.36]:box('window_upright','white',(x,2.30,1.65),(.055,.06,1.20))
for z in [1.06,2.24]:box('window_rail','white',(0,2.30,z),(2.75,.06,.055))
box('window_bar','tablewood',(0,1.97,.99),(2.65,.4,.055))
for x in [-.58,.58]:
    tube('bar_stool','orange',(x,1.7,.69),(x,1.7,.75),.18,20)
    for dx in [-.11,.11]:tube('stool_leg','dark',(x+dx,1.7,.025),(x+dx,1.7,.70),.02)
box('banquette_seat','yellow',(1.48,-.30,.46),(.66,2.45,.16));box('banquette_back','yellow',(1.74,-.30,.81),(.16,2.45,.68))
box('acoustic_panel','yellow',(1.78,.0,1.96),(.045,1.7,.88))
box('long_table','tablewood',(.56,-.32,.75),(.78,1.75,.055));box('table_support','dark',(.56,-.32,.38),(.40,.50,.73))
for y in [-.78,.05]:
    chair(-.22,y,-math.pi/2)
    # These photographed loose chairs are bright yellow rather than lounge orange.
    for family in ['seat','seat_back']:
        geometry=groups[(family,'orange')];geometry.material=materials['yellow']
finish_room(scene,'methodology-tea')
from refine_connaught_acoustics import apply_connaught_acoustics
apply_connaught_acoustics()
owned.append(bpy.data.objects['CON_ACOUSTICS161_tea_panel_joints'])
assert all(fingerprint(bpy.data.objects[name])==value for name,value in original.items())
component=OUT/'connaught-methodology-components.blend'
bpy.data.libraries.write(str(component),set(collections),fake_user=True)
audit={'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'originalGeometryPreserved':True,'originalObjects':len(original),'ownedObjects':[obj.name for obj in owned],'archivedObjects':[],
 'collections':[{'name':c.name,'ownedObjects':[o.name for o in c.objects]} for c in collections], 'spaces':room_records,
 'source':'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Cap-Dev/2026-January-CD-Newsletter-FINAL.pdf',
 'sourcePage':2,'completed':'Autumn2025','photos':['data/建筑图片/CON_Connaught House/01_建筑实拍/tower_photos_round4_tower_round4_jan_p2_1.jpg','data/建筑图片/CON_Connaught House/01_建筑实拍/tower_photos_round4_tower_round4_jan_p2_3.jpg'],
 'limitations':['Photographs publishedJanuary2026; exact capture dates unknown','No complete floor plan or measured dimensions','Separate cropped spaces; no inferred connection','Upper ceiling service routes estimated','Plants and furniture count are cropped photo-guided approximations','Existing historical CON room retained']}
(OUT/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
with bpy.data.libraries.load(str(component),link=False) as (source,target):target.collections=[c.name for c in collections]
assert len(target.collections)==2 and all(c and len(c.objects)>10 for c in target.collections)
for collection,name in zip(target.collections,['methodology-learning','methodology-tea']):
    scene=bpy.data.scenes.new('RELOADED_'+name);scene.collection.children.link(collection);bpy.context.window.scene=scene
    render_room(scene,name)
assert all(fingerprint(bpy.data.objects[name])==value for name,value in original.items())
proof={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'baselineUnchanged':hashlib.sha256(BASE.read_bytes()).hexdigest()==audit['baselineSha256'],'originalGeometryPreserved':True,'savedComponentReopened':True,'collections':len(target.collections),'ownedObjects':len(owned),'nativeRenders':['methodology-learning.png','methodology-tea.png']}
(OUT/'verification.json').write_text(json.dumps(proof,indent=2)+'\n');print('CON_METHOD_COMPONENTS_RELOADED',len(owned),flush=True)
