"""Add the photographed left Houghton Street wall lantern to the loaded campus.

No file opening or saving. The engineer's completed-project photograph supports
one visible lantern. Placement, dimensions, hidden supports and optical finishes
are estimates; no symmetric second lamp or lighting emission is inferred.
"""
from pathlib import Path
import json,math
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2]
NAMES=['OLD_LANTERN163_blue_frame','OLD_LANTERN163_opal_shade']


def apply_old_wall_lantern():
    if all(bpy.data.objects.get(name) for name in NAMES):
        return {'changedObjects':[],'addedObjects':[],'alreadyApplied':True}
    assert not any(bpy.data.objects.get(name) for name in NAMES)
    frame=json.loads((ROOT/'result/blender/old_houghton_next/audit.json').read_text())['registration']
    origin,right,outward=[Vector(frame[k])for k in ('origin','right','outward')]
    def point(x,d,z):return origin+right*x+outward*d+Vector((0,0,z))
    from facade_geometry import Geometry,materials
    blue=bpy.data.materials['OLD_Blue_painted_steel'].copy();blue.name='OLD_LANTERN163_blue_painted_metal'
    shader=blue.node_tree.nodes.get('Principled BSDF');shader.inputs['Metallic'].default_value=0;shader.inputs['Roughness'].default_value=.55
    opal=bpy.data.materials.new('OLD_LANTERN163_opal');opal.use_nodes=True;opal.diffuse_color=(.58,.62,.62,1)
    shader=opal.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=opal.diffuse_color
    shader.inputs['Roughness'].default_value=.38;shader.inputs['Transmission Weight'].default_value=.45
    opal['webOpacity']=.68
    materials['lantern_blue']=blue;materials['lantern_opal']=opal
    groups={}
    for name,key in zip(NAMES,['lantern_blue','lantern_opal']):
        g=Geometry('OLD','wall_lantern',key);g.name=name;g.collection=bpy.data.collections['OLD_EXTERIOR'];groups[key]=g
    door=bpy.data.objects['OLD_NEXT_EXTERIOR154_door_glass']
    door_x=[(door.matrix_world@v.co-origin).dot(right)for v in door.data.vertices]
    entrance_center=(min(door_x)+max(door_x))/2
    registered_x=entrance_center-6.7
    vertices,faces,owners=[],[],[]
    for obj in bpy.data.collections['OLD_EXTERIOR'].all_objects:
        if obj.type!='MESH' or obj.hide_render:continue
        start=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        faces.extend(tuple(start+i for i in p.vertices)for p in obj.data.polygons)
        owners.extend([obj.name]*len(obj.data.polygons))
    tree=BVHTree.FromPolygons(vertices,faces)
    hit,wall_normal,face,_=tree.ray_cast(point(registered_x,5,4.03),-outward,12)
    assert hit is not None and 'ashlar' in owners[face]
    if wall_normal.dot(outward)<0:wall_normal=-wall_normal
    outward=Vector((wall_normal.x,wall_normal.y,0)).normalized()
    right=Vector((-outward.y,outward.x,0))
    origin=Vector((hit.x,hit.y,0))
    x=0;depth=.52
    angle=math.atan2(right.y,right.x)
    groups['lantern_blue'].box(point(x,.04,4.03),(.18,.08,.42),angle)
    def tube(a,b,radius=.022,sides=8):
        a,b=Vector(a),Vector(b);axis=(b-a).normalized();u=axis.cross(Vector((0,0,1)))
        if u.length<.001:u=axis.cross(Vector((0,1,0)))
        u.normalize();v=axis.cross(u)
        verts=[p+radius*(u*math.cos(i*math.tau/sides)+v*math.sin(i*math.tau/sides))for p in [a,b]for i in range(sides)]
        faces=[tuple(reversed(range(sides))),tuple(range(sides,2*sides))]+[(i,(i+1)%sides,(i+1)%sides+sides,i+sides)for i in range(sides)]
        groups['lantern_blue'].add(verts,faces)
    # Bounded painted support from the registered wall plate to the lower cup.
    tube(point(x,.08,3.94),point(x,.17,3.94),.035)
    tube(point(x,.17,3.94),point(x,.17,4.32),.028)
    tube(point(x,.17,4.32),point(x,depth,4.32),.028)
    tube(point(x,depth,4.32),point(x,depth,4.43),.10,16)
    segments=24
    lower=[point(x+.10*math.cos(i*math.tau/segments),depth+.07*math.sin(i*math.tau/segments),4.43)for i in range(segments)]
    upper=[point(x+.43*math.cos(i*math.tau/segments),depth+.29*math.sin(i*math.tau/segments),5.30)for i in range(segments)]
    groups['lantern_opal'].add(lower+upper,[(i,(i+1)%segments,(i+1)%segments+segments,i+segments)for i in range(segments)])
    for i in range(segments):tube(upper[i],upper[(i+1)%segments],.014)
    for i in [0,8,16]:tube(lower[i],upper[i],.018)
    objects=[g.finish()for g in groups.values()]
    for obj in objects:
        obj['reference']='https://webbyates.com/projects/the-old-building/'
        obj['geometryScope']='Single photograph-visible wall lantern; placement and dimensions estimated.'
        for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
    return {'changedObjects':[],'addedObjects':[o.name for o in objects],
            'reference':'data/建筑图片/OLD_Old Building/01_建筑实拍/campus_photos_round2_OLD_old_webbyates_06.jpg',
            'url':'https://webbyates.com/projects/the-old-building/','projectCompletion':2024,'photographDate':'unknown',
            'lampCount':1,'wallPlateBackDepth':0,'centerX':registered_x,'wallOwner':owners[face],'wallPlaneOrigin':list(origin),'wallPlaneOutward':list(outward),'shadeDepth':depth,'heightRange':[3.82,5.314],
            'vertices':sum(len(o.data.vertices)for o in objects),'faces':sum(len(o.data.polygons)for o in objects),
            'scope':'Left Houghton wall lantern only; photo-visible inverted shade, blue supports and rim. Sizes, hidden supports and optics estimated; no emissive glow or second lamp.'}
