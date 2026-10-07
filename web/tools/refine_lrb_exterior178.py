"""Use one outward optical surface per photographed Plaza Café glazing panel.

Loaded-scene operation. Preserve the closed source batch as a hidden archive;
keep the photographed frames, furniture, pane outlines and optical finish.
"""
import bpy
from mathutils import Vector
SOURCE='LRB_NEXT_PLAZA155_glass'
OWNED='LRB_EXTERIOR178_plaza_single_panes'
RING=((46.40633451625346,-20.026247966340836),(47.37121302737788,-15.731676051953531),(57.867319883658716,-17.778716567458556),(58.12415382916924,-16.488119569767164),(60.192833277052934,-17.04438603148295),(62.664151708805555,-18.47958576277101),(64.48293571677299,-19.836911934749544),(66.03794990775441,-22.72960278432517),(64.90646860921608,-26.056234792441273))


def panel_outward(center):
    ring=[Vector((*p,0))for p in RING]
    signed=sum(a.x*b.y-b.x*a.y for a,b in zip(ring,ring[1:]+ring[:1]))
    candidates=[]
    for a,b in zip(ring,ring[1:]+ring[:1]):
        edge=b-a;t=max(0,min(1,(center-a).dot(edge)/edge.length_squared))
        delta=center-(a+edge*t);delta.z=0
        normal=Vector((-edge.y,edge.x,0)).normalized()
        candidates.append((delta.length,-normal if signed>0 else normal))
    return min(candidates,key=lambda row:row[0])[1]


def apply_lrb_exterior178():
    if bpy.data.objects.get(OWNED):
        return dict(alreadyApplied=True,addedObjects=[],archivedObjects=[],changedObjects=[])
    source=bpy.data.objects[SOURCE];data=source.data
    assert len(data.vertices)==528 and len(data.polygons)==396
    vertices=[];faces=[];uvs=[];slots=[];selected=[]
    normal_matrix=source.matrix_world.to_3x3().inverted().transposed()
    for index in range(66):
        ids=set(range(index*8,index*8+8));center=sum((source.matrix_world@data.vertices[i].co for i in ids),Vector())/8
        outward=panel_outward(center)
        options=[p for p in data.polygons if set(p.vertices).issubset(ids)]
        broad=[p for p in options if abs((normal_matrix@p.normal).normalized().dot(outward))>.999]
        main=max(broad,key=lambda p:((source.matrix_world@p.center)-center).dot(outward))
        loop_indices=list(main.loop_indices)
        if (normal_matrix@main.normal).normalized().dot(outward)<0:loop_indices.reverse()
        start=len(vertices);vertices.extend(data.vertices[data.loops[i].vertex_index].co.copy()for i in loop_indices)
        faces.append(tuple(range(start,len(vertices))));uvs.append([[layer.data[i].uv.copy()for i in loop_indices]for layer in data.uv_layers]);slots.append(main.material_index);selected.append(main.index)
    mesh=bpy.data.meshes.new(OWNED);mesh.from_pydata(vertices,[],faces);mesh.update()
    for material in data.materials:mesh.materials.append(material)
    for layer_index,old in enumerate(data.uv_layers):
        layer=mesh.uv_layers.new(name=old.name)
        for face,values in zip(mesh.polygons,uvs):
            for li,value in zip(face.loop_indices,values[layer_index]):layer.data[li].uv=value
    for face,slot in zip(mesh.polygons,slots):face.material_index=slot
    clone=source.copy();clone.data=mesh;clone.name=OWNED
    for collection in source.users_collection:collection.objects.link(clone)
    clone.hide_render=False;clone.hide_set(False)
    source.hide_render=True;source.hide_set(True)
    clone['reviewScope']='66single outward café panes; whole library proxy glass untouched'
    return dict(alreadyApplied=False,addedObjects=[OWNED],archivedObjects=[SOURCE],changedObjects=[],selectedSourceFaces=selected,paneCount=66,sourceURL='https://food.lse.ac.uk/outlets',sourcePhotos=['data/collections/campus_photos_round2/images/LRB/LRB_food_outlets_09.jpg'],photographDate='unknown',scope='Photographed Plaza Café perimeter glass; remove closed-box backfaces and edge faces, retain optical finish/frames/interior support',limitations=['Pavilion footprint and pane dimensions inherited map/photo estimates, not measured2026survey','Single surface is a realtime optical representation, not a physical fabrication thickness','Main library high-storey opaque proxies and dome unchanged'])
