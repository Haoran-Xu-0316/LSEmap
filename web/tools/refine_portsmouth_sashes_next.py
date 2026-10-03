"""Correct photographed Portsmouth paired sashes and chamfered upper lights.

Run in Blender's Text Editor. Unseen window patterns, roof and shopfront remain
unchanged. Archive original merged bars and keep their unaffected pieces in copies.
"""
from pathlib import Path
import array, hashlib, json, sys
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'result/blender/portsmouth_next'
OUT.mkdir(parents=True,exist_ok=True)
BASE = ROOT/'result/blender/LSE_campus_detailed_v121.blend'
if not BASE.exists():
    BASE = max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
bpy.ops.wm.open_mainfile(filepath=str(BASE))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
previous=json.loads((OUT/'audit.json').read_text()) if (OUT/'audit.json').exists() else None
if previous:
    for name in previous['ownedObjects']:
        obj=bpy.data.objects.get(name)
        if obj:
            mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True);mesh.use_fake_user=False
            if not mesh.users:bpy.data.meshes.remove(mesh)
    for name in previous['archivedObjects']:
        obj=bpy.data.objects[name];state=previous['originalVisibility'][name]
        obj.hide_render,obj.hide_viewport=state[:2];obj.hide_set(state[2])
for scene in bpy.data.scenes:
    for layer in scene.view_layers:layer.update()
def fingerprint(obj):
    digest=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type=='MESH':
        for data,field,kind,width in ((obj.data.vertices,'co','f',3),(obj.data.loops,'vertex_index','i',1),(obj.data.polygons,'material_index','i',1)):
            values=array.array(kind,[0])*(len(data)*width);data.foreach_get(field,values);digest.update(values.tobytes())
        for layer in obj.data.uv_layers:
            values=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);digest.update(values.tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return digest.hexdigest()
originals={o.name:fingerprint(o) for o in bpy.data.objects}
visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()] for o in bpy.data.objects}
ring=next(b for b in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings'] if b['code']=='POR')['rings'][0]
center=sum((Vector(p) for p in ring),Vector((0,0)))/len(ring)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Facade, materials
materials.clear();materials['frame']=bpy.data.materials['POR_V51_frame']
groups={};facades=[]
for index in (0,1):
    p,q=Vector(ring[index]),Vector(ring[index+1]);axis=(q-p).normalized();normal=Vector((-axis.y,axis.x))
    if normal.dot((p+q)/2-center)<0:normal=-normal
    facades.append(Facade({'code':'POR'},{'index':index,'p':list(p),'q':list(q),'outward':list(normal),'length':(q-p).length},groups))
levels=[(4.83,7.18),(8.20,10.58),(11.62,13.55)]
windows=[]
for facade in facades:
    edge=facade.wall['index'];bays=1 if edge==0 else 2;pitch=facade.length/bays;width=min(1.34,pitch*.58)
    for level,(low,high) in enumerate(levels):
        if edge==0 and level==0:continue
        for bay in range(bays):windows.append({'edge':edge,'facade':facade,'x':(bay+.5)*pitch,'low':low,'high':high,'width':width})
def inside_window(point,window):
    facade=window['facade'];origin=Vector((*facade.wall['p'],0));axis=Vector((*facade.u,0));normal=Vector((*facade.n,0))
    local=point-origin
    return abs(local.dot(normal))<.18 and abs(local.dot(axis)-window['x'])<window['width']/2+.04 and window['low']-.01<=point.z<=window['high']+.01
collection=bpy.data.collections['POR_EXTERIOR'];owned=[];removed={}
for old_name,label in [('POR_D5_fine_glazing_bar_frame','retained_glazing_bars'),('POR_D5_sash_rail_frame','retained_sash_rails')]:
    original=bpy.data.objects[old_name];obj=original.copy();obj.data=original.data.copy();obj.name='POR_NEXT_'+label;obj.data.name=obj.name;collection.objects.link(obj)
    # Original primitive boxes have eight private vertices, preserving every
    # unaffected component and its metric UVs without rebuilding nearby walls.
    assert len(obj.data.vertices)%8==0
    indices=[]
    for start in range(0,len(obj.data.vertices),8):
        point=sum((obj.matrix_world@obj.data.vertices[i].co for i in range(start,start+8)),Vector((0,0,0)))/8
        selected=next((w for w in windows if inside_window(point,w)),None)
        if selected and (label=='retained_glazing_bars' or selected['edge']==0 and abs(point.z-(selected['low']+selected['high'])/2)<.02):
            indices.extend(range(start,start+8))
    mesh=bmesh.new();mesh.from_mesh(obj.data);mesh.verts.ensure_lookup_table()
    bmesh.ops.delete(mesh,geom=[mesh.verts[i] for i in indices],context='VERTS');mesh.to_mesh(obj.data);mesh.free();obj.data.update()
    removed[old_name]=len(indices)//8;owned.append(obj);original.hide_render=True;original.hide_set(True)
assert removed=={'POR_D5_fine_glazing_bar_frame':32,'POR_D5_sash_rail_frame':2},removed
for window in windows:
    facade=window['facade'];x=window['x'];width=window['width'];low=window['low'];high=window['high'];height=high-low
    if window['edge']==1:
        # Each of the two adjoining sashes has two lights, not three.
        facade.box('paired_sash_bars','frame',x,(low+high)/2,.024,height,.075,.067)
        for fraction in (.25,.75):facade.box('paired_sash_bars','frame',x,low+height*fraction,width,.024,.075,.067)
    else:
        meeting=low+height*.70
        facade.box('chamfer_meeting_rail','frame',x,meeting,width,.070,.13,.038)
        for dx in (-width/6,width/6):facade.box('chamfer_leaded_bars','frame',x+dx,(low+high)/2,.022,height,.075,.067)
        for count,a,b in ((5,low,meeting),(3,meeting,high)):
            for j in range(1,count):facade.box('chamfer_leaded_bars','frame',x,a+(b-a)*j/count,width,.022,.075,.067)
for group in groups.values():
    obj=group.finish();obj.name='POR_NEXT_'+obj.name.removeprefix('POR_D5_');obj.data.name=obj.name
    for modifier in obj.modifiers:
        if modifier.type=='BEVEL':modifier.width=.003
    owned.append(obj)
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
def aperture_results():
    vertices,faces,owners=[],[],[]
    for obj in collection.all_objects:
        if obj.type!='MESH' or obj.hide_render:continue
        base=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        faces.extend(tuple(base+i for i in p.vertices) for p in obj.data.polygons);owners.extend([obj.name]*len(obj.data.polygons))
    tree=BVHTree.FromPolygons(vertices,faces);results=[]
    for window in windows:
        facade=window['facade'];normal=Vector((*facade.n,0))
        for fraction in (.10,.41,.61,.92):
            x=window['x']+window['width']*.22;z=window['low']+(window['high']-window['low'])*fraction
            hit=tree.ray_cast(Vector(facade.point(x,z,.5)),-normal,1)
            results.append({'edge':window['edge'],'height':z,'firstSurface':owners[hit[2]] if hit[2] is not None else None})
    return results
apertures=aperture_results();assert all(p['firstSurface']=='POR_D5_sash_glass_glass' for p in apertures),apertures
component=OUT/'portsmouth-sashes-component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
audit={'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'originalFingerprints':originals,'originalVisibility':visibility,'archivedObjects':list(removed),'ownedObjects':[o.name for o in owned],'removedBarBoxes':removed,'affectedWindows':8,'apertures':apertures,'sources':[{'local':'data/建筑图片/POR_1 Portsmouth Street/01_建筑实拍/exteriors_lse_estate_024.jpg','url':'https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate','date':'Undated official estate photograph','sha256':'4ba2bf4cf7ff8be4057e5d4e4166e241456eae6861c20f01b4095f8345d2c4f4'}],'limitations':['Opening positions, facade dimensions and roof retained estimates','Only photographed Portsmouth-side pairs and upper two chamfer windows corrected','Lower chamfer glass and unseen Sheffield sash patterns retained pending clearer reference','No new interior or current-tenant reconstruction']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print('POR_SASH_COMPONENT_SAVED',component.stat().st_size,flush=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE));collection=bpy.data.collections['POR_EXTERIOR']
for scene in bpy.data.scenes:
    for layer in scene.view_layers:layer.update()
with bpy.data.libraries.load(str(component),link=False) as (source,target):target.objects=audit['ownedObjects']
for obj in target.objects:collection.objects.link(obj)
for name in audit['archivedObjects']:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
assert all(p['firstSurface']=='POR_D5_sash_glass_glass' for p in aperture_results())
(OUT/'verification.json').write_text(json.dumps({'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'baselineUnchanged':hashlib.sha256(BASE.read_bytes()).hexdigest()==audit['baselineSha256'],'originalGeometryPreserved':True,'reloadedClearApertures':32},indent=2)+'\n')
print('POR_SASH_COMPONENT_RELOADED_VERIFIED',flush=True)
