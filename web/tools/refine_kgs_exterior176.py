"""KGS Portugal Street attic: five main axes and through-storey canted bays.

The official Estates photograph and Historic England listing support topology.
Published image capture date is unknown; inherited positions and widths are
photo estimates, not a 2026 measured survey. St Clement's elevation is unchanged.
Call apply_kgs_exterior176() on the loaded campus; no file IO is performed.
"""
import bpy
import bmesh
from mathutils import Vector

ORIGIN = Vector((-16.877382278442383, .6110793948173523, 0))
U = Vector((-.6417604684829712, -.7669051885604858, 0))
N = Vector((.7669051885604858, -.6417604684829712, 0))
COLLECTION = 'KGS176_PORTUGAL_ATTIC'
SOURCES = [
    'KGS_NEXT_window_piers_darkbrick', 'KGS_NEXT_window_spandrel_darkbrick',
    'KGS_NEXT_window_head_darkbrick', 'KGS_D5_window_glass_glass',
    'KGS_D5_sash_outer_frame_frame', 'KGS_D5_sash_meeting_rail_frame',
    'KGS_D5_sash_glazing_bar_frame', 'KGS_D5_projecting_sill_trim',
    'KGS_D5_window_lintel_stone', 'KGS_D5_V16_glazing_seal',
    'KGS_D5_V16_reveal_bead', 'KGS_D5_V16_timber_weatherboard',
    'KGS_D5_V16_sill_end_joint', 'KGS_D5_V17_sash_box_lining',
    'KGS_D5_V17_parting_groove', 'KGS_D5_V17_inner_sash_stop',
    'KGS_D5_V17_head_lining', 'KGS_D5_V17_sill_apron',
    'KGS_D5_V17_sill_undercut',
]
SOURCE_URLS = [
    'https://historicengland.org.uk/listing/the-list/list-entry/1235528',
    'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Images/LSE-Estate/Kings-Chambers-300x376.jpg',
]

def local(p):
    return Vector(((p-ORIGIN).dot(U), (p-ORIGIN).dot(N), p.z))

def world(p):
    return ORIGIN + U*p[0] + N*p[1] + Vector((0,0,p[2]))

class Batch:
    def __init__(self):
        self.vertices, self.faces = [], []
    def box(self, origin, axis, normal, width, depth, height):
        start = len(self.vertices)
        self.vertices.extend(origin + axis*x + normal*y + Vector((0,0,z))
                             for x,y,z in [(0,0,0),(width,0,0),(width,depth,0),(0,depth,0),
                                           (0,0,height),(width,0,height),(width,depth,height),(0,depth,height)])
        self.faces.extend(tuple(start+i for i in face) for face in
                          [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
    def plane(self, origin, axis, width, height, normal):
        start = len(self.vertices)
        self.vertices.extend([origin, origin+axis*width, origin+axis*width+Vector((0,0,height)), origin+Vector((0,0,height))])
        self.faces.append((start,start+1,start+2,start+3) if axis.cross(Vector((0,0,1))).dot(normal)>0 else (start+3,start+2,start+1,start))
    def object(self, name, material, collection, sheet=False):
        mesh = bpy.data.meshes.new(name+'_mesh')
        mesh.from_pydata(self.vertices, [], self.faces)
        mesh.materials.append(material)
        mesh.update()
        if not sheet:
            bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
        uv=mesh.uv_layers.new(name='MetricUV')
        for polygon in mesh.polygons:
            pts=[mesh.vertices[mesh.loops[i].vertex_index].co for i in polygon.loop_indices]
            axis=(pts[1]-pts[0]).normalized(); second=polygon.normal.cross(axis)
            for li,p in zip(polygon.loop_indices,pts):
                uv.data[li].uv=((p-pts[0]).dot(axis),(p-pts[0]).dot(second))
        obj=bpy.data.objects.new(name,mesh);collection.objects.link(obj)
        obj['reviewScope']='Portugal Street attic only; inherited estimated registration'
        return obj

def trim_source(source, collection, wall=False):
    """Clone batch, remove only connected parts belonging to flat front attic."""
    clone=source.copy();clone.data=source.data.copy();clone.name='KGS176_RETAIN_'+source.name
    collection.objects.link(clone)
    remove=[]
    bm=bmesh.new();bm.from_mesh(clone.data);visited=set()
    for vertex in bm.verts:
        if vertex in visited:continue
        part=[];stack=[vertex];visited.add(vertex)
        while stack:
            current=stack.pop();part.append(current)
            for edge in current.link_edges:
                other=edge.other_vert(current)
                if other not in visited:visited.add(other);stack.append(other)
        points=[local(source.matrix_world@v.co) for v in part]
        bounds=[(min(p[i] for p in points),max(p[i] for p in points)) for i in range(3)]
        low=12.899 if wall else 13.15
        if bounds[0][0]>=-6.3 and bounds[0][1]<=6.3 and bounds[1][0]>=-.4 and bounds[1][1]<=.5 and bounds[2][0]>=low:
            remove.extend(part)
    assert remove, 'Expected flat attic components in '+source.name
    bmesh.ops.delete(bm, geom=remove, context='VERTS')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(clone.data);bm.free();clone.data.update()
    clone['removedAtticVertices']=len(remove)
    return clone

def apply_kgs_exterior176():
    if bpy.data.collections.get(COLLECTION):
        return dict(alreadyApplied=True, addedObjects=[], archivedObjects=[], changedObjects=[])
    exterior=bpy.data.collections['KGS_EXTERIOR']
    collection=bpy.data.collections.new(COLLECTION);exterior.children.link(collection)
    archive=bpy.data.collections.new('KGS176_ARCHIVE');bpy.context.scene.collection.children.link(archive)
    original_glass=bpy.data.objects['KGS_D5_window_glass_glass']
    # Reuse lower-tier facet geometry to align the two end bays through the attic.
    facets=[]
    for start in [24,32,40,72,80,88]:
        indices=set(range(start,start+8))
        faces=[p for p in original_glass.data.polygons if set(p.vertices)<=indices and abs(p.normal.z)<.5]
        largest=sorted(faces,key=lambda p:p.area,reverse=True)[:2]
        front=max(largest,key=lambda p:local(original_glass.matrix_world@p.center).y)
        points=[original_glass.matrix_world@original_glass.data.vertices[i].co for i in front.vertices]
        bottom=sorted(points,key=lambda p:p.z)[:2];bottom.sort(key=lambda p:local(p).x)
        axis=(bottom[1]-bottom[0]).normalized(); normal=Vector((axis.y,-axis.x,0))
        if normal.dot(N)<0:axis=-axis;bottom.reverse();normal=-normal
        facets.append((bottom[0],axis,normal,(bottom[1]-bottom[0]).length))
    added=[];archived=[]
    for name in SOURCES:
        source=bpy.data.objects[name]
        clone=trim_source(source,collection,wall=name.startswith('KGS_NEXT_window_'))
        added.append(clone.name)
        for owner in list(source.users_collection):owner.objects.unlink(source)
        archive.objects.link(source);source.hide_render=True;source.hide_set(True)
        archived.append(source.name)
    green=next(m for m in bpy.data.objects['KGS176_RETAIN_KGS_NEXT_window_piers_darkbrick'].data.materials if m and 'green' in m.name.lower())
    frame=bpy.data.materials['HERITAGE09_frame'];stone=bpy.data.materials['HERITAGE09_trim']
    glass=original_glass.data.materials[0]
    walls=Batch();frames=Batch();panes=Batch();sills=Batch()
    z0,z1,z2,z3=12.90,13.43,14.72,15.17
    # Flat central portion: three original main axes, with real openings.
    edges=[-3.45,-2.623756,-1.663756,-.48,.48,1.663756,2.623756,3.45]
    for a,b in zip(edges[::2],edges[1::2]):walls.box(world((a,-.23,z1)),U,N,b-a,.36,z2-z1)
    for za,zb in [(z0,z1),(z2,z3)]:walls.box(world((-3.45,-.23,za)),U,N,6.9,.36,zb-za)
    for a,b in [(-6.165634,-5.78),(5.78,6.165634)]:walls.box(world((a,-.23,z0)),U,N,b-a,.36,z3-z0)
    windows=[(world((x-.41,-.04,z1)),U,N,.82) for x in [-2.143756,0,2.143756]]
    # Faceted end bays: stone/green reveals follow existing lower bay plan.
    for base,axis,normal,width in facets:
        base=Vector((base.x,base.y,z1))
        windows.append((base,axis,normal,width))
        for za,zb in [(z0,z1),(z2,z3)]:
            walls.box(Vector((base.x,base.y,za))-axis*.09-normal*.04,axis,normal,width+.18,.18,zb-za)
        for x in [-.09,width]:walls.box(base+axis*x-normal*.04,axis,normal,.09,.18,z2-z1)
    for base,axis,normal,width in windows:
        height=z2-z1
        panes.plane(base,axis,width,height,normal)
        for x in [-.06,width]:frames.box(base+axis*x+normal*.012,axis,normal,.06,.075,height)
        for z in [0,height-.06,height*.52]:frames.box(base+Vector((0,0,z))+normal*.012,axis,normal,width,.075,.06)
        sills.box(base-axis*.08-normal*.025-Vector((0,0,.12)),axis,normal,width+.16,.20,.12)
    for batch,name,material,sheet in [(walls,'KGS176_attic_green_openings',green,False),(frames,'KGS176_attic_sash_frames',frame,False),
                                     (panes,'KGS176_attic_single_glass',glass,True),(sills,'KGS176_attic_stone_sills',stone,False)]:
        added.append(batch.object(name,material,collection,sheet).name)
    collection['windowAxes']=5;collection['paneFacets']=9
    collection['sourceURL']='; '.join(SOURCE_URLS)
    collection['sourceDateLimitation']='Estates photo capture unknown; listing historical; dimensions estimated'
    return dict(alreadyApplied=False, addedObjects=added, archivedObjects=archived, changedObjects=[])
