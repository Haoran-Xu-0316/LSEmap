"""Read-only LRB219 evidence review against the accepted complete campus.

Open in Blender's Text Editor and run. Fixed configuration and no command-line
interface. No component is manufactured unless new, registered evidence proves
an independent correction. This review never saves the campus native.
"""
from pathlib import Path
import hashlib
import json
import sys
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'result/blender/LSE_campus_detailed_v218.blend'
SHA = 'd57142ea7dce27ea052bbd508f63dcd8c15136faccc132ac4f5915dff64fe27d'
OUT = ROOT / 'result/blender/lrb-exterior219'
sys.path.insert(0, str(ROOT / 'web/tools'))
from integrate_exterior_round194 import accepted_fingerprints, object_fingerprint
from refine_portsmouth_exterior207 import material_fingerprint


def update():
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()


def rna_value(value, depth=0):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bpy.types.ID):
        return dict(idType=value.bl_rna.identifier, name=value.name)
    if depth > 6:
        return value.bl_rna.identifier
    result = {}
    for prop in value.bl_rna.properties:
        if prop.identifier == 'rna_type':
            continue
        item = getattr(value, prop.identifier)
        if prop.type == 'COLLECTION':
            item = [rna_value(child, depth + 1) for child in item]
        elif prop.type == 'POINTER':
            item = rna_value(item, depth + 1)
        elif getattr(prop, 'is_array', False):
            item = list(item)
        result[prop.identifier] = item
    return result


def modifier_state(obj):
    values = [rna_value(modifier) for modifier in obj.modifiers]
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def snapshot():
    metadata = json.loads((ROOT / 'web/tools/building-metadata.json').read_text())
    rooms = {space['collection']: sorted(obj.name for obj in bpy.data.collections[space['collection']].all_objects)
             for space in metadata['spaces']}
    assert len(rooms) == 18 and len(set().union(*(set(values) for values in rooms.values()))) == 623
    return dict(objects={obj.name: object_fingerprint(obj) for obj in bpy.data.objects},
                materials={material.name: material_fingerprint(material) for material in bpy.data.materials},
                modifiers={obj.name: modifier_state(obj) for obj in bpy.data.objects},
                visibility={obj.name: obj.hide_render for obj in bpy.data.objects}, rooms=rooms)


def inspect_glazing():
    rows = []
    for obj in bpy.data.collections['LRB_EXTERIOR'].all_objects:
        if obj.type != 'MESH' or obj.hide_render:
            continue
        if not any('glass' in material.name.lower() or 'glazing' in material.name.lower()
                   for material in obj.data.materials if material):
            continue
        materials = []
        for material in obj.data.materials:
            shader = next((node for node in material.node_tree.nodes if node.type == 'BSDF_PRINCIPLED'), None)
            if shader:
                materials.append(dict(name=material.name, color=list(shader.inputs['Base Color'].default_value),
                                      metallic=float(shader.inputs['Metallic'].default_value),
                                      roughness=float(shader.inputs['Roughness'].default_value),
                                      alpha=float(shader.inputs['Alpha'].default_value),
                                      transmission=float(shader.inputs['Transmission Weight'].default_value),
                                      webOpacity=material.get('webOpacity'), webClosedGlazing=material.get('webClosedGlazing')))
        rows.append(dict(object=obj.name, polygons=len(obj.data.polygons), materials=materials))
    return rows


def preview():
    scene = bpy.data.scenes.new('LRB219_READONLY_REVIEW')
    scene.collection.children.link(bpy.data.collections['LRB_EXTERIOR'])
    # The accepted public interior is only linked to the temporary review scene.
    scene.collection.children.link(bpy.data.collections['LRB_PUBLIC_INTERIOR168_study'])
    world = bpy.data.worlds.new('LRB219_REVIEW_WORLD')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[1].default_value = .65
    environment = world.node_tree.nodes.new('ShaderNodeTexEnvironment')
    environment.image = bpy.data.images.load(str(ROOT / 'web/public/environment/kloppenheim-daylight-1k.hdr'), check_existing=True)
    world.node_tree.links.new(environment.outputs['Color'], world.node_tree.nodes['Background'].inputs[0])
    scene.world = world
    light = bpy.data.lights.new('LRB219_REVIEW_SUN', 'SUN')
    light.energy, light.angle = 1.8, .12
    sun = bpy.data.objects.new(light.name, light)
    scene.collection.objects.link(sun)
    sun.rotation_euler = Vector((-.6, .5, -1)).to_track_quat('-Z', 'Y').to_euler()
    data = bpy.data.cameras.new('LRB219_REVIEW_CAMERA')
    camera = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    data.type = 'ORTHO'
    data.clip_end = 500
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 1000, 800
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'AgX'
    scene.render.image_settings.file_format = 'PNG'
    views = []
    for label, target, offset, scale in [
        ('plaza-oblique', (70, 7, 13), (-65, -90, 36), 100),
        ('carey-portugal', (73, 8, 13), (70, 80, 31), 100),
    ]:
        target = Vector(target)
        camera.location = target + Vector(offset)
        camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
        data.ortho_scale = scale
        scene.render.filepath = str(OUT / ('accepted218-' + label + '.png'))
        bpy.ops.render.render(write_still=True, scene=scene.name)
        views.append(dict(label=label, target=list(target), camera=list(camera.location), orthoScale=scale))
    bpy.data.scenes.remove(scene)
    for obj in [camera, sun]:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.cameras.remove(data)
    bpy.data.lights.remove(light)
    bpy.data.worlds.remove(world)
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    update()
    return views


def write_audit(verification, glazing, views):
    references = []
    for path, source, capture, support in [
        ('data/collections/library_round5/photos/LRB_5ea4100c9303.jpg',
         'https://tyrensakt.com/projects/lse-library/', 'Unknown;2001 is the project year',
         'Built aerial: brown brick,pale stone bands,dark upper pavilion and north-cut dome'),
        ('data/collections/campus_photos_round3/images/LRB/LRB_LAK_geograph_668683.jpg',
         'https://www.geograph.org.uk/photo/668683', '2008-01-23',
         'Historic plaza daylight: dark joinery,reflective upper windows and pale horizontal stone'),
        ('data/建筑图片/LRB_Lionel Robbins Building_Library/01_建筑实拍/exteriors_lse_estate_016.jpg',
         'https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate', 'Unknown',
         'Official night photograph: brick/stone hierarchy only;no daylight colour calibration'),
        ('data/collections/library-roof-2025/existing-sw-elevation.pdf',
         '4556-FBR-LR-ZZ-DR-A-111 P01,17April2025,As Existing', 'Survey issue date;not photograph date',
         'Watkins Plaza window groups and roof/handrail arrangement;proposals excluded'),
        ('data/collections/library-roof-2025/existing-nw-elevation.pdf',
         '4556-FBR-LR-ZZ-DR-A-114 P01,17April2025,As Existing', 'Survey issue date;not photograph date',
         'Portugal Street triple lights,mansard,ground rail and stone detail;proposals excluded'),
    ]:
        references.append(dict(path=path, sha256=hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),
                               source=source, captureOrDateStatus=capture, support=support))
    report = dict(version=219, status='read-only-no-new-component', readOnly=True,
        baseline=str(BASE.relative_to(ROOT)), baselineSha256=SHA,
        targetCollection='LRB_EXTERIOR', destinationCollection='LRB_EXTERIOR',
        componentPath=None, componentSha256=None, addedObjects=[], archivedObjects=[], changedObjects=[],
        addedFingerprints={}, replacementMaterialBindings={},
        scope='Review accepted218 LRB exterior against archived built photographs and2025 existing elevations',
        decision='Retain accepted196 finish and210 roof. No newly registered,high-impact exterior error is established.',
        findings=[
            'Nine active glazing batches are dielectric:Metallic0. Normal retained proxy glazing remains alpha1/transmission0 with estimated roughness0.13;no optical-category regression found.',
            'The dome north aperture and66 cafe panes retain separate transparent materials and accepted geometry;no new transparent shell or interior is justified.',
            '196 brown brick,pale stone and charcoal joinery remain consistent with archived references. Historical/uncalibrated images do not support an additional numeric recolouring.',
            '210 corrected upper enclosure,window band and safety rails are present in actual218 views. Low-roof rail height and a second plant mass remain outside reliable registration.',
            '2025 Portugal elevation shows further stone ornament and ground rail detail. These remain local modelling limitations;no unregistered linear fence or decorative geometry is manufactured.',
        ],
        quantitativeDifference=dict(addedObjects=0, archivedObjects=0, changedOriginalObjectFingerprints=0,
            changedOriginalMaterialFingerprints=0, changedOriginalModifierFingerprints=0,
            changedRoomMemberships=0, acceptedUpperRoofObjectsChanged=0, sourceNativeBytesChanged=False),
        verification=verification, references=references, views=views,
        previews=['accepted218-plaza-oblique.png','accepted218-carey-portugal.png'],
        drawingPreviews=['existing-sw-elevation.png','existing-nw-elevation.png'],
        limitations=['Read-only review is not a building completion or current2026 condition claim.',
            'Review images are newly rendered from218 native,not reused196/210 images.',
            'No component exists or should be imported from this audit;no shared exporter,metadata,native or room is edited.',
            'Source photos/drawings remain private/local comparison evidence and are not distributed as public texture maps.'])
    (OUT/'audit.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    update()
    before = snapshot()
    expected = accepted_fingerprints(ROOT / 'result/blender/stage218', SHA)
    assert before['objects'] == expected
    assert len(expected) == 7569
    glazing = inspect_glazing()
    views = preview()
    after_preview = snapshot()
    assert before == after_preview
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    update()
    reopened = snapshot()
    assert before == reopened
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == SHA
    verification = dict(acceptedNativeOpenedAndReopened=True, acceptedObjectFingerprintsVerified=len(expected),
                        originalMaterialsVerified=len(before['materials']), allOriginalMaterialNodesUnchanged=True,
                        allOriginalModifiersUnchanged=True, allOriginalTransformsGeometryUVBindingsUnchanged=True,
                        allVisibilityUnchanged=True, protectedRoomCollections=18, protectedRoomObjects=623,
                        roomMembershipsAndObjectStatesUnchanged=True, baselineUnchanged=True)
    (OUT / 'inspection.json').write_text(json.dumps(dict(baselineSha256=SHA, glazing=glazing, views=views,
        lighting='Identical source material rendering: daylight HDR0.65,sun1.8,AgX,Cycles12samples,1000x800',
        verification=verification), indent=2) + '\n')
    (OUT / 'verification.json').write_text(json.dumps(verification, indent=2) + '\n')
    write_audit(verification, glazing, views)
    print('LRB219_READONLY_VERIFIED', len(expected), len(before['materials']), len(glazing), flush=True)


if __name__ == '__main__':
    run()
