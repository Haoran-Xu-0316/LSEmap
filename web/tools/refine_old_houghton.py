"""Correct the photographed OLD Houghton entrance in Blender's Text Editor.
Read native51, retain the other elevations/interiors, and save native52.
Photo proportions guide the facade; metric dimensions remain estimated.
"""
from pathlib import Path
import array, hashlib, json, math, sys
import bpy, bmesh
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage52'
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v51.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
collection = bpy.data.collections['OLD_EXTERIOR']
originals = list(bpy.data.objects)
def fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        digest.update(array.array('f', [v for vertex in obj.data.vertices for v in vertex.co]).tobytes())
        digest.update(str([m.name if m else '' for m in obj.data.materials]).encode())
    return digest.hexdigest()
before = {obj.name: fingerprint(obj) for obj in originals}
ring = next(b for b in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings'] if b['code']=='OLD')['rings'][0]
p, q = Vector((*ring[10], 0)), Vector((*ring[11], 0))
origin = (p+q)/2
right = (p-q).normalized()
outward = Vector((right.y, -right.x, 0))
def point(x, depth, height):
    return origin + right*x + outward*depth + Vector((0,0,height))
def local(position):
    delta = position-origin
    return Vector((delta.dot(right), delta.dot(outward), delta.z))
materials.clear()
for key, color, rough, metal in [
    ('stone',(.61,.595,.55),.82,0), ('joint',(.34,.335,.31),.87,0),
    ('blue',(.015,.09,.22),.39,.18), ('iron',(.027,.032,.033),.37,.3),
    ('glass',(.14,.19,.205),.22,.22), ('vent',(.025,.037,.046),.7,0)]:
    mat=bpy.data.materials.new('OLD_V52_'+key);mat.use_nodes=True;mat.diffuse_color=(*color,1)
    shader=mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value=mat.diffuse_color
    shader.inputs['Roughness'].default_value=rough;shader.inputs['Metallic'].default_value=metal
    materials[key]=mat
for index in range(7):
    mat=materials['stone'].copy();mat.name='OLD_V52_ashlar_'+str(index)
    tone=.965+index*.010
    mat.diffuse_color=tuple(c*tone for c in materials['stone'].diffuse_color[:3])+(1,)
    mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=mat.diffuse_color
    materials['ashlar_'+str(index)]=mat
batches={}
def batch(key):
    if key not in batches:
        batches[key]=Geometry('OLD','houghton_'+key,key)
        batches[key].name='OLD_V52_Houghton_'+key
    return batches[key]
def box(key,x,depth,z,w,d,h):
    batch(key).box(point(x,depth,z),(w,d,h),math.atan2(right.y,right.x))
# Keep the original continuous ashlar mesh as a hidden archive. Individual
# stone blocks leave actual recessed joints rather than stripes over the wall.
wall=bpy.data.objects['OLD_Entrance_ashlar_wall']
wall.hide_render=True;wall.hide_set(True)
openings=[(-4.2,4.2,.65,9.0)]
windows=[]
for x in [-6.7,6.7]:
    for z,h in [(2.6,2.65),(7.0,2.15)]:
        windows.append((x,z,1.44,h));openings.append((x-.72,x+.72,z-h/2,z+h/2))
for x in [-6.7,-3.35,0,3.35,6.7]:
    for z,h in [(11.9,3),(16.2,2.2)]:
        windows.append((x,z,1.62,h));openings.append((x-.81,x+.81,z-h/2,z+h/2))
def subtract(rect,hole):
    a,b,c,d=rect;e,f,g,h=hole
    e,f,g,h=max(a,e),min(b,f),max(c,g),min(d,h)
    if e>=f or g>=h:return [rect]
    return [r for r in [(a,e,c,d),(f,b,c,d),(e,f,c,g),(e,f,h,d)] if r[1]-r[0]>.015 and r[3]-r[2]>.015]
block_count=0
for row in range(33):
    bottom=row*.60;top=min(19.6,bottom+.60)
    if bottom>=top:continue
    start=-8.9-(.85 if row%2 else 0)
    for column in range(12):
        left=max(-8.9,start+column*1.7);right_edge=min(8.9,start+(column+1)*1.7)
        if left>=right_edge:continue
        rectangles=[(left,right_edge,bottom,top)]
        for opening in openings:rectangles=[part for rect in rectangles for part in subtract(rect,opening)]
        for a,b,c,d in rectangles:
            box('ashlar_'+str((row*3+column*5)%7),(a+b)/2,-.007,(c+d)/2,b-a-.009,.45,d-c-.009)
            block_count+=1
# Remove only the central vertical bars in the fourteen photographed windows.
# Secondary elevations and Clare Market retain their own window construction.
bars=bpy.data.objects['OLD_Window_sash_bars']
bm=bmesh.new();bm.from_mesh(bars.data);remove=[]
for face in bm.faces:
    positions=[local(bars.matrix_world@v.co) for v in face.verts]
    for x,z,w,h in windows:
        if all(abs(v.x-x)<.021 and .065<v.y<.19 and z-h/2-.02<v.z<z+h/2+.02 for v in positions):
            remove.append(face);break
bmesh.ops.delete(bm,geom=remove,context='FACES');bm.to_mesh(bars.data);bars.data.update();bm.free()
for x,z,w,h in windows:
    for offset in [-w/6,w/6]:box('blue',x+offset,.145,z,.041,.11,h-.08)
# The paired main entrance is black metal, distinct from the blue side windows.
removed_door_faces={}
for name in ['OLD_Window_glazing','OLD_Window_sash_frames','OLD_Window_sash_bars']:
    obj=bpy.data.objects[name];bm=bmesh.new();bm.from_mesh(obj.data)
    faces=[f for f in bm.faces if all(abs((v:=local(obj.matrix_world@vertex.co)).x)<2.85 and -.98<v.y<-.45 and .58<v.z<4.22 for vertex in f.verts)]
    removed_door_faces[name]=len(faces)
    bmesh.ops.delete(bm,geom=faces,context='FACES');bm.to_mesh(obj.data);obj.data.update();bm.free()
for x in [-1.4,1.4]:
    box('glass',x,-.70,2.38,2.63,.045,3.38)
    for sx in [-1,1]:box('iron',x+sx*1.335,-.59,2.38,.085,.12,3.48)
    for z in [.67,4.09]:box('iron',x,-.59,z,2.73,.12,.085)
# Inner archivolt reveals: shallow curved cut-stone courses and radial joints.
# The existing structural arch remains intact, with 0.87m of photographed recess.
for depth_index in range(3):
    front=.218-depth_index*.29;back=front-.282
    for segment in range(32):
        a=segment*math.pi/32+.0018;b=(segment+1)*math.pi/32-.0018
        vertices=[point(radius*math.cos(t),depth,4.8+radius*math.sin(t)) for depth in [back,front] for radius,t in [(2.886,a),(2.906,a),(2.906,b),(2.886,b)]]
        batch('ashlar_'+str((segment+depth_index*3)%7)).add(vertices,[(0,1,2,3),(4,7,6,5),(0,4,5,1),(3,2,6,7),(0,3,7,4),(1,5,6,2)])
# Small rectangular basement air grilles and the blue diamond grilles directly
# below the upper side windows are visible in the engineer's entrance photo.
for x in [-7.7,6.0,7.1,8.2]:
    box('vent',x,.228,.35,.45,.035,.22)
    for k in range(4):box('iron',x,.255,.275+k*.05,.43,.035,.018)
for x in [-6.7,6.7]:
    box('vent',x,.231,5.64,.52,.035,.25)
    for k in range(4):
        for slope in [-1,1]:
            # Thin diagonal grille bars as shallow strips, clipped to the opening.
            for i in range(5):
                xx=x-.24+k*.12+i*.024;zz=5.53+i*.04*slope+(0 if slope>0 else .16)
                if abs(xx-x)<.25:box('blue',xx,.26,zz,.028,.03,.042)
# Author shallow geometry from the observed five-figure/library composition.
# This conveys the photographed artwork arrangement; it is not a sculpture scan.
relief_people = [(-2.05,1.65),(-1.03,1.60),(0,1.93),(1.10,2.44),(2.17,1.61)]
def ellipsoid(x,y,z,rx,ry,rz):
    vertices=[]
    for j in range(9):
        latitude=-math.pi/2+math.pi*j/8
        for i in range(12):
            longitude=math.tau*i/12
            vertices.append(point(x+rx*math.cos(latitude)*math.cos(longitude),y+ry*math.cos(latitude)*math.sin(longitude),z+rz*math.sin(latitude)))
    batch('stone').add(vertices,[(j*12+i,j*12+(i+1)%12,(j+1)*12+(i+1)%12,(j+1)*12+i) for j in range(8) for i in range(12)])
def limb(a,b,radius):
    start,end=Vector(a),Vector(b);axis=(end-start).normalized();u=axis.cross(Vector((0,0,1)))
    if u.length<.01:u=Vector((1,0,0))
    u.normalize();v=axis.cross(u).normalized()
    vertices=[point(*(center+radius*(u*math.cos(i*math.tau/10)+v*math.sin(i*math.tau/10)))) for center in [start,end] for i in range(10)]
    batch('stone').add(vertices,[(i,(i+1)%10,(i+1)%10+10,i+10) for i in range(10)])
base=4.46
# Bookshelves stay behind the bodies, with height clipped by the arched opening.
for x in [-2.36,-.82,.76,2.34]:
    top=4.8+math.sqrt(2.80**2-x*x)
    box('ashlar_0',x,-.515,(base+top)/2,.045,.060,top-base)
for z in [4.65,5.38,6.12,6.83,7.36]:
    half=min(2.70,math.sqrt(max(0,2.80**2-max(0,z-4.8)**2)))
    box('ashlar_0',0,-.51,z,2*half,.075,.045)
    for k in range(int(half*2/.17)):
        x=-half+.11+k*.17;height=.13+.035*(k%5)
        if z+height<4.8+math.sqrt(max(0,2.77**2-x*x)):
            box('ashlar_'+str(k%7),x,-.47,z+height/2+.023,.09,.10,height)
for index,(x,height) in enumerate(relief_people):
    # Head, turned neck and shoulders project from the backing only by centimetres.
    head=base+height-.12
    ellipsoid(x+.035*(index-2),-.26,head,.115,.10,.145)
    limb((x,-.32,head-.13),(x,-.30,head-.27),.06)
    ellipsoid(x,-.32,head-.36,.23,.11,.15)
    # Flowing robed silhouette, ribbed into vertical cloth folds.
    vertices=[];levels=9;sides=16
    for j in range(levels):
        t=j/(levels-1);z=base+.13+t*(height-.58)
        center=x+.11*math.sin(t*math.pi+index*.7)
        width=.23+.065*math.sin(t*math.pi)-.075*t
        for k in range(sides):
            angle=math.tau*k/sides
            fold=1+.10*math.cos(angle*5+t*1.7)
            vertices.append(point(center+width*math.cos(angle)*fold,-.33+.13*math.sin(angle)*fold,z))
    batch('stone').add(vertices,[(j*sides+k,j*sides+(k+1)%sides,(j+1)*sides+(k+1)%sides,(j+1)*sides+k) for j in range(levels-1) for k in range(sides)])
    for side in [-1,1]:
        limb((x+side*.12,-.29,base+.21),(x+side*.17,-.26,base+.04),.055)
        ellipsoid(x+side*.17,-.23,base+.035,.12,.09,.042)
    shoulder=base+height-.38
    if index==3:
        poses=[[(x-.19,-.25,shoulder),(x-.32,-.17,shoulder+.38),(x-.37,-.16,shoulder+.70)],[(x+.19,-.25,shoulder),(x+.39,-.18,shoulder+.18),(x+.61,-.18,shoulder+.34)]]
    else:
        poses=[[(x-.20,-.24,shoulder),(x-.28,-.19,shoulder-.30),(x-.10,-.13,shoulder-.42)],[(x+.20,-.24,shoulder),(x+.31,-.18,shoulder-.26),(x+.10,-.13,shoulder-.39)]]
    for pose in poses:
        for a,b in zip(pose,pose[1:]):limb(a,b,.065)
        ellipsoid(*pose[-1],.075,.065,.07)
    if index in [0,1,4]:
        box('ashlar_0',x,-.19,base+.55,.48,.055,.03)
        for side in [-1,1]:limb((x+side*.24,-.19,base+.09),(x+side*.24,-.19,base+.91),.018)
        for k in range(5):box('ashlar_0',x-.20+k*.10,-.19,base+.70,.014,.02,.26)

added=[]
for key,geometry in batches.items():
    obj=geometry.finish();added.append(obj.name)
    if key=='stone':
        for polygon in obj.data.polygons:polygon.use_smooth=True
for layer in bpy.context.scene.view_layers:layer.update()
changed=[obj.name for obj in originals if fingerprint(obj)!=before[obj.name]]
assert all(name.startswith('OLD_') for name in changed),changed
for name in ['room-studies.json','room-spaces.json','building-review.json']:
    (OUT/name).write_bytes((ROOT/'result/blender/stage51'/name).read_bytes())
audit={'version':52,'baseline':51,'changedExistingObjects':changed,'changedOtherObjects':[n for n in changed if not n.startswith('OLD_')],'archivedWall':wall.name,'stoneBlocks':block_count,'windowCount':len(windows),'windowColumns':3,'reliefFigureCount':len(relief_people),'removedCentralBarFaces':len(remove),'removedDoorFaces':removed_door_faces,'addedObjects':added,'origin':list(origin),'right':list(right),'outward':list(outward),'camera':list(point(1.6,21,7.2)),'target':list(point(0,0,6.6)),'sourcePage':'https://webbyates.com/projects/the-old-building/','reference':'data/建筑图片/OLD_Old Building/01_建筑实拍/campus_photos_round2_OLD_old_webbyates_01.jpg','limitations':['Photo capture date unknown; facade dimensions estimated','Frith five-figure relief is a shallow photo-guided approximation, not a sculpture scan; heraldic carving unresolved; no source photo published','Other elevations and roof have not yet passed an exterior fidelity review','Full OLD interiors are not reconstructed']}
(OUT/'old-houghton-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v52.blend'))
print('OLD_HOUGHTON_SAVED',block_count,len(windows),len(remove))
