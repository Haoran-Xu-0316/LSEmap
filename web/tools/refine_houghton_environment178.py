"""Match photographed blackOLD ramp uprights while retaining the silver handrail.

Userreference09 clearly separates dark posts from the silver continuous rail.
Coating colour/roughness/metallic values are visual estimates, not measurements.
Only a copied post object/mesh/material changes; original stays archived intact.
"""
import bpy

SOURCE='OLD_NEXT_APPROACH_silver_posts'
TARGET='OLD178_Houghton_approach_black_posts'
HANDRAIL='OLD_NEXT_APPROACH_continuous_handrail'
ARCHIVE='OLD178_HOUGHTON_POST_ARCHIVE'
PHOTO='data/collections/public-realm-2026/user-references/reference-09.png'


def apply_houghton_environment178():
    if bpy.data.objects.get(TARGET):
        assert bpy.data.objects[SOURCE].hide_render,'Partial post archive state'
        return dict(alreadyApplied=True,addedObjects=[],archivedObjects=[],changedObjects=[])
    source=bpy.data.objects[SOURCE];handrail=bpy.data.objects[HANDRAIL]
    assert not source.hide_render and len(source.data.materials)==1
    original=source.data.materials[0]
    assert original and original in list(handrail.data.materials)
    owners=list(source.users_collection);assert len(owners)==1
    replacement=source.copy();replacement.data=source.data.copy();replacement.name=TARGET;replacement.data.name=TARGET+'_mesh'
    owners[0].objects.link(replacement)
    material=original.copy();material.name='OLD178_Houghton_black_post_coating'
    color=(.012,.018,.017,1);material.diffuse_color=color
    node=material.node_tree.nodes.get('Principled BSDF');assert node
    assert not node.inputs['Base Color'].is_linked
    node.inputs['Base Color'].default_value=color;node.inputs['Roughness'].default_value=.58;node.inputs['Metallic'].default_value=.1
    material['webBaseColor']=list(color);material['webRoughness']=.58;material['webMetallic']=.1
    material['finishValuesEstimated']=True;material['sourcePhoto']=PHOTO;material['referenceDate']='User photograph; capture date unknown'
    replacement.data.materials[0]=material
    replacement['reviewScope']='Eight retained registeredOLD slope uprights; dark photo-estimated coating only'
    replacement['sourcePhoto']=PHOTO
    archive=bpy.data.collections.new(ARCHIVE);bpy.context.scene.collection.children.link(archive)
    owners[0].objects.unlink(source);archive.objects.link(source);source.hide_render=True;source.hide_set(True)
    return dict(alreadyApplied=False,addedObjects=[TARGET],archivedObjects=[SOURCE],changedObjects=[],
                scope='Eight existingOLD raised-route uprights copied with black coating; shared silver continuous handrail retained',
                sourcePhoto=PHOTO,referenceDate='User photograph capture unknown',
                dimensions='No geometry or location changes; inherited eight900mm upright estimates',
                opticalValuesEstimated=True)
