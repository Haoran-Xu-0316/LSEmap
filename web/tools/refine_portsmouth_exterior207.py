"""Refine the photo-supported Portsmouth entrance corbel and door pull.

Constant configuration for Blender's Text Editor. Source206 is read-only.
Photographs support relative shape and handedness, not measured dimensions.
"""
from pathlib import Path
import array
import hashlib
import json
import sys
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/por-exterior207'
BASE = ROOT / 'result/blender/LSE_campus_detailed_v206.blend'
SOURCE_SHA = '605fc53169bd40b830fa817d7ecb17be2a6d38658236f3d69c9dd48aedc91c78'
COMPONENT = OUT / 'por-exterior207-component.blend'
COLLECTION = 'POR_EXTERIOR'
SOURCES = ['POR_D5_tapered_fascia_support_cream', 'POR_D5_fascia_side_support_cream',
           'POR_D5_door_pull_gold']
NAMES = ['POR207_narrowed_fascia_front', 'POR207_narrowed_fascia_returns',
         'POR207_left_dark_door_pull']
sys.path.insert(0, str(ROOT / 'web/tools'))
from integrate_exterior_round194 import object_fingerprint


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def material_fingerprint(material):
    record = [list(material.diffuse_color), sorted((key, str(material[key])) for key in material.keys())]
    if material.node_tree:
        record += [[node.name, node.type, [(s.name, str(getattr(s, 'default_value', None))) for s in node.inputs]]
                   for node in material.node_tree.nodes]
        record += [[link.from_node.name, link.from_socket.name, link.to_node.name, link.to_socket.name]
                   for link in material.node_tree.links]
    return hashlib.sha256(json.dumps(record).encode()).hexdigest()


def uv_sha(obj):
    digest = hashlib.sha256()
    for uv in obj.data.uv_layers:
        values = array.array('f', [0]) * (len(uv.data) * 2)
        uv.data.foreach_get('uv', values)
        digest.update(values.tobytes())
    return digest.hexdigest()


def render_views(label):
    scene = bpy.data.scenes.new('POR207_REVIEW_' + label)
    scene.collection.children.link(bpy.data.collections[COLLECTION])
    bpy.context.window.scene = scene
    world = bpy.data.worlds.new('POR207_REVIEW_WORLD_' + label)
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.68, .74, .8, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = .7
    scene.world = world
    sun = bpy.data.objects.new('POR207_REVIEW_SUN_' + label,
                              bpy.data.lights.new('POR207_REVIEW_SUN_' + label, 'SUN'))
    scene.collection.objects.link(sun)
    sun.data.energy = 2
    sun.data.angle = .2
    sun.rotation_euler = (.4, -.5, -.1)
    camera = bpy.data.objects.new('POR207_REVIEW_CAMERA_' + label,
                                 bpy.data.cameras.new('POR207_REVIEW_CAMERA_' + label))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = 'ORTHO'
    camera.data.clip_end = 500
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 900
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'AgX'
    scene.render.image_settings.file_format = 'PNG'
    cameras = []
    for name, target, position, scale in [
        ('whole', (-34, 23, 8.5), (-53, 64, 22), 22),
        ('entrance', (-34.5, 27, 2.8), (-42, 46, 6), 7.8),
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
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()
    originals = {obj.name: object_fingerprint(obj) for obj in bpy.data.objects}
    materials = {mat.name: material_fingerprint(mat) for mat in bpy.data.materials}
    visibility = {obj.name: [obj.hide_render, obj.hide_viewport, obj.hide_get()] for obj in bpy.data.objects}
    cameras = render_views('before')
    ring = next(building for building in json.loads((ROOT / 'result/blender/site_geometry.json').read_text())['buildings']
                if building['code'] == 'POR')['rings'][0]
    p, q = Vector((*ring[0], 0)), Vector((*ring[1], 0))
    axis = (q - p).normalized()
    midpoint = (p + q) / 2
    top_width = (q - p).length + .10
    bottom_width = top_width * .40
    owned, changes = [], []
    corbel_material = bpy.data.materials["POR_V51_cream"].copy()
    corbel_material.name = "POR207_native_cream_copy"
    pull_material = bpy.data.materials["POR14_metal"].copy()
    pull_material.name = "POR207_native_dark_metal_copy"
    for source_name, name in zip(SOURCES, NAMES):
        source = bpy.data.objects[source_name]
        assert not source.hide_render and source.parent is None
        clone = source.copy()
        clone.data = source.data.copy()
        clone.name = name
        clone.data.name = name
        clone['originalObject'] = source_name
        clone['webGeometrySource'] = source_name
        clone['destinationCollection'] = COLLECTION
        bpy.data.collections[COLLECTION].objects.link(clone)
        moved = []
        if source_name != SOURCES[-1]:
            clone.data.materials[0] = corbel_material
            for vertex in clone.data.vertices:
                point = clone.matrix_world @ vertex.co
                if abs(point.z - 3.72) < .0001:
                    offset = (point - midpoint).dot(axis)
                    corrected = point + axis * ((1 if offset > 0 else -1) * bottom_width / 2 - offset)
                    vertex.co = clone.matrix_world.inverted() @ corrected
                    moved.append(vertex.index)
        else:
            # In the high-resolution LSE photo the dark pull is on the viewer's
            # left. Native206 puts it on the viewer's right, on the opposite stile.
            for vertex in clone.data.vertices:
                vertex.co += clone.matrix_world.to_3x3().inverted() @ (axis * .70)
                moved.append(vertex.index)
            clone.data.materials[0] = pull_material
        clone.data.update()
        assert uv_sha(clone) == uv_sha(source)
        owned.append(clone)
        changes.append(dict(source=source_name, owned=name, movedVertices=moved,
                            sourceUvSha256=uv_sha(source), retainedUvSha256=uv_sha(clone),
                            materialAliases=[m.name for m in clone.data.materials]))
    assert [len(c['movedVertices']) for c in changes] == [2, 4, 8]
    for name in SOURCES:
        bpy.data.objects[name].hide_render = True
        bpy.data.objects[name].hide_set(True)
    assert all(object_fingerprint(bpy.data.objects[name]) == expected for name, expected in originals.items())
    assert all(material_fingerprint(bpy.data.materials[name]) == expected for name, expected in materials.items())
    component_state = {obj.name: object_fingerprint(obj) for obj in owned}
    bpy.data.libraries.write(str(COMPONENT), set(owned), fake_user=True, compress=True)
    audit = dict(baseline=str(BASE.relative_to(ROOT)), baselineSha256=SOURCE_SHA,
                 component=str(COMPONENT.relative_to(ROOT)), componentSha256=sha(COMPONENT),
                 ownedObjects=NAMES, addedObjects=NAMES, archivedObjects=SOURCES,
                 destinationCollection=COLLECTION, retainNewMaterials=True,
                 materialCopies={"POR207_native_cream_copy": "POR_V51_cream", "POR207_native_dark_metal_copy": "POR14_metal"},
                 originalVisibility={name: visibility[name] for name in SOURCES},
                 changes=changes, cameras=cameras, corbelTopWidth=top_width,
                 corbelOriginalBottomWidth=(q-p).length-.44, corbelNewBottomWidth=bottom_width,
                 lowerToUpperWidthRatio=.40,
                 sourceReferences=[
                     dict(local='data/建筑图片/POR_1 Portsmouth Street/01_建筑实拍/exteriors_lse_estate_024.jpg',
                          sha256=sha(ROOT/'data/建筑图片/POR_1 Portsmouth Street/01_建筑实拍/exteriors_lse_estate_024.jpg'),
                          url='https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Images/LSE-Estate/Portsmouth-Street2.jpg',
                          evidence='As-built archival exterior photo, date unknown; corbel relative silhouette and dark left door pull.'),
                     dict(local='data/collections/portsmouth-2026/gilded-acorn-official.jpg',
                          sha256=sha(ROOT/'data/collections/portsmouth-2026/gilded-acorn-official.jpg'),
                          url='https://info.lse.ac.uk/current-students/estates-division/Assets/Images/Gilded-Acorn.jpg',
                          evidence='Undated built exterior photo; pale shopfront and corner fascia retained.'),
                     dict(local=str((OUT/'retailer-shopfront-reference.jpg').relative_to(ROOT)),
                          sha256=sha(OUT/'retailer-shopfront-reference.jpg'),
                          url='https://thegildedacorn.co.uk/__l5e/assets-v1/d0d50872-866b-41ea-a94a-686756cfad10/gilded-acorn-shopfront.jpg',
                          evidence='Live retailer site image rechecked2026-10-15; pale joinery and transparent shopfront. Photo date unspecified; no doorway shown.')],
                 currentOfficialChecks=['https://info.lse.ac.uk/current-students/estates-division/facilities-guide/shops-banks-and-post-offices',
                                        'https://thegildedacorn.co.uk/'],
                 improvement='Narrow the broad lower corbel neck to the photographed trapezoid and move the dark entrance pull to the photographed left stile.',
                 limitations=['Corbel neck ratio is a photo estimate; existing heights, projection depth and all fascia/door dimensions retained.',
                              'Photo dates are unspecified; no current measured survey is claimed.',
                              'No glass optics, panes, normals, backing or interiors changed; webOpacity0.82 is retained.',
                              'No roof, wall, window, signage, shopfront divisions or other building changed.'])
    (OUT/'audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    with bpy.data.libraries.load(str(COMPONENT), link=False) as (source, target):
        assert set(source.objects) == set(NAMES)
        target.objects = list(NAMES)
    for obj in target.objects:
        bpy.data.collections[COLLECTION].objects.link(obj)
        assert object_fingerprint(obj) == component_state[obj.name]
        obj.hide_render = False
        obj.hide_set(False)
    for name in SOURCES:
        bpy.data.objects[name].hide_render = True
        bpy.data.objects[name].hide_set(True)
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()
    assert all(object_fingerprint(bpy.data.objects[name]) == expected for name, expected in originals.items())
    assert all(material_fingerprint(bpy.data.materials[name]) == expected for name, expected in materials.items())
    assert all([bpy.data.objects[name].hide_render, bpy.data.objects[name].hide_viewport, bpy.data.objects[name].hide_get()] == state
               for name, state in visibility.items() if name not in SOURCES)
    assert set(bpy.data.objects.keys()) - set(originals) == set(NAMES)
    render_views('after')
    verification = dict(savedComponentReopened=True, componentSha256=sha(COMPONENT), baselineSha256=sha(BASE),
                        baselineUnchanged=sha(BASE)==SOURCE_SHA, originalObjectsVerified=len(originals),
                        originalGeometryUvMaterialBindingsUnchanged=True, originalMaterialsVerified=len(materials),
                        unrelatedVisibilityPreserved=True, onlyThreeNativeAliases=True,
                        exactAddedObjects=NAMES, exactArchivedObjects=SOURCES,
                        replacementUvPreserved=True, replacementFingerprints=component_state,
                        glassGeometryNormalsBackingOpticsUnchanged=True,
                        renderedBeforeAfterWholeAndEntrance=True)
    (OUT/'verification.json').write_text(json.dumps(verification, indent=2)+'\n')
    print('POR207_VERIFIED', audit['componentSha256'], flush=True)


if __name__ == '__main__':
    run()
    bpy.ops.wm.quit_blender()
