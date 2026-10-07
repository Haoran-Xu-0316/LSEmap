"""Remove legacy metallic response from explicitly identified exterior glass.

Callable in the loaded scene. Retain all colours, opacity, transmission,
roughness, geometry, UVs and unrelated/shared source finishes. This corrects a
PBR parameter, not a measured glazing specification or a new transparency claim.
"""
import bpy
from refine_architectural_glass import shape_signature

SOURCES = (
    'CLM_NEXT_CLM_NEXT_CLM_V73_glass', 'COL_V41_neutral_glass_0',
    'CON_NEXT_CON_NEXT_CON_V41_neutral_glass_2',
    'CON_NEXT_CON_NEXT_GLAZING151_fanlight_glass_material',
    'CON_NEXT_CON_NEXT_GLAZING151_registered_lower_frontage_glass_material',
    'CON_NEXT_CON_V41_neutral_glass_2.002', 'CON_V41_neutral_glass_1',
    'INFILL_glass.001', 'KSW_NEXT_KSW_D3_recessed_glass',
    'OLD_Recessed_reflective_glazing', 'OLD_V79_Window_glazing',
    'PEL_NEXT_INFILL_glass', 'SAL_NEXT_SAL_Recessed_reflective_glazing',
    'SAL_Recessed_reflective_glazing', 'SAL_V101_lantern_glass', 'SAR_V119_glass',
)


def finish_state(material):
    node = material.node_tree.nodes['Principled BSDF']
    return dict(color=list(node.inputs['Base Color'].default_value),
                metallic=float(node.inputs['Metallic'].default_value),
                roughness=float(node.inputs['Roughness'].default_value),
                transmission=float(node.inputs['Transmission Weight'].default_value),
                webOpacity=material.get('webOpacity'))


def apply_dielectric_glazing():
    bindings, states, copies = [], {}, {}
    for obj in list(bpy.data.objects):
        if obj.type != 'MESH' or obj.hide_render:
            continue
        if not any(c.name.endswith('_EXTERIOR') for c in obj.users_collection):
            continue
        slots = [(i, m) for i, m in enumerate(obj.data.materials) if m and m.name in SOURCES]
        if not slots:
            continue
        shape = shape_signature(obj)
        if obj.data.users > 1:
            obj.data = obj.data.copy()
        for slot, source in slots:
            state = finish_state(source)
            assert state['metallic'] >= .249
            states[source.name] = state
            if source.name not in copies:
                material = source.copy()
                material.name = 'DIELECTRIC166_' + source.name
                material.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value = 0
                copies[source.name] = material
            material = copies[source.name]
            obj.data.materials[slot] = material
            after = finish_state(material)
            assert after == {**state, 'metallic': 0.0}
            bindings.append(dict(object=obj.name, slot=slot, sourceMaterial=source.name,
                                 material=material.name, shapeSignature=shape))
        assert shape_signature(obj) == shape
    for name, state in states.items():
        assert finish_state(bpy.data.materials[name]) == state
    return dict(alreadyApplied=not bool(bindings), addedObjects=[],
                changedObjects=sorted({b['object'] for b in bindings}),
                bindings=bindings, originalSourceMaterials=states,
                allShapesAndUVsPreserved=True,
                source='https://threejs.org/docs/pages/MeshStandardMaterial.html',
                scope='Explicit legacy glass finishes change metallic to dielectric0; all other optical values and geometry retained. No measured coating or complete interior claim.')
