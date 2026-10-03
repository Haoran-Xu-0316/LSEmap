"""Correct photographed Pethick-Lawrence entrance-facing narrow windows.

Run in Blender's Text Editor. Retain the tower height and roof. The two-column narrow-window rhythm follows
the visible lower official photographs; its upper repetition is an estimate.
"""
from pathlib import Path
import array, hashlib, json, sys
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'result/blender/pel_next'
OUT.mkdir(parents=True,exist_ok=True)
BASE = ROOT/'result/blender/LSE_campus_detailed_v122.blend'
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
# Existing entrance registration, retained and verified against current glass.
ORIGIN=Vector((109.09975115798566,-88.88292847380751,0))
END=Vector((114.7297651367445,-92.83246690353144,0))
axis=(END-ORIGIN).normalized();normal=Vector((.5742943523473701,.8186488849695666,0))
def local(point):
    delta=point-ORIGIN;return Vector((delta.dot(axis),delta.dot(normal),point.z))
collection=bpy.data.collections['PEL_EXTERIOR'];old_glass=bpy.data.objects['PEL_D5_recessed_glass_glass'];windows=[]
for start in range(0,len(old_glass.data.vertices),8):
    points=[local(old_glass.matrix_world@old_glass.data.vertices[i].co) for i in range(start,start+8)]
    center=sum(points,Vector())/8
    if abs(center.y+.18)<.02 and center.z>6.78 and 0<center.x<(END-ORIGIN).length:
        windows.append({'x':center.x,'z':center.z,'width':max(p.x for p in points)-min(p.x for p in points),'low':min(p.z for p in points),'high':max(p.z for p in points)})
assert len(windows)==33
families=['recessed_glass_glass','window_jambs_metal','sash_rails_metal','sash_verticals_metal','V16_glazing_seal','V16_reveal_bead','V16_metal_sill_channel','V16_sill_drain_slot','V17_folded_jamb_return','V17_cap_shadow_joint','V17_head_flashing','V17_flashing_downstand','V17_sill_front_fascia']
owned=[];archived=[];removed={}
for family in families:
    source=bpy.data.objects['PEL_D5_'+family];assert not source.hide_render
    copy=source.copy();copy.data=source.data.copy();copy.name='PEL_NEXT_retained_'+family;copy.data.name=copy.name;collection.objects.link(copy)
    bm=bmesh.new();bm.from_mesh(copy.data);seen=set();delete=[];count=0
    for seed in bm.verts:
        if seed in seen:continue
        part=[];todo=[seed];seen.add(seed)
        while todo:
            vertex=todo.pop();part.append(vertex)
            for edge in vertex.link_edges:
                other=edge.other_vert(vertex)
                if other not in seen:seen.add(other);todo.append(other)
        center=sum((local(copy.matrix_world@v.co) for v in part),Vector())/len(part)
        if -.50<center.y<.50 and any(abs(center.x-w['x'])<w['width']/2+.22 and w['low']-.20<center.z<w['high']+.20 for w in windows):
            delete.extend(part);count+=1
    assert count>0,(family,count)
    bmesh.ops.delete(bm,geom=delete,context='VERTS');bm.to_mesh(copy.data);bm.free();copy.data.update()
    owned.append(copy);removed[source.name]=count;archived.append(source.name);source.hide_render=True;source.hide_set(True)
assert removed['PEL_D5_recessed_glass_glass']==33
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Facade,materials
materials.clear();materials['concrete']=bpy.data.materials['INFILL_concrete'];materials['glass']=bpy.data.materials['INFILL_glass'];materials['silver']=bpy.data.materials['PEL_V61_silver']
groups={};facade=Facade({'code':'PEL'},{'p':list(ORIGIN.xy),'q':list(END.xy),'length':(END-ORIGIN).length,'outward':list(normal.xy)},groups)
new_windows=[]
for window in windows:
    x,z,width,low,high=(window[key] for key in ('x','z','width','low','high'));height=high-low
    if abs(x-(END-ORIGIN).length/2)<.10:
        facade.box('closed_middle_panels','concrete',x,z,width,height,.25,-.12)
        continue
    new_width=.55
    for sign in (-1,1):
        facade.box('narrow_window_shoulders','concrete',x+sign*(width+new_width)/4,z,(width-new_width)/2,height,.25,-.12)
        facade.box('narrow_aluminium_jambs','silver',x+sign*new_width/2,z,.045,height,.13,-.01)
    facade.box('narrow_glass','glass',x,z,new_width,height,.035,-.18)
    for level in (low,high,high-height*.22,high-height*.43):
        facade.box('narrow_aluminium_transoms','silver',x,level,new_width,.042,.13,.00)
    facade.box('narrow_sill_caps','silver',x,low-.025,new_width+.08,.045,.22,.025)
    new_windows.append(window)
for group in groups.values():
    obj=group.finish();obj.name='PEL_NEXT_'+obj.name.removeprefix('PEL_D5_');obj.data.name=obj.name
    for modifier in obj.modifiers:
        if modifier.type=='BEVEL':modifier.width=.004
    owned.append(obj)
assert len(new_windows)==22
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
def aperture_results():
    vertices,faces,owners=[],[],[]
    for obj in collection.all_objects:
        if obj.type!='MESH' or obj.hide_render:continue
        start=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        faces.extend(tuple(start+i for i in p.vertices) for p in obj.data.polygons);owners.extend([obj.name]*len(obj.data.polygons))
    tree=BVHTree.FromPolygons(vertices,faces);results=[]
    for window in new_windows:
        for fraction in (.12,.35,.80):
            x=window['x']+.09;z=window['low']+(window['high']-window['low'])*fraction
            hit=tree.ray_cast(Vector(facade.point(x,z,.50)),-normal,1)
            results.append({'x':x,'height':z,'firstSurface':owners[hit[2]] if hit[2] is not None else None})
    return results
probes=aperture_results();assert all(p['firstSurface']=='PEL_NEXT_narrow_glass_glass' for p in probes),probes
component=OUT/'pethick-windows-component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
audit={'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'originalFingerprints':originals,'originalVisibility':visibility,'archivedObjects':archived,'ownedObjects':[o.name for o in owned],'removedFrontMembers':removed,'originalFrontWindows':33,'correctedFrontWindows':22,'windowWidthEstimateM':.55,'apertureChecks':probes,'sources':[{'local':'data/建筑图片/PEL_Pethick-Lawrence House/01_建筑实拍/exteriors_lse_estate_023.jpg','url':'https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate','captureDate':None},{'local':'data/建筑图片/PEL_Pethick-Lawrence House/01_建筑实拍/tower_photos_round4_tower_round4_realm_p67_6.jpg','url':'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/2022-LSE-Public-Realm-Strategy.pdf','captureDate':'2021-08-31'}],'limitations':['Two outer narrow-window columns follow lower entrance-facing photographs','Upper continuation of this rhythm is extrapolated, not independently observed','Existing44m height and floor levels remain estimates','Other elevations and roof retained pending complete building photography','Window widths and aluminium profiles are photographic estimates','No new interior reconstruction']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print('PEL_WINDOW_COMPONENT_SAVED',component.stat().st_size,flush=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE));collection=bpy.data.collections['PEL_EXTERIOR']
for scene in bpy.data.scenes:
    for layer in scene.view_layers:layer.update()
with bpy.data.libraries.load(str(component),link=False) as (source,target):target.objects=audit['ownedObjects']
for obj in target.objects:collection.objects.link(obj)
for name in archived:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
assert all(p['firstSurface']=='PEL_NEXT_narrow_glass_glass' for p in aperture_results())
(OUT/'verification.json').write_text(json.dumps({'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'baselineUnchanged':hashlib.sha256(BASE.read_bytes()).hexdigest()==audit['baselineSha256'],'originalGeometryPreserved':True,'reloadedGlassFirstProbes':66},indent=2)+'\n');print('PEL_WINDOW_COMPONENT_RELOADED_VERIFIED',flush=True)
