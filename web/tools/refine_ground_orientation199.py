"""Correct inward native ground shells without changing their layout or UVs.

Run in Blender's Text Editor. Closed site shells use outward normals; flat grass sheets face upward.
Ambiguous open nonplanar meshes are left untouched. The original objects and source remain intact.
"""
from pathlib import Path
import hashlib,json,sys
import bpy,bmesh
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'result/blender/LSE_campus_detailed_v198.blend'
SHA='b45a6a433f350226beecfd201457420d86b2d253796098f86ff5417d5752b27e'
OUT=ROOT/'result/blender/ground-orientation199'
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import object_fingerprint
from refine_street_connections194 import corner_signature


def closed_islands(bm):
    pending=set(bm.faces);result=[]
    while pending:
        seed=pending.pop();faces={seed};queue=[seed]
        while queue:
            face=queue.pop()
            for edge in face.edges:
                for linked in edge.link_faces:
                    if linked in pending:pending.remove(linked);faces.add(linked);queue.append(linked)
        edges={edge for face in faces for edge in face.edges}
        result.append((faces,all(edge.is_manifold for edge in edges)))
    return result


def signed_volume(faces):
    value=0
    origin=next(iter(faces)).verts[0].co
    for face in faces:
        points=[vertex.co-origin for vertex in face.verts]
        for index in range(1,len(points)-1):value+=points[0].dot(points[index].cross(points[index+1]))/6
    return value


def build_component():
    OUT.mkdir(parents=True,exist_ok=True);assert hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
    before={obj.name:object_fingerprint(obj)for obj in bpy.data.objects}
    added=[];archived=[];records=[];skipped=[]
    candidates=list(dict.fromkeys(list(bpy.data.collections['00_SITE'].all_objects)+list(bpy.data.collections['03_PUBLIC_REALM'].all_objects)))
    for original in candidates:
        if original.type!='MESH' or original.hide_render:continue
        if not (original.name=='Local_ground_datum' or original.name.startswith(('00_SITE_Road_','Road_','GIS_green_'))):continue
        bm=bmesh.new();bm.from_mesh(original.data);bm.normal_update();islands=closed_islands(bm)
        heights=[(original.matrix_world@vertex.co).z for vertex in original.data.vertices]
        flat_green=original.name.startswith('GIS_green_') and max(heights)-min(heights)<1e-5
        if flat_green:
            normal_matrix=original.matrix_world.inverted().transposed().to_3x3()
            inward=[{face} for face in bm.faces if (normal_matrix@face.normal).z<-.5]
        elif all(closed for _,closed in islands):
            inward=[faces for faces,_ in islands if signed_volume(faces)<-1e-9]
        else:
            skipped.append(dict(object=original.name,reason='Ambiguous open/nonmanifold nonplanar shell; no orientation inference'));bm.free();continue
        if not inward:bm.free();continue
        original_signature=corner_signature(original.data)
        flipped=sum(len(faces)for faces in inward)
        for faces in inward:bmesh.ops.reverse_faces(bm,faces=list(faces))
        bm.normal_update()
        if flat_green:assert all((normal_matrix@face.normal).z>.5 for face in bm.faces)
        else:assert all(signed_volume(faces)>0 for faces,_ in closed_islands(bm))
        data=original.data.copy();data.name='GROUND199_'+original.name+'_mesh';bm.to_mesh(data);data.update();bm.free()
        assert corner_signature(data)==original_signature
        target=original.copy();target.data=data;target.name='GROUND199_'+original.name
        target['originalObject']=original.name
        for collection in original.users_collection:collection.objects.link(target)
        target.hide_render=False;target.hide_set(False)
        added.append(target.name);archived.append(original.name)
        records.append(dict(source=original.name,target=target.name,facesReoriented=flipped,closedComponents=0 if flat_green else len(islands),flatGreenSheet=flat_green,negativeComponentsBefore=0 if flat_green else len(inward),negativeComponentsAfter=0,cornerSignature=original_signature))
    assert 'GIS_green_way/30613392' in archived,'Observed park defect was not corrected'
    assert all(object_fingerprint(bpy.data.objects[name])==signature for name,signature in before.items())
    component=OUT/'ground-orientation199-component.blend';bpy.data.libraries.write(str(component),{bpy.data.objects[name]for name in added},fake_user=True,compress=True)
    report=dict(version=199,baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=hashlib.sha256(component.read_bytes()).hexdigest(),
                targetCollection='00_SITE',addedObjects=added,archivedObjects=archived,changedObjects=[],records=records,skipped=skipped,
                scope='Reverse inward closed site ground shells and downward flat grass sheets; preserve world layout, all vertex coordinates, face-to-corner UVs and material bindings. No added or removed ground coverage.',
                evidence='Observed black park patch in native review: ray hits GIS_green_way/30613392 atz0.05 with downward surface normal. Other original closed ground shells checked by signed volume.',
                limitations='Orientation repair does not verify road widths, landscape boundaries or current site survey accuracy.')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.objects=list(added)
    lookup={row['target']:row for row in records}
    for obj in dst.objects:
        bpy.context.scene.collection.objects.link(obj);assert corner_signature(obj.data)==lookup[obj.name]['cornerSignature']
        bm=bmesh.new();bm.from_mesh(obj.data);bm.normal_update()
        if lookup[obj.name]['flatGreenSheet']:assert all(face.normal.z>.5 for face in bm.faces)
        else:assert all(closed and signed_volume(faces)>0 for faces,closed in closed_islands(bm))
        bm.free()
    report['verification']=dict(componentReopened=True,allOwnedShellsOutward=True,positionsCoverageCornerUVAndBindingsPreserved=True,baselineSha256Unchanged=hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA)
    assert report['verification']['baselineSha256Unchanged']
    (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('GROUND199_ORIENTATION_COMPONENT',len(added),sum(r['facesReoriented']for r in records),flush=True)


if __name__=='__main__':build_component()
