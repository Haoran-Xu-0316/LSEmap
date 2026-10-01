"""Rebuild the photographed three-bay Lincoln's Inn Fields face of 51L.
Run in Blender Text Editor. Preserve native 91, every original object and
all non-front components through owned mesh copies. Photo publication: July 2025;
capture date, absolute dimensions and roof layout remain unverified.
"""
from pathlib import Path
import array, hashlib, json, math, shutil, sys
import bpy, bmesh
from mathutils import Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'result/blender/stage92'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v91.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
profile = next(p for p in json.loads((ROOT/'result/blender/stage05/infill-geometry.json').read_text()) if p['code']=='51L')
wall = profile['walls'][1]
a = Vector((*wall['p'], 0))
right = Vector(((wall['q'][0]-wall['p'][0])/wall['length'], (wall['q'][1]-wall['p'][1])/wall['length'], 0))
normal = Vector((*wall['outward'], 0))
length, height = wall['length'], profile['height']
floor_height = height/profile['floors']
collection = bpy.data.collections['51L_EXTERIOR']

def fingerprint(obj):
    h = hashlib.sha256(str([list(r) for r in obj.matrix_world]).encode())
    if obj.type=='MESH':
        h.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        h.update(array.array('i', [loop.vertex_index for loop in obj.data.loops]).tobytes())
    h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return h.hexdigest()

def local(p):
    delta=p-a
    return Vector((delta.dot(right),delta.dot(normal),p.z))

before={o.name:fingerprint(o) for o in bpy.data.objects}
copies=[]
# Remove whole disconnected construction components. Never cut through a box,
# and never alter original objects or neighboring street-side components.
for source in list(collection.all_objects):
    if source.hide_render or source.type!='MESH':
        continue
    bm=bmesh.new()
    bm.from_mesh(source.data)
    bm.verts.ensure_lookup_table()
    seen=set()
    removed=[]
    for seed in bm.verts:
        if seed in seen: continue
        group=[];pending=[seed];seen.add(seed)
        while pending:
            v=pending.pop();group.append(v)
            for edge in v.link_edges:
                other=edge.other_vert(v)
                if other not in seen:seen.add(other);pending.append(other)
        points=[local(source.matrix_world@v.co) for v in group]
        center=sum(points,Vector())/len(points)
        if not (.05<center.x<length-.05 and abs(center.y)<.55):continue
        if not all(-.45<p.x<length+.45 and -.75<p.y<.8 for p in points):continue
        removed.extend(group)
    if removed:
        indices=[v.index for v in removed]
        copy=source.copy();copy.data=source.data.copy()
        copy.name='51L_D5_threebay92_retained_'+source.name.removeprefix('51L_')
        collection.objects.link(copy)
        bmesh.ops.delete(bm,geom=removed,context='VERTS')
        bm.to_mesh(copy.data)
        copy.data.update()
        source.hide_render=True;source.hide_set(True)
        copies.append({'source':source.name,'copy':copy.name,'removedVertices':sorted(indices)})
    bm.free()

materials.clear()
for key,name in {'brick':'INFILL_red','stone':'EXT20_pale','frame':'51L_V57_frame',
                 'glass':'EXT20_glass','metal':'EXT20_metal','wood':'EXT20_wood','brass':'EXT20_bronze'}.items():
    materials[key]=bpy.data.materials[name]
groups={}
def batch(key):
    if key not in groups:groups[key]=Geometry('51L','threebay92_'+key,key)
    return groups[key]
def point(x,d,z):return a+right*x+normal*d+Vector((0,0,z))
def box(key,x,d,z,w,t,h):batch(key).box(point(x,d,z),(w,t,h),math.atan2(right.y,right.x))
def prism(key, outline, back, front):
    count=len(outline)
    vs=[point(x,d,z)for d in [back,front]for x,z in outline]
    faces=[tuple(reversed(range(count))),tuple(range(count,2*count))]
    faces += [(j,(j+1)%count,(j+1)%count+count,j+count)for j in range(count)]
    batch(key).add(vs,faces)

pitch=length/3
width=pitch*.58
windows=[]
for floor in range(1,6):
    z0=floor*floor_height
    lo,hi=z0+.82,z0+floor_height-.62
    rows=3 if floor==5 else 4
    for bay in range(3):
        x=(bay+.5)*pitch
        for side in [-1,1]:
            box('brick',x+side*(pitch+width)/4,-.12,(lo+hi)/2,(pitch-width)/2,.30,hi-lo)
        box('brick',x,-.12,(z0+lo)/2,pitch,.30,lo-z0)
        box('brick',x,-.12,(hi+z0+floor_height)/2,pitch,.30,z0+floor_height-hi)
        box('glass',x,-.18,(lo+hi)/2,width,.035,hi-lo)
        for side in [-1,1]:box('frame',x+side*width/2,-.02,(lo+hi)/2,.06,.14,hi-lo)
        for j in range(rows+1):box('frame',x,0,lo+(hi-lo)*j/rows,width,.13,.033)
        for j in [1,2]:box('frame',x-width/2+width*j/3,0,(lo+hi)/2,.025,.12,hi-lo)
        box('stone',x,.04,lo-.05,width+.20,.38,.12)
        box('stone',x,.04,hi+.07,width+.16,.25,.12)
        prism('stone',[(x-.09,hi+.04),(x+.09,hi+.04),(x+.15,hi+.36),(x-.15,hi+.36)],.025,.18)
        windows.append({'floor':floor,'bay':bay,'centerX':x,'width':width,'lower':lo,'upper':hi,'columns':3,'rows':rows})
# Three ground arches, with the photographed timber entrance at the right.
lo=.40;spring=2.30;radius=width/2
for bay in range(3):
    x=(bay+.5)*pitch
    for side in [-1,1]:
        box('stone',x+side*(pitch+width)/4,-.12,floor_height/2,(pitch-width)/2,.30,floor_height)
    box('stone',x,-.12,lo/2,width,.30,lo)
    outline=[(x-radius,lo),(x+radius,lo)]+[(x+radius*math.cos(math.pi*j/24),spring+radius*math.sin(math.pi*j/24))for j in range(25)]
    prism('glass',outline,-.19,-.155)
    for j in range(24):
        t0,t1=math.pi*j/24,math.pi*(j+1)/24
        x0,x1=x+radius*math.cos(t0),x+radius*math.cos(t1)
        z0,z1=spring+radius*math.sin(t0),spring+radius*math.sin(t1)
        prism('stone',[(x1,z1),(x0,z0),(x0,floor_height),(x1,floor_height)],-.27,.03)
        outer=radius+.045
        prism('metal',[(x+radius*math.cos(t1),spring+radius*math.sin(t1)),
                       (x+radius*math.cos(t0),spring+radius*math.sin(t0)),
                       (x+outer*math.cos(t0),spring+outer*math.sin(t0)),
                       (x+outer*math.cos(t1),spring+outer*math.sin(t1))],-.05,.055)
    for side in [-1,1]:box('metal',x+side*radius,0,(lo+spring)/2,.045,.12,spring-lo)
    for z in [lo,1.31,spring]:box('metal',x,0,z,width,.12,.035)
    box('metal',x,0,(lo+spring)/2,.035,.12,spring-lo)
    box('metal',x,0,spring+radius/2,.035,.12,radius)
    if bay==0:
        # Lower timber panel, vertical stiles and transom retain the arched fanlight.
        box('wood',x,-.11,.73,width-.08,.08,.66)
        for side in [-1,1]:box('wood',x+side*(radius-.065),-.10,1.57,.10,.11,1.65)
        box('wood',x,-.09,1.03,width-.08,.11,.10)
        box('wood',x,-.09,2.11,width-.08,.11,.10)
        box('wood',x,-.09,1.57,.09,.11,1.16)
        box('brass',x-.16,.005,1.51,.025,.06,.22)
    else:
        for j in [1,2]:box('metal',x-radius+width*j/3,0,(lo+spring)/2,.025,.12,spring-lo)
    windows.append({'floor':0,'bay':bay,'centerX':x,'width':width,'spring':spring,'radius':radius,'timberEntry':bay==0})
# Retained facade proportions; restore the two prominent horizontal stone courses.
for z in [floor_height,5*floor_height,height-.22,height+.05]:
    box('stone',length/2,.075,z,length+.06,.46,.18)
# Narrow alternate blocks at the rounded-corner boundary, not heavy white bars.
for j in range(int(height/.42)):
    z=(j+.5)*.42
    if z<floor_height:continue
    box('stone',length-.17,.05,z,.22 if j%2 else .34,.19,.16)
box('metal',.045,.095,(height+.5)/2,.055,.07,height-.5)

added=[r['copy']for r in copies]
for key,g in groups.items():
    obj=g.finish()
    # Keep curved arch strips continuous, avoiding individually bevelled tiles.
    for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
    bm=bmesh.new();bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(obj.data);bm.free()
    added.append(obj.name)
assert all(fingerprint(bpy.data.objects[n])==value for n,value in before.items())
for name in ['room-studies.json','room-spaces.json','building-review.json']:
    shutil.copyfile(ROOT/'result/blender/stage91'/name,OUT/name)
if not (OUT/'catalogue-before.json').exists():
    shutil.copyfile(ROOT/'web/public/models/catalogue.json',OUT/'catalogue-before.json')
audit={'version':92,'baseline':91,'baselineFingerprint':before,'copies':copies,'addedObjects':added,
       'frame':{'origin':list(a),'right':list(right),'normal':list(normal),'length':length},
       'windows':windows,'frontWallIndex':1,
       'sourceUrl':'https://www.lse.ac.uk/global-school-of-sustainability/news/2025/first-recipients-Global-Sustainability-Research-Fund',
       'published':'2025-07-31','captureDate':None,
       'scope':'Three Lincoln frontage bays; upper three-column sash grids, three ground arches, right timber entry, stone heads and cornices. Original objects, other faces, roof and interiors preserved.',
       'limitations':['Dimensions remain estimates on the retained GIS footprint','Roof photograph shows dormers and slopes still absent from this correction','Corner curvature, other street faces and interiors remain unverified']}
(OUT/'lincolns-three-bay-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v92.blend'))
print('LINCOLNS_THREE_BAY_SAVED',len(copies),len(windows),flush=True)
