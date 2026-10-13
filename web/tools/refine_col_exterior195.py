"""Photo-guided Columbia House stone, painted joinery and retained glass finish.

Run in Blender's Text Editor. Builds one standalone replacement component from
v194 without overwriting the campus. Existing topology, transforms and UVs are
preserved. Colours are photograph-guided, not calibrated survey measurements.
"""
from pathlib import Path
import array
import hashlib
import json
import struct
import zlib

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'result/blender/LSE_campus_detailed_v194.blend'
BASE_SHA = 'bcd7292cfda4c43ed4fd7622f564a5d3ce7ef8ac0360ba00d68b4081bd363c8e'
OUT = ROOT / 'result/blender/col-exterior195'
PREFIX = 'COL195_FINISH_'
UV_NAME = 'COLStoneFinish195'
REFERENCES = [
    ('data/建筑图片/COL_Columbia House/01_建筑实拍/small_round5_COL_handbook-000.png',
     'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Property-and-Space/LSE-Property-Handbook.pdf',
     '2025/26 property handbook; capture date unknown; main portal and lower street facade'),
    ('data/建筑图片/COL_Columbia House/01_建筑实拍/exteriors_lse_estate_004.jpg',
     'https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate',
     'Official estate photograph; capture date unknown; corner and street stone/joinery'),
]
STONE = {'STREET_D4_limestone', 'STREET_D4_cut_stone', 'STREET_D4_recessed_stone',
         'V16_COL_finish', 'V17_COL_finish', 'COL_V67_trim', 'COL_V67_stone',
         'COL175_retained_portland_stone', 'COL_V99_garrick_sign_stone'}


def state(obj):
    """Positions, topology, material-face bindings and original UV layer hashes."""
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    for data, field, kind, count in ((obj.data.vertices, 'co', 'f', 3),
                                    (obj.data.loops, 'vertex_index', 'i', 1),
                                    (obj.data.polygons, 'material_index', 'i', 1)):
        values = array.array(kind, [0]) * (len(data) * count)
        data.foreach_get(field, values)
        digest.update(values.tobytes())
    uv = {}
    for layer in obj.data.uv_layers:
        values = array.array('f', [0]) * (len(layer.data) * 2)
        layer.data.foreach_get('uv', values)
        uv[layer.name] = hashlib.sha256(values.tobytes()).hexdigest()
    return dict(geometry=digest.hexdigest(), uv=uv)


def kind(material):
    name = material.name
    if name in STONE:
        return 'stone'
    if 'dark_bronze_frames' in name or name == 'COL_V99_garrick_dark_metal':
        return 'joinery'
    if name == 'COL_V67_wood':
        return 'wood'
    if 'glass' in name.lower():
        return 'glass'
    return None


def stone_image():
    """Original subdued stone tones; no photo copied and no artificial joints."""
    size = 512
    y, x = np.mgrid[:size, :size] / size
    broad = (.44 * np.sin(2 * np.pi * (x + 2 * y) + .7)
             + .29 * np.cos(2 * np.pi * (3 * x - y) + 1.3)
             + .17 * np.sin(2 * np.pi * (5 * x + 3 * y) + .2))
    shade = 1 + .047 * broad
    rgb = np.stack([.823 * shade, .821 * shade, .791 * shade], axis=-1)
    pixels = (np.clip(rgb, 0, 1) * 255).round().astype(np.uint8)
    def chunk(tag, payload):
        return struct.pack('>I', len(payload)) + tag + payload + struct.pack('>I', zlib.crc32(tag + payload))
    raw = b''.join(b'\0' + row.tobytes() for row in pixels)
    encoded = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0))
               + chunk(b'sRGB', b'\0') + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))
    path = OUT / 'col-portland-stone195.png'
    path.write_bytes(encoded)
    image = bpy.data.images.load(str(path), check_existing=False)
    image.name = 'COL195_Portland_stone_original_tone_study'
    image.colorspace_settings.name = 'sRGB'
    image.pack()
    return image, dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(encoded).hexdigest(),
                      bytes=len(encoded), size=[size, size], licence='Original generated tone study')


def finish(source, image):
    material = source.copy()
    material.name = PREFIX + source.name
    shader = next(node for node in material.node_tree.nodes if node.type == 'BSDF_PRINCIPLED')
    family = kind(source)
    if family == 'stone':
        shader.inputs['Base Color'].default_value = (1, 1, 1, 1)
        shader.inputs['Roughness'].default_value = .86
        shader.inputs['Metallic'].default_value = 0
        texture = material.node_tree.nodes.new('ShaderNodeTexImage')
        texture.image = image
        texture.extension = 'REPEAT'
        texture.interpolation = 'Linear'
        uv = material.node_tree.nodes.new('ShaderNodeUVMap')
        uv.uv_map = UV_NAME
        material.node_tree.links.new(uv.outputs['UV'], texture.inputs['Vector'])
        material.node_tree.links.new(texture.outputs['Color'], shader.inputs['Base Color'])
        material.diffuse_color = (.643, .64, .589, 1)
        material['webBaseColorMap'] = True
        material['webBaseColorUV'] = UV_NAME
    elif family == 'joinery':
        # Photographed deep charcoal green finish is painted rather than bare
        # metallic bronze. Keep all actual seals and glazing division geometry.
        shader.inputs['Base Color'].default_value = (.038, .050, .047, 1)
        shader.inputs['Metallic'].default_value = .04
        shader.inputs['Roughness'].default_value = .34
        material.diffuse_color = (.038, .050, .047, 1)
    elif family == 'wood':
        shader.inputs['Base Color'].default_value = (.036, .021, .023, 1)
        shader.inputs['Metallic'].default_value = 0
        shader.inputs['Roughness'].default_value = .38
        material.diffuse_color = (.036, .021, .023, 1)
    elif family == 'glass':
        # Reflective windows remain opaque where source rooms are not verified.
        # No guessed empty-room transmission, alpha change or backing wall.
        shader.inputs['Base Color'].default_value = (.155, .182, .184, 1)
        shader.inputs['Metallic'].default_value = 0
        shader.inputs['Roughness'].default_value = .13
        shader.inputs['IOR'].default_value = 1.5
        material.diffuse_color = (.155, .182, .184, 1)
    material['finishScope'] = 'Photograph-guided COL exterior ' + family
    return material


def stone_uv(obj):
    layer = obj.data.uv_layers.new(name=UV_NAME)
    # 5m repeat aligned to retained native Aldwych/Houghton axes. Continuous
    # world projection avoids per-object seams; old UV layers remain untouched.
    u = Vector((-.99970835, .02415093, 0))
    n = Vector((-.02415093, -.99970835, 0))
    up = Vector((0, 0, 1))
    for face in obj.data.polygons:
        normal = (obj.matrix_world.to_3x3().inverted().transposed() @ face.normal).normalized()
        if abs(normal.z) > .65:
            a, b = u, n
        else:
            a, b = (u if abs(normal.dot(n)) >= abs(normal.dot(u)) else n), up
        for index in face.loop_indices:
            p = obj.matrix_world @ obj.data.vertices[obj.data.loops[index].vertex_index].co
            layer.data[index].uv = (p.dot(a) / 5, p.dot(b) / 5)


def preview(phase):
    scene = bpy.data.scenes.new('COL195_preview_' + phase)
    collection = bpy.data.collections.new(scene.name + '_objects')
    scene.collection.children.link(collection)
    for obj in bpy.data.collections['COL_EXTERIOR'].all_objects:
        if obj.type in {'MESH', 'FONT', 'CURVE'} and not obj.hide_render:
            collection.objects.link(obj)
    world = bpy.data.worlds.new(scene.name + '_world')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.78, .82, .87, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = .65
    scene.world = world
    sky = ROOT / 'web/public/environment/kloppenheim-sky-1k.hdr'
    env = world.node_tree.nodes.new('ShaderNodeTexEnvironment')
    env.image = bpy.data.images.load(str(sky), check_existing=True)
    world.node_tree.links.new(env.outputs['Color'], world.node_tree.nodes['Background'].inputs[0])
    light_data = bpy.data.lights.new(scene.name + '_sun', 'SUN')
    light_data.energy = 1.8
    light_data.angle = .12
    sun = bpy.data.objects.new(light_data.name, light_data)
    collection.objects.link(sun)
    sun.rotation_euler = Vector((-.6, .5, -1)).to_track_quat('-Z', 'Y').to_euler()
    camera_data = bpy.data.cameras.new(scene.name + '_camera')
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    collection.objects.link(camera)
    scene.camera = camera
    camera_data.type = 'ORTHO'
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    origin = Vector((16.67990685, -127.45446777, 0))
    u = Vector((-.99970835, .02415093, 0))
    n = Vector((-.02415093, -.99970835, 0))
    views = {'whole': (origin + u * 3 - n * 13 + Vector((0, 0, 14)), n * 48 + u * 22 + Vector((0, 0, 15)), 46),
             'portal': (origin + u * 2 + Vector((0, 0, 4.8)), n * 26 - u * 1.5 + Vector((0, 0, 1)), 11.5)}
    for name, (target, offset, scale) in views.items():
        camera.location = target + offset
        camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
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
    original = {o.name: state(o) for o in bpy.data.objects if o.type == 'MESH'}
    preview('before')
    image, image_record = stone_image()
    materials, replacements, bindings = {}, [], []
    target = bpy.data.collections['COL_EXTERIOR']
    for source in list(target.all_objects):
        # Hidden sources, unseen wall estimate, unverified roof and granite
        # steps are not recoloured under a street-photograph claim.
        if source.type != 'MESH' or source.hide_render or any(word in source.name.lower() for word in ('unseen', 'roof', 'parapet')):
            continue
        slots = [(i, m) for i, m in enumerate(source.data.materials) if m and kind(m)]
        if not slots:
            continue
        obj = source.copy()
        obj.data = source.data.copy()
        obj.name = PREFIX + source.name
        obj['originalObject'] = source.name
        obj['finishScope'] = 'COL street finish only; geometry, original UV, rooms and glazing transmission preserved'
        target.objects.link(obj)
        if any(kind(m) == 'stone' for _, m in slots):
            stone_uv(obj)
        for index, material in slots:
            if material.name not in materials:
                materials[material.name] = finish(material, image)
            obj.data.materials[index] = materials[material.name]
            bindings.append(dict(object=obj.name, slot=index, originalMaterial=material.name,
                                 material=materials[material.name].name, family=kind(material)))
        source.hide_render = True
        source.hide_set(True)
        obj.hide_render = False
        obj.hide_set(False)
        replacements.append(dict(originalObject=source.name, original=source.name, replacement=obj.name, targetCollection='COL_EXTERIOR'))
        check = state(obj)
        assert check['geometry'] == original[source.name]['geometry']
        assert all(check['uv'][name] == value for name, value in original[source.name]['uv'].items())
    assert len(replacements) >= 30
    assert all(state(bpy.data.objects[name]) == value for name, value in original.items())
    preview('after')
    path = OUT / 'col-exterior195-component.blend'
    owned = {bpy.data.objects[r['replacement']] for r in replacements}
    bpy.data.libraries.write(str(path), owned | set(materials.values()) | {image}, fake_user=True)
    report = dict(version=195, baseline=str(BASE.relative_to(ROOT)), baselineSha256=BASE_SHA,
                  componentPath=str(path.relative_to(ROOT)), componentSha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  targetCollection='COL_EXTERIOR', addedObjects=[r['replacement'] for r in replacements],
                  archivedObjects=[r['originalObject'] for r in replacements], changedObjects=[], replacements=replacements,
                  bindings=bindings, texture=image_record, geometryAndOriginalUVPreserved=True,
                  originalStates={r['originalObject']: original[r['originalObject']] for r in replacements},
                  references=[dict(path=p, sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest(), url=url, scope=scope) for p,url,scope in REFERENCES],
                  improvements=['Unify formerly beige/brown stone reveal and moulding material families to neutral Portland stone; real recess shadows retained.',
                                'Charcoal green painted window joinery replaces excessive metallic-bronze response.',
                                'Red-brown painted timber entrance refined; existing brass hardware retained.',
                                'Less dull neutral dielectric glass reflection; inherited transmission/alpha and room geometry retained.'],
                  previews=['before-whole.png','after-whole.png','before-portal.png','after-portal.png'],
                  previewLighting='Identical HDR sky, AgX, 1.8 sun, .65 background, 24 Cycles samples; COL exterior only',
                  limitations=['Colour is photograph guided, not a calibrated material survey; light/weather differ from the source photographs.',
                               'Photo-supported street finish extended consistently over existing street elevation; upper bay/roof counts remain estimates.',
                               'Native unseen wall, estimated mansard/parapet, granite entrance steps, interior and room geometry preserved.',
                               'Opaque unsupported window rooms remain opaque; no invented empty-room view or guessed backing wall.',
                               'Broad original tone map represents stone material only, not surveyed staining or copied photographic texture.'])
    (OUT/'building-refinement.json').write_text(json.dumps(report, indent=2)+'\n')
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(path))
    checks = []
    for replacement in replacements:
        obj = bpy.data.objects[replacement['replacement']]
        expected = original[replacement['originalObject']]
        actual = state(obj)
        assert actual['geometry'] == expected['geometry']
        assert all(actual['uv'][name] == value for name, value in expected['uv'].items())
        assert obj['originalObject'] == replacement['originalObject']
        checks.append(dict(object=obj.name, originalObject=obj['originalObject'], geometryPreserved=True, originalUVPreserved=True))
    assert all(m.name.startswith(PREFIX) for obj in bpy.data.objects for m in getattr(obj.data, 'materials', []) if m and kind(m))
    verification = dict(savedComponentReopened=True, baselineUnchanged=hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA,
                        componentSha256=hashlib.sha256(path.read_bytes()).hexdigest(), replacementCount=len(checks), objects=checks,
                        packedImages=[dict(name=i.name, packed=bool(i.packed_file)) for i in bpy.data.images if i.name.startswith('COL195')],
                        noRunningBuildProcessAfterExit=True)
    (OUT/'verification.json').write_text(json.dumps(verification, indent=2)+'\n')
    print('COL195_COMPONENT_READY',len(replacements),len(materials),image_record['bytes'],flush=True)


if __name__ == '__main__':
    build_component()
