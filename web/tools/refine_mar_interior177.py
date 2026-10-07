"""Single-surface glazing for MAR's photographed Great Hall and mezzanine.

Original glass boxes and materials stay archived. The replacement uses existing
pane outlines; original meshes had no UV layers. Only duplicate surfaces and a
dark display tint are removed. Replacement UVs are zero because glass is untextured.
Colour and opacity are visual estimates, not measured optical specifications.
"""
import bpy
from mathutils import Vector

SOURCES = ('MAR_D3_ground_glass_panes', 'MAR_D3_mezzanine_guard_glass')
TARGETS = ('MAR177_ground_glass_panes', 'MAR177_mezzanine_guard_glass')
SOURCES_URL = 'https://nickkane.co.uk/portfolio_page/marshall-building-lse-london-grafton-architects/'
RING = ((5.740808,77.669296),(9.378290,68.501632),(23.157800,33.811394),
        (9.246470,28.137186),(.395683,24.454534),(-2.540698,25.778506),
        (-2.804487,25.155460),(-26.219122,34.879487),(-37.700796,40.053061),
        (-38.575448,41.632933),(-39.408445,43.735718),(-40.602404,46.962213),
        (-43.434579,54.716928),(-44.531352,57.631900))


def _outward_at(point):
    area = sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(RING,RING[1:]+RING[:1]))
    closest = None
    for a,b in zip(RING,RING[1:]+RING[:1]):
        a,b=Vector((*a,0)),Vector((*b,0));edge=b-a
        t=max(0,min(1,(Vector((point.x,point.y,0))-a).dot(edge)/edge.length_squared))
        distance=(Vector((point.x,point.y,0))-a-edge*t).length
        normal=Vector((edge.y,-edge.x,0)).normalized()
        if area<0:normal=-normal
        if closest is None or distance<closest[0]:closest=(distance,normal)
    return closest[1]


def _sheet(source,name,collection,ground):
    mesh=source.data;vertices=[];faces=[];uvs=[]
    layer=mesh.uv_layers.active
    assert len(mesh.vertices)%8==0
    for start in range(0,len(mesh.vertices),8):
        candidates=[p for p in mesh.polygons if all(start<=i<start+8 for i in p.vertices)]
        assert len(candidates)==6
        broad=sorted(candidates,key=lambda p:p.area,reverse=True)[:2]
        center=sum((source.matrix_world@mesh.vertices[i].co for i in range(start,start+8)),Vector())/8
        normal=_outward_at(center) if ground else Vector((1,0,0))
        face=max(broad,key=lambda p:(source.matrix_world.to_3x3()@p.normal).dot(normal))
        if ground:assert (source.matrix_world.to_3x3()@face.normal).normalized().dot(normal)>.99
        offset=len(vertices)
        vertices.extend(mesh.vertices[i].co.copy() for i in face.vertices)
        faces.append(tuple(range(offset,offset+len(face.vertices))))
        uvs.extend(tuple(layer.data[i].uv) if layer else (0,0) for i in face.loop_indices)
    data=bpy.data.meshes.new(name+'_mesh');data.from_pydata(vertices,[],faces);data.update()
    layer_new=data.uv_layers.new(name='SurfaceUV')
    for item,uv in zip(layer_new.data,uvs):item.uv=uv
    material=source.data.materials[0].copy();material.name=name+'_dielectric'
    shader=material.node_tree.nodes['Principled BSDF']
    material.diffuse_color=(.72,.80,.84,1)
    shader.inputs['Base Color'].default_value=material.diffuse_color
    shader.inputs['Metallic'].default_value=0
    shader.inputs['Roughness'].default_value=.13
    shader.inputs['Transmission Weight'].default_value=.97
    material['webOpacity']=.30 if ground else .22
    material['opticalValuesEstimated']=True
    material['sourceURL']=SOURCES_URL
    data.materials.append(material)
    obj=bpy.data.objects.new(name,data);collection.objects.link(obj)
    obj.matrix_world=source.matrix_world.copy()
    obj['paneCount']=len(faces);obj['singleSurfaceGlazing']=True
    obj['sourceURL']=SOURCES_URL
    obj['reviewScope']='Existing photographed pane outline; optical values and positions remain estimates'
    return obj


def apply_mar_interior177():
    if all(bpy.data.objects.get(name) for name in TARGETS):
        return dict(alreadyApplied=True,addedObjects=[],archivedObjects=[],changedObjects=[])
    assert not any(bpy.data.objects.get(name) for name in TARGETS)
    archive=bpy.data.collections.new('MAR177_GLASS_ARCHIVE')
    bpy.context.scene.collection.children.link(archive)
    added=[];archived=[]
    for index,(source_name,target_name) in enumerate(zip(SOURCES,TARGETS)):
        source=bpy.data.objects[source_name]
        collection=bpy.data.collections['MAR_EXTERIOR' if index==0 else 'MAR_PUBLIC_INTERIOR_study']
        obj=_sheet(source,target_name,collection,index==0);added.append(obj.name)
        for owner in list(source.users_collection):owner.objects.unlink(source)
        archive.objects.link(source);source.hide_render=True;source.hide_set(True)
        archived.append(source.name)
    return dict(alreadyApplied=False,addedObjects=added,archivedObjects=archived,changedObjects=[],
                paneCounts={'ground':107,'mezzanine':54},sourceURL=SOURCES_URL,
                scope='107 Great Hall panes and54 mezzanine guards retain their apertures; one sheet per pane replaces six-face boxes.',
                limitations='Photograph capture date unknown. Existing pane locations, hall geometry and floor layout retained; opacity and neutral tint estimated.')
