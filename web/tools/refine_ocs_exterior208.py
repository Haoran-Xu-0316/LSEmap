"""Correct OCS restoration colours while preserving every accepted surface.

Open in Blender's Text Editor. Roof tile and green joinery colours are visual
estimates from the restoration team's photographs, not measured reflectance.
No source photograph pixels enter the component or published assets.
"""
from pathlib import Path
import array, hashlib, json, sys
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'result/blender/LSE_campus_detailed_v207.blend'
BASE_SHA = '44a0b2f09a6a13bbb9532e3a75e415aea7798bef63798e62036bbceb89ded7b0'
OUT = ROOT / 'result/blender/ocs-exterior208'
COMPONENT = OUT / 'ocs-exterior208-component.blend'
COLLECTION = 'OCS_EXTERIOR'
TILE_COLOR = (.25, .14, .115)
TILE_FACTORS = (.94, .96, .98, 1, 1.02, 1.04, 1.06, 1.08)
GREEN_COLOR = (.045, .055, .034)
sys.path.insert(0, str(ROOT / 'web/tools'))
from integrate_exterior_round194 import object_fingerprint, set_layer_hidden
from refine_portsmouth_exterior207 import material_fingerprint


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def surface_fingerprint(obj):
    """All geometry, UVs, normals and face bindings, excluding material names."""
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    for items, field, kind, size in [(obj.data.vertices, 'co', 'f', 3),
                                   (obj.data.vertices, 'normal', 'f', 3),
                                   (obj.data.loops, 'vertex_index', 'i', 1),
                                   (obj.data.polygons, 'material_index', 'i', 1),
                                   (obj.data.polygons, 'loop_total', 'i', 1)]:
        buffer = array.array(kind, [0]) * (len(items) * size)
        items.foreach_get(field, buffer)
        digest.update(buffer.tobytes())
    for layer in obj.data.uv_layers:
        buffer = array.array('f', [0]) * (len(layer.data) * 2)
        layer.data.foreach_get('uv', buffer)
        digest.update(layer.name.encode() + buffer.tobytes())
    return digest.hexdigest()


def render_view(label):
    scene = bpy.data.scenes.new('OCS208_REVIEW_' + label)
    scene.collection.children.link(bpy.data.collections[COLLECTION])
    bpy.context.window.scene = scene
    world = bpy.data.worlds.new('OCS208_WORLD_' + label)
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.68, .74, .80, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = .7
    scene.world = world
    sun = bpy.data.objects.new('OCS208_SUN', bpy.data.lights.new('OCS208_SUN', 'SUN'))
    sun.data.energy = 2
    sun.data.angle = .2
    sun.rotation_euler = (.4, -.5, -.1)
    camera = bpy.data.objects.new('OCS208_CAMERA', bpy.data.cameras.new('OCS208_CAMERA'))
    scene.collection.objects.link(sun)
    scene.collection.objects.link(camera)
    camera.location = (-46.5, 29, 11)
    target = Vector((-42.64, 43.08, 3.6))
    camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 12
    camera.data.clip_end = 100
    scene.camera = camera
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'AgX'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(OUT / (label + '-whole.png'))
    bpy.ops.render.render(write_still=True)
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    for obj in [sun, camera]:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.scenes.remove(scene)


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    assert sha(BASE) == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()
    originals = {o.name: object_fingerprint(o) for o in bpy.data.objects}
    original_materials = {m.name: material_fingerprint(m) for m in bpy.data.materials}
    original_visibility = {o.name: o.hide_render for o in bpy.data.objects}
    render_view('before')
    replacements = {}
    for index, factor in enumerate(TILE_FACTORS):
        source = bpy.data.materials['OCS_D3_clay_tile_' + str(index)]
        color = tuple(value * factor for value in TILE_COLOR)
        replacements[source.name] = (source, color, 'roof_tile_' + str(index))
    source = bpy.data.materials['OCS_V81_deep_green_timber']
    replacements[source.name] = (source, GREEN_COLOR, 'olive_green_joinery')
    palette = {}
    for source_name, (source, color, label) in replacements.items():
        material = source.copy()
        material.name = 'OCS208_' + label
        node = material.node_tree.nodes['Principled BSDF']
        assert not node.inputs['Base Color'].is_linked
        node.inputs['Base Color'].default_value = (*color, 1)
        material.diffuse_color = (*color, 1)
        material['colorBasis'] = 'Photograph-guided2023restoration palette, not measured reflectance or2026condition'
        palette[source_name] = material
    retained_materials = {}
    added, archived, changes = [], [], []
    for source in list(bpy.data.collections[COLLECTION].all_objects):
        if source.type != 'MESH' or source.hide_render:
            continue
        used_slots = {face.material_index for face in source.data.polygons}
        slots = [i for i, m in enumerate(source.data.materials) if i in used_slots and m and m.name in palette]
        if not slots:
            continue
        owned = source.copy()
        owned.data = source.data.copy()
        owned.name = 'OCS208_' + source.name.removeprefix('OCS_')
        owned['originalObject'] = source.name
        bpy.data.collections[COLLECTION].objects.link(owned)
        for index, material in enumerate(source.data.materials):
            if not material:
                continue
            if index in slots:
                owned.data.materials[index] = palette[material.name]
            else:
                # Appending a component must not import a second material with
                # an existing native name and silently suffix its identifier.
                if material.name not in retained_materials:
                    copied = material.copy()
                    copied.name = 'OCS208_retained_' + material.name
                    retained_materials[material.name] = copied
                owned.data.materials[index] = retained_materials[material.name]
        assert surface_fingerprint(owned) == surface_fingerprint(source)
        added.append(owned.name)
        archived.append(source.name)
        changes.append(dict(source=source.name, target=owned.name, slots=slots,
                            surfaceFingerprint=surface_fingerprint(source)))
    assert len(palette) == 9 and len(added) > 20
    assert all(object_fingerprint(bpy.data.objects[name]) == value for name, value in originals.items())
    states = {name: object_fingerprint(bpy.data.objects[name]) for name in added}
    bpy.data.libraries.write(str(COMPONENT), {bpy.data.objects[name] for name in added}, fake_user=True, compress=True)
    audit = dict(version=208, baseline=str(BASE.relative_to(ROOT)), baselineSha256=BASE_SHA,
                 componentPath=str(COMPONENT.relative_to(ROOT)), componentSha256=sha(COMPONENT),
                 targetCollection=COLLECTION, addedObjects=added, archivedObjects=archived, changedObjects=[],
                 changes=changes, palette=[dict(source=name, target=palette[name].name,
                                               before=list(replacements[name][0].diffuse_color),
                                               after=list(palette[name].diffuse_color)) for name in palette],
                 sourceUrls=['https://www.ayesa.com/en/projects/the-old-curiosity-shop/'],
                 references=[dict(path=str(path), sha256=sha(ROOT/path)) for path in [
                     Path('data/collections/exterior_photos_round4/images/OCS/OCS_ayesa_9.jpg'),
                     Path('data/collections/exterior_photos_round4/images/OCS/OCS_sykes_complete_1.png')]],
                 sourcePeriod='September2021-June2023restoration; exact photo dates unknown',
                 scope='Reduce bright orange tile contrast toward red-brown handmade tiles; bring the near-black blue-green shopfront toward photographed dark olive green. Keep roof shape, openings, glass optics and interiors.',
                 limitations=['Visual colour estimates, no calibrated reflectance or2026paint survey.',
                              'Existing roof outline and curved historical silhouette still require independent geometric registration.',
                              'Unseen elevations, full current interior and all other buildings retained.'])
    (OUT/'audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    with bpy.data.libraries.load(str(COMPONENT), link=False) as (_, target):
        target.objects = list(added)
    for obj in target.objects:
        bpy.data.collections[COLLECTION].objects.link(obj)
        assert object_fingerprint(obj) == states[obj.name], obj.name
    for name in archived:
        bpy.data.objects[name].hide_render = True
        set_layer_hidden(bpy.data.objects[name], True)
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()
    for record in changes:
        assert surface_fingerprint(bpy.data.objects[record['target']]) == record['surfaceFingerprint']
    assert all(object_fingerprint(bpy.data.objects[name]) == value for name, value in originals.items())
    assert all(material_fingerprint(bpy.data.materials[name]) == value for name, value in original_materials.items())
    assert all(bpy.data.objects[name].hide_render == hidden for name, hidden in original_visibility.items() if name not in archived)
    assert set(bpy.data.objects.keys()) - set(originals) == set(added)
    render_view('after')
    proof = dict(savedComponentReopened=True, componentSha256=sha(COMPONENT), baselineUnchanged=sha(BASE)==BASE_SHA,
                 originalObjectsVerified=len(originals), originalMaterialsVerified=len(original_materials),
                 originalGeometryUvMaterialBindingsUnchanged=True, replacementSurfacePreserved=True,
                 glassGeometryOpticsAndInteriorUnchanged=True, unrelatedVisibilityPreserved=True,
                 changedColorMaterials=9, retainedMaterialCopies=len(retained_materials), addedObjects=added, archivedObjects=archived)
    (OUT/'verification.json').write_text(json.dumps(proof, indent=2)+'\n')
    print('OCS208_COMPONENT_VERIFIED', len(added), sha(COMPONENT), flush=True)


if __name__ == '__main__':
    run()
