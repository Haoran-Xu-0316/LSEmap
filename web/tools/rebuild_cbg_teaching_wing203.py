"""Reconstruct CBG's stepped teaching-wing envelope in the registered202frame.

Private whole-building candidate only. The25m height/six visible levels remain
inherited photo estimates; theGIS seven-level tag is not silently interpreted
as a new height. Rooms, facade bay counts and podium still require registration.
"""
from pathlib import Path
import hashlib
import json
import math
import sys
import bpy
import bmesh
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from build_room_samples167 import RoomGeometry
from integrate_exterior_round194 import object_fingerprint
from refine_ground_orientation199 import closed_islands, signed_volume

BASE = ROOT / 'result/blender/cbg-envelope202/cbg-envelope202-component.blend'
NATIVE = ROOT / 'result/blender/LSE_campus_detailed_v201.blend'
OUT = ROOT / 'result/blender/cbg-wing203'
PREFIX = 'CBG203_WING_'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clip_below(outline, maximum_y):
    result = []
    for a, b in zip(outline, outline[1:] + outline[:1]):
        if a[1] <= maximum_y:
            result.append(a)
        if (a[1] < maximum_y < b[1]) or (b[1] < maximum_y < a[1]):
            t = (maximum_y-a[1])/(b[1]-a[1])
            result.append((a[0]+t*(b[0]-a[0]), maximum_y))
    return result


def build_candidate():
    OUT.mkdir(parents=True, exist_ok=True)
    source_sha, native_sha = sha(BASE), sha(NATIVE)
    assert native_sha == '83f8532de4378e614f53a327b8c3397ae375e880d655bd584f5e0ea4980f2bec'
    mapping = json.loads((ROOT/'result/blender/cbg-georegistration202/rebuild-mapping.json').read_text())
    source_audit = json.loads((BASE.parent/'audit.json').read_text())
    frame = mapping['frame'];ox,oy = frame['origin_G7_SW_world']
    ux,uy = frame['x_unit_SW'];vx,vy = frame['y_unit_SE_rear']
    def local(p):
        return Vector((ux*(p.x-ox)+uy*(p.y-oy),vx*(p.x-ox)+vy*(p.y-oy),p.z))
    def world(p):
        x,y,z = p
        return Vector((ox+ux*x+vx*y,oy+uy*x+vy*y,z))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(BASE), link=False) as (src,dst):
        dst.objects = source_audit['addedObjects']
    protected = {o.name:object_fingerprint(o) for o in dst.objects}
    collection = bpy.data.collections.new('CBG203_TEACHING_WING_PRIVATE')
    bpy.context.scene.collection.children.link(collection)
    changes, copies = [], []
    replacements = []
    for source in dst.objects:
        target = source.copy();target.data = source.data.copy()
        target.name = PREFIX+'retained_'+source.name
        collection.objects.link(target);copies.append(target)
        # Retain tower and all public circulation/furniture. Replace only the
        # obsolete rectangular low-wing exterior and the structural floor skins.
        owner = source.get('originalObject','')
        record = next((r for r in source_audit['records'] if r['source']==owner),{})
        exterior = 'CBG_EXTERIOR' in record.get('sourceOwners',[])
        floor_family = any(key in owner for key in ['roof_and_ground_plates','interior_floor_plates','low_wing_gallery_slabs','low_roof_terrace_paving'])
        if not (exterior or floor_family):
            continue
        bm=bmesh.new();bm.from_mesh(target.data);delete=[];removed=0
        for faces,closed in closed_islands(bm):
            vertices={v for face in faces for v in face.verts}
            pts=[local(target.matrix_world@v.co)for v in vertices]
            centre=sum(pts,Vector())/len(pts)
            if centre.x > .50 and max(p.z for p in pts) < 28.5:
                # Original separate low-wing solids end at25m. Tall tower solids
                # and its shared end atx0 remain owned by the tower candidate.
                delete.extend(vertices);removed+=1
        if removed:
            bmesh.ops.delete(bm,geom=list(set(delete)),context='VERTS')
            bm.to_mesh(target.data);target.data.update()
            changes.append(dict(source=source.name,target=target.name,removedComponents=removed,owner=owner))
        bm.free()
    def material(owner_contains):
        source=next(o for o in dst.objects if owner_contains in o.get('originalObject',''))
        return source.data.materials[0]
    g=RoomGeometry(collection,PREFIX)
    g.materials.update(glass=material('neutral_end_wall_glazing'),frame=material('end_wall_transoms'),
                       slab=material('roof_and_ground_plates'),stone=material('houghton_stone_rainscreen'),
                       paint=material('external_I_columns'))
    outline=[tuple(p)for p in mapping['houghton_teaching_block']['GIS_polygon_local']]
    perimeter_area=sum(a[0]*b[1]-b[0]*a[1]for a,b in zip(outline,outline[1:]+outline[:1]))
    H,LEVELS=25.0,6;step=H/LEVELS
    for level in [0,4,5,6]:
        g.prism('registered_teaching_floor_plates','slab',outline,level*step-.275,.27)
    gallery=clip_below(outline,-7.5)
    for level in [1,2,3]:
        g.prism('registered_lower_gallery_plates','slab',gallery,level*step-.275,.27)
    perimeter=[]
    for edge,(a,b)in enumerate(zip(outline,outline[1:]+outline[:1])):
        # The first two edges are the shared13-storey tower interface.
        if edge in [0,1]:continue
        delta=Vector((b[0]-a[0],b[1]-a[1]));length=delta.length;axis=delta.normalized()
        out=Vector((axis.y,-axis.x))*(1 if perimeter_area>0 else -1)
        angle=math.atan2(axis.y,axis.x)
        def at(distance,z,offset=0):
            return(a[0]+axis.x*distance+out.x*offset,a[1]+axis.y*distance+out.y*offset,z)
        # Nominal6m structural bays and approximately1.5m glazing divisions are
        # explicit presentation estimates. Exact observed counts are still pending.
        bays=max(1,round(length/6));glass_count=max(1,round(length/1.5))
        for floor in range(LEVELS):
            z0,z1=floor*step,(floor+1)*step
            for i in range(glass_count):
                width=length/glass_count
                g.box('registered_teaching_glazing','glass',at((i+.5)*width,(z0+z1)/2),(width-.075,.035,step-.18),angle)
                g.box('registered_teaching_mullions','frame',at(i*width,(z0+z1)/2,.05),(.065,.15,step),angle)
                g.box('registered_teaching_transoms','frame',at((i+.5)*width,z1-.72,.07),(width,.1,.05),angle)
            g.box('registered_teaching_floor_beams','paint',at(length/2,z0+.08,.18),(length,.42,.35),angle)
            if edge==6 and floor in [1,2]:
                for bay in range(bays):
                    g.box('registered_houghton_stone_panels','stone',at((bay+.5)*length/bays,(z0+z1)/2,.22),(length/bays*.61,.15,step-.4),angle)
        for bay in range(bays+1):
            g.box('registered_teaching_columns','paint',at(bay*length/bays,H/2,.31),(.48,.42,H),angle)
        g.box('registered_teaching_roof_edge','paint',at(length/2,H,.18),(length,.42,.35),angle)
        perimeter.append(dict(edge=edge,start=a,end=b,length=length,nominalStructuralBays=bays,estimatedGlazingDivisions=glass_count))
    added=g.finish()
    for obj in added:
        for vertex in obj.data.vertices:vertex.co=world(vertex.co)
        obj.data.update();obj['candidateScope']='Registered stepped teaching-wing envelope; incomplete facade/room/podium study'
    assert all(object_fingerprint(o)==protected[o.name]for o in dst.objects)
    assert sha(BASE)==source_sha and sha(NATIVE)==native_sha
    objects=copies+added
    component=OUT/'cbg-wing203-component.blend'
    bpy.data.libraries.write(str(component),set(objects),fake_user=True,compress=True)
    fingerprints={o.name:object_fingerprint(o)for o in objects}
    report=dict(status='private-partial-reconstruction-not-for-release',componentPath=str(component.relative_to(ROOT)),componentSha256=sha(component),
                inputComponentSha256=source_sha,nativeBaselineSha256=native_sha,addedObjects=list(fingerprints),changed202Objects=changes,
                registeredWingPolygon=outline,nominalHeight=H,inheritedVisibleLevels=LEVELS,GISLevelTag=7,perimeter=perimeter,
                floorSolidProof=g.solid_proof,source202Preserved=True,native201Preserved=True,
                limitations=['Height25m and6visiblelevels remain inherited photographic estimates, not a reconciliation of GIS7levels.',
                'Perimeter glass and structural counts are estimated modules; solar shades, exposed end bracing and photographed facade counts need reconstruction.',
                'Public interior circulation retained; room partitions and the low southern amenity podium are not completed.',
                'Tower office module widths, roof cutbacks and all camera updates still required before release.'])
    new_names={o.name for o in added}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(component),link=False)as(src,reopened):reopened.objects=list(fingerprints)
    for obj in reopened.objects:
        bpy.context.scene.collection.objects.link(obj)
        assert object_fingerprint(obj)==fingerprints[obj.name]
    for obj in reopened.objects:
        if obj.name not in new_names:continue
        bm=bmesh.new();bm.from_mesh(obj.data);bm.normal_update()
        assert all(closed and signed_volume(faces)>0 for faces,closed in closed_islands(bm)),obj.name
        bm.free()
    report['verification']=dict(reopenedFingerprintCount=len(fingerprints),newShellsOutward=True,
                                native201Unchanged=sha(NATIVE)==native_sha,input202Unchanged=sha(BASE)==source_sha)
    (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    # Whole-candidate review, with no expensive animation or duplicate full campus.
    scene=bpy.context.scene;scene.world=bpy.data.worlds.new('CBG203_wing_review_world');scene.world.color=(.8,.82,.84)
    scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_cavity=True
    scene.render.resolution_x,scene.render.resolution_y=1400,1000;scene.render.resolution_percentage=100
    camera=bpy.data.objects.new('CBG203_wing_review_camera',bpy.data.cameras.new('CBG203_wing_review_camera'));scene.collection.objects.link(camera)
    camera.data.type='ORTHO';camera.data.ortho_scale=100;scene.camera=camera
    for name,position,target in [('whole',(-20,-75,45),(-5,-2,20)),('wing',(-15,-70,42),(14,-5,13))]:
        camera.location=world(position);camera.rotation_euler=(world(target)-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
    print('CBG203_WING_REOPENED',len(fingerprints),sum(r['removedComponents']for r in changes),flush=True)


if __name__=='__main__':build_candidate()
