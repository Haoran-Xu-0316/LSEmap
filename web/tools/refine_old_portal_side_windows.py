"""Correct the two narrow windows inside OLD's Houghton portal.
Run in Blender Text Editor. Private user references remain unpublished.
"""
from pathlib import Path
import array, hashlib, json, math, sys
import bpy, bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage78'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v77.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
frame=json.loads((ROOT/'result/blender/stage52/old-houghton-audit.json').read_text())
origin,right,outward=[Vector(frame[k]) for k in ['origin','right','outward']]
def point(x,d,z):return origin+right*x+outward*d+Vector((0,0,z))
def local(p):
    p=p-origin
    return (p.dot(right),p.dot(outward),p.z)
def fingerprint(obj):
    digest=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type=='MESH':
        digest.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i',[loop.vertex_index for loop in obj.data.loops]).tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return digest.hexdigest()
before={o.name:fingerprint(o) for o in bpy.data.objects}
# Delete complete components in the two superseded ground-floor windows only.
removed={}
names=['OLD_Window_glazing','OLD_Window_stone_reveals','OLD_Window_stone_sills',
       'OLD_Window_stone_lintels','OLD_Window_sash_frames','OLD_Window_sash_bars',
       'OLD_V52_Houghton_blue']
for name in names:
    obj=bpy.data.objects[name]
    mesh=bmesh.new();mesh.from_mesh(obj.data)
    seen=set();delete=[];count=0
    for v in list(mesh.verts):
        if v in seen:continue
        stack=[v];seen.add(v);component=[]
        while stack:
            a=stack.pop();component.append(a)
            for edge in a.link_edges:
                b=edge.other_vert(a)
                if b not in seen:seen.add(b);stack.append(b)
        positions=[local(obj.matrix_world@v.co) for v in component]
        if any(all(abs(x-center)<1.0 and -.12<d<.70 and 1.05<z<4.15 for x,d,z in positions) for center in [-6.7,6.7]):
            delete.extend(component);count+=1
    assert count>0,(name,count)
    bmesh.ops.delete(mesh,geom=delete,context='VERTS')
    mesh.to_mesh(obj.data);mesh.free();obj.data.update()
    removed[name]=count
hidden=['OLD_Entrance_arch_piers']
for name in hidden:
    obj=bpy.data.objects[name];obj.hide_render=True;obj.hide_set(True)
materials.clear()
for key,source in [('stone','OLD_V52_stone'),('blue','OLD_V52_blue'),('glass','OLD_V52_glass')]:
    materials[key]=bpy.data.materials[source].copy()
    materials[key].name='OLD_V78_'+key
batches={}
def batch(family,key):
    name=family+'_'+key
    if name not in batches:batches[name]=Geometry('OLD','portal78_'+name,key)
    return batches[name]
def box(family,key,x,d,z,w,t,h):
    batch(family,key).box(point(x,d,z),(w,t,h),math.atan2(right.y,right.x))
def subtract(rect,hole):
    a,b,c,d=rect;e,f,g,h=hole
    e,f,g,h=max(a,e),min(b,f),max(c,g),min(d,h)
    if e>=f or g>=h:return [rect]
    return [r for r in [(a,e,c,d),(f,b,c,d),(e,f,c,g),(e,f,h,d)] if r[1]-r[0]>.012 and r[3]-r[2]>.012]
# Infill the old outer apertures with coursed stone matching their neighbours.
for center in [-6.7,6.7]:
    for row in range(2,7):
        bottom,top=max(1.275,row*.60),min(3.925,(row+1)*.60)
        if top<=bottom:continue
        bounds=sorted({center-.72,center+.72,*[x for x in [(-8.9-(.85 if row%2 else 0))+j*1.7 for j in range(13)] if center-.72<x<center+.72]})
        for a,b in zip(bounds,bounds[1:]):
            box('outer_infill','stone',(a+b)/2,-.007,(bottom+top)/2,b-a-.009,.45,top-bottom-.009)
# The portal shoulders have actual narrow openings, rather than glass placed
# on top of solid stone. Keep the inherited entrance height and arch unchanged.
windows=[{'x':sign*3.55,'width':.82,'bottom':1.275,'top':3.925} for sign in [-1,1]]
for window in windows:
    x=window['x'];w=window['width'];low=window['bottom'];high=window['top']
    a,b=(2.90,4.20) if x>0 else (-4.20,-2.90)
    for row in range(1,8):
        c,d=max(.69,row*.60),min(4.80,(row+1)*.60)
        for aa,bb,cc,dd in subtract((a,b,c,d),(x-w/2,x+w/2,low,high)):
            box('shoulder','stone',(aa+bb)/2,-.205,(cc+dd)/2,bb-aa-.009,.85,dd-cc-.009)
    # Stone cheek faces lead from the outer portal shoulder to recessed blue steel.
    for sign in [-1,1]:
        box('reveal','stone',x+sign*(w/2+.018),-.22,(low+high)/2,.036,.83,high-low)
    box('reveal','stone',x,-.22,low-.035,w+.08,.83,.07)
    box('reveal','stone',x,-.22,high+.035,w+.08,.83,.07)
    box('pane','glass',x,-.60,(low+high)/2,w-.09,.035,high-low-.09)
    for sign in [-1,1]:
        box('frame','blue',x+sign*(w/2-.025),-.54,(low+high)/2,.05,.085,high-low)
    for z in [low+.025,high-.025]:
        box('frame','blue',x,-.54,z,w,.085,.05)
    box('muntin','blue',x,-.495,(low+high)/2,.028,.07,high-low-.08)
    for j in range(1,4):
        box('muntin','blue',x,-.495,low+(high-low)*j/4,w-.08,.07,.03 if j!=2 else .045)
added=[]
for geometry in batches.values():
    obj=geometry.finish()
    for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
    added.append(obj.name)
changed=[n for n,v in before.items() if fingerprint(bpy.data.objects[n])!=v]
assert set(changed)==set(names),changed
for filename in ['room-studies.json','room-spaces.json','building-review.json']:
    (OUT/filename).write_bytes((ROOT/'result/blender/stage77'/filename).read_bytes())
audit={'version':78,'baseline':77,'frame':frame,'windows':windows,'columns':2,'rows':4,
       'hiddenPreviousObjects':hidden,'removedWindowComponents':removed,'changedExistingObjects':changed,'addedObjects':added,
       'referenceUrl':'https://commons.wikimedia.org/wiki/File:LSE_Old_Building_Entrance,_Houghton_Street.jpg',
       'reference':'Shadowssettle own photograph dated 2020-04-04; corroborated by user supplied entrance image, exact user photo date unknown',
       'limitations':['Window placement, widths and stone courses estimated from photographs, not surveyed',
                       'Upper windows, whole building wings, unseen elevations and complete interiors remain under review']}
(OUT/'old-portal-windows-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v78.blend'))
print('OLD_PORTAL_WINDOWS_SAVED',removed,len(added))
