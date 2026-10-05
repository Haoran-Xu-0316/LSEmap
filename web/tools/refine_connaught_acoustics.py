"""Refine photographed CON2025 acoustic-panel articulation.

Call on an already-loaded campus in Blender. No file opening or saving. Joint
paths approximate visible photograph motifs, not a measured or complete survey.
"""
import bpy
from mathutils import Vector

LEARNING='CON_NEXT_con_methodology_panel_joint_blue'
TEA='CON_ACOUSTICS161_tea_panel_joints'
PHOTO_ROOT='data/collections/tower_photos_round4/images/CON/'


def _ribbon(vertices, faces, x, a, b, width):
    """A closed four-sided joint strip on a YZ panel, batched with its peers."""
    a,b=Vector(a),Vector(b)
    tangent=b-a
    assert tangent.length>width
    normal=Vector((-tangent.y,tangent.x)).normalized()*width/2
    base=len(vertices)
    for depth in [-.0006,.0006]:
        for point in [a+normal,b+normal,b-normal,a-normal]:
            vertices.append((x+depth,point.x,point.y))
    faces.extend(tuple(base+i for i in face) for face in [(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])


def _mesh(name, collection, material, x, segments, width):
    vertices,faces=[],[]
    for a,b in segments:_ribbon(vertices,faces,x,a,b,width)
    mesh=bpy.data.meshes.new(name+'_mesh')
    mesh.from_pydata(vertices,[],faces);mesh.update();mesh.materials.append(material)
    obj=bpy.data.objects.get(name)
    if obj:
        previous=obj.data;obj.data=mesh
        if not previous.users:bpy.data.meshes.remove(previous)
    else:
        obj=bpy.data.objects.new(name,mesh);collection.objects.link(obj)
    return obj


def apply_connaught_acoustics():
    if bpy.data.objects.get(TEA):return {'changedObjects':[],'addedObjects':[],'alreadyApplied':True}
    learning=bpy.data.objects[LEARNING]
    wall=bpy.data.objects['CON_NEXT_con_methodology_cyan_acoustic_wall_cyan']
    front=max(v.co.x for v in wall.data.vertices)
    # Triangle/diagonal network, clipped to the inherited panel silhouette.
    left,right=.145,3.755
    segments=[((y,.025),(y,2.775)) for y in [.91,1.67,2.43,3.19]]
    for index,(low,high) in enumerate([(left,.91),(.91,1.67),(1.67,2.43),(2.43,3.19),(3.19,right)]):
        for z in [.24,.91,1.58,2.25]:
            rise=min(.49,2.775-z)
            a,b=((low,z),(high,z+rise)) if index%2 else ((low,z+rise),(high,z))
            segments.append((a,b))
    _mesh(LEARNING,learning.users_collection[0],learning.data.materials[0],front+.001,segments,.004)
    tea_wall=bpy.data.objects['CON_NEXT_con_tea_point_acoustic_panel_yellow']
    front=min(v.co.x for v in tea_wall.data.vertices)
    material=bpy.data.materials.new('CON_ACOUSTICS161_mustard_joint')
    material.diffuse_color=(.52,.32,.018,1);material.use_nodes=True
    shader=material.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=material.diffuse_color;shader.inputs['Roughness'].default_value=.90
    segments=[]
    for z in [1.58,1.75,1.92,2.09,2.26]:
        # Broad repeated chevrons are visible; pitch/depth remain estimates.
        segments.extend([((-.82,z+.10),(0,z)),((0,z),(.82,z+.10))])
    joint=_mesh(TEA,tea_wall.users_collection[0],material,front-.001,segments,.004)
    joint['reference']='2026January newsletter,2025autumn refurbishment'
    return {'changedObjects':[LEARNING],'addedObjects':[TEA],
            'references':[PHOTO_ROOT+'jan_p2_1.jpg',PHOTO_ROOT+'jan_p2_3.jpg'],
            'scope':'Photograph-visible diagonal and chevron motifs; paths, joint widths and pitch estimated. Existing walls, cabinet and furniture unchanged.',
            'learningSegments':len(bpy.data.objects[LEARNING].data.vertices)//8,'teaSegments':len(segments)}
