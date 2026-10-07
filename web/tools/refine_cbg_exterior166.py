"""Remove double glazing behind CBG's eight existing entrance door leaves.

Apply to a loaded scene; never opens or saves a whole-campus file. Built Joas
photographs show transparent entrances with interior structure. Door dimensions
and positions remain inherited estimates. User red/orange shades are preserved.
"""
from pathlib import Path
import math
import bpy,bmesh
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
CURTAIN='CBG_NEXT_office_retained_CBG_NEXT_neutral_curtain_wall_glazing'
DOORS='CBG_NEXT_neutral_entry_glass_door_leaves'
NEW_CURTAIN='CBG_NEXT_EXTERIOR166_curtain_with_door_apertures'
NEW_DOORS='CBG_NEXT_EXTERIOR166_thin_entry_glass'


def apply_cbg_exterior166():
    if bpy.data.objects.get(NEW_DOORS):
        assert bpy.data.objects.get(NEW_CURTAIN)
        return {'alreadyApplied':True,'changedObjects':[],'addedObjects':[]}
    assert not bpy.data.objects.get(NEW_CURTAIN)
    from mathutils.bvhtree import BVHTree
    site=bpy.data.objects[DOORS]
    origin=Vector((36.96627426147461,-62.79413604736328,0))
    angle=math.radians(58);u=Vector((math.cos(angle),math.sin(angle),0));n=Vector((-u.y,u.x,0))
    def local(p):return Vector(((p-origin).dot(u),(p-origin).dot(n),p.z))
    def world(p):return origin+u*p[0]+n*p[1]+Vector((0,0,p[2]))
    bm=bmesh.new();bm.from_mesh(site.data);seen=set();bounds=[]
    for vertex in bm.verts:
        if vertex in seen:continue
        stack=[vertex];seen.add(vertex);points=[]
        while stack:
            v=stack.pop();points.append(local(site.matrix_world@v.co))
            for e in v.link_edges:
                other=e.other_vert(v)
                if other not in seen:seen.add(other);stack.append(other)
        bounds.append([[min(p[i] for p in points),max(p[i] for p in points)] for i in range(3)])
    bm.free();assert len(bounds)==8
    source=bpy.data.objects[CURTAIN];assert not source.hide_render and not site.hide_render
    data=source.data;layers=list(data.uv_layers)
    vertices,faces,face_uvs,material_indices=[],[],[],[];changed_faces=[];retained_faces=[]
    def append(poly,material,original=None):
        start=len(vertices)
        vertices.extend(data.vertices[i].co.copy() for i in original.vertices) if original is not None else vertices.extend(source.matrix_world.inverted()@world(p[0]) for p in poly)
        faces.append(tuple(start+i for i in range(len(poly))))
        face_uvs.append([p[1] for p in poly]);material_indices.append(material)
    def clip(poly,axis,value,sign):
        out=[]
        for a,b in zip(poly,poly[1:]+poly[:1]):
            da=sign*(a[0][axis]-value);db=sign*(b[0][axis]-value)
            if da>=-1e-8:out.append(a)
            if (da>1e-8 and db<-1e-8) or (da<-1e-8 and db>1e-8):
                t=da/(da-db);out.append((a[0].lerp(b[0],t),[x.lerp(y,t) for x,y in zip(a[1],b[1])]))
        return out
    for polygon in data.polygons:
        initial=[(local(source.matrix_world@data.vertices[data.loops[li].vertex_index].co),[Vector(layer.data[li].uv) for layer in layers]) for li in polygon.loop_indices]
        pieces=[initial];altered=False
        for b in bounds:
            x0,x1=b[0];z0,z1=b[2];door_y=sum(b[1])/2
            pane_y=2 if door_y>0 else (-14 if door_y<-10 else -2)
            next_pieces=[]
            for poly in pieces:
                if not all(abs(p[0].y-pane_y)<.06 for p in poly) or max(p[0].x for p in poly)<=x0 or min(p[0].x for p in poly)>=x1 or max(p[0].z for p in poly)<=z0 or min(p[0].z for p in poly)>=z1:
                    next_pieces.append(poly);continue
                remainder=poly
                for axis,value,sign in [(0,x0,1),(0,x1,-1),(2,z0,1),(2,z1,-1)]:
                    outside=clip(remainder,axis,value,-sign)
                    if len(outside)>=3:next_pieces.append(outside)
                    remainder=clip(remainder,axis,value,sign)
                    if len(remainder)<3:break
                if len(remainder)>=3:altered=True
            pieces=next_pieces
        if altered:
            for poly in pieces:append(poly,polygon.material_index)
        else:append(initial,polygon.material_index,polygon)
        (changed_faces if altered else retained_faces).append(polygon.index)
    assert changed_faces
    mesh=bpy.data.meshes.new(NEW_CURTAIN);mesh.from_pydata(vertices,[],faces);mesh.update()
    for m in data.materials:mesh.materials.append(m)
    for layer_index,old_layer in enumerate(layers):
        layer=mesh.uv_layers.new(name=old_layer.name)
        for poly,values in zip(mesh.polygons,face_uvs):
            for li,value in zip(poly.loop_indices,values):layer.data[li].uv=value[layer_index]
    for poly,mi in zip(mesh.polygons,material_indices):poly.material_index=mi
    curtain=source.copy();curtain.data=mesh;curtain.name=NEW_CURTAIN
    bpy.data.collections['CBG_EXTERIOR'].objects.link(curtain)
    dv,df=[],[]
    for b in bounds:
        a,c=b[0];h,j=b[2];y=sum(b[1])/2;start=len(dv)
        dv.extend(world(p)for p in [(a,y,h),(c,y,h),(c,y,j),(a,y,j)])
        df.append(tuple(start+i for i in ([0,1,2,3] if y<0 else [3,2,1,0])))
    door_mesh=bpy.data.meshes.new(NEW_DOORS);door_mesh.from_pydata(dv,[],df);door_mesh.update()
    for m in site.data.materials:door_mesh.materials.append(m)
    door=bpy.data.objects.new(NEW_DOORS,door_mesh);bpy.data.collections['CBG_EXTERIOR'].objects.link(door)
    door['scope']='Single physical pane per existing entry leaf; optical finish inherited, not measured'
    for obj in [source,site]:obj.hide_render=True;obj.hide_set(True)
    return {'addedObjects':[NEW_CURTAIN,NEW_DOORS],'archivedObjects':[CURTAIN,DOORS],'changedObjects':[],
            'doorBoundsLocal':bounds,'changedSourceFaces':changed_faces,'retainedSourceFaces':retained_faces,
            'source':'data/collections/campus_photos_round2/images/CBG/CBG_cbg_joas_02.jpg',
            'references':['CBG_cbg_joas_02.jpg','CBG_cbg_joas_03.jpg','CBG_cbg_joas_06.webp'],
            'date':'Photographic capture date unknown; archive naming is not capture dating',
            'scope':'Eight inherited entrance leaves and directly overlapping curtain panes only',
            'limitations':['Door locations and dimensions inherit existing estimates, not surveyed as-built positions',
                           'No new interior geometry or stronger opacity introduced',
                           'User red-primary/orange-return shade finish is retained; daylight photographs appear pale champagne',
                           'Real glass build-up is approximated by one render surface; optical parameters retained']}
