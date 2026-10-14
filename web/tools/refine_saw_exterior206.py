"""Restore SAW's photograph-supported glazing while retaining native geometry.

Run with Blender. This produces an independent component and never saves over
source205. Glass optical values are daylight visual estimates, not measured data.
"""
from pathlib import Path
import array
import hashlib
import json
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/saw-exterior206'
BASE = ROOT / 'result/blender/LSE_campus_detailed_v205.blend'
SOURCE_SHA = 'bd8171002dda80d4228b99ded708b1a31da4645d333b518fd10125d8b3278a7a'
COMPONENT = OUT / 'saw-exterior206-component.blend'
COLLECTION = 'SAW_EXTERIOR'
FAMILIES = ['north_fold', 'central_return', 'south_fold', 'glazed_notch_return']
SOURCES = ['SAW_EXTERIOR166_' + family + '_single_panes' for family in FAMILIES]
SOURCES += ['SAW_D5_roof83_lower_roof_glazing', 'SAW_D5_roof83_upper_roof_glazing']
NAMES = ['SAW206_' + family + '_clear_glazing' for family in FAMILIES]
NAMES += ['SAW206_lower_roof_clear_glazing', 'SAW206_upper_roof_clear_glazing']
NORMALS = [(0.959556818, .281515121, 0), (.717579722, -.696476400, 0),
           (.980894029, -.194542423, 0), (-.351933032, -.936025143, 0)]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def geometry(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        for data, field, kind, count in [(obj.data.vertices, 'co', 'f', 3),
                                          (obj.data.loops, 'vertex_index', 'i', 1),
                                          (obj.data.polygons, 'material_index', 'i', 1)]:
            values = array.array(kind, [0]) * (len(data) * count)
            data.foreach_get(field, values)
            digest.update(values.tobytes())
        for layer in obj.data.uv_layers:
            values = array.array('f', [0]) * (len(layer.data) * 2)
            layer.data.foreach_get('uv', values)
            digest.update(values.tobytes())
        digest.update(str([(p.loop_total, p.use_smooth) for p in obj.data.polygons]).encode())
        digest.update(str([(m.name, m.type) for m in obj.modifiers]).encode())
    return digest.hexdigest()


def optics(material):
    shader = material.node_tree.nodes.get('Principled BSDF')
    result = {key: list(shader.inputs[key].default_value) if key == 'Base Color'
              else float(shader.inputs[key].default_value)
              for key in ['Base Color', 'Metallic', 'Roughness', 'Transmission Weight', 'Alpha', 'IOR']}
    result['webOpacity'] = material.get('webOpacity')
    return result


def render_views(label):
    scene = bpy.context.scene
    retained = set(bpy.data.collections[COLLECTION].all_objects)
    retained |= set(bpy.data.collections['SAW_PUBLIC_INTERIOR_study'].all_objects)
    for obj in bpy.data.objects:
        if obj.type in {'MESH', 'FONT', 'CURVE'} and obj not in retained:
            obj.hide_render = True
        if obj.type == 'LIGHT':
            obj.hide_render = True
    world = bpy.data.worlds.new('SAW206_preview_world')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (.62, .68, .76, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .7
    scene.world = world
    light_data = bpy.data.lights.new('SAW206_preview_light', 'AREA')
    light_data.energy = 5000
    light_data.size = 35
    light = bpy.data.objects.new(light_data.name, light_data)
    scene.collection.objects.link(light)
    light.location = (-20, -25, 55)
    light.rotation_euler = (Vector((-65, 10, 14)) - light.location).to_track_quat('-Z', 'Y').to_euler()
    camera_data = bpy.data.cameras.new('SAW206_preview_camera')
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera_data.type = 'ORTHO'
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 900
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    for view, focus, position, scale in [
        ('whole', (-65, 12, 13), (-6, -54, 36), 70),
        ('entrance', (-57, 8, 4), (-29, -26, 13), 27),
        ('roof', (-65, 17, 22), (-30, 50, 38), 37),
    ]:
        camera.location = position
        camera.rotation_euler = (Vector(focus) - camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera_data.ortho_scale = scale
        scene.render.filepath = str(OUT / (label + '-' + view + '.png'))
        bpy.ops.render.render(write_still=True)


def build_component():
    OUT.mkdir(exist_ok=True)
    assert sha(BASE) == SOURCE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    originals = {obj.name: geometry(obj) for obj in bpy.data.objects}
    source_geometry = {name: originals[name] for name in SOURCES}
    source_optics = {name: optics(bpy.data.objects[name].data.materials[0]) for name in SOURCES}
    assert all(source_optics[name]['Transmission Weight'] == 0 for name in SOURCES[-2:])
    visible = {name: [bpy.data.objects[name].hide_render, bpy.data.objects[name].hide_viewport,
                      bpy.data.objects[name].hide_get()] for name in SOURCES}
    assert all(not state[0] for state in visible.values())
    owned = []
    changes = []
    for source, name in zip(SOURCES, NAMES):
        original = bpy.data.objects[source]
        assert original.parent is None, source
        clone = original.copy()
        clone.data = original.data.copy()
        clone.name = name
        clone.data.name = name
        bpy.data.collections[COLLECTION].objects.link(clone)
        material = original.data.materials[0].copy()
        material.name = name + '_dielectric'
        shader = material.node_tree.nodes['Principled BSDF']
        # Near-neutral substrate lets the photographed sky and interior supply
        # their own colour; old dark teal artificially coloured transmission.
        shader.inputs['Base Color'].default_value = (.78, .83, .84, 1)
        shader.inputs['Transmission Weight'].default_value = .92
        shader.inputs['Roughness'].default_value = .10
        shader.inputs['Metallic'].default_value = 0
        shader.inputs['IOR'].default_value = 1.5
        shader.inputs['Alpha'].default_value = 1
        material.diffuse_color = (.78, .83, .84, 1)
        material['webOpacity'] = .55 if source in SOURCES[:4] else .62
        material['opticsBasis'] = 'Neutral dielectric daylight estimate from archived SAW built photos; no measured transmittance.'
        clone.data.materials[0] = material
        assert geometry(clone) == source_geometry[source]
        owned.append(clone)
        changes.append(dict(source=source, owned=name, collection=COLLECTION, retainNewMaterials=True,
                            sourceGeometrySha256=source_geometry[source], sourceOptics=source_optics[source],
                            material=optics(material), sourceFaces=len(original.data.polygons)))
    assert all(geometry(bpy.data.objects[name]) == value for name, value in originals.items())
    bpy.data.libraries.write(str(COMPONENT), set(owned), fake_user=True, compress=True)
    refs = [
        ('data/collections/saw-roof-2026/lse-roof.jpg',
         'https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/development-projects/saw/breeam'),
        ('data/collections/materials/originals/saw_ehsmith_image_04.jpg',
         'https://ehsmithclayproducts.co.uk/case_studies/saw-swee-hock-building/'),
        ('data/collections/exteriors/images/saw_archdaily_022.jpg',
         'https://www.archdaily.com/555540/lse-saw-hock-student-centre-o-donnell-tuomey-architects'),
    ]
    audit = dict(baseline=str(BASE.relative_to(ROOT)), baselineSha256=SOURCE_SHA,
                 component=str(COMPONENT.relative_to(ROOT)), componentSha256=sha(COMPONENT),
                 ownedObjects=NAMES, addedObjects=NAMES, archivedObjects=SOURCES,
                 changes=changes, destinationCollection=COLLECTION, sourceCollection=COLLECTION,
                 retainNewMaterials=True, originalVisibility=visible, sourceGeometry=source_geometry,
                 originalObjectCount=len(originals), allOriginalGeometryPreserved=True,
                 originalGeometryAggregateSha256=hashlib.sha256(json.dumps(originals, sort_keys=True).encode()).hexdigest(),
                 sourceReferences=[dict(local=path, sha256=sha(ROOT / path), url=url, captureDate='unknown') for path, url in refs],
                 currentOfficialCheck='Official LSE SAW Estates page rechecked2026-10-15; historical building opened2014. Images are as-built archival references, not a current interior survey.',
                 improvement='Opaque terrace glazing restored to dielectric glass; dark teal curtain absorption neutralized so existing interior and sky reflections remain visible.',
                 limitations=['Optical values are visually estimated and not measured glass specifications.',
                              'No new interiors, doors, furniture, floor enclosure or facade dimensions were invented.',
                              'July2026 Estates newsletter schedules Three Tuns refurbishment; no completion or current bar interior is asserted.',
                              'All six pane meshes, UVs, normals, bounds, face counts and transforms retained exactly.',
                              'Brick screens, mortar, masonry, roof/PV geometry, frames and every other building are unchanged.',
                              'Web opacity is retained for existing curtain families; final web appearance needs integrator verification.'])
    (OUT / 'audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    print('SAW206_COMPONENT_SAVED', audit['componentSha256'], flush=True)


if __name__ == '__main__':
    build_component()
    bpy.ops.wm.quit_blender()
