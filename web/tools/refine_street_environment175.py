"""Photographed Houghton approach-wall vent pair; operate on the loaded scene.
Dimensions and stations are photograph estimates, not surveyed construction.
"""
import math
import bpy
from mathutils import Vector

SOURCE = 'OLD_NEXT_APPROACH_tapered_stone_sidewall'
WALL = 'SITE175_Houghton_approach_wall_vent_openings'
GRILLES = 'SITE175_Houghton_approach_vent_pair'
ORIGIN = Vector((6.868992805480957,-66.35987854003906,0))
U = Vector((.45541495084762573,.8902792930603027,0))
N = Vector((.8902792930603027,-.45541495084762573,0))
Z = Vector((0,0,1))
# Two rectangular grille fields visible in reference09. Exact pitch is unresolved.
VENTS = [(-21.753660202,.285,.48,.22),(-18.553660202,.22,.40,.18)]
FACE = 1.2500009536743164

def world(x,d,z):
    return ORIGIN + U*x + N*d + Z*z

def apply_street_environment175():
    if bpy.data.objects.get(WALL) and bpy.data.objects.get(GRILLES):
        return dict(alreadyApplied=True,addedObjects=[],archivedObjects=[],changedObjects=[])
    source=bpy.data.objects[SOURCE]
    collection=next(iter(source.users_collection))
    wall=source.copy();wall.data=source.data.copy();wall.name=WALL;collection.objects.link(wall)
    wall.hide_render=False;wall.hide_viewport=False;wall.hide_set(False)
    for x,z,w,h in VENTS:
        bpy.ops.mesh.primitive_cube_add(size=1,location=world(x,FACE-.09,z))
        cutter=bpy.context.object;cutter.name='SITE175_PRIVATE_CUTTER'
        cutter.rotation_euler[2]=math.atan2(U.y,U.x);cutter.scale=(w,.4,h)
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        mod=wall.modifiers.new('Photographed vent opening','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
        bpy.context.view_layer.objects.active=wall;bpy.ops.object.modifier_apply(modifier=mod.name)
        mesh=cutter.data;bpy.data.objects.remove(cutter,do_unlink=True);bpy.data.meshes.remove(mesh)
    # Outward normals are computed after the exact cut; original remains untouched.
    import bmesh
    bm=bmesh.new();bm.from_mesh(wall.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(wall.data);bm.free()
    verts=[];faces=[];slots=[]
    def box(x,d,z,w,depth,h,slot):
        base=len(verts)
        verts.extend(world(x+sx*w/2,d+sd*depth/2,z+sz*h/2) for sz in [-1,1] for sd in [-1,1] for sx in [-1,1])
        # U,N,Z forms a left-handed frame; reverse cube face winding.
        fs=[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)]
        faces.extend(tuple(base+i for i in reversed(f)) for f in fs);slots.extend([slot]*6)
    for x,z,w,h in VENTS:
        # Metal perimeter inside the opening; no intersecting stone overlay.
        t=.018;d=FACE-.012
        box(x-w/2+t/2,d,z,t,.024,h,0);box(x+w/2-t/2,d,z,t,.024,h,0)
        box(x,d,z-h/2+t/2,w-2*t,.024,t,0);box(x,d,z+h/2-t/2,w-2*t,.024,t,0)
        # Dark recessed backing models only the photographed vent face, no duct.
        box(x,FACE-.065,z,w-2*t,.012,h-2*t,1)
        for i in range(5):
            zz=z-h/2+t+(h-2*t)*(i+.5)/5
            box(x,FACE-.025,zz,w-2*t,.018,.014,0)
    mesh=bpy.data.meshes.new(GRILLES);mesh.from_pydata(verts,[],faces);mesh.update()
    obj=bpy.data.objects.new(GRILLES,mesh);collection.objects.link(obj)
    for label,colour,rough in [('frame',(.085,.095,.10),.62),('recess',(.018,.024,.028),.9)]:
        material=bpy.data.materials.new('SITE175_vent_'+label);material.use_nodes=True
        material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(*colour,1)
        material.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=rough
        material.diffuse_color=(*colour,1);material['webBaseColor']=list(colour)+[1];material['webMetallic']=0.;material['webRoughness']=rough
        mesh.materials.append(material)
    uv=mesh.uv_layers.new(name='MetricUV')
    for polygon,slot in zip(mesh.polygons,slots):
        polygon.material_index=slot
        for li in polygon.loop_indices:
            p=mesh.vertices[mesh.loops[li].vertex_index].co-ORIGIN
            uv.data[li].uv=(p.dot(U),p.z)
    source.hide_render=True;source.hide_set(True)
    return dict(alreadyApplied=False,addedObjects=[WALL,GRILLES],archivedObjects=[SOURCE],changedObjects=[], scope='Houghton OLD raised approach sidewall: two photographed rectangular grilles', sourcePhotos=['data/collections/public-realm-2026/user-references/reference-09.png'], registration={'origin':list(ORIGIN),'right':list(U),'outward':list(N),'wallFaceDepth':FACE,'ventFields':[{'station':x,'centerHeight':z,'width':w,'height':h} for x,z,w,h in VENTS],'method':'Native approach frame retained; photo-estimated vent sizes and stations, not surveyed','captureDate':'unknown','grillePitch':'Five estimated horizontal courses; exact built pitch unresolved'})
