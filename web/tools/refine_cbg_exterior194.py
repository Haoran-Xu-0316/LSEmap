"""CBG exterior coating and glazing refinement from the retained photographs.

Run in Blender's Text Editor. The callable changes the loaded model only; the
standalone handoff opens v193 and writes a separate, reusable component. It does
not infer a roof/stair layout or save another complete campus. The red-primary
palette follows the user's explicit choice, not a photographed colour survey.
"""
from pathlib import Path
import ast
import hashlib
import json
import sys
import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/cbg-exterior194'
BASE = ROOT / 'result/blender/LSE_campus_detailed_v193.blend'
BASE_SHA = '795f45f02fae1087a138cb3fd4d63a62869182d5c0cfaab202e4c2a9e98855fb'
PREFIX = 'CBG194_'
COLLECTION = 'CBG_EXTERIOR'


def material_state(material):
    node = material.node_tree.nodes.get('Principled BSDF')
    return {'colorLinear': list(node.inputs['Base Color'].default_value),
            'metallic': float(node.inputs['Metallic'].default_value),
            'roughness': float(node.inputs['Roughness'].default_value),
            'transmission': float(node.inputs['Transmission Weight'].default_value),
            'webOpacity': material.get('webOpacity')}


def finish_kind(material):
    name = material.name
    if 'neutral_glazing' in name:
        return 'glass'
    if 'orange_blade_returns' in name:
        return 'orange'
    if 'ochre_anodised_blade' in name:
        return 'red'
    if 'off_white_external_steel' in name:
        return 'white'
    return None


def apply_cbg_exterior194():
    """Keep every mesh/UV and assign independent coatings to visible CBG skins."""
    sys.path.insert(0, str(ROOT / 'web/tools'))
    from refine_architectural_glass import shape_signature
    collection = bpy.data.collections[COLLECTION]
    if any(obj.name.startswith(PREFIX) for obj in collection.all_objects):
        raise RuntimeError('CBG194 is already present; use the untouched baseline')
    originals = {obj.name: shape_signature(obj) for obj in collection.all_objects if obj.type == 'MESH'}
    materials, changes, added, archived, states = {}, [], [], [], {}
    for source in list(collection.all_objects):
        if source.type != 'MESH' or source.hide_render:
            continue
        slots = [(i, material, finish_kind(material)) for i, material in enumerate(source.data.materials)
                 if material and material.use_nodes and finish_kind(material)]
        if not slots:
            continue
        replacement = source.copy()
        replacement.data = source.data.copy()
        replacement.name = PREFIX + source.name
        replacement.data.name = replacement.name
        replacement['originalObject'] = source.name
        replacement['cbgExterior194'] = True
        collection.objects.link(replacement)
        for index, previous, kind in slots:
            if previous.name not in materials:
                material = previous.copy()
                material.name = PREFIX + {'glass': 'neutral_facade_glass', 'red': 'red_powdercoat',
                                           'orange': 'orange_powdercoat', 'white': 'white_powdercoat'}[kind]
                node = material.node_tree.nodes.get('Principled BSDF')
                node.inputs['Metallic'].default_value = 0
                if kind == 'glass':
                    # Neutral70/37 is documented, but web alpha is a presentation
                    # approximation rather than physical light transmission.
                    node.inputs['Roughness'].default_value = .12
                    material['webOpacity'] = .40
                else:
                    colors = {'red': (.49, .019, .014), 'orange': (.65, .16, .027),
                              'white': (.75, .765, .74)}
                    color = colors[kind] + (1,)
                    material.diffuse_color = color
                    node.inputs['Base Color'].default_value = color
                    node.inputs['Roughness'].default_value = .48
                    # Paint is a dielectric layer even when its substrate is metal.
                    node.inputs['Metallic'].default_value = .02
                materials[previous.name] = material
                states[previous.name] = {'before': material_state(previous),
                                         'after': material_state(material), 'kind': kind,
                                         'replacementMaterial': material.name}
            replacement.data.materials[index] = materials[previous.name]
        assert shape_signature(replacement) == originals[source.name]
        source.hide_render = True
        source.hide_set(True)
        added.append(replacement.name)
        archived.append(source.name)
        changes.append({'source': source.name, 'target': replacement.name,
                        'targetCollection': COLLECTION, 'shapeSignature': originals[source.name]})
    assert added and len(added) == len(archived)
    assert all(shape_signature(bpy.data.objects[name]) == signature for name, signature in originals.items())
    return {'addedObjects': added, 'archivedObjects': archived, 'changedObjects': [],
            'targetCollection': COLLECTION, 'replacements': changes, 'materials': states,
            'allOriginalShapesAndUVsPreserved': True,
            'scope': 'All visible neutral glass, red/orange blade paint and off-white painted exterior steel. No frame, opening, floor, stair or roof geometry changes.',
            'references': [
                {'file': 'data/collections/cbg_facade_contractor/photo-2.jpg',
                 'url': 'https://www.dobler-metallbau.com/wp-content/uploads/2020/11/55_LSE_1174x684px2.jpg',
                 'observed': 'Grey/silver structural edges, mostly pale blade surfaces, warm orange/gold returns and neutral sky-reflective glazing.'},
                {'file': 'data/collections/cbg_facade_contractor/photo-6.jpg',
                 'url': 'https://www.dobler-metallbau.com/wp-content/uploads/2020/11/55_LSE_1174x684px6.jpg',
                 'observed': 'Interior surfaces visible behind neutral curtain glass; reflections vary with sky.'},
                {'file': 'data/collections/cbg_facade_contractor/dobler-lse-facade.pdf',
                 'url': 'https://www.dobler-metallbau.com/wp-content/uploads/2021/11/LSE_eng_web.pdf',
                 'observed': 'Neutral70/37 glazing specification; physical transmission is not WebGL alpha.'}],
            'limitations': ['Red-primary blade faces retain explicit user direction. Contractor/architect photographs predominantly show pale broad faces and orange/gold returns; red is not claimed to be a measured as-built coating.',
                            'RGB, opacity and roughness are visual estimates without an on-site colour card.',
                            'The private roof candidate is deliberately excluded: its floor and circulation registration remain unverified.',
                            'Every existing roof, room and structural bay is retained; internal completeness remains unproven.']}


def build_handoff():
    OUT.mkdir(parents=True, exist_ok=True)
    source_sha = hashlib.sha256(BASE.read_bytes()).hexdigest()
    assert source_sha == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    record = apply_cbg_exterior194()
    for reference in record['references']:
        reference['sha256'] = hashlib.sha256((ROOT / reference['file']).read_bytes()).hexdigest()
        reference['captureDate'] = 'unknown'
    owned = {bpy.data.objects[name] for name in record['addedObjects']}
    path = OUT / 'cbg-exterior194-component.blend'
    bpy.data.libraries.write(str(path), owned, path_remap='RELATIVE', fake_user=True, compress=True)
    record.update(sourceVersion=193, sourceModelSha256=source_sha,
                  componentPath=str(path.relative_to(ROOT)), componentSha256=hashlib.sha256(path.read_bytes()).hexdigest())
    # The private renderer uses the same conversion and mesh evaluation as release.
    module = ast.parse((ROOT / 'web/tools/export_scene.py').read_text())
    namespace = dict(__file__=str(ROOT / 'web/tools/export_scene.py'), ROOT=ROOT, OUTPUT=OUT,
                     full_detail=True, material_cache={}, depsgraph=bpy.context.evaluated_depsgraph_get())
    functions = [node for node in module.body if isinstance(node, (ast.FunctionDef, ast.Import, ast.ImportFrom))]
    exec(compile(ast.Module(body=functions, type_ignores=[]), 'private-cbg-export', 'exec'), namespace)
    # Replacement names retain their source UV/bevel policy in the root release.
    policy = namespace['source_geometry_name']
    namespace['source_geometry_name'] = lambda obj: policy(bpy.data.objects[obj['originalObject']]) if obj.get('originalObject') else policy(obj)
    scene = bpy.data.scenes.new('CBG_EXTERIOR194_PRIVATE_REVIEW')
    objects = set(bpy.data.collections[COLLECTION].all_objects) | set(bpy.data.collections['CBG_PUBLIC_INTERIOR_study'].all_objects)
    namespace['clone_group'](list(objects), 'CBG', scene)
    namespace['export_scene'](scene, 'cbg-exterior194.glb')
    # Reopen the component to prove the saved handoff retains shape and coating.
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    with bpy.data.libraries.load(str(path), link=False) as (source, target):
        target.objects = list(record['addedObjects'])
    from refine_architectural_glass import shape_signature
    for obj, replacement in zip(target.objects, record['replacements']):
        bpy.data.collections[COLLECTION].objects.link(obj)
        assert obj['originalObject'] == replacement['source']
        assert shape_signature(obj) == replacement['shapeSignature']
        for material in obj.data.materials:
            if material.name.startswith(PREFIX) and 'facade_glass' in material.name:
                assert abs(material['webOpacity'] - .40) < 1e-7
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == source_sha
    record['savedComponentReopened'] = True
    (OUT / 'audit.json').write_text(json.dumps(record, indent=2) + '\n')
    print('CBG_EXTERIOR194_HANDOFF', len(owned), record['componentSha256'], flush=True)


if __name__ == '__main__':
    build_handoff()
