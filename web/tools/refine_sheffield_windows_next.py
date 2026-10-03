"""Match Sheffield Street's photographed paired lights and glazed timber entry.

Run in Blender's Text Editor. Only a small exterior component is saved. Existing
window apertures, facade dimensions, roof and unseen elevations stay unchanged.
"""
from pathlib import Path
import array, hashlib, json, sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'result/blender/shf_next'
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT/'result/blender/LSE_campus_detailed_v120.blend'
if not BASE.exists():
    BASE = max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'), key=lambda p:int(p.stem.rsplit('v',1)[1]))
bpy.ops.wm.open_mainfile(filepath=str(BASE))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
previous = json.loads((OUT/'audit.json').read_text()) if (OUT/'audit.json').exists() else None
if previous:
    for name in previous['ownedObjects']:
        obj = bpy.data.objects.get(name)
        if obj:
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            data.use_fake_user = False
            if not data.users:bpy.data.meshes.remove(data)
    for name, state in previous['originalVisibility'].items():
        if name in previous['archivedObjects']:
            obj = bpy.data.objects[name]
            obj.hide_render, obj.hide_viewport = state[:2]
            obj.hide_set(state[2])
def fingerprint(obj):
    h = hashlib.sha256(str([list(r) for r in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        for data, field, kind, count in ((obj.data.vertices,'co','f',3),(obj.data.loops,'vertex_index','i',1),(obj.data.polygons,'material_index','i',1)):
            values = array.array(kind,[0])*(len(data)*count)
            data.foreach_get(field,values);h.update(values.tobytes())
        for layer in obj.data.uv_layers:
            values = array.array('f',[0])*(len(layer.data)*2)
            layer.data.foreach_get('uv',values);h.update(values.tobytes())
    h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return h.hexdigest()
originals = {o.name:fingerprint(o) for o in bpy.data.objects}
visibility = {o.name:[o.hide_render,o.hide_viewport,o.hide_get()] for o in bpy.data.objects}
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Facade, materials
materials.clear()
for key in ('frame','door','glass'):
    materials[key] = bpy.data.materials['SHF_V50_'+key]
ring = next(p for p in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings'] if p['code']=='SHF')['rings'][0]
p,q = Vector(ring[0]),Vector(ring[6])
axis = (q-p).normalized();normal = Vector((-axis.y,axis.x))
center = sum((Vector(v) for v in ring),Vector((0,0)))/len(ring)
if normal.dot((p+q)/2-center)<0:normal=-normal
profile = {'code':'SHF'}
wall = {'p':list(p),'q':list(q),'length':(q-p).length,'outward':list(normal)}
groups = {};front = Facade(profile,wall,groups)
pitch = front.length/4;centers = [pitch*(i+.5) for i in range(4)];width = pitch*.69
levels = [(1.20,1.20),(4.30,2.20),(7.95,2.40),(11.65,2.40),(14.90,1.30)]
for bay,x in enumerate(centers):
    for level,(z,h) in enumerate(levels):
        if bay==2 and level==0:continue
        for j in range(1,6):
            front.box('paired_stiles','frame',x-width/2+width*j/6,z,.068 if j%2==0 else .028,h,.12,-.025)
        # Narrow top light, then three lower rows in each tall sash.
        divisions = [z+h/2-h*.23]
        if level in (1,2,3):
            lower_height = h*.77
            divisions += [z-h/2+lower_height*j/3 for j in (1,2)]
        for j,height in enumerate(divisions):
            front.box('overlight_transoms','frame',x,height,width,.066 if j==0 else .030,.12,-.025)
door_x = centers[2];door_w = 2.30
for side in (-1,1):
    x = door_x+side*door_w/4;w = door_w/2-.09
    # Solid lower joinery ends beneath the upper glazing, never behind it.
    front.box('entry_lower_timber','door',x,.76,w,1.32,.085,-.055)
    for panel in (-1,1):
        front.box('entry_lower_panels','door',x+panel*w*.24,.76,w*.38,1.12,.025,.000)
    z = 2.17;h = 1.28
    front.box('entry_glass','glass',x,z,w-.12,h,.035,-.055)
    for edge in (-1,1):
        front.box('entry_glazing_stiles','door',x+edge*(w/2-.035),z,.07,h+.08,.10,-.025)
        front.box('entry_glazing_rails','door',x,z+edge*h/2,w,.07,.10,-.025)
    for j in (1,2):
        front.box('entry_glazing_stiles','door',x-w/2+w*j/3,z,.028,h,.10,-.025)
        front.box('entry_glazing_rails','door',x,z-h/2+h*j/3,w,.028,.10,-.025)
owned = []
for group in groups.values():
    obj = group.finish();obj.name = 'SHF_NEXT_'+obj.name.removeprefix('SHF_D5_');obj.data.name = obj.name
    for modifier in obj.modifiers:
        if modifier.type=='BEVEL':modifier.width = .004
    owned.append(obj)
archived = ['SHF_V50_window_mullion_frame','SHF_V50_window_transom_frame','SHF_V50_door_leaf_door','SHF_V50_door_light_glass']
for name in archived:
    obj = bpy.data.objects[name];obj.hide_render=True;obj.hide_set(True)
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
# Test upper-glazing clearance through the whole facade thickness, excluding glass.
def opaque_tree():
    vertices,faces,owners = [],[],[]
    for obj in bpy.data.collections['SHF_EXTERIOR'].all_objects:
        if obj.type!='MESH' or obj.hide_render or 'glass' in obj.name:continue
        base=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        faces.extend(tuple(base+i for i in p.vertices) for p in obj.data.polygons)
        owners.extend([obj.name]*len(obj.data.polygons))
    return BVHTree.FromPolygons(vertices,faces),owners
probes = [(door_x+side*door_w/4+offset,z) for side in (-1,1) for offset in (-.20,.20) for z in (1.65,2.08,2.53)]
def entry_clearance():
    tree,owners = opaque_tree();normal=Vector((*front.n,0));results=[]
    for x,z in probes:
        hit=tree.ray_cast(Vector(front.point(x,z,.18)),-normal,.55)
        results.append({'x':x,'z':z,'opaqueSurface':owners[hit[2]] if hit[2] is not None else None})
    return results
clearance = entry_clearance();assert all(p['opaqueSurface'] is None for p in clearance),clearance
component = OUT/'sheffield-windows-component.blend'
bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
audit = {'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'originalFingerprints':originals,'originalVisibility':visibility,'archivedObjects':archived,'ownedObjects':[o.name for o in owned],'windowCount':19,'windowColumns':6,'tallWindowRows':4,'entryClearance':clearance,'sources':[{'local':'data/建筑图片/SHF_Sheffield Street/01_建筑实拍/exteriors_lse_estate_027.jpg','url':'https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate','date':'Undated official photograph'},{'url':'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Property-and-Space/LSE-Property-Handbook.pdf','date':'2025/26 handbook, photograph date unspecified','page':40}],'limitations':['Facade dimensions and bay positions retained estimates','Dormer grid and unseen roof are unchanged pending clearer evidence','No new interior reconstruction','Joinery profile thicknesses estimated from photographs']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print('SHF_COMPONENT_SAVED',component.stat().st_size,flush=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE))
with bpy.data.libraries.load(str(component),link=False) as (source,target):target.objects=audit['ownedObjects']
for obj in target.objects:bpy.data.collections['SHF_EXTERIOR'].objects.link(obj)
for name in archived:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
assert all(p['opaqueSurface'] is None for p in entry_clearance())
verification={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'baselineUnchanged':hashlib.sha256(BASE.read_bytes()).hexdigest()==audit['baselineSha256'],'originalGeometryPreserved':True,'reloadedClearEntryProbes':12,'savedComponentReopened':True}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
print('SHF_COMPONENT_RELOADED_VERIFIED',flush=True)
