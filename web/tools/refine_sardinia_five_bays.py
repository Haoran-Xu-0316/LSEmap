"""Reconstruct SAR's five-bay main street facade from identified photographs.
Run in Blender Text Editor. Footprint and existing storey heights are retained;
unlabelled dimensions and pane subdivisions are estimates, not a measured survey.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import sys
import bpy
import bmesh
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage119';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,materials
baseline=ROOT/'result/blender/LSE_campus_detailed_v118.blend'
current=ROOT/'result/blender/LSE_campus_detailed_v119.blend'
rebuild_current=not baseline.exists()
if rebuild_current:
    candidates=list((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'))
    current=max(candidates,key=lambda path:int(path.stem.rsplit('v',1)[1]))
bpy.ops.wm.open_mainfile(filepath=str(current if rebuild_current else baseline))
if rebuild_current:
    previous=json.loads((OUT/'sardinia-frontage-audit.json').read_text())
    for name in previous['addedObjects']+[r['copy'] for r in previous['retainedCopies'] if r['copy']]:
        obj=bpy.data.objects[name];data=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
        if not data.users:bpy.data.meshes.remove(data)
    for name in previous['archivedObjects']:
        obj=bpy.data.objects[name];obj.hide_render=previous['originalVisibility'][name];obj.hide_set(obj.hide_render)
    for material in list(bpy.data.materials):
        if material.name.startswith('SAR_V119_') and not material.users:bpy.data.materials.remove(material)
for scene in bpy.data.scenes:
    for layer in scene.view_layers:layer.update()
scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
collection=bpy.data.collections['SAR_EXTERIOR']
ring=next(b['rings'][0] for b in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings'] if b['code']=='SAR')
origin=Vector((*ring[2],0));axis=(Vector((*ring[3],0))-origin).normalized();normal=Vector((-axis.y,axis.x,0))
length=(Vector((*ring[3],0))-origin).length;angle=math.atan2(axis.y,axis.x)
height=23.;storey=height/6;pitch=length/5

def fingerprint(obj):
    h=hashlib.sha256(str([list(r) for r in obj.matrix_world]).encode())
    if obj.type=='MESH':
        verts=array.array('f',[0])*(3*len(obj.data.vertices));loops=array.array('i',[0])*len(obj.data.loops)
        obj.data.vertices.foreach_get('co',verts);obj.data.loops.foreach_get('vertex_index',loops)
        h.update(verts.tobytes());h.update(loops.tobytes())
    h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return h.hexdigest()
before={obj.name:fingerprint(obj) for obj in bpy.data.objects}
visibility={obj.name:obj.hide_render for obj in bpy.data.objects}
archived=[];copies=[]
keep={'SAR_D5_roof_slab','SAR_V102_D5_party_walls_red','SAR_V102_school_name_fascia_stone',
      'SAR_V19_REM_projecting_dentil_cornice_pale_stone','SAR_V19_REM_cornice_dentils_pale_stone'}
# Preserve side/rear components of each original batch. Mesh connectivity, rather
# than material names, identifies each independent original construction piece.
for old in list(collection.all_objects):
    if old.hide_render or old.type!='MESH' or old.name in keep:continue
    bm=bmesh.new();bm.from_mesh(old.data);seen=set();remove=[];removed=0
    for vertex in list(bm.verts):
        if vertex in seen:continue
        stack=[vertex];seen.add(vertex);component=[]
        while stack:
            v=stack.pop();component.append(v)
            for edge in v.link_edges:
                other=edge.other_vert(v)
                if other not in seen:seen.add(other);stack.append(other)
        points=[old.matrix_world@v.co-origin for v in component]
        if old.name.startswith(('SAR_V20_EXT_entry_','SAR_V20_EXT_door_')) or all(-.85<p.dot(normal)<.85 and -.85<p.dot(axis)<length+.85 for p in points):
            remove.extend(component);removed+=1
    if not remove:bm.free();continue
    bmesh.ops.delete(bm,geom=remove,context='VERTS');copy_name=None
    if bm.faces:
        new=old.copy();new.data=old.data.copy();new.name='SAR_V119_retained_'+old.name.removeprefix('SAR_')
        collection.objects.link(new);bm.to_mesh(new.data);new.data.update();copy_name=new.name
    bm.free();old.hide_render=True;old.hide_set(True);archived.append(old.name)
    copies.append({'source':old.name,'copy':copy_name,'removedFrontComponents':removed})
assert len(archived)>=35,(len(archived),archived)
materials.clear()
for key,source in [('brick','SAR_V102_red_brick_INFILL_red'),('stone','SAR_V102_stone'),
                   ('frame','INFILL_frame.001'),('glass','INFILL_glass.001'),('metal','HERITAGE09_wood'),
                   ('roof','INFILL_slate'),('bronze','HERITAGE09_gold')]:
    # Some source finishes have Blender's generated numeric suffixes; search only
    # the named source family and record the exact copied material in the audit.
    material=bpy.data.materials.get(source)
    if material is None:
        material=next((m for m in bpy.data.materials if m.name.startswith(source)),None)
    assert material is not None,source
    new=material.copy();new.name='SAR_V119_'+key;materials[key]=new
for key,color,roughness in [('metal',(.023,.025,.024,1),.65),('frame',(.69,.69,.64,1),.71),('roof',(.075,.081,.082,1),.88)]:
    material=materials[key];material.diffuse_color=color
    node=material.node_tree.nodes['Principled BSDF'];node.inputs['Base Color'].default_value=color;node.inputs['Roughness'].default_value=roughness
batches={}
def batch(key):
    if key not in batches:batches[key]=Geometry('SAR','front119_'+key,key)
    return batches[key]
def point(x,d,z):return origin+axis*x+normal*d+Vector((0,0,z))
def box(key,x,d,z,w,t,h):
    if min(w,t,h)>.00001:batch(key).box(point(x,d,z),(w,t,h),angle)
def prism(key,outline,back,front):
    if sum(x0*z1-x1*z0 for (x0,z0),(x1,z1) in zip(outline,outline[1:]+outline[:1]))<0:outline=list(reversed(outline))
    count=len(outline);vertices=[point(x,d,z) for d in [back,front] for x,z in outline]
    faces=[tuple(range(count)),tuple(reversed(range(count,2*count)))]+[(i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count)]
    batch(key).add(vertices,faces)
def strip(key,x0,z0,x1,z1,width,back,front):
    u=Vector((x1-x0,z1-z0)).normalized();v=Vector((-u.y,u.x))*width/2
    prism(key,[(x0+v.x,z0+v.y),(x1+v.x,z1+v.y),(x1-v.x,z1-v.y),(x0-v.x,z0-v.y)],back,front)
def ellipse(key,x,spring,radius,rise,thickness,back,front):
    for i in range(32):
        a,b=i*math.pi/32,(i+1)*math.pi/32
        prism(key,[(x+radius*math.cos(a),spring+rise*math.sin(a)),(x+radius*math.cos(b),spring+rise*math.sin(b)),
                   (x+(radius+thickness)*math.cos(b),spring+(rise+thickness)*math.sin(b)),(x+(radius+thickness)*math.cos(a),spring+(rise+thickness)*math.sin(a))],back,front)

def brick_patch(left,right,low,high):
    if right-left<.0001 or high-low<.0001:return
    if low>=2*storey:
        box('brick',(left+right)/2,-.20,(low+high)/2,right-left,.40,high-low)
        return
    # Full backing is recessed behind distinct rusticated blocks. The gaps are
    # actual 55mm horizontal slots, not darker strips laid on a flat wall.
    box('brick',(left+right)/2,-.2225,(low+high)/2,right-left,.355,high-low)
    cursor=low
    for centre in [.50,1.14,1.79,2.44,3.09,3.79,4.43,5.08,5.73,6.38,7.03]:
        a,b=centre-.0275,centre+.0275
        if b<=low or a>=high:continue
        top=min(high,a)
        if top>cursor:box('brick',(left+right)/2,-.0075,(cursor+top)/2,right-left,.075,top-cursor)
        cursor=max(cursor,min(high,b))
    if high>cursor:box('brick',(left+right)/2,-.0075,(cursor+high)/2,right-left,.075,high-cursor)

def joinery(key,x,low,high,width,columns,rows):
    for sign in [-1,1]:box(key,x+sign*(width/2-.035),.035,(low+high)/2,.07,.17,high-low)
    for z in [low+.035,high-.035]:box(key,x,.035,z,width,.17,.07)
    for column in range(1,columns):box(key,x-width/2+width*column/columns,.045,(low+high)/2,.038,.10,high-low)
    for row in range(1,rows):box(key,x,.045,low+(high-low)*row/rows,width,.10,.036)

openings=[]
for floor in range(6):
    low=floor*storey+(.58 if floor==0 else .82)
    high=(floor+1)*storey-(.58 if floor==0 else .62)
    bounds=[]
    for bay in range(5):
        x=(bay+.5)*pitch;door=floor==0 and bay==2
        width=1.40 if door else (2.40 if floor==0 else 2.48 if floor==1 else 2.15)
        lo=.018 if door else low;hi=3.10 if door else high
        bounds.append((x-width/2,x+width/2,lo,hi))
        openings.append({'floor':floor,'bay':bay,'x':x,'width':width,'low':lo,'high':hi,'kind':'entry' if door else 'ground-arch' if floor==0 else 'casement'})
        if door:continue
        box('glass',x,-.075,(lo+hi)/2,width-.08,.025,hi-lo-.08)
        joinery('metal' if floor==0 else 'frame',x,lo,hi,width,4,3 if floor==1 else 4)
        if floor==0:
            # The curved central head sits within a rectangular glazed opening.
            # Its two side lights and upper corner lights remain transparent.
            ellipse('metal',x,2.50,width/4,.55,.04,.025,.13)
            for side in [-1,1]:box('metal',x+side*width/4,.075,(lo+2.50)/2,.055,.11,2.50-lo)
            for j in range(13):box('metal',x-width/2+.08+j*(width-.16)/12,.22,.39,.023,.035,.57)
            for z in [.11,.36,.66]:box('metal',x,.22,z,width-.12,.045,.035)
        else:
            box('stone',x,.08,lo-.10,width+.32,.30,.18)
            if floor in [2,3,4]:
                for side in [-1,1]:box('stone',x+side*(width/2+.07),.09,(lo+hi)/2,.14,.20,hi-lo+.22)
                box('stone',x,.09,hi+.08,width+.36,.22,.16)
            if floor==2:
                base=hi+.26;half=(width+.72)/2
                box('stone',x,.17,base,width+.72,.32,.14)
                if bay%2==0:
                    prism('stone',[(x-half,base+.07),(x+half,base+.07),(x,base+.65)],.04,.24)
                    strip('stone',x-half,base+.07,x,base+.65,.11,.08,.35)
                    strip('stone',x,base+.65,x+half,base+.07,.11,.08,.35)
                else:
                    outline=[(x-half,base+.07),(x+half,base+.07)]+[(x+half*math.cos(i*math.pi/32),base+.07+.53*math.sin(i*math.pi/32)) for i in range(33)]
                    prism('stone',outline,.04,.24)
                    ellipse('stone',x,base+.07,half,.53,.105,.06,.35)
                for side in [-1,1]:box('stone',x+side*(width/2+.13),.17,hi+.04,.20,.30,.29)
    # A thick real wall partition surrounds every opening; no opaque backing
    # rectangle fills the glazed windows in either the overview or detail mesh.
    previous=0
    for left,right,lo,hi in bounds:
        brick_patch(previous,left,floor*storey,(floor+1)*storey)
        brick_patch(left,right,floor*storey,lo)
        brick_patch(left,right,hi,(floor+1)*storey)
        previous=right
    brick_patch(previous,length,floor*storey,(floor+1)*storey)
# The photographed ground openings have tall brick jack arches beneath the
# mezzanine sills. Each wedge has a real shallow joint and horizontal brick UVs.
for bay in [0,1,3,4]:
    x=(bay+.5)*pitch;width=2.40
    for j in range(9):
        lo0=x-width/2+width*j/9+.006;lo1=x-width/2+width*(j+1)/9-.006
        hi0=x-(width+.24)/2+(width+.24)*j/9+.006;hi1=x-(width+.24)/2+(width+.24)*(j+1)/9-.006
        prism('brick',[(lo0,3.25),(lo1,3.25),(hi1,4.46),(hi0,4.46)],-.015,.055)
for z in [5*storey+.04,23.03]:box('stone',length/2,.09,z,length+.12,.34,.17)
# Central automatic paired entrance: 120cm guide opening, other frame dimensions
# estimated. Five entrance steps are inside the doors, not outside on the pavement.
x=length/2
for side in [-1,1]:
    centre=x+side*.30
    joinery('metal',centre,.018,2.64,.60,2,2)
    box('glass',centre,-.08,1.329,.52,.025,2.542)
    box('bronze',centre-side*.21,.13,1.31,.025,.03,.28)
for side in [-1,1]:box('stone',x+side*.91,.15,1.55,.27,.54,3.10)
box('stone',x,.18,3.15,2.28,.62,.20)
box('glass',x,-.06,2.89,1.30,.024,.36)
for side in [-1,1]:box('stone',x+side*.78,.15,2.91,.13,.50,.45)
box('stone',x,.20,3.34,2.53,.74,.16)
prism('roof',[(x-1.34,3.42),(x+1.34,3.42),(x,4.04)],-.10,.66)
strip('stone',x-1.34,3.40,x,4.02,.10,.42,.76)
strip('stone',x,4.02,x+1.34,3.40,.10,.42,.76)
for side in [-1,1]:
    strip('stone',x+side*.90,2.98,x+side*1.12,3.29,.13,.26,.50)
    box('bronze',x+side*1.08,.14,1.63,.21,.025,.30)
# Dark plinth below the window grilles and the photographed hanging sign bracket.
box('metal',length/2,.01,.065,length,.12,.13)
box('metal',x+.63,.67,3.86,.035,1.03,.045)
box('metal',x+.63,1.16,3.59,.65,.045,.44)
box('metal',x+.63,.42,3.86,1.23,.045,.035)
# Convert the photographed two-line hanging sign to our owned mesh batch.
# This preserves letter geometry identically in overview and detailed exports.
curve=bpy.data.curves.new('SAR_V119_sign_source','FONT');curve.body='SARDINIA\nHOUSE'
curve.align_x='CENTER';curve.align_y='CENTER';curve.size=.12;curve.extrude=.002
curve.font=bpy.data.objects['SAR_V102_school_name'].data.font
text=bpy.data.objects.new('SAR_V119_sign_source',curve);collection.objects.link(text)
right=-axis;up=Vector((0,0,1))
text.matrix_world=Matrix(((right.x,up.x,normal.x,0),(right.y,up.y,normal.y,0),(right.z,up.z,normal.z,0),(0,0,0,1)))
text.matrix_world.translation=point(x+.63,1.189,3.59);bpy.context.view_layer.update()
evaluated=text.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
batch('frame').add([text.matrix_world@v.co for v in mesh.vertices],[list(p.vertices) for p in mesh.polygons])
evaluated.to_mesh_clear();bpy.data.objects.remove(text,do_unlink=True);bpy.data.curves.remove(curve)
added=[]
for geometry in batches.values():
    obj=geometry.finish();added.append(obj.name)
    for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
    bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
    # A single horizontal metric mapping keeps procedural brick rows continuous,
    # independent of triangulation and the orientation of each original quad.
    if geometry.material==materials['brick']:
        for poly in obj.data.polygons:
            for index in poly.loop_indices:
                p=obj.matrix_world@obj.data.vertices[obj.data.loops[index].vertex_index].co-origin
                obj.data.uv_layers.active.data[index].uv=(p.dot(axis),p.z)
assert all(fingerprint(bpy.data.objects[n])==h for n,h in before.items())
audit=dict(version=119,baseline=118,originalFingerprints=before,originalVisibility=visibility,
    archivedObjects=archived,retainedCopies=copies,addedObjects=added,openings=openings,
    origin=list(origin),axis=list(axis),normal=list(normal),frontLength=length,height=height,
    bayCount=5,guideDoorOpening=1.20,externalStepsAdded=0,
    sourceUrls=['https://commons.wikimedia.org/wiki/File:Sardinia_House,_London,_March_2022.jpg','https://commons.wikimedia.org/wiki/File:Sardinia_House,_Sardinia_Street_7_Jan_2017_03.jpg','https://www.accessable.co.uk/london-school-of-economics/access-guides/sardinia-house','https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Property-and-Space/LSE-Property-Handbook.pdf'],
    limits=['Five main street bays and central entry identified from 2022 photo and official handbook; adjoining three-bay building excluded','Footprint, 23m height and floor datums retained; registration, aperture dimensions, colours and pane subdivisions are estimates','Guide five steps are beyond the doors; full foyer, roof and unseen elevations remain unresolved','2017 and 2022 photos are historical evidence, not a verified 2026 survey'])
(OUT/'sardinia-frontage-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(current))
print('SARDINIA_FIVE_BAY_FRONTAGE_SAVED',len(archived),len(added),flush=True)
