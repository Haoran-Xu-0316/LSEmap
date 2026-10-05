"""Open CON2025 window/partition apertures and use independent clear glazing.

Call on the loaded full campus in Blender. The newsletter photographs support
visible glazing and frame relationships, not adjacent offices or a full floor
plan. Aperture dimensions are inherited model estimates; optical parameters
are presentation estimates. This module never opens or saves a file.
"""
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

PREFIX='CON_NEXT_'
ROOMS=[('con_methodology','rear_glazed_partition_glass'),('con_tea_point','rear_window_glass')]


def _bounds(obj):
    points=[obj.matrix_world@v.co for v in obj.data.vertices]
    return tuple(min(p[i] for p in points) for i in range(3)),tuple(max(p[i] for p in points) for i in range(3))


def _box(vertices,faces,lo,hi):
    offset=len(vertices)
    vertices.extend((x,y,z) for x in [lo[0],hi[0]] for y in [lo[1],hi[1]] for z in [lo[2],hi[2]])
    faces.extend(tuple(offset+i for i in face) for face in [(0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)])


def _replace(obj,vertices,faces,material):
    previous=obj.data
    mesh=bpy.data.meshes.new(obj.name+'_aperture_mesh')
    inverse=obj.matrix_world.inverted()
    mesh.from_pydata([inverse@Vector(v) for v in vertices],[],faces)
    mesh.update();mesh.materials.append(material);obj.data=mesh
    if not previous.users:bpy.data.meshes.remove(previous)


def _glass_material(room):
    name='CON_GLAZING162_'+room+'_clear_glass'
    material=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.diffuse_color=(.68,.73,.72,1);material.use_nodes=True
    shader=material.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value=material.diffuse_color
    shader.inputs['Metallic'].default_value=0
    shader.inputs['Roughness'].default_value=.13
    shader.inputs['Transmission Weight'].default_value=.88
    shader.inputs['IOR'].default_value=1.5
    material['webOpacity']=.18
    material['finishScope']='Clear thin glazing; tint and optics estimated. Web alpha approximation, no refraction render pass.'
    return material


def apply_connaught_room_glazing():
    walls=[bpy.data.objects[PREFIX+room+'_rear_wall_white'] for room,_ in ROOMS]
    if all(w.get('verifiedGlassOpening162') for w in walls):
        return {'changedObjects':[],'addedObjects':[],'alreadyApplied':True}
    bpy.context.view_layer.update()
    proof=[];changed=[]
    for (room,glass_suffix),wall in zip(ROOMS,walls):
        glass=bpy.data.objects[PREFIX+room+'_'+glass_suffix]
        wall_lo,wall_hi=_bounds(wall);glass_lo,glass_hi=_bounds(glass)
        assert wall_lo[0]<glass_lo[0]<glass_hi[0]<wall_hi[0]
        assert wall_lo[2]<glass_lo[2]<glass_hi[2]<wall_hi[2]
        original_wall_material=wall.data.materials[0]
        original_glass_material=glass.data.materials[0]
        vertices,faces=[],[]
        # Four closed masonry pieces define a true rectangular through-opening.
        _box(vertices,faces,wall_lo,(glass_lo[0],wall_hi[1],wall_hi[2]))
        _box(vertices,faces,(glass_hi[0],wall_lo[1],wall_lo[2]),wall_hi)
        _box(vertices,faces,(glass_lo[0],wall_lo[1],wall_lo[2]),(glass_hi[0],wall_hi[1],glass_lo[2]))
        _box(vertices,faces,(glass_lo[0],wall_lo[1],glass_hi[2]),(glass_hi[0],wall_hi[1],wall_hi[2]))
        _replace(wall,vertices,faces,original_wall_material)
        assert _bounds(wall)==(wall_lo,wall_hi)
        # A single thin surface avoids alpha stacking from the old solid box.
        y=(glass_lo[1]+glass_hi[1])/2
        vertices=[(glass_lo[0],y,glass_lo[2]),(glass_hi[0],y,glass_lo[2]),(glass_hi[0],y,glass_hi[2]),(glass_lo[0],y,glass_hi[2])]
        _replace(glass,vertices,[(0,1,2,3)],_glass_material(room))
        # Test rays per room object, avoiding overlapping independent study scenes.
        center=Vector(((glass_lo[0]+glass_hi[0])/2,wall_lo[1]-1,(glass_lo[2]+glass_hi[2])/2))
        bpy.context.view_layer.update()
        wall_hit=BVHTree.FromPolygons([wall.matrix_world@v.co for v in wall.data.vertices],[tuple(p.vertices) for p in wall.data.polygons]).ray_cast(center,Vector((0,1,0)))[0]
        glass_hit=BVHTree.FromPolygons([glass.matrix_world@v.co for v in glass.data.vertices],[tuple(p.vertices) for p in glass.data.polygons]).ray_cast(center,Vector((0,1,0)))[0]
        assert wall_hit is None and glass_hit is not None
        wall['verifiedGlassOpening162']=True
        changed.extend([wall.name,glass.name])
        proof.append({'room':room,'wallBoundsUnchanged':True,'apertureHasNoOpaqueWallHit':True,'glazingRayHit':True,
                      'glassFaces':len(glass.data.polygons),'priorSharedGlassMaterial':original_glass_material.name,
                      'openingBounds':[glass_lo[0],glass_hi[0],glass_lo[2],glass_hi[2]],'webOpacity':.18})
    return {'changedObjects':changed,'addedObjects':[],'rooms':proof,
            'references':['data/collections/tower_photos_round4/images/CON/jan_p2_1.jpg','data/collections/tower_photos_round4/images/CON/jan_p2_3.jpg'],
            'scope':'Real apertures behind clear thin glazing. Existing wall outer bounds, frame positions and furniture retained. Adjacent offices and outdoor surroundings unmodelled; dimensions and optics estimated.'}
