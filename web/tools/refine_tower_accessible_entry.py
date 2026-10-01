"""Correct the shared PAN/FAW automatic entrance from the AccessAble survey.
Run in Blender Text Editor. The documented clear width is 0.98m; position and
unmeasured heights retain the native scene's estimated facade registration.
"""
from pathlib import Path
import array, hashlib, json, math, shutil, sys
import bpy, bmesh
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage88'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v87.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
building = next(b for b in json.loads((ROOT/'result/blender/stage03/pan_faw/tower_geometry.json').read_text())['buildings'] if b['code']=='PAN')
wall = next(w for w in building['walls'] if w['entrance'])
origin = Vector((*wall['p'],0))
right = Vector(((wall['q'][0]-wall['p'][0])/wall['length'],
                (wall['q'][1]-wall['p'][1])/wall['length'],0))
outward = Vector((*wall['outward'],0))
angle = math.atan2(right.y,right.x)
def point(x,depth,z):
    return origin + right*x + outward*depth + Vector((0,0,z))
def local(obj,v):
    p = obj.matrix_world@v.co-origin
    return Vector((p.dot(right),p.dot(outward),p.z))
def fingerprint(obj):
    digest = hashlib.sha256(str([list(r) for r in obj.matrix_world]).encode())
    if obj.type=='MESH':
        digest.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i',[loop.vertex_index for loop in obj.data.loops]).tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return digest.hexdigest()
def components(mesh):
    seen=set()
    for v in mesh.verts:
        if v in seen or not v.link_faces:
            continue
        seen.add(v);todo=[v];group=[]
        while todo:
            p=todo.pop();group.append(p)
            for e in p.link_edges:
                q=e.other_vert(p)
                if q not in seen:
                    seen.add(q);todo.append(q)
        yield group
before={obj.name:fingerprint(obj) for obj in bpy.data.objects}
retained=[];hidden=[];removed={}
for family in ['ground_glass','ground_mullions']:
    source=bpy.data.objects['PAN_D3_'+family]
    copy=source.copy();copy.data=source.data.copy()
    copy.name='PAN_D5_entry88_retained_'+family
    bpy.data.collections['PAN_EXTERIOR'].objects.link(copy)
    mesh=bmesh.new();mesh.from_mesh(copy.data);delete=[];count=0
    for group in components(mesh):
        points=[local(copy,v) for v in group]
        centre=sum(points,Vector())/len(points)
        # Remove the first facade glazing box and the two obsolete internal bars,
        # not glass or mullions on the remaining entrance bays or other elevations.
        in_panel = family=='ground_glass' and abs(centre.x-1.96)<.01 and abs(centre.y+.15)<.01 and abs(centre.z-1.99)<.01
        in_bar = family=='ground_mullions' and min(abs(centre.x-1.3),abs(centre.x-2.6))<.01 and abs(centre.y+.05)<.01 and abs(centre.z-2)<.01
        if in_panel or in_bar:
            count+=1;delete.extend(group)
    assert count==(1 if family=='ground_glass' else 2),(family,count)
    bmesh.ops.delete(mesh,geom=delete,context='VERTS')
    mesh.to_mesh(copy.data);mesh.free()
    retained.append(copy.name);removed[source.name]=count
    source.hide_render=True;source.hide_set(True);hidden.append(source.name)
materials.clear()
def material(key,color,roughness,metallic=0):
    m=bpy.data.materials.new('PAN_V88_'+key);m.use_nodes=True;m.diffuse_color=(*color,1)
    shader=m.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value=m.diffuse_color
    shader.inputs['Roughness'].default_value=roughness
    shader.inputs['Metallic'].default_value=metallic
    materials[key]=m
    return m
material('dark_door_frame',(.045,.052,.047),.35,.45)
glass=material('door_glazing',(.16,.205,.19),.18)
glass.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value=.22
glass['webOpacity']=.66
material('control_metal',(.46,.48,.46),.4,.65)
material('safety_yellow',(.70,.51,.035),.75)
batches={}
def batch(key):
    if key not in batches:
        batches[key]=Geometry('PAN','entry88_'+key,key)
    return batches[key]
members=[]
def box(key,x,depth,z,width,thickness,height):
    batch(key).box(point(x,depth,z),(width,thickness,height),angle)
    members.append({'material':key,'centre':[x,depth,z],'size':[width,thickness,height]})
# A 50mm perimeter frame leaves the surveyed 980mm clear horizontal opening.
centre=1.95;clear=.98;frame=.05;outer=clear+2*frame
low,high=.14,3.18
for side in [-1,1]:
    box('dark_door_frame',centre+side*(clear/2+frame/2),-.05,(low+high)/2,frame,.13,high-low)
for z in [low,high]:
    box('dark_door_frame',centre,-.05,z,outer,.13,frame)
box('door_glazing',centre,-.14,(low+high)/2,clear,.03,high-low-frame)
# Retain fixed glazing on both sides and the transom above the automatic leaf.
fixed_material=bpy.data.materials['PAN_D3_clear_glass']
materials['fixed_glass']=fixed_material
for lo,hi in [(.03,centre-outer/2),(centre+outer/2,3.89)]:
    box('fixed_glass',(lo+hi)/2,-.15,1.99,hi-lo,.028,3.72)
box('fixed_glass',centre,-.15,(high+3.85)/2,outer,.028,3.85-high)
# Surveyed push-pad centre is 0.78m above grade; exact plate size is estimated.
box('control_metal',centre-outer/2-.13,.05,.78,.09,.045,.13)
box('dark_door_frame',centre-outer/2-.13,.08,.78,.045,.014,.064)
# The provider's exterior photograph shows a circular contrast marker on the leaf.
radius=.07;z=1.38;segments=32
vertices=[point(centre,-.119,z)]+[point(centre+radius*math.cos(i*math.tau/segments),-.119,z+radius*math.sin(i*math.tau/segments)) for i in range(segments)]
faces=[(0,1+i,1+(i+1)%segments) for i in range(segments)]
batch('safety_yellow').add(vertices,faces)
# Revolving doors retain their shape; only their metal finish becomes independent
# of the pale aluminium used by the upper windows and cycle stands.
door_copies=[]
for family in ['revolving_door_rings','revolving_central_spindles','door_wing_edges','door_push_bars']:
    source=bpy.data.objects['PAN_D3_'+family]
    copy=source.copy();copy.data=source.data.copy()
    copy.name='PAN_D5_entry88_'+family
    copy.data.materials.clear();copy.data.materials.append(materials['dark_door_frame'])
    bpy.data.collections['PAN_EXTERIOR'].objects.link(copy)
    source.hide_render=True;source.hide_set(True);hidden.append(source.name)
    door_copies.append({'source':source.name,'copy':copy.name})
added=retained+[r['copy'] for r in door_copies]
for geometry in batches.values():
    obj=geometry.finish();added.append(obj.name)
    for modifier in list(obj.modifiers):
        obj.modifiers.remove(modifier)
    mesh=bmesh.new();mesh.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(mesh,faces=list(mesh.faces))
    mesh.to_mesh(obj.data);mesh.free()
assert all(fingerprint(bpy.data.objects[n])==v for n,v in before.items())
for name in ['room-studies.json','room-spaces.json','building-review.json']:
    shutil.copyfile(ROOT/'result/blender/stage87'/name,OUT/name)
shutil.copyfile(ROOT/'web/public/models/catalogue.json',OUT/'catalogue-before.json')
audit={'version':88,'baseline':87,'baselineFingerprint':before,
       'frame':{'origin':list(origin),'right':list(right),'outward':list(outward)},
       'members':members,'hiddenObjects':hidden,'retainedObjects':retained,'removedComponents':removed,
       'doorCopies':door_copies,'addedObjects':added,'doorCentre':centre,
       'clearWidthMetres':clear,'frameWidthMetres':frame,'controlCentreMetres':.78,
       'reference':'https://www.accessable.co.uk/london-school-of-economics/access-guides/fawcett-house-tower-2',
       'surveyContext':'Provider reception section mentions August 2020; exact entrance photograph date unknown','limitations':['Door registration, height, plate size and marker position estimated on the retained facade',
       'Clear width and push-pad height derive from the provider survey, not a new 2026 measurement',
       'No operational animation or current access guarantee; sculpture, upper massing, roof and complete interiors remain under review']}
(OUT/'tower-entry-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v88.blend'))
print('TOWER_ACCESSIBLE_ENTRY_SAVED',len(added),removed,flush=True)
