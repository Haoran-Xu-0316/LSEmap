"""Photo-guided OLD Clare Market lower facade and forecourt.
Run in Blender's Text Editor. Preserve the native48 archive; dimensions and
registration on the central north GIS edge are estimates, not a measured survey.
"""
from pathlib import Path
import bpy,bmesh,json,math,sys,hashlib,array
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage49'
OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v48.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
originals=list(bpy.data.objects)
def fingerprint(obj):
    h=hashlib.sha256(str([list(r)for r in obj.matrix_world]).encode())
    if obj.type=='MESH':h.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
    return h.hexdigest()
before={o.name:fingerprint(o)for o in originals}
site=json.loads((ROOT/'result/blender/site_geometry.json').read_text())
ring=next(b for b in site['buildings']if b['code']=='OLD')['rings'][0]
a,b=Vector((*ring[7],0)),Vector((*ring[8],0))
origin=(a+b)/2;right=(a-b).normalized();outward=Vector((right.y,-right.x,0));length=(b-a).length
collection=bpy.data.collections['OLD_EXTERIOR']
archive=bpy.data.collections.new('OLD_V49_ORIGINAL_CLARE_MARKET');bpy.context.scene.collection.children.link(archive)
removed={}
# Replace only local lower-facade polygons. The complete original component
# survives as a hidden archival copy; all other elevations stay in place.
for obj in list(collection.all_objects):
    if obj.type!='MESH' or obj.hide_render:continue
    bm=bmesh.new();bm.from_mesh(obj.data);targets=[]
    for face in bm.faces:
        points=[obj.matrix_world@v.co-origin for v in face.verts]
        if all(abs(p.dot(outward))<.72 and abs(p.dot(right))<length/2+.08 for p in points) and sum(p.z for p in points)/len(points)<11.80:
            targets.append(face)
    if targets:
        saved=obj.copy();saved.data=obj.data.copy();saved.name=obj.name+'_V49_ARCHIVE';archive.objects.link(saved);saved.hide_render=True;saved.hide_set(True)
        removed[obj.name]=len(targets)
        bmesh.ops.delete(bm,geom=targets,context='FACES');bm.to_mesh(obj.data);obj.data.update()
    bm.free()
materials.clear()
palette={'stone':(.58,.56,.50),'edge':(.65,.63,.56),'joint':(.37,.36,.32),'blue':(.012,.082,.19),'glass':(.18,.25,.28),'metal':(.29,.33,.34),'soil':(.10,.085,.06),'leaf':(.10,.17,.055),'red':(.47,.008,.016),'white':(.86,.86,.83),'letter':(.65,.66,.65),'flower':(.72,.48,.018)}
for key,color in palette.items():
    mat=bpy.data.materials.new('OLD_V49_'+key);mat.diffuse_color=(*color,1);mat.use_nodes=True
    shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=mat.diffuse_color;shader.inputs['Roughness'].default_value=.80
    if key=='glass':shader.inputs['Roughness'].default_value=.22;shader.inputs['Metallic'].default_value=.15
    if key=='blue':shader.inputs['Roughness'].default_value=.42;shader.inputs['Metallic'].default_value=.18
    if key in ['stone','edge']:
        nodes=mat.node_tree.nodes;links=mat.node_tree.links
        tex=nodes.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=18
        coords=nodes.new('ShaderNodeTexCoord');links.new(coords.outputs['Generated'],tex.inputs['Vector'])
        ramp=nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=tuple(c*.94 for c in color)+(1,);ramp.color_ramp.elements[1].color=tuple(c*1.025 for c in color)+(1,)
        links.new(tex.outputs['Fac'],ramp.inputs['Fac']);links.new(ramp.outputs['Color'],shader.inputs['Base Color'])
        bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.0007
        links.new(tex.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],shader.inputs['Normal'])
    materials[key]=mat
batches={}
def batch(key):
    if key not in batches:
        g=Geometry('OLD','clare_'+key,key);g.name='OLD_V49_Clare_'+key;batches[key]=g
    return batches[key]
def point(x,y,z):return origin+right*x+outward*y+Vector((0,0,z))
def box(key,x,y,z,w,d,h):batch(key).box(point(x,y,z),(w,d,h),math.atan2(right.y,right.x))
def beam(key,start,end,r=.025):
    pa,pb=point(*start),point(*end);axis=(pb-pa).normalized();u=axis.cross(Vector((0,0,1)))
    if u.length<.01:u=right.copy()
    u.normalize();v=axis.cross(u).normalized();n=8
    vertices=[p+r*(u*math.cos(i*math.tau/n)+v*math.sin(i*math.tau/n))for p in [pa,pb]for i in range(n)]
    batch(key).add(vertices,[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n)for i in range(n)])
centers=[-length/3,0,length/3]
# Three tall lower bays, broad stone piers and separate relief spandrels.
for x in [-length/2,*[(centers[i]+centers[i+1])/2 for i in [0,1]],length/2]:box('stone',x,-.20,5.9,.95,.46,11.8)
for z,h in [(.35,.70),(5.85,1.25),(10.80,2.0)]:box('stone',0,-.20,z,length,.46,h)
for i,x in enumerate(centers):
    width=length/3-.95
    for z,h in [(2.95,4.40),(8.05,3.10)]:
        box('glass',x,-.13,z,width-.16,.035,h-.12)
        for side in [-1,1]:box('blue',x+side*(width/2-.045),.008,z,.09,.13,h)
        for zz in [z-h/2,z+h/2]:box('blue',x,.008,zz,width,.13,.095)
        lights=2 if i==0 else 3
        for j in range(1,lights):box('blue',x-width/2+width*j/lights,.02,z,.055,.14,h)
        for j in range(1,4):
            if i!=0 or z>5:box('blue',x,.02,z-h/2+h*j/4,width,.14,.050)
    box('edge',x,.025,5.85,width,.10,1.05)
    # Recessed panel edges establish the photographed Frith frieze positions.
    # Figurative relief carving is not invented or projected from private photos.
    for zz in [5.34,6.37]:box('edge',x,.09,zz,width+.06,.13,.08)
    box('edge',x,.17,.73,width+.25,.37,.15)
# The blue portal surrounds the left bay and a recessed glazed entrance.
x=centers[0];width=length/3-.95
for sx in [-1,1]:box('blue',x+sx*(width/2+.03),.06,2.95,.18,.29,4.44)
box('blue',x,.06,3.14,width,.24,.50)
box('blue',x,.06,4.20,width,.14,.065)
box('blue',x,.07,3.73,width,.26,.10)
box('blue',x,.07,2.98,.055,.19,1.94)
for sx in [-1,1]:beam('metal',(x+sx*.15,.19,1.38),(x+sx*.15,.19,2.04),.018)
font=bpy.data.fonts.load('/System/Library/Fonts/Supplemental/Arial.ttf')
rotation=Matrix((right,Vector((0,0,1)),outward)).transposed().to_euler()
for word,z,size in [('Student Services Centre',3.21,.20),('Old Building',2.96,.29)]:
    curve=bpy.data.curves.new('OLD_V49_Portal_'+word,'FONT');curve.body=word;curve.font=font;curve.align_x='CENTER';curve.size=size;curve.extrude=.002;curve.materials.append(materials['letter'])
    obj=bpy.data.objects.new(curve.name,curve);collection.objects.link(obj);obj.location=point(x,.22,z);obj.rotation_euler=rotation
# Photographed shallow steps, stainless rails and stone raised planter.
measured_steps=[]
for step in range(4):
    top=.73-step*.17;start=len(batch('edge').vertices)
    box('edge',x,.52+step*.36,(top+.05)/2,width+.55,.40,top-.05)
    vertices=batch('edge').vertices[start:]
    measured_steps.append([min(p[2]for p in vertices),max(p[2]for p in vertices)])
for sx in [-1,1]:
    beam('metal',(x+sx*(width/2+.18),.42,1.57),(x+sx*(width/2+.18),1.65,.97),.026)
    for y,z in [(.42,1.57),(1.65,.97)]:beam('metal',(x+sx*(width/2+.18),y,z-.77),(x+sx*(width/2+.18),y,z),.022)
box('stone',1.50,1.04,.52,8.8,1.1,1.00);box('soil',1.50,1.04,1.03,8.45,.90,.06)
for j in range(14):
    px=-2.25+j*.57
    for k in range(5):
        angle=j*.61+k*math.tau/5;span=.30+.035*((j+k)%3)
        vertices=[];faces=[]
        for step in range(13):
            t=step/12;distance=span*t;width=.075*math.sin(math.pi*t)
            height=1.06+.42*math.sin(t*1.25)-.12*t*t
            for side in [-1,1]:vertices.append(point(px+distance*math.cos(angle)-side*width*math.sin(angle),1.03+distance*math.sin(angle)+side*width*math.cos(angle),height))
        faces=[(2*i,2*i+1,2*i+3,2*i+2)for i in range(12)]
        batch('leaf').add(vertices,faces+[tuple(reversed(f))for f in faces])
for px in [3.15,4.20]:
    beam('leaf',(px,1.03,1.04),(px,1.03,1.95),.013)
    for k in range(6):
        angle=k*math.tau/6
        petal=[point(px,1.03,1.93),point(px+.12*math.cos(angle-.28),1.03+.12*math.sin(angle-.28),2.05),point(px+.16*math.cos(angle),1.03+.16*math.sin(angle),2.17),point(px+.12*math.cos(angle+.28),1.03+.12*math.sin(angle+.28),2.05)]
        batch('flower').add(petal,[(0,1,2,3),(3,2,1,0)])
# Recessed ashlar courses follow the solid stone piers and planter panels.
for xx in [-length/2,*[(centers[i]+centers[i+1])/2 for i in [0,1]],length/2]:
    for row in range(1,20):box('joint',xx,.034,row*.60,.94,.009,.009)
for xx in [-2.5,-1.5,-.5,.5,1.5,2.5,3.5,4.5,5.5]:box('joint',xx,1.595,.52,.008,.010,.96)
# Photo-guided joined LS sculpture, red front / white sides.
profiles=json.loads((ROOT/'web/tools/lse-letter-profiles.json').read_text())['letters']
sign=point(centers[0]+1.55,2.65,.055);scale=1.02
for letter,outline in profiles.items():
    for key,lo,hi in [('white',-.18,.18),('red',.181,.191)]:
        pts=[sign+right*(px*scale)+Vector((0,0,pz*scale))+outward*depth for depth in [lo,hi]for px,pz in outline]
        n=len(outline);faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n)for i in range(n)]
        # Source outline is clockwise; flip caps for this right/up/outward frame.
        batch(key).add(pts,[tuple(reversed(f))for f in faces])
added=[g.finish().name for g in batches.values()]
for layer in bpy.context.scene.view_layers:layer.update()
changed=[o.name for o in originals if fingerprint(o)!=before[o.name]]
assert set(changed)==set(removed),changed
for name in ['room-studies.json','room-spaces.json','building-review.json']:(OUT/name).write_bytes((ROOT/'result/blender/stage48'/name).read_bytes())
cam=point(0,14,8.0);target=point(0,.4,4.5)
audit={'version':49,'baseline':48,'edgeIndex':7,'edgeLength':length,'origin':list(origin),'right':list(right),'outward':list(outward),'measuredStepRanges':measured_steps,'removedLocalFaces':removed,'changedExistingObjects':changed,'addedObjects':added,'camera':list(cam),'target':list(target),'limitations':['Facade dimensions and registration estimated on the central Clare Market GIS edge from supplied photographs','Frith relief frames are modeled; figurative carving remains unresolved','Full Student Services interior is not reconstructed','2027 refurbishment plans are not used as current as-built evidence']}
(OUT/'old-clare-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v49.blend'))
print('OLD_CLARE_SAVED',len(changed),length)
