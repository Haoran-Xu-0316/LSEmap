"""Complete the photographed near-corner Kingsway roof strip on loaded campus.
The ten retained dormers, portal, remaining roof and all source data survive.
"""
import bpy,bmesh
from mathutils import Vector

SOURCE='61A_D5_main_roof'
BASE='61A177_retained_roof_outside_registered_slope'
SLOPE='61A177_Kingsway_ten_dormer_roof_slope'
APRON_SOURCE='61A_D5_slate_apron_slate'
APRON='61A177_retained_slate_apron_outside_ten_dormers'
PHOTO='data/collections/campus_photos_round2/images/61A/61A_aldwych_survey_01.jpg'
SOURCE_URL='https://www.walshandassociates.co.uk/projects'
INDICES=list(range(6,16))

def registration():
    o=bpy.data.objects['61A_D5_roof_dormer_stone'];rows=[]
    for index in INDICES:
        ps=[o.matrix_world@v.co for v in o.data.vertices[index*8:index*8+8]]
        rows.append(sum(ps,Vector())/8)
    c=rows[0];u=(rows[-1]-c).normalized();u.z=0;u.normalize();n=Vector((-u.y,u.x,0))
    stations=[(p-c).dot(u)for p in rows];pitch=(stations[-1]-stations[0])/(len(stations)-1)
    return c,u,n,stations,pitch

def clip(poly,axis,value,greater):
    """Clip convex attributed vertices without changing their interpolated UV."""
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=(a[0][axis]-value)*(1 if greater else -1);db=(b[0][axis]-value)*(1 if greater else -1)
        if da>=-1e-9:out.append(a)
        if (da>1e-9 and db<-1e-9)or(da<-1e-9 and db>1e-9):
            t=da/(da-db);out.append((a[0].lerp(b[0],t),[x.lerp(y,t)for x,y in zip(a[1],b[1])]))
    return out

def intersect(poly,bounds):
    for axis,value,greater in [(0,bounds[0],True),(0,bounds[1],False),(1,bounds[2],True),(1,bounds[3],False)]:
        poly=clip(poly,axis,value,greater)
        if len(poly)<3:return []
    return poly

def subtract(poly,bounds):
    out=[];inside=poly
    for axis,value,greater in [(0,bounds[0],True),(0,bounds[1],False),(1,bounds[2],True),(1,bounds[3],False)]:
        outside=clip(inside,axis,value,not greater)
        if len(outside)>=3:out.append(outside)
        inside=clip(inside,axis,value,greater)
        if len(inside)<3:break
    return out

def apply_61a_exterior177():
    if all(bpy.data.objects.get(k)for k in [BASE,SLOPE,APRON]):
        return dict(alreadyApplied=True,addedObjects=[],archivedObjects=[],changedObjects=[])
    source=bpy.data.objects[SOURCE];col=bpy.data.collections['61A_EXTERIOR'];c,u,n,stations,pitch=registration()
    def world(x,d,z):return Vector((c.x,c.y,0))+u*x+n*d+Vector((0,0,z))
    def local(p):return Vector(((p-c).dot(u),(p-c).dot(n),p.z))
    bounds=(stations[0]-1.25,stations[-1]+1.25,-1.05,1.35)
    holes=[(x-.977,x+.977,-.677,.81)for x in stations]
    # Remove only the strip footprint, retaining flat support pads under dormers.
    vv=[];ff=[];uvs=[];slots=[]
    for face in source.data.polygons:
        poly=[]
        for li in face.loop_indices:
            p=local(source.matrix_world@source.data.vertices[source.data.loops[li].vertex_index].co)
            poly.append((p,[layer.data[li].uv.copy()for layer in source.data.uv_layers]))
        retained=subtract(poly,bounds);inside=intersect(poly,bounds)
        if inside:
            retained.extend(q for h in holes if len(q:=intersect(inside,h))>=3)
        for q in retained:
            if len(q)<3:continue
            start=len(vv);vv.extend(world(*p)for p,uv in q);ff.append(tuple(range(start,len(vv))));uvs.extend(uv for p,uv in q);slots.append(face.material_index)
    mesh=bpy.data.meshes.new(BASE);mesh.from_pydata(vv,[],ff);mesh.update()
    for material in source.data.materials:mesh.materials.append(material)
    for i,layer in enumerate(source.data.uv_layers):
        dst=mesh.uv_layers.new(name=layer.name)
        for f,slot in zip(mesh.polygons,slots):
            f.material_index=slot
            for li,vi in zip(f.loop_indices,f.vertices):dst.data[li].uv=uvs[vi][i]
    base=bpy.data.objects.new(BASE,mesh);col.objects.link(base)
    apron_source=bpy.data.objects[APRON_SOURCE]
    vv=[];ff=[];uvs=[];slots=[]
    for face in apron_source.data.polygons:
        poly=[]
        for li in face.loop_indices:
            p=local(apron_source.matrix_world@apron_source.data.vertices[apron_source.data.loops[li].vertex_index].co)
            poly.append((p,[layer.data[li].uv.copy()for layer in apron_source.data.uv_layers]))
        retained=subtract(poly,bounds);inside=intersect(poly,bounds)

        for q in retained:
            if len(q)<3:continue
            start=len(vv);vv.extend(world(*p)for p,uv in q);ff.append(tuple(range(start,len(vv))));uvs.extend(uv for p,uv in q);slots.append(face.material_index)
    mesh=bpy.data.meshes.new(APRON);mesh.from_pydata(vv,[],ff);mesh.update()
    for material in apron_source.data.materials:mesh.materials.append(material)
    for i,layer in enumerate(apron_source.data.uv_layers):
        dst=mesh.uv_layers.new(name=layer.name)
        for f,slot in zip(mesh.polygons,slots):
            f.material_index=slot
            for li,vi in zip(f.loop_indices,f.vertices):dst.data[li].uv=uvs[vi][i]
    apron=bpy.data.objects.new(APRON,mesh);col.objects.link(apron)
    # Closed wedge; exact retained eave datum29.5 and retained legacy inner ridge32.1.
    x0,x1,d0,d1=bounds
    vs=[world(x,d,z)for z in [29.46,29.55]for d in [d0,d1]for x in [x0,x1]]
    vs[4].z=vs[5].z=32.1
    roofmesh=bpy.data.meshes.new(SLOPE);roofmesh.from_pydata(vs,[],[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)]);roofmesh.update()
    roof=bpy.data.objects.new(SLOPE,roofmesh);col.objects.link(roof)
    bm=bmesh.new();bm.from_mesh(roofmesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(roofmesh);bm.free()
    for lo,hi,da,db in holes:
        bpy.ops.mesh.primitive_cube_add(size=1,location=world((lo+hi)/2,(da+db)/2,31))
        cutter=bpy.context.object;cutter.rotation_euler[2]=__import__('math').atan2(u.y,u.x);cutter.scale=(hi-lo,db-da,5)
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        mod=roof.modifiers.new('Retained dormer clearance','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
        bpy.context.view_layer.objects.active=roof;bpy.ops.object.modifier_apply(modifier=mod.name)
        temp=cutter.data;bpy.data.objects.remove(cutter,do_unlink=True);bpy.data.meshes.remove(temp)
    # Seat the closed eave around the retained cornice without overlapping it.
    # Source cornice section in this registered straight wing: depth0.97..1.35,
    # z29.40..29.56. A continuous3mm seat avoids coplanar Boolean remnants.
    bpy.ops.mesh.primitive_cube_add(size=1,location=world((x0+x1)/2,1.1635,29.48))
    seat=bpy.context.object;seat.rotation_euler[2]=__import__('math').atan2(u.y,u.x)
    seat.scale=(x1-x0+.006,.393,.166)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    mod=roof.modifiers.new('Retained cornice seating clearance','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=seat
    bpy.context.view_layer.objects.active=roof;bpy.ops.object.modifier_apply(modifier=mod.name)
    temporary=seat.data;bpy.data.objects.remove(seat,do_unlink=True);bpy.data.meshes.remove(temporary)
    bm=bmesh.new();bm.from_mesh(roof.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(roof.data);bm.free()
    mat=bpy.data.materials['61A_slate'].copy();mat.name='61A177_registered_street_slate';roof.data.materials.clear();roof.data.materials.append(mat)
    for face in roof.data.polygons:face.material_index=0
    uv=roof.data.uv_layers.new(name='MetricRoofUV')
    for face in roof.data.polygons:
        ps=[roof.data.vertices[i].co for i in face.vertices];a=ps[0];aa=(ps[1]-a).normalized();nn=face.normal;bb=nn.cross(aa)
        for li,vi in zip(face.loop_indices,face.vertices):
            p=roof.data.vertices[vi].co-a;uv.data[li].uv=(p.dot(aa),p.dot(bb))
    source.hide_render=True;source.hide_set(True)
    apron_source.hide_render=True;apron_source.hide_set(True)
    return dict(alreadyApplied=False,addedObjects=[BASE,SLOPE,APRON],archivedObjects=[SOURCE,APRON_SOURCE],changedObjects=[],sourceURL=SOURCE_URL,sourcePhotos=[PHOTO],reviewScope='Near-corner Kingsway street wing roof strip behind10retained dormers; not full roof',registration={'origin':list(c),'axis':list(u),'outward':list(n),'stripBounds':list(bounds),'dormerIndices':INDICES,'dormerStations':stations,'holeBounds':holes,'eaveZ':29.55,'innerRidgeZ':32.1,'method':'Retained native wall/dormer coordinates; Retained legacy photograph-estimated2.4m slope depth and2.55m rise; replace backwards uncropped apron with outward closed roof and true dormer openings','photographDate':'unknown'},limitations=['Historical pre-redevelopment photograph, not2026survey','Rear roof and far street continuation retained provisional','Portal and all26dormer shapes/UV/materials untouched; only10near-corner dormers register this slope'])
