"""Rebuild OLD's lower Clare Market bays from the supplied exterior photographs.
Use Blender's Text Editor. Native52 and all other buildings remain intact.
Five bay registration is photo guided on the existing GIS edge, not surveyed.
"""
from pathlib import Path
import bpy,bmesh,json,math,sys,array,hashlib
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage53';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v52.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
collection=bpy.data.collections['OLD_EXTERIOR']
originals=list(bpy.data.objects)
def fingerprint(obj):
    digest=hashlib.sha256(str([list(row)for row in obj.matrix_world]).encode())
    if obj.type=='MESH':digest.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
    return digest.hexdigest()
before={obj.name:fingerprint(obj)for obj in originals}
ring=next(b for b in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings']if b['code']=='OLD')['rings'][0]
a,b=Vector((*ring[7],0)),Vector((*ring[8],0));origin=(a+b)/2;right=(a-b).normalized();outward=Vector((right.y,-right.x,0));length=(b-a).length
hidden=[]
for obj in list(collection.all_objects):
    if obj.name.startswith('OLD_V49_') and not obj.hide_render:
        obj.hide_render=True;obj.hide_set(True);hidden.append(obj.name)
# Remove old local window ornaments as well as the old wall faces. Wider depth
# coverage eliminates the generic reveal/sill geometry previously left behind.
removed={}
for obj in list(collection.all_objects):
    if obj.type!='MESH' or obj.hide_render:continue
    bm=bmesh.new();bm.from_mesh(obj.data);faces=[]
    for face in bm.faces:
        points=[obj.matrix_world@v.co-origin for v in face.verts]
        if all(abs(p.dot(outward))<1.20 and abs(p.dot(right))<length/2+.04 and p.z<=11.81 for p in points):faces.append(face)
    if faces:
        removed[obj.name]=len(faces);bmesh.ops.delete(bm,geom=faces,context='FACES');bm.to_mesh(obj.data);obj.data.update()
    bm.free()
materials.clear()
for key,color in {'stone':(.59,.58,.535),'edge':(.64,.63,.58),'blue':(.014,.085,.20),'glass':(.16,.22,.24),'metal':(.29,.33,.34),'soil':(.08,.075,.05),'leaf':(.08,.16,.055),'red':(.47,.008,.016),'white':(.86,.86,.83),'letter':(.65,.66,.65)}.items():
    mat=bpy.data.materials.new('OLD_V53_'+key);mat.use_nodes=True;mat.diffuse_color=(*color,1)
    shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=mat.diffuse_color;shader.inputs['Roughness'].default_value=.8
    if key in {'glass','blue','metal'}:shader.inputs['Roughness'].default_value=.3;shader.inputs['Metallic'].default_value=.2
    materials[key]=mat
batches={}
def batch(key):
    if key not in batches:
        batches[key]=Geometry('OLD','clare_'+key,key);batches[key].name='OLD_V53_Clare_'+key
    return batches[key]
def point(x,y,z):return origin+right*x+outward*y+Vector((0,0,z))
def box(key,x,y,z,w,d,h):batch(key).box(point(x,y,z),(w,d,h),math.atan2(right.y,right.x))
def beam(key,start,end,r=.024):
    pa,pb=point(*start),point(*end);axis=(pb-pa).normalized();u=axis.cross(Vector((0,0,1)))
    if u.length<.01:u=right.copy()
    u.normalize();v=axis.cross(u).normalized();count=8
    vertices=[p+r*(u*math.cos(i*math.tau/count)+v*math.sin(i*math.tau/count))for p in [pa,pb]for i in range(count)]
    batch(key).add(vertices,[(i,(i+1)%count,(i+1)%count+count,i+count)for i in range(count)]+[tuple(reversed(range(count))),tuple(range(count,2*count))])
centers=[-length/2+length*(i+.5)/5 for i in range(5)];pier=.92;width=length/5-pier
# Four ordinary glazed bays beside the blue Student Services doorway.
for index in range(6):
    x=-length/2+length*index/5
    for row in range(20):box('stone',x,-.205,.295+row*.59,pier,.46,.582)
for z,h in [(.35,.70),(5.85,1.25),(10.80,2.0)]:
    for i,x in enumerate(centers):box('stone',x,-.205,z,width+.025,.46,h)
for index,x in enumerate(centers):
    for z,h in [(2.95,4.40),(8.05,3.10)]:
        box('glass',x,-.24,z,width-.15,.035,h-.12)
        for sx in [-1,1]:box('blue',x+sx*(width/2-.045),-.11,z,.09,.15,h)
        for zz in [z-h/2,z+h/2]:box('blue',x,-.11,zz,width,.15,.095)
        columns=2 if index==0 else 3
        for j in range(1,columns):box('blue',x-width/2+width*j/columns,-.10,z,.052,.15,h)
        if index!=0 or z>5:
            rows=5 if z<5 else 4
            for j in range(1,rows):box('blue',x,-.10,z-h/2+h*j/rows,width,.15,.045)
    box('edge',x,.045,.73,width+.24,.35,.15)
    # Recessed Frith frieze reserves; figurative panel carving not guessed here.
    box('edge',x,-.015,5.85,width,.16,1.05)
    for zz in [5.34,6.37]:box('edge',x,.045,zz,width+.06,.12,.08)
    for sx in [-1,1]:box('edge',x+sx*width/2,.045,5.85,.07,.12,1.10)
x=centers[0]
box('blue',x,-.075,3.11,width,.21,.50)
box('blue',x,-.075,3.72,width,.21,.085)
for sx in [-1,1]:beam('metal',(x+sx*.13,.06,1.35),(x+sx*.13,.06,2.02),.018)
font=bpy.data.fonts.load('/System/Library/Fonts/Supplemental/Arial.ttf')
rotation=Matrix((right,Vector((0,0,1)),outward)).transposed().to_euler()
for text,z,size in [('Student Services Centre',3.21,.115),('Old Building',2.97,.18)]:
    curve=bpy.data.curves.new('OLD_V53_Portal_'+text,'FONT');curve.body=text;curve.font=font;curve.align_x='CENTER';curve.size=size;curve.extrude=.002;curve.materials.append(materials['letter'])
    obj=bpy.data.objects.new(curve.name,curve);collection.objects.link(obj);obj.location=point(x,.055,z);obj.rotation_euler=rotation
for step in range(4):
    top=.73-step*.17;box('edge',x,.50+step*.36,(top+.05)/2,width+.60,.41,top-.05)
for sx in [-1,1]:
    rail=x+sx*(width/2+.18)
    beam('metal',(rail,.37,1.57),(rail,1.69,.97))
    for y,z in [(.37,1.57),(1.69,.97)]:beam('metal',(rail,y,z-.77),(rail,y,z),.021)
planter_left=centers[1]-width/2;planter_right=centers[-1]+width/2
planter_length=planter_right-planter_left;planter_center=(planter_left+planter_right)/2
box('stone',planter_center,.85,.52,planter_length,1.05,1.00);box('soil',planter_center,.85,1.03,planter_length-.18,.86,.055)
for i in range(1,11):box('edge',planter_left+planter_length*i/11,1.38,.52,.014,.025,.98)
for j in range(34):
    x=planter_left+.18+(planter_length-.36)*j/33
    for k in range(5):
        angle=j*.61+k*math.tau/5;span=.28+.07*((j+k)%3);vertices=[]
        for i in range(13):
            t=i/12;width_leaf=.075*math.sin(math.pi*t);distance=span*t;height=1.07+.50*math.sin(t*1.30)-.15*t*t
            for side in [-1,1]:vertices.append(point(x+distance*math.cos(angle)-side*width_leaf*math.sin(angle),.85+distance*math.sin(angle)+side*width_leaf*math.cos(angle),height))
        faces=[(2*i,2*i+1,2*i+3,2*i+2)for i in range(12)];batch('leaf').add(vertices,faces+[tuple(reversed(f))for f in faces])
# Preserve the photographed red-front/white-side sculpture while moving it out
# of the doorway line into the forecourt beside the first planter bay.
profiles=json.loads((ROOT/'web/tools/lse-letter-profiles.json').read_text())['letters']
sign=point(centers[0]+1.55,2.50,.055)
for letter,outline in profiles.items():
    for key,lo,hi in [('white',-.18,.18),('red',.181,.191)]:
        pts=[sign+right*px+Vector((0,0,pz))+outward*depth for depth in [lo,hi]for px,pz in outline]
        n=len(outline);faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n)for i in range(n)]
        batch(key).add(pts,[tuple(reversed(f))for f in faces])
added=[g.finish().name for g in batches.values()]
for layer in bpy.context.scene.view_layers:layer.update()
changed=[obj.name for obj in originals if fingerprint(obj)!=before[obj.name]]
assert all(n.startswith('OLD_')for n in changed),changed
for name in ['room-studies.json','room-spaces.json','building-review.json']:(OUT/name).write_bytes((ROOT/'result/blender/stage52'/name).read_bytes())
audit={'version':53,'baseline':52,'changedExistingObjects':changed,'changedOtherObjects':[n for n in changed if not n.startswith('OLD_')],'hiddenPreviousObjects':hidden,'removedLocalFaces':removed,'bayCount':5,'ordinaryGlazedBays':4,'bayWidth':width,'edgeLength':length,'addedObjects':added,'camera':list(point(-2,22,7.8)),'target':list(point(0,.4,5.8)),'references':['data/collections/public-realm-2026/user-references/reference-04.png','data/collections/public-realm-2026/user-references/reference-08.png'],'limitations':['Five bays registered approximately on the existing GIS footprint from supplied photos; dimensions not surveyed','Frith Clare Market figurative panels remain reserved for later modelling','Upper elevation and roof remain unverified; no current roof survey available','Houghton entrance refinement and all other buildings preserved']}
(OUT/'old-clare-proportions-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v53.blend'))
print('OLD_CLARE_PROPORTIONS_SAVED',len(changed),width)
