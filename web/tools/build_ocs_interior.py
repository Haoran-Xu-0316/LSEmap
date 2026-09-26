"""Build a bounded OCS historical shoe-shop interior from two checked photos.

Run inside Blender. Existing v20 objects remain untouched. Only the photographed
retail area is represented; no inferred stair, rear room or current tenancy.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import sys
import bpy
from mathutils import Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'result/blender/stage21/ocs'
OUT.mkdir(parents=True, exist_ok=True)
SOURCE = ROOT/'result/blender/LSE_campus_detailed_v20.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
originals = list(bpy.data.objects)
campus_names = set(bpy.data.scenes['00_CAMPUS_COMPLETE'].objects.keys())

def fingerprint(objects):
    digest = hashlib.sha256()
    for obj in sorted(objects, key=lambda o:o.name):
        digest.update(obj.name.encode())
        digest.update(array.array('f', [v for row in obj.matrix_world for v in row]).tobytes())
        if obj.type != 'MESH': continue
        points = array.array('f', [0])*(len(obj.data.vertices)*3)
        obj.data.vertices.foreach_get('co', points)
        digest.update(points.tobytes())
        digest.update('|'.join(m.name if m else '' for m in obj.data.materials).encode())
    return digest.hexdigest()
protected_before = fingerprint(originals)
placeholder = bpy.data.collections.get('OCS_PUBLIC_INTERIOR_study')
if placeholder:
    assert not placeholder.all_objects, 'Existing nonempty room must not be replaced'
    bpy.data.collections.remove(placeholder)
collection = bpy.data.collections.new('OCS_PUBLIC_INTERIOR_study')
collection['roomSample'] = True
collection['roomLabel'] = 'OCS鞋店历史室内样本'
scene = bpy.data.scenes.new('OCS_V21_INTERIOR_REVIEW')
scene.collection.children.link(collection)
bpy.context.window.scene = scene
colors = {'timber':(.055,.046,.031), 'boards':(.10,.095,.067),
          'floor':(.28,.14,.065), 'floor_light':(.33,.18,.080),
          'floor_dark':(.225,.112,.050), 'oak':(.36,.23,.10),
          'plywood':(.50,.38,.20), 'plaster':(.70,.69,.61),
          'glass':(.15,.26,.29), 'metal':(.042,.046,.039),
          'black_shoe':(.027,.030,.026), 'tan_shoe':(.40,.24,.115),
          'brown_shoe':(.13,.060,.031), 'cloth':(.040,.043,.035),
          'sole':(.022,.020,.017), 'light':(.90,.87,.69)}
for name,color in colors.items():
    mat = bpy.data.materials.new('OCS_V21_'+name)
    mat.use_nodes = True
    mat.diffuse_color = (*color,1)
    shader = mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = mat.diffuse_color
    shader.inputs['Roughness'].default_value = .43 if name.endswith('shoe') else .70
    if name=='metal': shader.inputs['Metallic'].default_value=.5
    if name=='light':
        shader.inputs['Emission Color'].default_value=(*color,1)
        shader.inputs['Emission Strength'].default_value=.8
    materials[name]=mat
batches={}
def group(name,material):
    key=(name,material)
    if key not in batches:
        g=Geometry('OCS',name,material)
        g.collection=collection
        g.name='OCS_V21_INT_'+name+'_'+material
        batches[key]=g
    return batches[key]
def box(name,mat,center,size,angle=0): group(name,mat).box(center,size,angle)
def tube(name,mat,a,b,radius=.015):
    a,b=Vector(a),Vector(b);t=(b-a).normalized();u=t.cross(Vector((0,0,1)))
    if u.length<.01:u=t.cross(Vector((0,1,0)))
    u.normalize();v=t.cross(u);n=8
    points=[p+radius*(u*math.cos(i*math.tau/n)+v*math.sin(i*math.tau/n)) for p in [a,b] for i in range(n)]
    faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    group(name,mat).add(points,faces)
def prism(name,mat,outline,z,height):
    n=len(outline);points=[(x,y,h) for h in [z,z+height] for x,y in outline]
    group(name,mat).add(points,[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)])

# Continuous planked floor, low timber frame and cut-open front/right walls.
width,depth,height=4.6,6.8,2.45
box('floor_base','floor',(0,0,-.11),(width,depth,.20))
for i in range(19):
    x=-width/2+(i+.5)*width/19
    for j,(a,b) in enumerate([(-3.4,-.5+(i%3)*.3),(-.5+(i%3)*.3,3.4)]):
        box('floor_planks',['floor','floor_light','floor_dark'][(i+j)%3],(x,(a+b)/2,.006),(width/19-.009,b-a-.01,.018))
box('rear_wall','plaster',(0,3.4,height/2),(width,.14,height))
box('left_wall','boards',(-2.3,0,height/2),(.14,depth,height))
for z in [.16,.38,.60,.82,1.04,1.26,1.48,1.70,1.92,2.14,2.36]:
    box('board_joints','timber',(-2.218,0,z),(.012,depth,.012))
# Original photo shows timber posts and a short open rear ceiling field.
for y in [-2.9,-.7,2.25,3.32]:box('timber_posts','timber',(-2.13,y,1.20),(.17,.17,2.4))
for x in [-2.13,1.96]:box('rear_posts','timber',(x,3.25,1.20),(.19,.17,2.4))
box('left_ceiling_beam','timber',(-2.14,0,2.34),(.22,depth,.22))
box('rear_ceiling_beam','timber',(0,3.25,2.34),(4.55,.22,.22))
box('cross_beam','timber',(0,1.85,2.34),(4.55,.23,.22))
box('rear_ceiling_cutaway','plaster',(-1.15,2.62,2.43),(2.08,1.25,.08))

# Window coordinates run across each visible wall, never invent an exterior fit.
def window(center,width,height,angle=0):
    x,y,z=center;c,s=math.cos(angle),math.sin(angle)
    def p(dx,dz,offset=0):return(x+c*dx-s*offset,y+s*dx+c*offset,z+dz)
    box('window_glass','glass',center,(width,.035,height),angle)
    for sign in [-1,1]:
        box('window_jamb','timber',p(sign*width/2,0,-.05),(.075,.11,height+.1),angle)
        box('window_head_sill','timber',p(0,sign*height/2,-.05),(width+.12,.15,.075),angle)
    box('window_meeting_rail','timber',p(0,0,-.07),(width,.10,.055),angle)
    box('window_display_shelf','oak',p(0,-height/2-.03,-.18),(width+.14,.38,.065),angle)
    for dx in [-.30,0,.30]:box('window_glazing_bars','metal',p(dx,0,-.026),(.014,.018,height-.07),angle)
    for dz in [-.48,-.24,.24,.48]:box('window_glazing_bars','metal',p(0,dz,-.026),(width-.07,.018,.012),angle)
window((-.80,3.30,1.37),1.52,1.51)
# Rotation +90deg puts the small reveal into the room along positive X.
for y in [-1.86,.73]:window((-2.20,y,1.42),1.48,1.58,math.pi/2)

# Foreground shoe-display table and the lower central timber cabinet.
box('display_table_top','oak',(-.73,-1.90,.80),(1.25,1.72,.075))
for x in [-1.22,-.24]:
    for y in [-2.55,-1.25]:box('display_table_legs','timber',(x,y,.395),(.055,.055,.79))
box('display_cabinet','oak',(-.50,.43,.44),(1.32,1.12,.88))
box('display_cabinet_lip','timber',(-.50,.43,.9),(1.39,1.18,.035))
for x in [-.83,-.17]:
    box('cabinet_door_panel','floor',(x,-.145,.46),(.57,.025,.67))
    box('cabinet_pull','metal',(x,-.17,.70),(.17,.035,.018))

# Shoes are original low-poly construction, not a projected brand photograph.
shoe_count=0
def shoe(x,y,z,angle=0,mat='black_shoe'):
    global shoe_count
    shoe_count+=1;c,s=math.cos(angle),math.sin(angle)
    outline=[(-.060,-.16),(.046,-.16),(.065,-.11),(.071,.06),(.060,.14),(.020,.18),(-.027,.18),(-.065,.13),(-.074,.04)]
    def p(dx,dy,dz):return(x+c*dx-s*dy,y+s*dx+c*dy,z+dz)
    prism('shoe_sole','sole',[(p(a,b,0)[0],p(a,b,0)[1]) for a,b in outline],z,.020)
    # Curved upper rises at the heel/collar and tapers over the toe.
    lower=[p(a*.96,b,.022) for a,b in outline]
    upper=[p(a*.77,b*.92,.12 if b<-.07 else .072 if b<.08 else .045) for a,b in outline]
    n=len(outline);group('shoe_upper',mat).add(lower+upper,[tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)])
    box('shoe_collar','sole',p(0,-.105,.127),(.068,.07,.010),angle)
    for dy in [-.035,-.005,.025]:tube('shoe_laces','sole',p(-.04,dy,.092),p(.04,dy,.092),.003)
for i in range(4):
    for j in range(2):shoe(-1.05+j*.47,-2.50+i*.37,.841,angle=.1*(i%2),mat=['black_shoe','tan_shoe','brown_shoe'][(i+j)%3])
for x,y in [(-.87,.10),(-.33,.11),(-.80,.64),(-.29,.65)]:shoe(x,y,.924,mat='black_shoe')
for x in [-1.26,-.91,-.56]:shoe(x,3.04,.646,angle=math.pi/2,mat='brown_shoe')

# Curved plywood chairs are visible as shoe displays in the second reference.
def display_chair(x,y,angle=0):
    c,s=math.cos(angle),math.sin(angle)
    def p(dx,dy,dz):return(x+c*dx-s*dy,y+s*dx+c*dy,dz)
    # Curved seat formed from narrow connected strips, with curved back profile.
    for i in range(12):
        a=-.24+i*.04;b=a+.04
        za=.465+.05*(abs(a)/.24)**2;zb=.465+.05*(abs(b)/.24)**2
        group('plywood_seat','plywood').add([p(a,-.23,za),p(b,-.23,zb),p(b,.23,zb+.015),p(a,.23,za+.015)],[(0,1,2,3)])
    for i in range(12):
        za=.53+i*.041;zb=za+.041
        ya=.20+.08*((za-.53)/.49)**2;yb=.20+.08*((zb-.53)/.49)**2
        group('plywood_back','plywood').add([p(-.24,ya,za),p(.24,ya,za),p(.23,yb,zb),p(-.23,yb,zb)],[(0,1,2,3)])
    for dx in [-.19,.19]:
        for dy in [-.16,.16]:tube('chair_legs','metal',p(dx*1.1,dy*1.1,.02),p(dx,dy,.47),.012)
    shoe(x,y,.49,angle=angle+.35,mat='black_shoe')
for y in [-2.45,-1.42,-.39]:display_chair(1.28,y,angle=-math.pi/2)

# Rear clothes rack and shelving are bounded at the photographed retail area.
tube('clothes_rail','metal',(.50,3.10,1.97),(1.80,3.10,1.97),.022)
for x in [.55,1.05,1.55]:
    tube('hanger','metal',(x-.16,3.1,1.77),(x,3.1,1.95),.008)
    tube('hanger','metal',(x,3.1,1.95),(x+.16,3.1,1.77),.008)
    # Simple garment silhouette; no mannequins or invented people.
    outline=[(-.20,1.76),(-.33,1.48),(-.22,1.42),(-.17,.73),(.17,.73),(.22,1.42),(.33,1.48),(.20,1.76)]
    vertices=[(x+dx,y,z) for y in [3.03,3.09] for dx,z in outline];n=len(outline)
    group('hanging_coats','cloth').add(vertices,[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)])
for y in [-.62,1.07]:box('shelf_stile','timber',(2.06,y,1.12),(.09,.07,2.24))
for z in [.18,.67,1.18,1.72,2.22]:box('display_shelves','timber',(1.88,.225,z),(.50,1.76,.055))
for y in [-.29,.12,.61]:shoe(1.87,y,.704,angle=math.pi/2,mat='tan_shoe')
for x,y in [(-1.95,-.65),(-1.95,2.1),(.9,3.14)]:box('small_spot_light','light',(x,y,2.23),(.12,.10,.045))

objects=[]
for batch in batches.values():
    obj=batch.finish()
    obj['scope']='Historical shoe-retail area, unknown photo date; dimensions and furniture placement estimated'
    if 'plywood_' in obj.name:
        solid=obj.modifiers.new('Thin plywood shell','SOLIDIFY');solid.thickness=.014
    for modifier in obj.modifiers:
        if modifier.type=='BEVEL':modifier.width=.006;modifier.segments=1
    objects.append(obj)
bpy.context.view_layer.update()
assert fingerprint(originals)==protected_before,'An original object changed'
assert set(bpy.data.scenes['00_CAMPUS_COMPLETE'].objects.keys())==campus_names,'Room leaked into campus'
assert all(math.isfinite(v) for obj in objects for vert in obj.data.vertices for v in vert.co)
camera_position=(7.6,-10.4,7.0);target=(0,.05,1.05)
camera=bpy.data.objects.new('OCS_V21_INT_camera',bpy.data.cameras.new('OCS_V21_INT_camera'));scene.collection.objects.link(camera)
camera.location=camera_position;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.lens=39;scene.camera=camera
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'refined.blend'))
evidence=json.loads((ROOT/'result/blender/stage21/remaining-evidence.json').read_text())
ocs=next(b for b in evidence['buildings'] if b['code']=='OCS')
manifest={'sourceModel':'result/blender/LSE_campus_detailed_v20.blend','buildings':[{'code':'OCS','status':'added','changes':['Low timber-frame retail cutaway with two side windows and one rear window','Planked floor, central cabinet, shoe display table, three curved plywood display chairs, rear clothes rail and shelving'],'sources':[{'url':image['url'],'parentUrl':image['parentUrl'],'visuallyReviewed':True} for image in ocs['newImages']],'limitations':['Photo date unknown; do not label as2026current interior','One bounded retail-area sample, no measured plan','Room dimensions and relative placement estimated; no hidden rooms or staircase reconstructed'],'addedObjects':[{'name':obj.name,'collection':collection.name} for obj in objects],'roomStudy':{'label':collection['roomLabel'],'camera':camera_position,'target':target,'scope':'鞋店历史室内局部样本，拍摄日期未注明；尺寸与陈列位置估算，非整栋内部。'},'shoeCount':shoe_count,'componentCount':sum(b.parts for b in batches.values())}], 'verification':{'originalGeometryUnchanged':True,'originalGeometrySha256':protected_before,'campusMembershipUnchanged':True,'newVerticesFinite':True}}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
# Render authored geometry only. Remote source photographs are never embedded.
bpy.context.window.scene=scene
scene.world=bpy.data.worlds.new('OCS_V21_studio');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.52,.59,.65,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.60
for name,position,power,size in [('front',(0,-3,6),850,5),('window',(-4,1,4),600,3)]:
    light=bpy.data.objects.new('OCS_V21_'+name,bpy.data.lights.new('OCS_V21_'+name,'AREA'));scene.collection.objects.link(light);light.location=position;light.data.energy=power;light.data.shape='DISK';light.data.size=size;light.rotation_euler=(Vector((0,0,.7))-light.location).to_track_quat('-Z','Y').to_euler()
scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True;scene.render.resolution_x=1100;scene.render.resolution_y=880;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/'ocs-interior.png');bpy.context.view_layer.update();bpy.ops.render.render(write_still=True)
print('OCS_INTERIOR_COMPLETE',len(objects),shoe_count,flush=True)
