"""Correct St Clement's whole street envelope and entrance finish hierarchy.

Run in Blender's Text Editor. Archived official and dated whole-building photos
support neutral off-white render, pale frames, red-brown landings and a gray
entrance fascia. Colours are estimates, not a measured or current survey. Every
source face, UV layer, glazing opacity, artwork object and room is preserved.
"""
from pathlib import Path
import array
import hashlib
import json

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'result/blender/LSE_campus_detailed_v196.blend'
BASE_SHA = '1c1185738e796221c6d30f06aec906b99829cad4867fbb2bced77d657afc298b'
OUT = ROOT / 'result/blender/stc-exterior197'
PREFIX = 'STC197_FINISH_'
TARGET = 'STC_EXTERIOR'
REFERENCES = [
    {'path': 'data/建筑图片/STC_St Clement_s/01_建筑实拍/campus_photos_round2_STC_geograph_7222785_01.jpg',
     'url': 'https://www.geograph.org.uk/photo/7222785', 'photographCaptureDate': '2022-06-01 archive record',
     'supports': 'Whole Clare Market and corner frontage: neutral off-white render, pale frames, red-brown recessed landings and darker ground plinth'},
    {'path': 'data/建筑图片/STC_St Clement_s/01_建筑实拍/exteriors_lse_estate_029.jpg',
     'url': 'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Images/LSE-Estate/STC-web.jpg',
     'photographCaptureDate': 'Unknown',
     'supports': 'Official entrance close-up: white render, medium-gray fascia, red jamb, gray lower plinth and stainless door edge'},
]


def state(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    for data, field, kind, width in ((obj.data.vertices, 'co', 'f', 3),
                                     (obj.data.loops, 'vertex_index', 'i', 1),
                                     (obj.data.polygons, 'material_index', 'i', 1)):
        values = array.array(kind, [0]) * (len(data) * width)
        data.foreach_get(field, values)
        digest.update(values.tobytes())
    uv = {}
    for layer in obj.data.uv_layers:
        values = array.array('f', [0]) * (len(layer.data) * 2)
        layer.data.foreach_get('uv', values)
        uv[layer.name] = hashlib.sha256(values.tobytes()).hexdigest()
    return {'geometry': digest.hexdigest(), 'uv': uv}


def family(obj, material):
    name = obj.name
    if 'ARTWORK' in name or 'ENVELOPE_corner_panel_frame' in name:
        return None
    if name in {'STC_D5_ground_plinth_stone', 'STC_D5_corner_plinth_stone'}:
        return 'ground-plinth'
    if name == 'STC_D5_entry_name_fascia_stone':
        return 'entry-fascia'
    if name == 'STC_D5_entry_right_reveal_stone':
        return 'white-render'
    if material.name == 'STC11_render' and 'east_blank_wall' not in name:
        return 'white-render'
    if material.name == 'STC11_stone' and any(word in name for word in ('window_reveal', 'projecting_sill', 'roof_coping')):
        return 'pale-reveal'
    if material.name == 'STC11_frame' and any(word in name for word in ('window_', 'attic_')):
        return 'pale-painted-frame'
    if material.name in {'STC11_terracotta', 'STC_NEXT_STC11_terracotta'}:
        return 'red-brown-landings'
    if 'glass' in material.name.lower() and any(word in name for word in ('attic_glass', 'recessed_glass', 'entry_rear_glass', 'landing_rear_door')):
        return 'dielectric-glass'
    return None


def shader_record(material):
    p = next(n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    return {'baseColor': list(p.inputs['Base Color'].default_value),
            'roughness': p.inputs['Roughness'].default_value,
            'metallic': p.inputs['Metallic'].default_value,
            'alpha': p.inputs['Alpha'].default_value,
            'transmission': p.inputs['Transmission Weight'].default_value,
            'webOpacity': material.get('webOpacity'),
            'webClosedGlazing': material.get('webClosedGlazing')}


def finish(source, kind):
    material = source.copy()
    material.name = PREFIX + kind + '_' + source.name
    p = next(n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    finishes = {
        'white-render': ((.71, .715, .695, 1), .88, 0),
        'pale-reveal': ((.58, .595, .57, 1), .80, 0),
        'pale-painted-frame': ((.61, .625, .60, 1), .34, .02),
        'red-brown-landings': ((.285, .092, .075, 1), .82, 0),
        'entry-fascia': ((.235, .245, .24, 1), .60, .02),
        'ground-plinth': ((.205, .22, .205, 1), .88, 0),
    }
    if kind == 'dielectric-glass':
        p.inputs['Roughness'].default_value = .13
        p.inputs['Metallic'].default_value = 0
        p.inputs['IOR'].default_value = 1.5
    else:
        color, roughness, metallic = finishes[kind]
        p.inputs['Base Color'].default_value = color
        p.inputs['Roughness'].default_value = roughness
        p.inputs['Metallic'].default_value = metallic
    material.diffuse_color = p.inputs['Base Color'].default_value
    material['finishScope'] = 'Photo-guided STC street exterior ' + kind
    # Retain authored enclosure policy; no transparency or empty-room invention.
    before, after = shader_record(source), shader_record(material)
    assert all(before[key] == after[key] for key in ('alpha', 'transmission', 'webOpacity', 'webClosedGlazing'))
    return material


def preview(phase):
    scene = bpy.data.scenes.new('STC197_preview_' + phase)
    collection = bpy.data.collections.new(scene.name + '_objects')
    scene.collection.children.link(collection)
    points = []
    for obj in bpy.data.collections[TARGET].all_objects:
        if obj.type in {'MESH', 'FONT', 'CURVE'} and not obj.hide_render:
            collection.objects.link(obj)
            if obj.type == 'MESH':
                points.extend(obj.matrix_world @ Vector(v) for v in obj.bound_box)
    low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    center = (low + high) / 2
    world = bpy.data.worlds.new(scene.name + '_world')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[1].default_value = .65
    env = world.node_tree.nodes.new('ShaderNodeTexEnvironment')
    env.image = bpy.data.images.load(str(ROOT / 'web/public/environment/kloppenheim-daylight-1k.hdr'), check_existing=True)
    world.node_tree.links.new(env.outputs['Color'], world.node_tree.nodes['Background'].inputs[0])
    scene.world = world
    light_data = bpy.data.lights.new(scene.name + '_sun', 'SUN')
    light_data.energy, light_data.angle = 1.8, .12
    sun = bpy.data.objects.new(light_data.name, light_data)
    collection.objects.link(sun)
    sun.rotation_euler = Vector((-.6, .5, -1)).to_track_quat('-Z', 'Y').to_euler()
    camera_data = bpy.data.cameras.new(scene.name + '_camera')
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    collection.objects.link(camera)
    scene.camera = camera
    camera_data.type = 'ORTHO'
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 1000, 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    record = next(p for p in json.loads((ROOT / 'web/tools/building-metadata.json').read_text())['buildings'] if p['code'] == 'STC')
    direction = record['exteriorDirection']
    outward = Vector((direction[0], -direction[2], .28)).normalized()
    def native(point):
        return Vector((point[0], -point[2], point[1]))
    entrance = native(record['detailView']['target'])
    entry_offset = native(record['detailView']['position']) - entrance
    views = {'whole': (center, center + outward * 90, 50),
             'entrance': (entrance, entrance + entry_offset.normalized() * 30, 7)}
    for name, (target, location, scale) in views.items():
        camera.location = location
        camera.rotation_euler = (target - location).to_track_quat('-Z', 'Y').to_euler()
        camera_data.ortho_scale = scale
        scene.render.filepath = str(OUT / (phase + '-' + name + '.png'))
        bpy.ops.render.render(write_still=True, scene=scene.name)
    bpy.data.scenes.remove(scene)
    bpy.data.collections.remove(collection)


def build_component():
    OUT.mkdir(parents=True, exist_ok=True)
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()
    originals = {o.name: state(o) for o in bpy.data.objects if o.type == 'MESH'}
    original_bindings = {o.name: [m.name if m else None for m in o.data.materials]
                         for o in bpy.data.objects if o.type == 'MESH'}
    preview('before')
    materials, replacements, bindings = {}, [], []
    target = bpy.data.collections[TARGET]
    for source in list(target.all_objects):
        if source.type != 'MESH' or source.hide_render:
            continue
        slots = [(i, m, family(source, m)) for i, m in enumerate(source.data.materials) if m and family(source, m)]
        if not slots:
            continue
        obj = source.copy()
        obj.data = source.data.copy()
        obj.name = PREFIX + source.name
        obj['originalObject'] = source.name
        obj['webGeometrySource'] = source.get('webGeometrySource', source.name)
        target.objects.link(obj)
        for index, source_material, kind in slots:
            key = (source_material.name, kind)
            if key not in materials:
                materials[key] = finish(source_material, kind)
            material = materials[key]
            obj.data.materials[index] = material
            bindings.append({'object': obj.name, 'slot': index, 'family': kind,
                             'originalMaterial': source_material.name, 'material': material.name,
                             'before': shader_record(source_material), 'after': shader_record(material)})
        source.hide_render = True
        source.hide_set(True)
        obj.hide_render = False
        obj.hide_set(False)
        replacements.append({'originalObject': source.name, 'original': source.name,
                             'replacement': obj.name, 'targetCollection': TARGET})
        assert state(obj) == originals[source.name]
    assert len(replacements) >= 25
    assert all(state(bpy.data.objects[name]) == value for name, value in originals.items())
    assert all([m.name if m else None for m in bpy.data.objects[name].data.materials] == value
               for name, value in original_bindings.items())
    preview('after')
    path = OUT / 'stc-exterior197-component.blend'
    bpy.data.libraries.write(str(path), {bpy.data.objects[r['replacement']] for r in replacements} | set(materials.values()), fake_user=True)
    report = {'version': 197, 'baseline': str(BASE.relative_to(ROOT)), 'baselineSha256': BASE_SHA,
              'componentPath': str(path.relative_to(ROOT)), 'componentSha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'targetCollection': TARGET, 'addedObjects': [r['replacement'] for r in replacements],
              'archivedObjects': [r['originalObject'] for r in replacements], 'changedObjects': [], 'replacements': replacements,
              'bindings': bindings, 'originalStates': {r['originalObject']: originals[r['originalObject']] for r in replacements},
              'geometryAndOriginalUVPreserved': True, 'artworkAndRoomObjectsUntouched': True,
              'references': [dict(r, sha256=hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()) for r in REFERENCES],
              'improvements': ['Neutral off-white whole street render replaces a yellow-green cast.',
                               'Pale painted window frames and reveals retain their existing divisions with a smoother coated finish.',
                               'Red-brown recessed landing and attic finish replaces oversaturated orange-brown.',
                               'Official gray entrance fascia and lower gray plinth now have distinct finishes instead of pale reveal stone.',
                               'Window dielectric roughness reduced from0.24to0.13; colours, enclosure policy and opacity retained.'],
              'previews': ['before-whole.png', 'after-whole.png', 'before-entrance.png', 'after-entrance.png'],
              'previewLighting': 'Identical HDR sky, sun1.8, background0.65, AgX,12Cycles samples',
              'limitations': ['Photo-guided estimated finishes, not calibrated measurements or a2026 condition survey.',
                             'Ground plinth gray is supported by street and entrance images; exact aggregate and weathering are not reproduced.',
                             'Unobserved rear wall, art panel and frame, roof membrane, room layouts and inherited geometry remain unchanged.',
                             'Glass remains an opaque reflective proxy wherever room registration is unknown; no unsupported clear shell added.']}
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(path))
    checks = []
    for replacement in replacements:
        obj = bpy.data.objects[replacement['replacement']]
        assert state(obj) == originals[replacement['originalObject']]
        assert obj['originalObject'] == replacement['originalObject']
        checks.append({'object': obj.name, 'geometryAndAllUVPreserved': True})
    report['verification'] = {'savedComponentReopened': True,
                              'baselineUnchanged': hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA,
                              'allOriginalGeometryUVAndBindingsPreserved': True, 'objects': checks}
    (OUT / 'audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print('STC197_COMPONENT_READY', len(replacements), len(materials), flush=True)


if __name__ == '__main__':
    build_component()
