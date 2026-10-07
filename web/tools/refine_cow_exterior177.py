"""COW177: outward glass boxes and seated solid street-dormer roof sheets.

The LSE Estates photograph and contractor's2019 project photo show complete
pitched caps over the photographed street dormers. Existing cap top coordinates
and window registration are retained;0.06m effective cap assembly thickness is
photo-estimated; cheek upper edges are seated to the retained cap pitch, not measured lead-sheet thickness.
The four unphotographed dormer cap/cheek pairs and whole roof layout are unchanged.
No interior, glass opacity, material colour or window subdivision is invented.
Call on the loaded campus; this module does not read or save a complete model.
"""
import bpy
import bmesh
from mathutils import Vector

COLLECTION='COW177_STREET_SURFACES'
GLASS='COW_D5_window_glass_glass'
CAPS='COW_D5_dormer_pitched_cap_lead'
CAP_DEPTH=.06
CHEEKS='COW_D5_dormer_cheek_lead'
# Accepted source footprint registration, same street edges used by joinery98.
STREET_EDGES=[
 ((27.80905944219141,-14.18533304763732),(-4.9911844889841745,-6.898000466597701),7),
 ((-4.9911844889841745,-6.898000466597701),(-5.789492048801045,-3.1374754575428563),1),
 ((-5.789492048801045,-3.1374754575428563),(2.624009021212343,7.242903819508863),3),
]
SOURCE_URLS=[
 'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Images/LSE-Estate/Cowdray-web.jpg',
 'https://www.russellcawberry.com/projects/cowdray-house',
 'https://www.russellcawberry.com/files/projects/Cowdray%2520House/056_cowdray_house_MR.jpg',
]

def street_windows():
    windows=[]
    for p,q,count in STREET_EDGES:
        start,end=Vector((*p,0)),Vector((*q,0));axis=(end-start).normalized();normal=Vector((-axis.y,axis.x,0))
        for index in range(count):
            windows.append(dict(center=start+(end-start)*((index+.5)/count),axis=axis,normal=normal))
    return windows

def street_face(source, face):
    center=source.matrix_world@face.calc_center_median()
    for window in street_windows():
        offset=center-window['center']
        if abs(offset.dot(window['axis']))<.6 and -.8<offset.dot(window['normal'])<-.3 and 20.5<center.z<21:
            return True
    return False

def clone(source, name, collection):
    obj=source.copy();obj.data=source.data.copy();obj.name=name;obj.data.name=name+'_mesh';collection.objects.link(obj)
    obj.hide_render=False;obj.hide_set(False)
    return obj

def archive(source, collection):
    for owner in list(source.users_collection):owner.objects.unlink(source)
    collection.objects.link(source);source.hide_render=True;source.hide_set(True)

def metric_uv(obj, first_face=0):
    mesh=obj.data
    if not mesh.uv_layers:
        mesh.uv_layers.new(name='MetricUV');first_face=0
    for layer in mesh.uv_layers:
        for face in mesh.polygons:
            if face.index<first_face:continue
            points=[obj.matrix_world@mesh.vertices[mesh.loops[i].vertex_index].co for i in face.loop_indices]
            axis=(points[1]-points[0]).normalized();normal=obj.matrix_world.to_3x3()@face.normal;second=normal.cross(axis)
            for li,point in zip(face.loop_indices,points):
                layer.data[li].uv=((point-points[0]).dot(axis),(point-points[0]).dot(second))

def apply_cow_exterior177():
    if bpy.data.collections.get(COLLECTION):
        return dict(alreadyApplied=True,addedObjects=[],archivedObjects=[],changedObjects=[])
    exterior=bpy.data.collections['COW_EXTERIOR'];collection=bpy.data.collections.new(COLLECTION);exterior.children.link(collection)
    archived=bpy.data.collections.new('COW177_SOURCE_ARCHIVE');bpy.context.scene.collection.children.link(archived)
    glass_source=bpy.data.objects[GLASS];caps_source=bpy.data.objects[CAPS];cheeks_source=bpy.data.objects[CHEEKS]
    glass=clone(glass_source,'COW_NEXT_EXTERIOR177_glass_outward',collection)
    bm=bmesh.new();bm.from_mesh(glass.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(glass.data);bm.free();glass.data.update()
    if not glass.data.uv_layers:metric_uv(glass)
    caps=clone(caps_source,'COW_NEXT_EXTERIOR177_street_roofcaps',collection)
    bm=bmesh.new();bm.from_mesh(caps.data);selected=[face for face in list(bm.faces)if street_face(caps_source,face)]
    assert len(selected)==22,('Expected two roof sheets on each of11street dormers',len(selected))
    inverse=caps_source.matrix_world.inverted().to_3x3();down=inverse@Vector((0,0,-CAP_DEPTH))
    # Each original slope retains its top surface and original UV-point bindings.
    # Close each sheet independently: the two pitched sheets meet along the ridge.
    for face in selected:
        original=list(face.verts);bottom=[bm.verts.new(v.co+down)for v in original]
        underside=bm.faces.new(list(reversed(bottom)))
        sides=[bm.faces.new([original[i],original[(i+1)%4],bottom[(i+1)%4],bottom[i]])for i in range(4)]
        bmesh.ops.recalc_face_normals(bm,faces=[face,underside]+sides)
    bm.to_mesh(caps.data);bm.free();caps.data.update()
    metric_uv(caps,first_face=len(caps_source.data.polygons))
    cheeks=clone(cheeks_source,'COW_NEXT_EXTERIOR177_seated_cheeks',collection)
    bm=bmesh.new();bm.from_mesh(cheeks.data);seen=set();owned_count=0
    for seed in list(bm.verts):
        if seed in seen:continue
        stack=[seed];seen.add(seed);part=[]
        while stack:
            vertex=stack.pop();part.append(vertex)
            for edge in vertex.link_edges:
                other=edge.other_vert(vertex)
                if other not in seen:seen.add(other);stack.append(other)
        points=[cheeks.matrix_world@vertex.co for vertex in part];center=sum(points,Vector())/len(points)
        matched=None
        for window in street_windows():
            offset=center-window['center']
            if .5<abs(offset.dot(window['axis']))<.85 and -.9<offset.dot(window['normal'])<-.5:
                matched=window;break
        if not matched:continue
        owned_count+=1
        for vertex,point in zip(part,points):
            if point.z<20.38:continue
            x=(point-matched['center']).dot(matched['axis'])
            point.z=20.92-.38*abs(x)/.91-CAP_DEPTH+.001
            vertex.co=cheeks.matrix_world.inverted()@point
        bmesh.ops.recalc_face_normals(bm,faces=list({face for vertex in part for face in vertex.link_faces}))
    assert owned_count==22,owned_count
    bm.to_mesh(cheeks.data);bm.free();cheeks.data.update()
    if not cheeks.data.uv_layers:metric_uv(cheeks)
    cheeks['photoEstimatedSlopedTop']=True
    caps['ownedStreetDormers']=11;caps['assemblyDepthEstimate']=CAP_DEPTH
    collection['scope']='110glass-box outward normals;11photographed street-dormer caps closed and seated; four other cap pairs unchanged'
    collection['sourceURL']='; '.join(SOURCE_URLS)
    collection['dateLimitations']='Contractor2019 project, capture unknown; Estates photograph capture unknown; no2026survey claim'
    archive(glass_source,archived);archive(caps_source,archived);archive(cheeks_source,archived)
    return dict(alreadyApplied=False,addedObjects=[glass.name,caps.name,cheeks.name],archivedObjects=[glass_source.name,caps_source.name,cheeks_source.name],changedObjects=[])
