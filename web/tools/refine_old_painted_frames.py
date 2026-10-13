"""Give documented OLD blue paint a dielectric satin finish.

Apply to the loaded campus. Explicit painted-frame materials receive independent
copies; colour, transmission, opacity, geometry and all other finishes remain.
Photos establish a coating, not calibrated reflectance or colour values.
"""
from pathlib import Path
import hashlib
import bpy
ROOT=Path(__file__).resolve().parents[2]
PREFIX='OLD_PAINT193_'
ROUGHNESS=.46
SOURCES=(
    'OLD_Blue_painted_steel',
    'OLD_EXTERIOR168_blue_painted_dormer_jambs',
    'OLD_NEXT_OLD_NEXT_OLD_V112_blue',
    'OLD_NEXT_OLD_V112_blue',
    'OLD_NEXT_OLD_V53_blue',
    'OLD_V112_blue',
    'OLD_V113_blue',
    'OLD_V52_blue',
    'OLD_V77_blue',
    'OLD_V78_blue',
    'OLD_V85_four_column_blue',
    'OLD_V87_Clare_four_column_blue',
)


def material_state(material):
    node=material.node_tree.nodes['Principled BSDF']
    inputs={}
    for socket in node.inputs:
        if not hasattr(socket,'default_value'):continue
        value=socket.default_value
        inputs[socket.identifier]=list(value) if hasattr(value,'__iter__') else value
    return dict(diffuse=list(material.diffuse_color),inputs=inputs,
                opacity=material.get('webOpacity'),closedGlazing=material.get('webClosedGlazing'))


def apply_old_painted_frames():
    complete=all(bpy.data.materials.get(PREFIX+name) for name in SOURCES)
    if complete:
        assert all(bpy.data.materials[PREFIX+name].node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value==0 for name in SOURCES)
        return dict(alreadyApplied=True,addedObjects=[],archivedObjects=[],changedObjects=[])
    assert not any(bpy.data.materials.get(PREFIX+name) for name in SOURCES)
    sources={name:bpy.data.materials[name] for name in SOURCES}
    original={name:material_state(mat) for name,mat in sources.items()}
    owners=[]
    for obj in bpy.data.objects:
        if obj.type!='MESH' or obj.hide_render:continue
        slots=[(i,mat.name) for i,mat in enumerate(obj.data.materials) if mat and mat.name in sources]
        if not slots:continue
        assert all(c.name=='OLD_EXTERIOR' for c in obj.users_collection),(obj.name,[c.name for c in obj.users_collection])
        owners.append((obj,slots))
    assert len(owners)==20,len(owners)
    copies={}
    for name,source in sources.items():
        shader=source.node_tree.nodes['Principled BSDF']
        assert not shader.inputs['Base Color'].is_linked
        assert 0<shader.inputs['Metallic'].default_value<.36
        assert shader.inputs['Transmission Weight'].default_value==0
        source.use_fake_user=True
        material=source.copy();material.name=PREFIX+name
        material.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value=0
        material.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=ROUGHNESS
        material['finishScope']='OLD identified blue painted frames only; satin reflectance estimate, original colour retained'
        copies[name]=material
    bindings=[]
    for obj,slots in owners:
        if obj.data.users>1:obj.data=obj.data.copy()
        for index,name in slots:
            obj.data.materials[index]=copies[name]
            bindings.append(dict(object=obj.name,slot=index,sourceMaterial=name,material=copies[name].name))
    assert all(material_state(sources[name])==value for name,value in original.items())
    references=[]
    for path in ['data/collections/campus_photos_round2/images/OLD/OLD_old_webbyates_06.jpg','data/collections/old-clare-reference/front.png']:
        references.append(dict(path=path,sha256=hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),captureDate='unknown'))
    return dict(alreadyApplied=False,addedObjects=[],archivedObjects=[],changedObjects=[o.name for o,_ in owners],
                bindings=bindings,originalSourceMaterials=original,materialCount=len(copies),roughness=ROUGHNESS,
                references=references,scope='Existing Houghton, Clare Market and roof blue painted frames receive dielectric satin finish; palette and geometry retained',
                limitations=['Paint roughness is a visual estimate, not a measured specification',
                             'No colour calibration or unseen/current full exterior completion claim',
                             'All glazing, exposed steel, lantern and rooms retained'])
