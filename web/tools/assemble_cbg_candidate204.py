"""Combine registered CBG wing, metric office and roof work without duplication.

A saved whole-building review remains private until podium, roof circulation,
photographed facade counts and world cameras are reconciled. Source203 is read-only.
"""
from pathlib import Path
import hashlib
import json
import sys
import bpy
import bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import object_fingerprint
from refine_ground_orientation199 import closed_islands,signed_volume
from refine_cbg_roof203 import frame,volume_planes,trim_object,REAR_DECK,END_DECK,HEIGHT
OUT=ROOT/'result/blender/cbg-assembled204'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def build_candidate():
    OUT.mkdir(parents=True,exist_ok=True)
    reports={name:json.loads((ROOT/f'result/blender/{name}/audit.json').read_text())for name in ['cbg-envelope202','cbg-wing203','cbg-office204','cbg-teaching204','cbg-roof203']}
    inputs={name:ROOT/report['componentPath']for name,report in reports.items()}
    for name,path in inputs.items():assert digest(path)==reports[name]['componentSha256'],name
    frozen={str(path.relative_to(ROOT)):digest(path)for path in inputs.values()}
    native=ROOT/'result/blender/LSE_campus_detailed_v203.blend';native_sha=digest(native)
    assert native_sha=='976e645ef4b58e19485feff1fe3ff2fb64d9b5d497739642a2429548d821df8a'
    mapping=json.loads((ROOT/'result/blender/cbg-georegistration202/rebuild-mapping.json').read_text());local,world=frame(mapping)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene;scene.name='CBG204_ASSEMBLED_PRIVATE_REVIEW'
    collection=bpy.data.collections.new('CBG204_ASSEMBLED');scene.collection.children.link(collection)
    def append(name,names):
        with bpy.data.libraries.load(str(inputs[name]),link=False)as(src,loaded):loaded.objects=list(names)
        result=list(loaded.objects)
        for obj in result:collection.objects.link(obj)
        return result
    objects=append('cbg-wing203',reports['cbg-wing203']['addedObjects'])
    removed=[]
    def replace(name,key):
        nonlocal objects
        dead=set(reports[name][key]);assert dead<=set(o.name for o in objects)
        for obj in list(objects):
            if obj.name in dead:removed.append(obj.name);objects.remove(obj);bpy.data.objects.remove(obj,do_unlink=True)
        objects+=append(name,reports[name]['addedObjects'])
    replace('cbg-office204','archivedInputObjects');replace('cbg-teaching204','removeObjects')
    source_owners={row['source']:row['sourceOwners']for row in reports['cbg-envelope202']['records']}
    # New office groups retain the old semantic owner, without replacing the
    # entire old facade batch when only its top is clipped.
    new_office_owner={
        'metric_office_glass':'CBG194_GLASS181_CBG_NEXT_office_glass',
        'retained_circulation_glass':'CBG194_GLASS181_CBG_NEXT_EXTERIOR166_curtain_with_door_apertures',
        'metric_office_solid':'CBG_NEXT_office_solid',
        'metric_office_vent_transoms':'CBG_NEXT_office_frames',
        'metric_front_jambs':'CBG_NEXT_office_frames',
        'metric_front_heads_sills':'CBG_NEXT_office_frames'}
    trim_rows=[];residual_column_parts=0
    for source in list(objects):
        if not source.data.vertices:
            removed.append(source.name);objects.remove(source);bpy.data.objects.remove(source,do_unlink=True);continue
        if source.name.startswith('CBG204_OFFICE_')and'originalObject'not in source:
            suffix=source.name.removeprefix('CBG204_OFFICE_');source['originalObject']=new_office_owner[suffix]
        owner=source.get('originalObject','')
        source['destinationCollection']='CBG_PUBLIC_INTERIOR_study'if'CBG_PUBLIC_INTERIOR_study'in source_owners.get(owner,[])or source.name.endswith(('registered_teaching_floor_plates','registered_lower_gallery_plates'))else'CBG_EXTERIOR'
        # Remove stale rectangle end skins at the oldx0 negative-y interface.
        # Tower end skins occupy positive-y, and retained public interior stays.
        if source.name.startswith('CBG203_WING_retained_') and 'CBG_EXTERIOR' in source_owners.get(owner,[]):
            bm=bmesh.new();bm.from_mesh(source.data);delete=[]
            for faces,closed in closed_islands(bm):
                vertices={v for face in faces for v in face.verts};pts=[local(source.matrix_world@v.co)for v in vertices]
                centre=sum(pts,Vector())/len(pts)
                if -.8<centre.x<.5 and centre.y<-3 and max(p.z for p in pts)<28.5:delete.extend(vertices)
            if delete:
                bmesh.ops.delete(bm,geom=list(set(delete)),context='VERTS');bm.to_mesh(source.data);source.data.update()
            bm.free()
            if not source.data.vertices:
                removed.append(source.name);objects.remove(source);bpy.data.objects.remove(source,do_unlink=True);continue
        # The original25m rectangle's columns atx0 survived the previous wing
        # deletion threshold. They are obsolete; the newly registered system stays.
        if source.name.startswith('CBG203_WING_retained_CBG202_CBG194_CBG_D_external_I_columns'):
            bm=bmesh.new();bm.from_mesh(source.data);delete=[]
            for faces,closed in closed_islands(bm):
                vertices={v for face in faces for v in face.verts};pts=[local(source.matrix_world@v.co)for v in vertices]
                if max(p.z for p in pts)<28.5:delete.extend(vertices);residual_column_parts+=1
            if delete:bmesh.ops.delete(bm,geom=list(set(delete)),context='VERTS');bm.to_mesh(source.data);source.data.update()
            bm.free()
            if not source.data.vertices:removed.append(source.name);objects.remove(source);bpy.data.objects.remove(source,do_unlink=True);continue
        if not owner:continue
        footprints=reports['cbg-roof203']['cutbackFootprints']
        glass=any(m and('glass'in m.name.lower()or m.get('webOpacity',1)<1)for m in source.data.materials)
        cut_z=REAR_DECK-.01 if glass else REAR_DECK+.30
        volumes=[volume_planes(footprints['rearTerrace'],cut_z,56),volume_planes(footprints['coreEndSetback'],cut_z,56)]
        if not any(tag in owner for tag in ['external_I_columns','roof_and_ground_plates','red_roof_recess']):
            volumes.append(volume_planes(footprints['openCanopy'],END_DECK-.01 if glass else END_DECK+.4,56 if glass else HEIGHT-.38))
        if any(tag in owner for tag in ['tower_floor_plates','tower_front_galleries']):volumes.append(volume_planes(footprints['upperStairWell'],REAR_DECK-.35,REAR_DECK+.18))
        result=trim_object(source,local,world,volumes)
        if result:
            target,row=result;target['destinationCollection']=source['destinationCollection'];collection.objects.link(target)
            objects.remove(source);bpy.data.objects.remove(source,do_unlink=True);objects.append(target);trim_rows.append(row)
    # Explicit top-flight removal is separate from roof-volume clipping. These
    # five public stair batches are unchanged by office/wing authoring, so use
    # their verified eight-flight retained replacements, not inherited ninths.
    stair_rows=[r for r in reports['cbg-roof203']['replacements'] if r['target'].startswith('CBG203_ROOF_lower_retained_')]
    for row in stair_rows:
        matches=[obj for obj in objects if obj.get('originalObject')==row['sourceNative']]
        assert len(matches)==1,(row,matches)
        obsolete=matches[0];objects.remove(obsolete);removed.append(obsolete.name);bpy.data.objects.remove(obsolete,do_unlink=True)
        replacement=append('cbg-roof203',[row['target']])[0]
        replacement['destinationCollection']='CBG_PUBLIC_INTERIOR_study';objects.append(replacement)
    # Only the roof's independent added geometry enters this assembly. Its
    # inherited lower202 replacement meshes would undo office/wing corrections.
    roof_names=[row['target']for row in reports['cbg-roof203']['newGeometry']]
    objects+=append('cbg-roof203',roof_names)
    assert len({o.name for o in objects})==len(objects)
    topology=[]
    for obj in objects:
        if not obj.data.vertices:continue
        bm=bmesh.new();bm.from_mesh(obj.data);bm.normal_update();closed_count,open_count=0,0
        for faces,closed in closed_islands(bm):
            if closed:assert signed_volume(faces)>0,(obj.name,'inward');closed_count+=1
            else:open_count+=1
        bm.free();topology.append(dict(object=obj.name,closedComponents=closed_count,openComponents=open_count))
    path=OUT/'cbg-assembled204-component.blend';bpy.data.libraries.write(str(path),set(objects),fake_user=True,compress=True)
    fingerprints={obj.name:object_fingerprint(obj)for obj in objects}
    report=dict(status='private-whole-building-assembly-not-for-release',componentPath=str(path.relative_to(ROOT)),componentSha256=digest(path),baselineSha256=native_sha,
                inputHashes=frozen,addedObjects=list(fingerprints),removedInputObjects=removed,roofTrims=trim_rows,obsoleteLowColumnPartsRemoved=residual_column_parts,
                topology=topology,officeModules=len(reports['cbg-office204']['officeModules']),officeProbeCount=len(reports['cbg-office204']['surfaceProbes']),
                limitations=['Southern amenity podium still absent; cannot release this as complete envelope.',
                            'Registered upper stair footprint and the inherited upper flight/landing need a connected final geometry.',
                            'Exact facade divisions and floor levels remain photographic or design estimates.',
                            'World exterior/interior/gallery cameras have not been updated to the reversed footprint.'])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(path),link=False)as(src,loaded):loaded.objects=list(fingerprints)
    objects=list(loaded.objects);scene=bpy.context.scene;scene.name='CBG204_ASSEMBLED_PRIVATE_REVIEW'
    for obj in objects:scene.collection.objects.link(obj);assert object_fingerprint(obj)==fingerprints[obj.name]
    report['verification']=dict(componentReopened=True,allFingerprintsMatch=True,inputHashesUnchanged=all(digest(ROOT/p)==sha for p,sha in frozen.items()),native203Unchanged=digest(native)==native_sha)
    scene.world=bpy.data.worlds.new('CBG204_assembly_world');scene.world.color=(.8,.82,.84);scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_cavity=True
    scene.render.resolution_x,scene.render.resolution_y=1500,1100;scene.render.resolution_percentage=100
    cam=bpy.data.objects.new('CBG204_assembly_camera',bpy.data.cameras.new('CBG204_assembly_camera'));scene.collection.objects.link(cam);scene.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=105
    for name,position,target in [('whole',(-18,-85,56),(-4,2,25)),('rear',(-18,85,65),(-8,3,24))]:
        cam.location=world(position);cam.rotation_euler=(world(target)-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
    review=OUT/'cbg-assembled204-review.blend';bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(review))
    report['reviewPath']=str(review.relative_to(ROOT));report['reviewSha256']=digest(review)
    (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n');print('CBG204_ASSEMBLY_REOPENED',len(fingerprints),len(trim_rows),flush=True)


if __name__=='__main__':build_candidate()
