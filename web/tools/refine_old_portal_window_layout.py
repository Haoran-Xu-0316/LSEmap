"""Correct OLD portal window layout and coursed Houghton wing masonry.
Run in Blender Text Editor. The complete project photograph confirms four
ground-floor windows around the portal; the cropped view shows only the inner two.
"""
from pathlib import Path
import array,hashlib,json,sys,math
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage79';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,materials
frame=json.loads((ROOT/'result/blender/stage52/old-houghton-audit.json').read_text())
origin,right,outward=[Vector(frame[k]) for k in ['origin','right','outward']]
def local(p):
    p=p-origin
    return p.dot(right),p.dot(outward),p.z
def fingerprint(obj):
    h=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type=='MESH':
        h.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
        h.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
    h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return h.hexdigest()
names=['OLD_Window_glazing','OLD_Window_stone_reveals','OLD_Window_stone_sills',
       'OLD_Window_stone_lintels','OLD_Window_sash_frames','OLD_Window_sash_bars',
       'OLD_V52_Houghton_blue']
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v77.blend'))
restored={}
for name in names:
    obj=bpy.data.objects[name]
    assert len(obj.data.materials)==1,name
    mesh=bmesh.new();mesh.from_mesh(obj.data)
    seen=set();components=[]
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
            indexes={v:i for i,v in enumerate(component)}
            faces={f for v in component for f in v.link_faces}
            components.append({'vertices':[tuple(obj.matrix_world@v.co) for v in component],
                               'faces':[[indexes[v] for v in f.verts] for f in faces]})
    assert components,name
    restored[name]={'material':obj.data.materials[0].name,'components':components}
    mesh.free()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v78.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
before={o.name:fingerprint(o) for o in bpy.data.objects}
hidden=['OLD_D5_portal78_outer_infill_stone','OLD_Houghton_flanking_wings']
for name in hidden:
    obj=bpy.data.objects[name];obj.hide_render=True;obj.hide_set(True)
materials.clear();added=[]
for name,record in restored.items():
    key=name.removeprefix('OLD_')
    materials[key]=bpy.data.materials[record['material']].copy()
    materials[key].name='OLD_V79_'+key
    geometry=Geometry('OLD','portal79_'+key,key)
    for component in record['components']:geometry.add(component['vertices'],component['faces'])
    obj=geometry.finish()
    for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
    added.append(obj.name)

# Replace the two unjointed street-wing wall fields with coursed Portland stone.
# Retain every inherited opening and the GIS edge; photographs guide finish only.
ring=next(b for b in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings'] if b['code']=='OLD')['rings'][0]
length=math.dist(ring[10],ring[11])
wall_batches={}
for i in range(7):
    key='ashlar_'+str(i)
    materials[key]=bpy.data.materials['OLD_V52_stone'].copy()
    materials[key].name='OLD_V79_'+key
    tone=.965+i*.01
    color=tuple(c*tone for c in materials[key].diffuse_color[:3])+(1,)
    materials[key].diffuse_color=color
    materials[key].node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=color
    wall_batches[key]=Geometry('OLD','wings79_'+key,key)
def point(x,d,z):return origin+right*x+outward*d+Vector((0,0,z))
def subtract(rect,hole):
    a,b,c,d=rect;e,f,g,h=hole
    e,f,g,h=max(a,e),min(b,f),max(c,g),min(d,h)
    if e>=f or g>=h:return [rect]
    return [r for r in [(a,e,c,d),(f,b,c,d),(e,f,c,g),(e,f,h,d)] if r[1]-r[0]>.012 and r[3]-r[2]>.012]
holes=[];stone_count=0
for lo,hi in [(-length/2,-8.9),(8.9,length/2)]:
    centers=[lo+(hi-lo)*(k+.5)/4 for k in range(4)]
    wing_holes=[(x-.82,x+.82,z-1.3,z+1.3) for x in centers for z in [2.7,6.7,10.8,14.9,18.8,22.6]]
    holes.extend(wing_holes)
    for row in range(41):
        c,d=row*.60,min(24.5,(row+1)*.60)
        start=lo-(.85 if row%2 else 0)
        for column in range(math.ceil((hi-start)/1.7)):
            a,b=max(lo,start+column*1.7),min(hi,start+(column+1)*1.7)
            if b<=a:continue
            rectangles=[(a,b,c,d)]
            for hole in wing_holes:rectangles=[part for rect in rectangles for part in subtract(rect,hole)]
            for aa,bb,cc,dd in rectangles:
                wall_batches['ashlar_'+str((row*3+column*5)%7)].box(point((aa+bb)/2,-.225,(cc+dd)/2),(bb-aa-.009,.45,dd-cc-.009),math.atan2(right.y,right.x))
                stone_count+=1
for geometry in wall_batches.values():
    obj=geometry.finish()
    for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
    added.append(obj.name)

changed=[n for n,h in before.items() if fingerprint(bpy.data.objects[n])!=h]
assert not changed,changed
for filename in ['room-studies.json','room-spaces.json','building-review.json']:
    (OUT/filename).write_bytes((ROOT/'result/blender/stage78'/filename).read_bytes())
audit={'version':79,'baseline':78,'frame':frame,'outerWindowAxes':[-6.7,6.7],
       'innerWindowAxes':[-3.55,3.55],'totalGroundWindows':4,'wingWindowHoles':holes,'wingStoneBlocks':stone_count,
       'sourceComponents':{n:len(r['components']) for n,r in restored.items()},
       'addedObjects':added,'hiddenPreviousObjects':hidden,'changedExistingObjects':changed,
       'referenceUrl':'https://webbyates.com/projects/the-old-building/',
       'reference':'Damian Griffiths project photograph for 2024 completed refurbishment; exact capture date unknown',
       'wingReference':'data/collections/public-realm-2026/user-references/reference-09.png; user street photograph, capture date unknown',
       'corroboratingReferenceUrl':'https://www.flickr.com/photos/lseinpictures/53100549153/',
       'limitations':['Corrects the mistaken removal of outer windows in edition 78',
                       'Outer joinery restored exactly from edition 77; placement and dimensions still photo estimates',
                       'Both Houghton wing wall fields use estimated coursed Portland stone; all 48 existing openings retained',
                       'Whole building wings, unseen roof and complete interiors remain under review']}
(OUT/'old-portal-layout-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v79.blend'))
print('OLD_PORTAL_LAYOUT_SAVED',sum(len(r['components']) for r in restored.values()))
