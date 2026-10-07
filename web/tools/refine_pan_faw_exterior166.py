"""Photo-register PAN's shared PAN/FAW entrance and lower-front glazing.

Call apply_pan_faw_exterior() in an already loaded campus. The five broad window
modules per row, frames, opaque blinds and all other elevations remain intact.
FAW's independent upper elevations lack registered evidence and are retained.
"""
from pathlib import Path
import hashlib
import bpy

ROOT=Path(__file__).resolve().parents[2]
PREFIX='PAN166_'
SOURCES=[
 'PAN_D3_revolving_door_curved_glass',
 'PAN_D3_revolving_glass_wings',
 'PAN_D5_entry88_retained_ground_glass',
 'PAN_D5_entry88_fixed_glass',
 'PAN_D5_entry88_door_glazing',
 'PAN_NEXT_ENVELOPE_five_module_glass',
]
PHOTO='result/blender/faw_exterior156/sources/plb-entrance.jpg'


def apply_pan_faw_exterior():
    """Use independent optical materials; keep source meshes and their UVs."""
    names=[PREFIX+name for name in SOURCES]
    if all(bpy.data.objects.get(name) for name in names):
        assert all(bpy.data.objects[source].hide_render for source in SOURCES)
        return {'alreadyApplied':True,'addedObjects':names,'archivedObjects':SOURCES,'changedObjects':[]}
    assert not any(bpy.data.objects.get(name) for name in names), 'Partial prior application'
    photo_sha=hashlib.sha256((ROOT/PHOTO).read_bytes()).hexdigest()
    materials={}
    for family,color,rough,transmission,opacity in [
        ('entry',(.52,.56,.54),.105,.85,.32),
        ('windows',(.38,.43,.42),.135,.68,.52),
    ]:
        source=bpy.data.objects[SOURCES[0 if family=='entry' else -1]].data.materials[0]
        mat=source.copy();mat.name=PREFIX+family+'_reflective_clear_glass'
        mat.diffuse_color=(*color,1)
        node=mat.node_tree.nodes['Principled BSDF']
        node.inputs['Base Color'].default_value=mat.diffuse_color
        node.inputs['Metallic'].default_value=0
        node.inputs['Roughness'].default_value=rough
        node.inputs['Transmission Weight'].default_value=transmission
        node.inputs['IOR'].default_value=1.5
        mat['webOpacity']=opacity
        mat['scope']='Photo-estimated optics; no clear opening added through existing blinds'
        materials[family]=mat
    for source_name,name in zip(SOURCES,names):
        original=bpy.data.objects[source_name]
        assert not original.hide_render and original.type=='MESH'
        copy=original.copy();copy.data=original.data.copy();copy.name=name
        bpy.data.collections['PAN_EXTERIOR'].objects.link(copy)
        assert len(copy.data.materials)==1
        copy.data.materials[0]=materials['windows' if source_name==SOURCES[-1] else 'entry']
        copy['reference']=PHOTO;copy['sourcePhotoSha256']=photo_sha
        copy['dimensionStatus']='Source geometry unchanged; optics photo-estimated, not calibrated'
        original.hide_render=True;original.hide_set(True)
    return {'alreadyApplied':False,'addedObjects':names,'archivedObjects':SOURCES,
            'changedObjects':[], 'sourcePhoto':PHOTO,'sourcePhotoSha256':photo_sha,
            'sourceURL':'https://www.architectureplb.com/sectors/universities-and-colleges/lse-towers',
            'sourceProjectCompletion':'August2018; photograph capture date unspecified',
            'entryGlass':{'transmission':.85,'webOpacity':.32,'roughness':.105},
            'registered25WindowGlass':{'transmission':.68,'webOpacity':.52,'roughness':.135},
            'limitations':['Shared entrance belongs to PAN and serves FAW; no second FAW entrance added',
                           'Opaque internal blinds and all upper/side/back glazing retained',
                           'FAW full elevations, crown and exact frame dimensions remain unverified',
                           'No surveyed2026condition or complete interior reconstruction claimed']}
