"""Photo-guided black paint for the existing Houghton entrance pair.

The archived photograph supports black painted cast iron, not measured PBR
values. Copy one material, bind only the two existing posts, and retain every
original shape, UV, material and other object's material assignment.
"""
import bpy

TARGETS=('SITE165_Houghton_cast_iron_bollard','SITE169_Houghton_second_cast_iron_bollard')
MATERIAL='SITE171_Houghton_satin_black_paint'


def apply_street_material171():
    objects=[bpy.data.objects[n] for n in TARGETS]
    owned=bpy.data.materials.get(MATERIAL)
    if owned and all(len(o.data.materials)==1 and o.data.materials[0]==owned for o in objects):
        return {'alreadyApplied':True,'addedObjects':[],'archivedObjects':[],'changedObjects':[],'changedMaterials':[]}
    assert owned is None, 'Partial paint application must not overwrite material bindings'
    original=objects[0].data.materials[0]
    assert original.name=='SITE165_Houghton_black_cast_iron'
    assert all(len(o.data.materials)==1 and o.data.materials[0]==original for o in objects)
    paint=original.copy();paint.name=MATERIAL
    # Linear-space dark colour: avoids the previous grey-looking high base value.
    colour=(.008,.011,.010,1)
    paint.diffuse_color=colour
    shader=paint.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value=colour
    shader.inputs['Metallic'].default_value=.04
    shader.inputs['Roughness'].default_value=.53
    paint['reference']='data/collections/public-realm-2026/user-references/reference-09.png'
    paint['photoDate']='Unknown; user supplied'
    paint['scope']='Estimated satin black painted cast iron; no material measurement or current-condition claim'
    for obj in objects:obj.data.materials[0]=paint
    return {'alreadyApplied':False,'addedObjects':[],'archivedObjects':[], 'changedObjects':list(TARGETS),
            'changedMaterials':[MATERIAL],'retainedMaterial':original.name,
            'linearBaseColor':list(colour),'roughness':.53,'metallic':.04,
            'reference':paint['reference'],'limitations':['PBR paint values are visual estimates from the photograph.', 'Only two already existing entrance posts are rebound; their positions and geometry are retained.']}
