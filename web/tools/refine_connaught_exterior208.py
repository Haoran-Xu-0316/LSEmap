"""Correct the isolated yellow cast of Connaught's entrance granite.

Run in Blender's Text Editor. The source207 file is read-only. The undated
300x400px official entrance photograph supports grey granite below pale stone,
not calibrated colour, full elevations, roof geometry or a current survey.
"""
from pathlib import Path
import hashlib
import json
import sys
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/con-exterior208'
BASE = ROOT / 'result/blender/LSE_campus_detailed_v207.blend'
SOURCE_SHA = '44a0b2f09a6a13bbb9532e3a75e415aea7798bef63798e62036bbceb89ded7b0'
COMPONENT = OUT / 'connaught-exterior208-component.blend'
COLLECTION = 'CON_EXTERIOR'
SOURCE = 'CON_D5_vestibule68_granite'
ADDED = 'CON208_neutral_gray_entrance_granite'
sys.path.insert(0, str(ROOT / 'web/tools'))
from integrate_exterior_round194 import object_fingerprint, update_scene, set_layer_hidden
from refine_portsmouth_exterior207 import material_fingerprint, uv_sha


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_views(label):
    scene = bpy.data.scenes.new('CON208_REVIEW_' + label)
    scene.collection.children.link(bpy.data.collections[COLLECTION])
    bpy.context.window.scene = scene
    scene.world = bpy.data.worlds.new('CON208_REVIEW_WORLD_' + label)
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes['Background']
    background.inputs[0].default_value = (.68, .74, .8, 1)
    background.inputs[1].default_value = .7
    sun = bpy.data.objects.new('CON208_REVIEW_SUN_' + label,
                              bpy.data.lights.new('CON208_REVIEW_SUN_' + label, 'SUN'))
    scene.collection.objects.link(sun)
    sun.data.energy = 2
    sun.data.angle = .2
    sun.rotation_euler = (.4, -.5, -.1)
    camera = bpy.data.objects.new('CON208_REVIEW_CAMERA_' + label,
                                 bpy.data.cameras.new('CON208_REVIEW_CAMERA_' + label))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = 'ORTHO'
    camera.data.clip_end = 500
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 800
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'AgX'
    scene.render.image_settings.file_format = 'PNG'
    cameras = []
    for name, target, position, scale in [
        ('whole', (-19, -115, 14), (-6, -175, 41), 52),
        ('entrance', (-16.178358, -130.222015, 2.6), (-15.132238, -141.201355, 4.4), 6.7),
    ]:
        camera.location = position
        camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera.data.ortho_scale = scale
        scene.render.filepath = str(OUT / (label + '-' + name + '.png'))
        bpy.ops.render.render(write_still=True)
        cameras.append(dict(view=name, target=target, position=position, orthoScale=scale))
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    for obj in (camera, sun):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.scenes.remove(scene)
    return cameras


def run():
    OUT.mkdir(exist_ok=True)
    assert sha(BASE) == SOURCE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    originals = {obj.name: object_fingerprint(obj) for obj in bpy.data.objects}
    materials = {mat.name: material_fingerprint(mat) for mat in bpy.data.materials}
    visibility = {obj.name: [obj.hide_render, obj.hide_viewport, obj.hide_get()] for obj in bpy.data.objects}
    cameras = render_views('before')
    source = bpy.data.objects[SOURCE]
    assert not source.hide_render and source.parent is None
    assert len(source.data.materials) == 1
    old_material = source.data.materials[0]
    assert old_material.name == 'CON_V68_granite'
    clone = source.copy()
    clone.data = source.data.copy()
    clone.name = ADDED
    clone.data.name = ADDED
    clone['originalObject'] = SOURCE
    clone['webGeometrySource'] = SOURCE
    clone['destinationCollection'] = COLLECTION
    material = old_material.copy()
    material.name = 'CON208_neutral_gray_granite'
    # Match the already accepted cool-neutral adjacent granite family. This
    # fixes the doorway's isolated ochre cast without recolouring limestone.
    material.diffuse_color = (.40, .415, .425, 1)
    shader = material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = material.diffuse_color
    ramp = next(node for node in material.node_tree.nodes if node.type == 'VALTORGB')
    before_ramp = [list(element.color) for element in ramp.color_ramp.elements]
    for element, color in zip(ramp.color_ramp.elements,
                              [(.35, .365, .375, 1), (.45, .465, .475, 1)]):
        element.color = color
    clone.data.materials[0] = material
    bpy.data.collections[COLLECTION].objects.link(clone)
    update_scene()
    source.hide_render = True
    set_layer_hidden(source, True)
    assert uv_sha(clone) == uv_sha(source)
    assert all(object_fingerprint(bpy.data.objects[name]) == expected for name, expected in originals.items())
    assert all(material_fingerprint(bpy.data.materials[name]) == expected for name, expected in materials.items())
    component_state = {ADDED: object_fingerprint(clone)}
    bpy.data.libraries.write(str(COMPONENT), {clone}, fake_user=True, compress=True)
    reference = ROOT / 'data/collections/exteriors/images/lse_estate_005.jpg'
    audit = dict(baseline=str(BASE.relative_to(ROOT)), baselineSha256=SOURCE_SHA,
                 component=str(COMPONENT.relative_to(ROOT)), componentSha256=sha(COMPONENT),
                 ownedObjects=[ADDED], addedObjects=[ADDED], archivedObjects=[SOURCE],
                 destinationCollection=COLLECTION, retainNewMaterials=True,
                 materialCopies={material.name: old_material.name},
                 originalVisibility={SOURCE: visibility[SOURCE]}, cameras=cameras,
                 sourceReferences=[dict(local=str(reference.relative_to(ROOT)), sha256=sha(reference),
                     url='https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Images/LSE-Estate/Connaught-web.jpg',
                     page='https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate',
                     photoDate='unknown', dimensions=[300, 400], checkedDate='2026-10-15',
                     evidence='Grey lower granite distinct from pale limestone above; no full elevation verification.')],
                 change=dict(source=SOURCE, owned=ADDED, sourceColor=list(old_material.diffuse_color),
                             newColor=list(material.diffuse_color), oldRamp=before_ramp,
                             newRamp=[list(element.color) for element in ramp.color_ramp.elements],
                             adjacentReferenceMaterial='CON_V30_fine_grey_granite',
                             retainedUvSha256=uv_sha(clone)),
                 scope='Single dedicated entrance casing material: remove yellow cast and align with existing grey lower frontage. No new transparency or geometry.',
                 limitations=['Undated low-resolution official photograph; not a calibrated colour survey or verified current2026 facade.',
                              'The existing3.12m granite-to-limestone height is estimated and retained.',
                              'All glass optics, nodes, geometry, backing, window joinery and interior studies remain unchanged.',
                              'Unseen upper elevations and roof remain unresolved; no unsupported shape changes.'])
    (OUT / 'audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    with bpy.data.libraries.load(str(COMPONENT), link=False) as (src, dst):
        assert src.objects == [ADDED]
        dst.objects = [ADDED]
    bpy.data.collections[COLLECTION].objects.link(dst.objects[0])
    update_scene()
    dst.objects[0].hide_render = False
    set_layer_hidden(dst.objects[0], False)
    bpy.data.objects[SOURCE].hide_render = True
    set_layer_hidden(bpy.data.objects[SOURCE], True)
    assert object_fingerprint(dst.objects[0]) == component_state[ADDED]
    assert all(object_fingerprint(bpy.data.objects[name]) == expected for name, expected in originals.items())
    assert all(material_fingerprint(bpy.data.materials[name]) == expected for name, expected in materials.items())
    assert all([bpy.data.objects[name].hide_render, bpy.data.objects[name].hide_viewport, bpy.data.objects[name].hide_get()] == state
               for name, state in visibility.items() if name != SOURCE)
    assert set(bpy.data.objects.keys()) - set(originals) == {ADDED}
    render_views('after')
    verification = dict(savedComponentReopened=True, baselineSha256=sha(BASE),
                        baselineUnchanged=sha(BASE)==SOURCE_SHA, componentSha256=sha(COMPONENT),
                        originalObjectsVerified=len(originals), originalMaterialsVerified=len(materials),
                        originalGeometryUvMaterialBindingsUnchanged=True, unrelatedVisibilityPreserved=True,
                        exactAddedObjects=[ADDED], exactArchivedObjects=[SOURCE],
                        replacementUvPreserved=True, replacementFingerprints=component_state,
                        glassGeometryNormalsBackingOpticsUnchanged=True,
                        renderedBeforeAfterWholeAndEntrance=True)
    (OUT / 'verification.json').write_text(json.dumps(verification, indent=2)+'\n')
    print('CON208_VERIFIED', audit['componentSha256'], flush=True)


if __name__ == '__main__':
    run()
    bpy.ops.wm.quit_blender()
