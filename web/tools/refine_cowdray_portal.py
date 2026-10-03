"""Rebuild Cowdray's photographed corner portal without a historical stage chain.
Run in Blender Text Editor. Source dimensions are estimates except the guide's
three steps and 73cm active opening; a nominal two-leaf width is an estimate.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import sys
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage118';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,materials
baseline=ROOT/'result/blender/LSE_campus_detailed_v117.blend'
current=ROOT/'result/blender/LSE_campus_detailed_v118.blend'
rebuild_current=not baseline.exists()
bpy.ops.wm.open_mainfile(filepath=str(current if rebuild_current else baseline))
if rebuild_current:
    previous=json.loads((OUT/'cow-portal-audit.json').read_text())
    for name in previous['addedObjects']:
        obj=bpy.data.objects[name];mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
        if not mesh.users:bpy.data.meshes.remove(mesh)
    for name in previous['archivedObjects']:
        obj=bpy.data.objects[name];obj.hide_render=previous['originalVisibility'][name];obj.hide_set(obj.hide_render)
    for m in list(bpy.data.materials):
        if m.name.startswith('COW_V118_') and not m.users:bpy.data.materials.remove(m)
for scene in bpy.data.scenes:
    for layer in scene.view_layers:layer.update()
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
collection=bpy.data.collections['COW_EXTERIOR']
def fingerprint(o):
    h=hashlib.sha256(str([list(r) for r in o.matrix_world]).encode())
    if o.type=='MESH':
        v=array.array('f',[0])*(3*len(o.data.vertices));i=array.array('i',[0])*len(o.data.loops)
        o.data.vertices.foreach_get('co',v);o.data.loops.foreach_get('vertex_index',i)
        h.update(v.tobytes());h.update(i.tobytes())
    h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode())
    return h.hexdigest()
before={o.name:fingerprint(o) for o in bpy.data.objects}
visibility={o.name:o.hide_render for o in bpy.data.objects}
archived=[]
for o in list(collection.all_objects):
    if o.hide_render:continue
    part=o.name.removeprefix('COW_D5_')
    if part.startswith(('portal_','corner_portal_','corner_arch_spandrel_','entrance_', 'door_', 'arched_fanlight_', 'rusticated_portal_')):
        o.hide_render=True;o.hide_set(True);archived.append(o.name)
assert len(archived)==20,(len(archived),archived)
ring=next(b['rings'][0] for b in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings'] if b['code']=='COW')
a,b=[Vector((*ring[i],0)) for i in [4,5]]
axis=(b-a).normalized();normal=Vector((-axis.y,axis.x,0));origin=(a+b)/2;span=(b-a).length
angle=math.atan2(axis.y,axis.x)
materials.clear()
for key,source in [('stone','HERITAGE09_stone'),('trim','HERITAGE09_trim'),('glass','HERITAGE09_glass'),('wood','HERITAGE09_wood'),('bronze','HERITAGE09_gold')]:
    m=bpy.data.materials[source].copy();m.name='COW_V118_'+key;materials[key]=m
wood=materials['wood'];wood.diffuse_color=(.043,.032,.023,1)
wood.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=wood.diffuse_color
wood.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.66
bronze=materials['bronze'];bronze.diffuse_color=(.24,.17,.065,1)
bronze.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=bronze.diffuse_color
bronze.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.46
batches={}
def batch(key):
    if key not in batches:batches[key]=Geometry('COW','portal118_'+key,key)
    return batches[key]
def point(x,d,z):return origin+axis*x+normal*d+Vector((0,0,z))
def box(key,x,d,z,w,t,h):batch(key).box(point(x,d,z),(w,t,h),angle)
def slab(key,outline,back,front):
    area=sum(x0*z1-x1*z0 for (x0,z0),(x1,z1) in zip(outline,outline[1:]+outline[:1]))
    if area<0:outline=list(reversed(outline))
    vertices=[point(x,d,z) for d in [back,front] for x,z in outline]
    n=len(outline);faces=[tuple(range(n)),tuple(reversed(range(n,2*n)))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    batch(key).add(vertices,faces)
def tube(key,coords,radius,sides=8):
    # Relief ribs use round sections, authored from the visible scroll silhouette.
    vertices=[]
    for i,(x,z,d) in enumerate(coords):
        pa=Vector(coords[max(0,i-1)][:2]);pb=Vector(coords[min(len(coords)-1,i+1)][:2])
        tangent=(pb-pa).normalized();perp=Vector((-tangent.y,tangent.x))
        for j in range(sides):
            t=j*math.tau/sides
            vertices.append(point(x+perp.x*radius*math.cos(t),d+radius*math.sin(t),z+perp.y*radius*math.cos(t)))
    faces=[]
    for i in range(len(coords)-1):
        for j in range(sides):faces.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))
    faces += [tuple(reversed(range(sides))),tuple((len(coords)-1)*sides+j for j in range(sides))]
    batch(key).add(vertices,[tuple(reversed(face)) for face in faces])

threshold=.45;door_width=1.46;door_top=2.67;spring=2.92;radius=.84;rise=.74
# Thick corner wall partitions; no full rectangle behind the fanlight or door.
for sign in [-1,1]:box('stone',sign*(span/2+radius)/2,-.22,2.45,span/2-radius,.44,4.9)
box('stone',0,-.22,threshold/2,2*radius,.44,threshold)
for i in range(32):
    t0,t1=i*math.pi/32,(i+1)*math.pi/32
    x0,x1=radius*math.cos(t0),radius*math.cos(t1)
    z0,z1=spring+rise*math.sin(t0),spring+rise*math.sin(t1)
    slab('stone',[(x0,z0),(x1,z1),(x1,4.90),(x0,4.90)],-.44,0)
# Nominal two-leaf clear width, constrained by the documented active opening.
leaf_width=door_width/2
for sign in [-1,1]:
    x=sign*leaf_width/2;lo=threshold;hi=door_top;glass_lo=1.185;glass_hi=hi-.13;w=leaf_width-.14
    for offset in [-1,1]:box('wood',x+offset*(leaf_width/2-.038),-.045,(lo+hi)/2,.076,.13,hi-lo)
    for z,h in [(lo+.065,.13),(1.12,.13),(hi-.065,.13)]:box('wood',x,-.045,z,leaf_width,.13,h)
    box('wood',x,-.07,.82,leaf_width-.12,.08,.46)
    # Raised lower panels and six upper lights. Glazing has a genuine void behind it.
    for offset in [-1,1]:box('wood',x+offset*(w/2-.025),.005,.82,.05,.06,.48)
    for z in [.57,1.06]:box('wood',x,.005,z,w,.06,.055)
    box('glass',x,-.067,(glass_lo+glass_hi)/2,w,.025,glass_hi-glass_lo)
    for j in range(1,3):box('wood',x-w/2+w*j/3,.015,(glass_lo+glass_hi)/2,.028,.075,glass_hi-glass_lo)
    for z in [glass_lo,(glass_lo+glass_hi)/2,glass_hi]:box('wood',x,.015,z,w,.075,.035)
    box('bronze',x-sign*.22,.082,1.48,.030,.032,.24)
    box('bronze',x-sign*.22,.045,1.48,.075,.022,.31)
for sign in [-1,1]:box('wood',sign*(door_width/2+.07),-.055,(threshold+spring)/2,.14,.18,spring-threshold)
box('wood',0,-.055,door_top+.12,door_width+.18,.18,.20)
# The transom and arched head are one glazed aperture, not a timber backing slab.
outline=[(-radius,door_top+.22),(radius,door_top+.22)]+[(radius*math.cos(i*math.pi/32),spring+rise*math.sin(i*math.pi/32)) for i in range(33)]
batch('glass').add([point(x,-.075,z) for x,z in outline],[tuple(reversed(range(len(outline))))])
for i in range(32):
    a0,a1=i*math.pi/32,(i+1)*math.pi/32
    v=[point(r*math.cos(t),d,spring+h*math.sin(t)) for d in [-.02,.25]
       for r,h,t in [(radius,rise,a0),(radius,rise,a1),(radius+.22,rise+.22,a1),(radius+.22,rise+.22,a0)]]
    batch('stone').add(v,[tuple(reversed(face)) for face in [(0,1,2,3),(4,7,6,5),(0,4,5,1),(3,2,6,7),(1,5,6,2),(0,3,7,4)]])
    # Inner dark frame and fine carved bead around the opening.
    coords=[(radius*math.cos(t),spring+rise*math.sin(t),.028) for t in [a0,a1]]
    tube('wood',coords,.035)
for shift in [-.42,0,.42]:
    h=rise*math.sqrt(1-(shift/radius)**2)
    box('wood',shift,.025,(door_top+.22+spring+h)/2,.026,.075,spring+h-door_top-.22)
box('wood',0,.025,spring,2*radius,.075,.030)
# Paired moulded pilasters, slender reeds, stepped bases and volute capitals.
for sign in [-1,1]:
    x=sign*1.13
    for z,w,h,t in [(.22,.48,.44,.60),(.49,.39,.10,.52),(.64,.31,.18,.46),(2.96,.40,.10,.53),(3.12,.49,.17,.59),(3.25,.56,.10,.66)]:
        box('trim',x,.18,z,w,t,h)
    box('stone',x,.16,1.81,.28,.43,2.18)
    for dx in [-.086,0,.086]:box('trim',x+dx,.39,1.81,.025,.045,2.12)
    for side in [-1,1]:
        coords=[]
        for i in range(25):
            t=i*math.tau*1.15/24;r=.09*(1-i/31)
            coords.append((x+side*(.17+r*math.cos(t)),3.08+r*math.sin(t),.43))
        tube('trim',coords,.025)
# Layered entablature meets the retained first-floor moulding without inventing a canopy.
for z,w,h,t in [(3.84,2.56,.14,.47),(4.05,2.63,.28,.47),(4.25,2.75,.10,.62),(4.39,2.88,.15,.75),(4.52,2.95,.09,.82),(4.66,3.08,.14,.88)]:
    box('trim',0,.17,z,w,t,h)
# Stylised carved mask and acanthus scrolls: silhouette guided by photography,
# not a scan or a claim to replicate every historic carved feature.
for sign in [-1,1]:
    for side in [-1,1]:
        coords=[]
        for i in range(25):
            t=i*math.pi*1.6/24;r=.20*(1-i/38)
            coords.append((sign*(.38+r*math.cos(t)),4.06+side*r*math.sin(t)*.65,.43))
        tube('stone',coords,.047)
    tube('stone',[(sign*(.15+.07*i),3.89+.08*math.sin(i*math.pi/6),.43) for i in range(7)],.055)
# Small relief face formed by closed curved surfaces, without photographic textures.
vertices=[]
for i in range(1,12):
    theta=i*math.pi/12
    for j in range(24):
        phi=j*math.tau/24
        vertices.append(point(.13*math.sin(theta)*math.cos(phi),.45+.09*math.sin(theta)*math.sin(phi),4.05+.19*math.cos(theta)))
faces=[]
for i in range(10):
    for j in range(24):faces.append((i*24+j,i*24+(j+1)%24,(i+1)*24+(j+1)%24,(i+1)*24+j))
faces += [tuple(reversed(range(24))),tuple(240+j for j in range(24))]
batch('stone').add(vertices,[tuple(reversed(face)) for face in faces])
box('stone',0,.535,4.06,.040,.045,.14)
for sign in [-1,1]:tube('stone',[(sign*.025,4.14,.525),(sign*.06,4.15,.53),(sign*.10,4.13,.50)],.021)
box('trim',0,.27,3.69,.24,.48,.27)
# Three medium risers within the published 11-17cm interval; tread sizes estimated.
steps=[]
for i in range(3):
    high=.15*(i+1);outer=1.20-.30*i;inner=-.10
    box('stone',0,(outer+inner)/2,high/2,2.45,outer-inner,high)
    steps.append({'top':high,'outer':outer,'inner':inner,'width':2.45,'probeDepth':outer-.15})
# Plaques are visible fittings; their contents and function are not invented.
for z in [1.24,1.73]:box('bronze',.98,.28,z,.22,.025,.20)
added=[]
for geometry in batches.values():
    obj=geometry.finish();added.append(obj.name)
    obj['scope']='Photo-guided Cowdray entrance; three documented steps, other dimensions and historic carving approximate'
    for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
assert all(fingerprint(bpy.data.objects[n])==h for n,h in before.items())
audit=dict(version=118,baseline=117,originalFingerprints=before,originalVisibility=visibility,archivedObjects=archived,addedObjects=added,
           origin=list(origin),axis=list(axis),normal=list(normal),span=span,steps=steps,threshold=threshold,
           doorWidth=door_width,activeOpeningReference=.73,doorTop=door_top,spring=spring,archRadius=radius,archRise=rise,
           sourceUrls=['https://www.accessable.co.uk/london-school-of-economics/access-guides/cowdray-house','https://www.russellcawberry.com/projects/cowdray-house'],
           limits=['Guide survey and photo capture dates are unverified; not a 2026 site survey','Three steps and 73cm active opening supported; nominal two-leaf width, risers, treads and other dimensions estimated','Carved mask, leaves and capitals are authored approximations, not scans','Roof, street-window centres and existing independent interior study retained; complete COW still unverified'])
(OUT/'cow-portal-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(current))
print('COWDRAY_PORTAL_SAVED',len(archived),len(added),flush=True)
