"""Join SAL's registered stone coping without overlapping internal end caps.

The seven photographed gables have continuous stone bands. Preserve the native
centreline anchors and nominal140mm radius; dimensions remain modelling estimates.
Each chain becomes one closed swept hexagonal solid with mitred joints.
Seven intersecting gable panes are recessed behind the stone band; window
silhouettes and glass finishes retained. The missing central masonry aperture
is opened behind its existing three-light frame; other facades remain untouched.
"""
import math
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
SOURCE='SAL_Gable_stone_ogee_coping'
TARGET='SAL184_'+SOURCE
RADIUS=.14
TOLERANCE=.00005


def registered_chains(source):
    mesh=bmesh.new();mesh.from_mesh(source.data);seen=set();segments=[]
    for seed in mesh.verts:
        if seed in seen:continue
        stack=[seed];seen.add(seed);group=[]
        while stack:
            vertex=stack.pop();group.append(vertex)
            for edge in vertex.link_edges:
                neighbour=edge.other_vert(vertex)
                if neighbour not in seen:seen.add(neighbour);stack.append(neighbour)
        vertices=sorted(group,key=lambda v:v.index)
        assert len(vertices)==12,'Expected an original six-sided beam'
        segments.append([sum((source.matrix_world@v.co for v in vertices[i:i+6]),Vector())/6 for i in (0,6)])
    mesh.free()
    # Cluster only the duplicated ends of adjacent existing beams.
    centres=[];samples=[];edges=[]
    for segment in segments:
        indices=[]
        for point in segment:
            index=next((i for i,centre in enumerate(centres)if(point-centre).length<TOLERANCE),None)
            if index is None:index=len(centres);centres.append(point.copy());samples.append([])
            samples[index].append(point);indices.append(index)
        edges.append(tuple(indices))
    centres=[sum(group,Vector())/len(group)for group in samples]
    adjacency={i:[]for i in range(len(centres))}
    for a,b in edges:adjacency[a].append(b);adjacency[b].append(a)
    assert all(len(neighbours)in(1,2)for neighbours in adjacency.values())
    pending=set(adjacency);chains=[]
    while pending:
        start=next(i for i in sorted(pending)if len(adjacency[i])==1)
        chain=[];previous=None;current=start
        while current is not None:
            pending.remove(current);chain.append(centres[current])
            following=next((i for i in adjacency[current]if i!=previous),None)
            previous,current=current,following
        chains.append(chain)
    assert len(segments)==154 and len(chains)==7
    return chains,segments


def swept_chain(points,depth_axis):
    directions=[(b-a).normalized()for a,b in zip(points,points[1:])]
    vertices=[]
    for i,point in enumerate(points):
        before=directions[max(0,i-1)];after=directions[min(i,len(directions)-1)]
        r0=before.cross(depth_axis).normalized();r1=after.cross(depth_axis).normalized()
        side=(r0+r1).normalized();factor=side.dot(r0)
        assert factor>.5,'Registered corner exceeds the supported miter angle'
        for k in range(6):
            angle=k*math.tau/6
            vertices.append(point+RADIUS*(depth_axis*math.cos(angle)+side*math.sin(angle)/factor))
    faces=[tuple(reversed(range(6))),tuple(range(len(vertices)-6,len(vertices)))]
    for ring in range(len(points)-1):
        for k in range(6):
            a=ring*6+k;b=ring*6+(k+1)%6
            faces.append((a,b,b+6,a+6))
    return vertices,faces


GLASS_SOURCE='GLASS181_SAL_NEXT_GLAZING149_retained_frontage_glass'
GLASS_TARGET='SAL184_'+GLASS_SOURCE
GLASS_CLEARANCE=.02


def mesh_tree(obj):
    return BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],
                               [tuple(face.vertices)for face in obj.data.polygons])


def recess_gable_panes(coping,chains,depth_axis):
    """Move only the seven closed panes intersecting the inherited coping.

    Maintain aperture silhouette and finite glass thickness. Set their front
    behind the stone's back face with a20mm modelling clearance. This is a
    construction relation supported by the photograph, not a measured rebate.
    """
    source=bpy.data.objects[GLASS_SOURCE]
    touched={i for _,face in mesh_tree(coping).overlap(mesh_tree(source))
             for i in source.data.polygons[face].vertices}
    bm=bmesh.new();bm.from_mesh(source.data);bm.verts.ensure_lookup_table()
    pending=set(bm.verts);groups=[]
    while pending:
        seed=pending.pop();stack=[seed];group={seed}
        while stack:
            vertex=stack.pop()
            for edge in vertex.link_edges:
                neighbour=edge.other_vert(vertex)
                if neighbour in pending:pending.remove(neighbour);group.add(neighbour);stack.append(neighbour)
        indices=sorted(v.index for v in group)
        if touched.intersection(indices):groups.append(indices)
    bm.free();assert len(groups)==7 and all(len(group)==8 for group in groups)
    target=source.copy();target.data=source.data.copy();target.name=GLASS_TARGET;target.data.name=GLASS_TARGET
    for collection in source.users_collection:collection.objects.link(target)
    target.hide_render=False;target.hide_set(False);inverse=target.matrix_world.inverted();records=[]
    for indices in groups:
        points=[source.matrix_world@source.data.vertices[i].co for i in indices]
        centre=sum(points,Vector())/len(points)
        chain=min(chains,key=lambda points:((sum(points,Vector())/len(points))-centre).length)
        rear=min(point.dot(depth_axis)for point in chain)-RADIUS
        old_front=max(point.dot(depth_axis)for point in points)
        shift=rear-GLASS_CLEARANCE-old_front;assert shift<0 and abs(shift)<.5
        for index,point in zip(indices,points):target.data.vertices[index].co=inverse@(point+depth_axis*shift)
        records.append({'vertices':indices,'depthShift':shift,'oldFront':old_front,'newFront':rear-GLASS_CLEARANCE,'copingRear':rear})
    target.data.update();source.hide_render=True;source.hide_set(True)
    return target,records



WALL_SOURCE='SAL183_SAL_NEXT_GLAZING149_opened_six_gable_masonry'
WALL_TARGET='SAL184_'+WALL_SOURCE


def open_central_gable(glass,pane_records,normal):
    """Open the missing central aperture behind its existing three-light frame."""
    axis=Vector((-normal.y,normal.x,0))
    groups=[[glass.matrix_world@glass.data.vertices[i].co for i in record['vertices']]for record in pane_records]
    points=max(groups,key=lambda ps:max(p.dot(axis)for p in ps)-min(p.dot(axis)for p in ps))
    centre=sum(points,Vector())/len(points)
    width=max(p.dot(axis)for p in points)-min(p.dot(axis)for p in points)+.004
    bottom=min(p.z for p in points)-.002;top=max(p.z for p in points)+.002
    source=bpy.data.objects[WALL_SOURCE];target=source.copy();target.data=source.data.copy();target.name=WALL_TARGET;target.data.name=WALL_TARGET
    for collection in source.users_collection:collection.objects.link(target)
    target.hide_render=False;target.hide_set(False)
    vertices=[centre+axis*(x*width/2)+normal*d+Vector((0,0,z-centre.z))for x in [-1,1]for d in [-.75,.75]for z in [bottom,top]]
    mesh=bpy.data.meshes.new('SAL184_central_window_tool')
    mesh.from_pydata(vertices,[],[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    tool=bpy.data.objects.new(mesh.name,mesh);source.users_collection[0].objects.link(tool)
    bpy.context.view_layer.objects.active=target
    modifier=target.modifiers.new('Central gable window aperture','BOOLEAN');modifier.operation='DIFFERENCE';modifier.solver='EXACT';modifier.object=tool
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(tool,do_unlink=True);bpy.data.meshes.remove(mesh)
    source.hide_render=True;source.hide_set(True)
    return target,{'width':width,'bottom':bottom,'top':top,'centre':list(centre),'depth':1.5,'basis':'Existing central three-light window silhouette, not new surveyed dimensions'}


def apply_sal_coping184():
    if bpy.data.objects.get(TARGET):
        return {'alreadyApplied':True,'addedObjects':[],'archivedObjects':[],'changedObjects':[]}
    source=bpy.data.objects[SOURCE];assert not source.hide_render
    chains,segments=registered_chains(source)
    angle=math.radians(24.35);depth_axis=Vector((-math.sin(angle),math.cos(angle),0))
    vertices=[];faces=[]
    for chain in chains:
        points,polygons=swept_chain(chain,depth_axis);offset=len(vertices)
        vertices.extend(points);faces.extend(tuple(i+offset for i in face)for face in polygons)
    mesh=bpy.data.meshes.new(TARGET);inverse=source.matrix_world.inverted()
    mesh.from_pydata([inverse@point for point in vertices],[],faces);mesh.update()
    for material in source.data.materials:mesh.materials.append(material)
    uv=mesh.uv_layers.new(name='Metric_facade_UV')
    for face in mesh.polygons:
        points=[vertices[i]for i in face.vertices];origin=points[0];u=(points[1]-origin).normalized()
        normal=(points[1]-origin).cross(points[-1]-origin).normalized();v=normal.cross(u)
        for loop,point in zip(face.loop_indices,points):uv.data[loop].uv=((point-origin).dot(u),(point-origin).dot(v))
    target=source.copy();target.name=TARGET;target.data=mesh
    for collection in source.users_collection:collection.objects.link(target)
    target.hide_render=False;target.hide_set(False)
    glass,pane_records=recess_gable_panes(source,chains,depth_axis)
    wall,aperture=open_central_gable(glass,pane_records,depth_axis)
    source.hide_render=True;source.hide_set(True)
    target['constructionBasis']='Seven continuous mitred stone bands on retained approximate photo-led anchors'
    return {'alreadyApplied':False,'code':'SAL','version':184,'addedObjects':[target.name,glass.name,wall.name],
      'archivedObjects':[source.name,GLASS_SOURCE,WALL_SOURCE],'changedObjects':[],
      'originalBeams':154,'continuousClosedChains':7,'chainVertexCounts':[len(chain)for chain in chains],
      'centrelineAnchors':[[list(point)for point in chain]for chain in chains],
      'centralAperture':aperture,'recessedGablePanes':pane_records,'glassClearance':GLASS_CLEARANCE,
      'radius':RADIUS,'endpointClusteringTolerance':TOLERANCE,
      'originalFaces':len(source.data.polygons),'newFaces':len(mesh.polygons),
      'sources':['https://www.jesticowhiles.com/project/lincolns-inn-fields-london-school-of-economics/'],
      'scope':'Continuous stone coping and seven recessed gable panes; missing central masonry aperture opened, with window silhouette, finishes and coping anchors retained. Section and rebate are modelling estimates, not a current measured facade survey.'}
