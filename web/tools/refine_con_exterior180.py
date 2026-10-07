"""Remove duplicate optical surfaces from eight registered CON entrance panes.

The source batches and all unregistered panes survive. Optical estimates belong
only to photographed glass with previously registered vestibule support.
"""
import bpy
from mathutils import Vector
PREFIX='CON_EXTERIOR180_'
TARGETS={'CON_NEXT_GLAZING151_registered_lower_frontage_glass':(1,2,5,6,7),'CON_NEXT_GLAZING151_fanlight_glass':(0,),'CON_NEXT_GLAZING151_inner_door_glass':(0,1)}
OUTWARD=Vector((.16680996119976044,-.9859890937805176,0))


def apply_con_exterior180():
    names=[PREFIX+k.removeprefix('CON_NEXT_GLAZING151_')for k in TARGETS]
    if all(bpy.data.objects.get(n)for n in names):
        return dict(alreadyApplied=True,addedObjects=[],archivedObjects=[],changedObjects=[])
    if any(bpy.data.objects.get(n)for n in names):raise RuntimeError('Incomplete CON180 component')
    records=[]
    for source_name,targets in TARGETS.items():
        source=bpy.data.objects[source_name];data=source.data;retained=[];selected=[]
        normal_matrix=source.matrix_world.to_3x3().inverted().transposed()
        for part in range(len(data.vertices)//8):
            ids=set(range(part*8,part*8+8));faces=[f for f in data.polygons if set(f.vertices).issubset(ids)]
            assert len(faces)==6
            if part not in targets:retained.extend((f,list(f.loop_indices))for f in faces);continue
            broad=[f for f in faces if abs((normal_matrix@f.normal).normalized().dot(OUTWARD))>.999]
            assert len(broad)==2
            face=max(broad,key=lambda f:(source.matrix_world@f.center).dot(OUTWARD));loops=list(face.loop_indices)
            if (normal_matrix@face.normal).normalized().dot(OUTWARD)<0:loops.reverse()
            retained.append((face,loops));selected.append(dict(part=part,face=face.index))
        used=sorted({data.loops[i].vertex_index for face,loops in retained for i in loops});lookup={v:i for i,v in enumerate(used)}
        mesh=bpy.data.meshes.new(PREFIX+source_name.removeprefix('CON_NEXT_GLAZING151_'));mesh.from_pydata([data.vertices[i].co for i in used],[],[tuple(lookup[data.loops[i].vertex_index]for i in loops)for face,loops in retained]);mesh.update()
        for material in data.materials:mesh.materials.append(material)
        for layer in data.uv_layers:
            new=mesh.uv_layers.new(name=layer.name)
            for face,record in zip(mesh.polygons,retained):
                for li,old_li in zip(face.loop_indices,record[1]):new.data[li].uv=layer.data[old_li].uv
        for face,(old,loops)in zip(mesh.polygons,retained):face.material_index=old.material_index
        clone=source.copy();clone.data=mesh;clone.name=mesh.name
        for collection in source.users_collection:collection.objects.link(clone)
        selected_materials={data.polygons[r['face']].material_index for r in selected}
        for index in selected_materials:
            mat=data.materials[index].copy();mat.name=PREFIX+source_name.removeprefix('CON_NEXT_GLAZING151_')+'_optical';mesh.materials[index]=mat
            if source_name.endswith('inner_door_glass'):
                shader=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');shader.inputs['Metallic'].default_value=0;shader.inputs['Alpha'].default_value=.42;mat['webOpacity']=.42
                mat['opticalEstimate']='Photographed inner vestibule visibility; estimated42percent web opacity, not measured coating'
        clone.hide_render=False;clone.hide_set(False);source.hide_render=True;source.hide_set(True)
        records.append(dict(source=source_name,owned=clone.name,selectedSourceFaces=selected,retainedOriginalFaceIndices=[f.index for f,loops in retained],originalVertices=used,sourceUvLayers=[u.name for u in data.uv_layers],singlePaneCount=len(selected),unchangedProxyParts=len(data.vertices)//8-len(targets)))
    return dict(alreadyApplied=False,addedObjects=names,archivedObjects=list(TARGETS),changedObjects=[],records=records,sourceURL='https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate',sourcePhotos=['data/建筑图片/CON_Connaught House/01_建筑实拍/exteriors_lse_estate_005.jpg'],photographDate='unknown',scope='Eight151-registered panes only; lower-frontage/fanlight opacity82percent retained, two inner doors metal0/opacity42percent estimate',limitations=['Full upper facade/roof still lack attributed photograph registration','Unregistered29lower proxy panes preserved opaque','Registered vestibule geometry inherited photo estimates, not2026survey'])
