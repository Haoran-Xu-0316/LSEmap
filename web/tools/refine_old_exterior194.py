"""Photo-guided OLD limestone finish, preserving all geometry and existing UVs.

Run in Blender's Text Editor. The material map is an original periodic paint
study, not a photograph, measured colour chart, weathering survey or geometry
reconstruction. Output is a standalone component; the accepted campus stays intact.
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
BASE = ROOT / 'result/blender/LSE_campus_detailed_v193.blend'
OUT = ROOT / 'result/blender/old-exterior194'
PREFIX = 'OLD194_STONE_'
UV_NAME = 'StoneFinish194'
REFERENCE_PATHS = (
    'data/collections/old-exterior-2026/user-references/houghton-arch-masonry.png',
    'data/collections/old-exterior-2026/user-references/houghton-entrance-latest.png',
    'data/collections/old-clare-reference/front.png',
)
# Only visible native wall, arch and sculpted limestone families. Paving, granite
# steps, ramp, planter coping, roofs, plaster, glass and painted joinery excluded.
EXCLUDE = ('incision', 'field', 'roof', 'entrance_limestone', 'ACCESS_stone',
           'APPROACH_stone', 'planter', 'joint', 'shadow')


def shape_state(obj):
    """Hash original topology, transforms, normals and every existing UV layer."""
    mesh = obj.data
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    for data, field, kind, count in ((mesh.vertices, 'co', 'f', 3),
                                    (mesh.loops, 'vertex_index', 'i', 1),
                                    (mesh.polygons, 'material_index', 'i', 1)):
        values = array.array(kind, [0]) * (len(data) * count)
        data.foreach_get(field, values)
        digest.update(values.tobytes())
    layers = {}
    for layer in mesh.uv_layers:
        values = array.array('f', [0]) * (len(layer.data) * 2)
        layer.data.foreach_get('uv', values)
        layers[layer.name] = hashlib.sha256(values.tobytes()).hexdigest()
    return dict(geometry=digest.hexdigest(), uv=layers)


def write_stone_map():
    """512px periodic broad tone variation; restrained grain survives mipmaps."""
    size = 512
    y, x = np.mgrid[:size, :size] / size
    # Periodic harmonics avoid tiling edges. Broad tone variation establishes
    # weathered stone rather than dense subpixel speckles or painted mortar.
    broad = (.42 * np.sin(2 * np.pi * (x + 2 * y) + .6)
             + .30 * np.cos(2 * np.pi * (3 * x - y) + 1.2)
             + .18 * np.sin(2 * np.pi * (5 * x + 3 * y) + .2))
    grain = .002 * np.sin(2 * np.pi * (31 * x + 29 * y))
    shade = 1 + .085 * broad + grain
    rgb = np.stack([.823 * shade, .812 * shade, .780 * shade], axis=-1)
    pixels = (np.clip(rgb, 0, 1) * 255).round().astype(np.uint8)
    def chunk(tag, payload):
        return struct.pack('>I', len(payload)) + tag + payload + struct.pack('>I', zlib.crc32(tag + payload))
    raw = b''.join(b'\0' + row.tobytes() for row in pixels)
    encoded = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0))
               + chunk(b'sRGB', b'\0') + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))
    path = OUT / 'old-portland-stone194.png'
    path.write_bytes(encoded)
    image = bpy.data.images.load(str(path), check_existing=False)
    image.name = 'OLD194_Portland_stone_original_paint_study'
    image.colorspace_settings.name = 'sRGB'
    image.pack()
    return image, dict(path=str(path.relative_to(ROOT)), width=size, height=size,
                      colourSpace='sRGB', sha256=hashlib.sha256(encoded).hexdigest(),
                      bytes=len(encoded), licence='Original generated asset; no reference photo pixels used')


def target_material(material):
    name = material.name
    return (('limestone' in name or name.endswith('_stone') or 'arch_limestone' in name)
            and not any(term in name for term in EXCLUDE))


def make_material(source, image):
    material = source.copy()
    material.name = PREFIX + source.name
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    output = nodes.new('ShaderNodeOutputMaterial')
    shader = nodes.new('ShaderNodeBsdfPrincipled')
    shader.inputs['Base Color'].default_value = (1, 1, 1, 1)
    shader.inputs['Metallic'].default_value = 0
    shader.inputs['Roughness'].default_value = .89
    texture = nodes.new('ShaderNodeTexImage')
    texture.image = image
    texture.extension = 'REPEAT'
    texture.interpolation = 'Linear'
    uv = nodes.new('ShaderNodeUVMap')
    uv.uv_map = UV_NAME
    links.new(uv.outputs['UV'], texture.inputs['Vector'])
    links.new(texture.outputs['Color'], shader.inputs['Base Color'])
    links.new(shader.outputs['BSDF'], output.inputs['Surface'])
    material.diffuse_color = (1, 1, 1, 1)
    material['webBaseColorMap'] = True
    material['webBaseColorUV'] = UV_NAME
    material['finishScope'] = 'Photo-guided neutral warm limestone; original periodic tone study, not measured weathering'
    return material


def add_world_stone_uv(obj):
    """Add a dedicated physical-scale projection without touching existing UVs."""
    layer = obj.data.uv_layers.new(name=UV_NAME)
    # Houghton facade axes; Clare faces choose the other projection. 4.5m repeat
    # spans several blocks and follows world positions, avoiding per-object seams.
    axis = Vector((.45541495084762573, .8902792930603027, 0))
    normal = Vector((.8902792930603027, -.45541495084762573, 0))
    for face in obj.data.polygons:
        world_normal = (obj.matrix_world.to_3x3().inverted().transposed() @ face.normal).normalized()
        if abs(world_normal.z) > .65:
            horizontal, vertical = axis, normal
        else:
            horizontal = axis if abs(world_normal.dot(normal)) >= abs(world_normal.dot(axis)) else normal
            vertical = Vector((0, 0, 1))
        for index in face.loop_indices:
            p = obj.matrix_world @ obj.data.vertices[obj.data.loops[index].vertex_index].co
            layer.data[index].uv = (p.dot(horizontal) / 4.5, p.dot(vertical) / 4.5)
    obj.data.uv_layers.active = layer
    layer.active_render = True


def render_comparison(phase, replacements):
    scene = bpy.data.scenes.new('OLD194_REVIEW_' + phase)
    collection = bpy.data.collections.new(scene.name)
    scene.collection.children.link(collection)
    for obj in bpy.data.collections['OLD_EXTERIOR'].all_objects:
        if not obj.hide_render:
            collection.objects.link(obj)
    world = bpy.data.worlds.new(scene.name)
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (.82, .85, .88, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .65
    scene.world = world
    light = bpy.data.lights.new(scene.name + '_sun', 'SUN')
    light.energy = 1.6
    light.angle = .12
    sun = bpy.data.objects.new(light.name, light)
    collection.objects.link(sun)
    sun.rotation_euler = Vector((-.6, .5, -1)).to_track_quat('-Z', 'Y').to_euler()
    camera = bpy.data.cameras.new(scene.name + '_camera')
    cam = bpy.data.objects.new(camera.name, camera)
    collection.objects.link(cam)
    scene.camera = cam
    camera.type = 'ORTHO'
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    frames = {
        'houghton': (Vector((-7.28653, -89.75267, 0)), Vector((.455415, .890279, 0)), Vector((.890279, -.455415, 0)), 0, 7.0, 20.5),
        'clare': (Vector((-6.69891, -37.83887, 0)), Vector((-.891731, .452566, 0)), Vector((.452566, .891731, 0)), 0, 6.0, 19.8),
    }
    for name, (origin, axis, normal, x, z, scale) in frames.items():
        target = origin + axis * x + Vector((0, 0, z))
        cam.location = target + normal * 34 + axis * 2 + Vector((0, 0, 1.8))
        cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
        camera.ortho_scale = scale
        scene.render.filepath = str(OUT / (phase + '-' + name + '.png'))
        bpy.ops.render.render(write_still=True, scene=scene.name)
    bpy.data.scenes.remove(scene)
    bpy.data.collections.remove(collection)


def build_component():
    OUT.mkdir(parents=True, exist_ok=True)
    baseline_sha = hashlib.sha256(BASE.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()
    originals = {o.name: shape_state(o) for o in bpy.data.objects if o.type == 'MESH'}
    original_visibility = {o.name: o.hide_render for o in bpy.data.objects}
    render_comparison('before', [])
    image, image_record = write_stone_map()
    copies, replacements, bindings = {}, [], []
    collection = bpy.data.collections['OLD_EXTERIOR']
    for source in list(collection.all_objects):
        if source.hide_render or source.type != 'MESH' or any(k in source.name.lower() for k in ('roof', 'planter')):
            continue
        slots = [(i, m) for i, m in enumerate(source.data.materials) if m and target_material(m)]
        if not slots:
            continue
        obj = source.copy()
        obj.data = source.data.copy()
        obj.name = PREFIX + source.name
        obj['originalObject'] = source.name
        obj['finishScope'] = 'OLD exterior limestone appearance only; topology, positions, existing UVs, glass and paint retained'
        collection.objects.link(obj)
        add_world_stone_uv(obj)
        for index, material in slots:
            if material.name not in copies:
                copies[material.name] = make_material(material, image)
            obj.data.materials[index] = copies[material.name]
            bindings.append(dict(object=obj.name, slot=index, originalMaterial=material.name, material=copies[material.name].name))
        source.hide_render = True
        source.hide_set(True)
        obj.hide_render = False
        obj.hide_set(False)
        replacements.append(dict(original=source.name, replacement=obj.name, targetCollection='OLD_EXTERIOR'))
        current = shape_state(obj)
        assert current['geometry'] == originals[source.name]['geometry']
        assert all(current['uv'][name] == digest for name, digest in originals[source.name]['uv'].items())
    assert len(replacements) > 20
    assert all(shape_state(bpy.data.objects[name]) == state for name, state in originals.items())
    render_comparison('after', replacements)
    component = OUT / 'old-exterior194-component.blend'
    owned = {bpy.data.objects[item['replacement']] for item in replacements}
    bpy.data.libraries.write(str(component), owned | set(copies.values()) | {image}, fake_user=True)
    report = dict(version=194, baseline=str(BASE.relative_to(ROOT)), baselineSha256=baseline_sha,
                  component=str(component.relative_to(ROOT)), componentSha256=hashlib.sha256(component.read_bytes()).hexdigest(),
                  addedObjects=[r['replacement'] for r in replacements], archivedObjects=[r['original'] for r in replacements],
                  changedObjects=[], replacements=replacements, bindings=bindings, image=image_record,
                  geometryAndOriginalUVPreserved=True, originalObjectStates=originals,
                  originalVisibility={name: original_visibility[name] for name in [r['original'] for r in replacements]},
                  references=[dict(path=p, sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest(), captureDate='unknown') for p in REFERENCE_PATHS],
                  previewLighting='Identical AgX, 1.6 sun, .65 neutral sky; only OLD exterior shown',
                  coordinateSystem='Native world positions unchanged; 4.5m repeating Houghton/Clare plane projection in StoneFinish194',
                  limitations=['Photo-estimated colour and tonal variation are not calibrated colour or a measured weathering map.',
                               'Existing registration, massing, artwork silhouettes, four approach steps and side ramp retained; no claim of surveyed dimensional correctness.',
                               'All room geometry, glass optics, blue frame parameters and former UV layers retained.',
                               'General rooftop geometry and unseen elevations remain evidence limited.'])
    (OUT/'building-refinement.json').write_text(json.dumps(report, indent=2)+'\n')
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == baseline_sha
    print('OLD194_COMPONENT_READY', len(replacements), len(copies), image_record['bytes'], flush=True)


if __name__ == '__main__':
    build_component()
