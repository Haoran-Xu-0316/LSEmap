"""Rebuild CKK's documented east frontage, preserving its roof and interior.

Photographic reconstruction, not a measured elevation. Run in Blender's Text
Editor. The 2008 project image establishes the retained facade, not current cafe
furniture or signs. Native dimensions, window widths and levels are estimates.
"""
from pathlib import Path
import array,hashlib,json,math,shutil
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage33';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v32.blend'))
centre=Vector((-110.49102024587766,77.56014819690478,0))
c,s=math.cos(math.radians(22)),math.sin(math.radians(22))
outward=Vector((c,s,0))
collection=bpy.data.collections['CKK_EXTERIOR']
def fingerprint(o):
    v=array.array('f',[0])*(3*len(o.data.vertices));o.data.vertices.foreach_get('co',v)
    i=array.array('i',[0])*len(o.data.loops);o.data.loops.foreach_get('vertex_index',i)
    return hashlib.sha256(v.tobytes()+i.tobytes()).hexdigest()
before={o.name:fingerprint(o) for o in bpy.data.objects if o.type=='MESH'}
changed=[];removed=[]
# Retire the generic front bay geometry instead of hiding it behind a new skin.
# Roofs remain intact; this half-space also trims the short corner returns.
for obj in list(collection.all_objects):
    if obj.type!='MESH' or 'roof' in obj.name.lower() or obj.name.startswith('CKK_V32_'):continue
    if max(((obj.matrix_world@v.co-centre).dot(outward) for v in obj.data.vertices),default=0)<21.8:continue
    bm=bmesh.new();bm.from_mesh(obj.data)
    point=obj.matrix_world.inverted()@(centre+outward*21.8)
    normal=obj.matrix_world.to_3x3().transposed()@outward
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=point,plane_no=normal,clear_outer=True,dist=1e-6)
    changed.append(obj.name)
    if not bm.faces:
        removed.append(obj.name);bm.free();bpy.data.objects.remove(obj,do_unlink=True)
    else:
        bm.to_mesh(obj.data);bm.free();obj.data.update()

def material(name,rgb,roughness=.75,metallic=0):
    mat=bpy.data.materials.new(name);mat.use_nodes=True;mat.diffuse_color=(*rgb,1)
    shader=mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value=mat.diffuse_color
    shader.inputs['Roughness'].default_value=roughness;shader.inputs['Metallic'].default_value=metallic
    return mat
stone=material('CKK_V33_pale_portland_stone',(.65,.635,.59))
recess=material('CKK_V33_stone_joint',(.34,.34,.32))
frames=material('CKK_V33_dark_bronze_frames',(.14,.155,.15),.46,.3)
glass=material('CKK_V33_muted_glass',(.28,.33,.33),.16)
door=material('CKK_V33_entry_bronze',(.26,.225,.16),.38,.5)
batches={}
def add(name,mat,vertices,faces):
    b=batches.setdefault(name,{'material':mat,'vertices':[],'faces':[]});offset=len(b['vertices'])
    b['vertices'].extend(vertices);b['faces'].extend(tuple(offset+i for i in f) for f in faces)
def box(name,mat,p,size):
    x,y,z=p;a,b,h=[k/2 for k in size]
    add(name,mat,[(x+dx*a,y+dy*b,z+dz*h) for dx,dy,dz in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]],[(0,2,6,4),(1,5,7,3),(0,4,5,1),(2,3,7,6),(0,1,3,2),(4,6,7,5)])
def panel(x,y0,y1,z0,z1,name='CKK_V33_masonry',mat=stone,depth=.5):
    if y1-y0>1e-5 and z1-z0>1e-5:box(name,mat,(x-depth/2,(y0+y1)/2,(z0+z1)/2),(depth,y1-y0,z1-z0))

# Three narrow bays in each projecting side wing; five broader central bays.
blocks=[(-16.4,-8.9,[-14.65,-12.65,-10.65],.92,23.2),
        (-8.9,8.9,[-7,-3.5,0,3.5,7],1.65,22.92),
        (8.9,16.4,[10.65,12.65,14.65],.92,23.2)]
rows=[(.6,4.2),(5.3,8.0),(9.3,12.5),(13.8,16.5),(17.9,20.5),(22.5,24.0)]
openings=[]
for left,right,centres,width,x in blocks:
    last=0
    for level,(bottom,top) in enumerate(rows):
        panel(x,left,right,last,bottom)
        edge=left
        for y in centres:
            w=width
            if abs(y)<.1 and level==0:w=2.1
            if abs(y)<.1 and level==1:w=2.7
            panel(x,edge,y-w/2,bottom,top)
            openings.append((x,y,w,bottom,top,level))
            edge=y+w/2
        panel(x,edge,right,bottom,top);last=top
    panel(x,left,right,last,25)
# Reconnect the rebuilt frontage to the untouched side elevations.
for y in [-16.4,16.4]:box('CKK_V33_corner_returns',stone,(22.45,y,12.5),(1.5,.25,25))

for x,y,w,bottom,top,level in openings:
    if abs(y)<.1 and level==1:continue  # Central fanlight is genuinely arched below.
    panel(x-.12,y-w/2,y+w/2,bottom,top,'CKK_V33_recessed_glass',glass,.06)
    for side in [-1,1]:
        box('CKK_V33_window_frames',frames,(x-.075,y+side*(w/2-.035),(bottom+top)/2),(.12,.075,top-bottom))
        box('CKK_V33_stone_reveals',stone,(x+.045,y+side*(w/2+.07),(bottom+top)/2),(.19,.14,top-bottom+.16))
    for z in [bottom+.035,top-.035]:box('CKK_V33_window_frames',frames,(x-.075,y,z),(.12,w,.07))
    box('CKK_V33_centre_mullions',frames,(x-.055,y,(bottom+top)/2),(.12,.055,top-bottom))
    box('CKK_V33_projecting_sills',stone,(x+.12,y,bottom-.10),(.44,w+.30,.15))
    if level==2 and (abs(y)<8.9 or abs(abs(y)-12.65)<.1):
        # Pedimented principal-floor window surrounds, simplified without invented carving.
        box('CKK_V33_window_hoods',stone,(x+.2,y,top+.17),(.58,w+.6,.2))
        box('CKK_V33_window_hoods',stone,(x+.12,y,top+.34),(.39,w+.76,.12))

# Strong horizontal cornice above the principal storeys and a quieter base band.
for z,projection,height in [(8.55,.25,.18),(8.76,.36,.14),(21.12,.25,.25),(21.43,.45,.24),(21.7,.61,.15),(24.6,.17,.13)]:
    for left,right,_,_,x in blocks:panel(x+projection,left,right,z-height/2,z+height/2,'CKK_V33_stringcourses',stone,projection+.24)
for i in range(66):
    y=-16.05+i*.495
    x=23.2 if abs(y)>8.9 else 22.92
    box('CKK_V33_cornice_dentils',stone,(x+.34,y,21.13),(.4,.18,.25))
# Rusticated lower two storeys: joints stop at actual openings.
for level in range(1,19):
    z=level*.455
    if z>8.45:continue
    for left,right,centres,w,x in blocks:
        intervals=[(left,right)]
        for ox,y,ow,bottom,top,_ in openings:
            if abs(ox-x)>.01 or y<left or y>right or not bottom-.03<=z<=top+.03:continue
            updated=[]
            for a,b in intervals:
                if y-ow/2>a:updated.append((a,min(b,y-ow/2)))
                if y+ow/2<b:updated.append((max(a,y+ow/2),b))
            intervals=[(a,b) for a,b in updated if b>a]
        for a,b in intervals:panel(x+.004,a,b,z-.014,z+.014,'CKK_V33_rustication_joints',recess,.014)

# Semicircular fanlight, radial stone voussoirs and the shallow columned portico.
x=23.08;spring=6.55;radius=1.35
panel(x-.1,-radius,radius,5.3,spring,'CKK_V33_fanlight_glass',glass,.05)
for i in range(40):
    a=i*math.pi/40;b=(i+1)*math.pi/40
    add('CKK_V33_fanlight_glass',glass,[(x-.1,0,spring),(x-.1,radius*math.cos(a),spring+radius*math.sin(a)),(x-.1,radius*math.cos(b),spring+radius*math.sin(b))],[(0,1,2)])
    # Fill the rectangular aperture corners above the curved head.
    ya,yb=radius*math.cos(a),radius*math.cos(b);za,zb=spring+radius*math.sin(a),spring+radius*math.sin(b)
    add('CKK_V33_arch_spandrels',stone,[(22.92,ya,za),(22.92,yb,zb),(22.92,yb,8),(22.92,ya,8)],[(0,1,2,3)])
for i in range(13):
    a=i*math.pi/13+.012;b=(i+1)*math.pi/13-.012
    points=[(x,r*math.cos(t),spring+r*math.sin(t)) for r,t in [(radius,a),(radius,b),(radius+.30,b),(radius+.30,a)]]
    add('CKK_V33_arch_stones',stone,points,[(0,1,2,3)])
# Fanlight framing follows the arched opening rather than a rectangular insert.
for i in range(48):
    a=i*math.pi/48;b=(i+1)*math.pi/48
    add('CKK_V33_fanlight_frame',frames,[(x+.015,r*math.cos(t),spring+r*math.sin(t)) for r,t in [(radius-.025,a),(radius-.025,b),(radius+.025,b),(radius+.025,a)]],[(0,1,2,3)])
box('CKK_V33_fanlight_frame',frames,(x+.015,0,spring),(.05,2*radius,.05))
for i in range(1,6):
    a=i*math.pi/6;dy,dz=radius*math.cos(a),radius*math.sin(a)
    py,pz=-math.sin(a)*.018,math.cos(a)*.018
    add('CKK_V33_fanlight_frame',frames,[(x+.015,py,spring+pz),(x+.015,dy+py,spring+dz+pz),(x+.015,dy-py,spring+dz-pz),(x+.015,-py,spring-pz)],[(0,1,2,3)])
for y in [-1.6,1.6]:
    box('CKK_V33_portal_bases',stone,(23.5,y,.22),(.75,.65,.44))
    box('CKK_V33_portal_capitals',stone,(23.5,y,4.45),(.74,.68,.27))
    # Round columns with modest entasis; no speculative decorative capitals.
    n=20;verts=[]
    for z,r in [(.44,.23),(1.5,.235),(4.31,.19)]:
        verts.extend((23.5+r*math.cos(j*2*math.pi/n),y+r*math.sin(j*2*math.pi/n),z) for j in range(n))
    faces=[(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)]+[(n+j,n+(j+1)%n,2*n+(j+1)%n,2*n+j) for j in range(n)]
    add('CKK_V33_portal_columns',stone,verts,faces)
for z,width,depth,h in [(4.7,4.1,.85,.3),(4.99,4.36,1.0,.16),(5.18,4.15,.78,.18)]:box('CKK_V33_portal_entablature',stone,(23.43,0,z),(depth,width,h))
for y in [-.97,0,.97]:box('CKK_V33_entry_frames',door,(23.0,y,2.28),(.18,.1,3.72))
for z in [.42,4.12]:box('CKK_V33_entry_frames',door,(23.0,0,z),(.18,2.08,.12))
box('CKK_V33_entry_transom',door,(23.02,0,3.25),(.18,2.1,.1))
for y in [-.16,.16]:box('CKK_V33_door_handles',door,(23.14,y,1.85),(.08,.045,.6))

created=[]
for name,b in batches.items():
    me=bpy.data.meshes.new(name)
    me.from_pydata([(centre.x+c*x-s*y,centre.y+s*x+c*y,z) for x,y,z in b['vertices']],[],b['faces']);me.materials.append(b['material']);me.update()
    obj=bpy.data.objects.new(name,me);collection.objects.link(obj);obj['source_status']='Photographic elevation study; heights and dimensions estimated';created.append(name)
after={o.name:fingerprint(o) for o in bpy.data.objects if o.type=='MESH'}
assert all(after.get(name)==value for name,value in before.items() if name not in changed)
for name in ['room-studies.json','room-spaces.json','building-review.json']:shutil.copyfile(ROOT/'result/blender/stage32'/name,OUT/name)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v33.blend'))
(OUT/'ckk-frontage-audit.json').write_text(json.dumps({'reference':'data/collections/library_round5/photos/CKK_8f06506667f1.jpg','changed':changed,'removed':removed,'created':created,'unchangedMeshes':len(before)-len(changed),'scope':'East facade and short corner returns. Roof and interiors preserved. Main frontage proportions estimated; signs, carvings and post-2025 cafe layout not reconstructed.'},indent=2)+'\n')
print('CKK_FRONTAGE_COMPLETE',len(changed),len(created))
