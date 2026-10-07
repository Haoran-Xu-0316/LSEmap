"""Correct two legacy glass finishes and CKK's photographed atrium glazing.

Callable on the loaded native model. Colours/transmittance remain visual
estimates; no facade, room or glazing geometry is altered.
"""
from array import array
import hashlib
import bpy

LEGACY={
 'CKK_EXTERIOR_Glazing_bays':'CKK_GLASS164_legacy_dielectric',
 'LRB_NEXT_ENVELOPE_retained_EXTERIOR_Glazing_bays':'LRB_GLASS164_legacy_dielectric',
}
ATRIA=['CKK_cross_bridge_glass','CKK_entrance_door_glazing','CKK_gallery_glass',
       'CKK_glazed_room_fronts','CKK_rear_glazed_panels','CKK_stair_glass']


def shape_signature(obj):
    h=hashlib.sha256(str([list(row)for row in obj.matrix_world]).encode())
    for items,field,width,kind in [(obj.data.vertices,'co',3,'f'),(obj.data.loops,'vertex_index',1,'i'),(obj.data.polygons,'material_index',1,'i')]:
        values=array(kind,[0])*(len(items)*width);items.foreach_get(field,values);h.update(values.tobytes())
    for layer in obj.data.uv_layers:
        values=array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);h.update(values.tobytes())
    return h.hexdigest()


def apply_architectural_glass():
    names=list(LEGACY)+ATRIA
    if all(bpy.data.objects[n].get('architecturalGlass164')for n in names):
        return {'changedObjects':[],'addedObjects':[],'alreadyApplied':True}
    assert not any(bpy.data.objects[n].get('architecturalGlass164')for n in names)
    before={n:shape_signature(bpy.data.objects[n])for n in names}
    source_states={};bindings=[]
    atrium_source=bpy.data.objects[ATRIA[0]].data.materials[0]
    assert atrium_source.name=='ATRIA_glass'
    clear=atrium_source.copy();clear.name='CKK_GLASS164_clear_atrium'
    clear.diffuse_color=(.78,.83,.82,1)
    bsdf=clear.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value=clear.diffuse_color
    bsdf.inputs['Metallic'].default_value=0
    bsdf.inputs['Roughness'].default_value=.12
    bsdf.inputs['Transmission Weight'].default_value=.94
    clear['webOpacity']=.16
    for name in names:
        obj=bpy.data.objects[name];source=obj.data.materials[0];node=source.node_tree.nodes['Principled BSDF']
        source_states[source.name]={'color':list(node.inputs['Base Color'].default_value),'metallic':float(node.inputs['Metallic'].default_value),'roughness':float(node.inputs['Roughness'].default_value),'transmission':float(node.inputs['Transmission Weight'].default_value),'webOpacity':source.get('webOpacity')}
        if name in LEGACY:
            assert abs(node.inputs['Metallic'].default_value-.6)<.001
            mat=source.copy();mat.name=LEGACY[name]
            mat.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value=0
        else:
            assert source==atrium_source
            mat=clear
        obj.data.materials[0]=mat
        obj['architecturalGlass164']=True
        bindings.append({'object':name,'sourceMaterial':source.name,'material':mat.name,'shapeSignature':before[name]})
    assert all(shape_signature(bpy.data.objects[n])==digest for n,digest in before.items())
    for name,state in source_states.items():
        source=bpy.data.materials[name];node=source.node_tree.nodes['Principled BSDF']
        assert list(node.inputs['Base Color'].default_value)==state['color']
        assert float(node.inputs['Metallic'].default_value)==state['metallic']
        assert float(node.inputs['Transmission Weight'].default_value)==state['transmission']
    return {'changedObjects':names,'addedObjects':[],'bindings':bindings,'originalSourceMaterials':source_states,'allShapesAndUVsPreserved':True,
            'scope':'Legacy CKK/LRB glazing changes metallic0.6 to dielectric0 while preserving colour, roughness and opacity; six CKK public-atrium glazing objects receive independent neutral clear finish. All shapes, UVs, openings, frames and other rooms retained. Colour and optical values are estimates, not measured glazing specifications.',
            'source':'https://grimshaw.global/projects/education-and-science/london-school-of-economics-new-academic-building/',
            'reference':'data/collections/exteriors/images/ckk_grimshaw_007.jpg','photographDate':'unknown'}
