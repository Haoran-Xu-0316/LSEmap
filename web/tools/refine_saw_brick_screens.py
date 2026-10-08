"""Seat SAW's existing openwork bricks in their surrounding wall planes.

EH Smith's close and contextual photographs show a continuous brick face. The
accepted native facade registrations supply the working planes; dimensions
remain photographic estimates. Move existing bricks only, preserving mesh
counts, per-corner UVs, masonry colours, bevels, glazing and interiors. Add
recessed mortar only at actual neighbouring brick contacts.
"""
from pathlib import Path
import hashlib,json
import bpy,bmesh
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
PREFIX='SAW_NEXT_SCREEN_flush_'
SOURCES=[f'SAW_NEXT_EXTERIOR155_retained_openwork_bricks_{i}' for i in range(8)]+['SAW_NEXT_EXTERIOR155_north_fold_openwork_bricks']
FAMILIES=('north_fold','central_return','south_fold')


def connected_bricks(mesh):
    adjacency=[[] for _ in mesh.vertices]
    for edge in mesh.edges:
        a,b=edge.vertices;adjacency[a].append(b);adjacency[b].append(a)
    unseen=set(range(len(mesh.vertices)))
    while unseen:
        first=unseen.pop();stack=[first];indices=[first]
        while stack:
            for index in adjacency[stack.pop()]:
                if index in unseen:
                    unseen.remove(index);stack.append(index);indices.append(index)
        assert len(indices)==8, 'Expected retained closed cuboid bricks'
        yield indices


def facade_frames():
    records=json.loads((ROOT/'result/blender/stage82/saw-curtain-audit.json').read_text())['facades']
    return {r['family']:(Vector(r['p']),Vector(r['n'])) for r in records if r['family'] in FAMILIES}



def add_mortar_beds(frames, bricks):
    """Recessed pad sidewalls; touching brick faces cap the concealed top and bottom."""
    vertices=[];faces=[];pads=[]
    cube_faces=((0,2,6,4),(1,5,7,3),(0,4,5,1),(2,3,7,6),(0,1,3,2),(4,6,7,5))
    for family, rows in bricks.items():
        origin,normal=frames[family];tangent=Vector((-normal.y,normal.x,0))
        by_top={}
        for brick in rows:by_top.setdefault(round(brick[3]*10000),[]).append(brick)
        for upper in rows:
            for lower in by_top.get(round((upper[2]-.013)*10000),[]):
                left=max(lower[0],upper[0])+.002
                right=min(lower[1],upper[1])-.002
                if right-left<.015:continue
                bottom,top=lower[3],upper[2]
                assert .0129<top-bottom<.0131
                depth_min,depth_max=-.211,-.004
                offset=len(vertices)
                vertices.extend(origin+tangent*x+normal*d+Vector((0,0,z)) for x,d,z in (
                    (left,depth_min,bottom),(left,depth_min,top),(left,depth_max,bottom),(left,depth_max,top),
                    (right,depth_min,bottom),(right,depth_min,top),(right,depth_max,bottom),(right,depth_max,top)))
                faces.extend(tuple(offset+i for i in face)for face in cube_faces)
                pads.append({'family':family,'lowerBrick':lower[4],'upperBrick':upper[4],
                             'bounds':[left,right,bottom,top,depth_min,depth_max]})
    assert pads
    wall=bpy.data.objects['SAW_NEXT_EXTERIOR155_north_fold_pierced_wall']
    source=wall.data.materials[0]
    brick_node=next(node for node in source.node_tree.nodes if node.type=='TEX_BRICK')
    color=tuple(brick_node.inputs['Mortar'].default_value)
    material=bpy.data.materials.new('SAW_SCREEN_bedding_mortar');material.use_nodes=True
    material.diffuse_color=color
    shader=material.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value=color;shader.inputs['Roughness'].default_value=.94
    material['sourceMortarMaterial']=source.name
    material['scope']='Recessed mortar at photographed openwork brick contacts; section estimated'
    mesh=bpy.data.meshes.new('SAW_NEXT_SCREEN_mortar_beds');mesh.from_pydata(vertices,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.normal_update()
    # The touching opaque bricks already cap these planes. Avoid duplicate
    # internal surfaces and their cost in both overview and detailed exports.
    caps=[face for face in bm.faces if abs(face.normal.z)>.9999]
    assert len(caps)==len(pads)*2
    bmesh.ops.delete(bm,geom=caps,context='FACES_ONLY')
    bm.to_mesh(mesh);bm.free()
    mesh.materials.append(material)
    obj=bpy.data.objects.new('SAW_NEXT_SCREEN_mortar_beds',mesh);bpy.data.collections['SAW_EXTERIOR'].objects.link(obj)
    obj['scope']='One recessed pad per overlapping pair of adjacent courses; no blanket infill across apertures'
    return obj, pads


def apply_saw_brick_screens():
    targets=[PREFIX+str(i) for i in range(len(SOURCES))]
    if any(name in bpy.data.objects for name in targets):
        assert all(name in bpy.data.objects and not bpy.data.objects[name].hide_render for name in targets)
        assert all(bpy.data.objects[name].hide_render for name in SOURCES)
        assert 'SAW_NEXT_SCREEN_mortar_beds' in bpy.data.objects
        return {'alreadyApplied':True,'addedObjects':[],'archivedObjects':[],'changedObjects':[]}
    frames=facade_frames();records=[];counts={f:0 for f in FAMILIES};bricks={f:[] for f in FAMILIES}
    for source_name,target_name in zip(SOURCES,targets):
        source=bpy.data.objects[source_name]
        assert not source.hide_render
        clone=source.copy();clone.data=source.data.copy();clone.name=target_name
        for collection in source.users_collection:collection.objects.link(clone)
        matrix=source.matrix_world.copy();inverse=matrix.inverted().to_3x3()
        count=0;offsets=[]
        for indices in connected_bricks(source.data):
            points=[matrix@source.data.vertices[i].co for i in indices]
            centre=sum(points,Vector())/8
            family=min(frames,key=lambda f:abs((centre-frames[f][0]).dot(frames[f][1])+.018))
            origin,normal=frames[family]
            depths=[(p-origin).dot(normal) for p in points]
            assert abs(sum(depths)/8+.018)<.00004, (source_name,family,depths)
            front=max(depths)
            assert .08945<front<.08955, (source_name,family,front)
            offset=inverse@(-normal*front)
            for index in indices:clone.data.vertices[index].co+=offset
            tangent=Vector((-normal.y,normal.x,0))
            xs=[(point-origin).dot(tangent) for point in points]
            zs=[point.z-origin.z for point in points]
            bricks[family].append((min(xs),max(xs),min(zs),max(zs),source_name+':'+str(count)))
            counts[family]+=1;count+=1;offsets.append(front)
        clone.data.update();clone['sourceObject']=source_name
        clone['scope']='Align existing openwork brick fronts with registered wall faces; dimensions and colours retained'
        source.hide_render=True;source.hide_set(True)
        records.append({'source':source_name,'target':target_name,'bricks':count,'oldProjectionRange':[min(offsets),max(offsets)],'newProjection':0.0})
    mortar,pads=add_mortar_beds(frames,bricks)
    targets.append(mortar.name)
    bpy.context.view_layer.update()
    photos=['materials_saw_ehsmith_image_01.jpg','materials_saw_ehsmith_image_03.jpg','exteriors_saw_archdaily_000.jpg']
    refs=[]
    for name in photos:
        path=ROOT/'data/建筑图片/SAW_Saw Swee Hock Student Centre/01_建筑实拍'/name
        refs.append({'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'captureDate':'unknown'})
    return {'alreadyApplied':False,'addedObjects':targets,'archivedObjects':SOURCES,'changedObjects':[],
            'records':records,'brickCounts':counts,'addedTriangles':len(pads)*8,'mortarPads':pads,'references':refs,
            'limitations':['Existing registered wall planes and dimensions are estimates, not surveyed positions.',
                           'Mortar sections are estimates; finer brick texture and complete current interior remain unresolved.',
                           'Only the three photographed folded faces are treated; unseen rear geometry retained.']}
