"""Read-only COL street exterior audit against the archived built photographs.

Run in Blender's Text Editor or call audit_col_exterior202(). This fixed-path
workflow opens v201, renders two bounded exterior views and records evidence.
It never saves a campus, creates a component or changes accepted model geometry.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

import bpy
from mathutils import Vector

ROOT = Path('/Users/haoranxu/Desktop/LSEmap')
BASE = ROOT / 'result/blender/LSE_campus_detailed_v201.blend'
BASE_SHA = '83f8532de4378e614f53a327b8c3397ae375e880d655bd584f5e0ea4980f2bec'
OUT = ROOT / 'result/blender/col-exterior202'
REFERENCES = [
    ('data/建筑图片/COL_Columbia House/01_建筑实拍/small_round5_COL_handbook-000.png',
     'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Property-and-Space/LSE-Property-Handbook.pdf',
     '2025/26 handbook; photographic capture unknown', 'Main portal and lower Aldwych facade; tree obscures the left portion.'),
    ('data/建筑图片/COL_Columbia House/01_建筑实拍/exteriors_lse_estate_004.jpg',
     'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Images/LSE-Estate/Columbia-House-300x376.jpg',
     'Built photograph; capture unknown', 'Low-resolution street corner, Garrick entrance and oblique lower Houghton facade; roof cropped.'),
    ('result/blender/col_detail167/mathematics-003.jpg',
     'https://www.lse.ac.uk/Mathematics/assets/documents/PUBLIC-AthSw-For-Website.pdf',
     'Application text April2020, PDF metadata September2022; capture unknown', 'Three-column corner and nearest first-floor Houghton windows; no complete upper elevation.'),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def state_function():
    # Reuse the accepted geometry/original-UV checker without creating bytecode.
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('col195_readonly_state', ROOT / 'web/tools/refine_col_exterior195.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.state


def render_views(target):
    scene = bpy.data.scenes.new('COL202_readonly_preview')
    collection = bpy.data.collections.new('COL202_readonly_preview_objects')
    scene.collection.children.link(collection)
    for obj in target.all_objects:
        if obj.type in {'MESH', 'FONT', 'CURVE'} and not obj.hide_render:
            collection.objects.link(obj)
    world = bpy.data.worlds.new('COL202_readonly_preview_world')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[1].default_value = .65
    sky = world.node_tree.nodes.new('ShaderNodeTexEnvironment')
    sky.image = bpy.data.images.load(str(ROOT / 'web/public/environment/kloppenheim-daylight-1k.hdr'), check_existing=True)
    world.node_tree.links.new(sky.outputs['Color'], world.node_tree.nodes['Background'].inputs[0])
    scene.world = world
    light_data = bpy.data.lights.new('COL202_readonly_sun', 'SUN')
    light_data.energy = 1.8
    light_data.angle = .12
    sun = bpy.data.objects.new(light_data.name, light_data)
    collection.objects.link(sun)
    sun.rotation_euler = Vector((-.6, .5, -1)).to_track_quat('-Z', 'Y').to_euler()
    camera_data = bpy.data.cameras.new('COL202_readonly_camera')
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    collection.objects.link(camera)
    scene.camera = camera
    camera_data.type = 'ORTHO'
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    origin = Vector((16.67990685, -127.45446777, 0))
    u = Vector((-.99970835, .02415093, 0))
    n = Vector((-.02415093, -.99970835, 0))
    corner = Vector((6.93853448, -126.32244338, 0))
    cn = Vector((-.640445, -.768004, 0))
    views = {
        'whole': (origin + u * 3 - n * 13 + Vector((0, 0, 14)), n * 48 + u * 22 + Vector((0, 0, 15)), 46),
        'corner': (corner + Vector((0, 0, 4.35)), cn * 21 + Vector((0, 0, 1.1)), 10.8),
    }
    cameras = {}
    for name, (aim, offset, scale) in views.items():
        camera.location = aim + offset
        camera.rotation_euler = (aim - camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera_data.ortho_scale = scale
        scene.render.filepath = str(OUT / ('current-' + name + '.png'))
        bpy.ops.render.render(write_still=True, scene=scene.name)
        cameras[name] = dict(position=list(camera.location), target=list(aim), orthoScale=scale, path=scene.render.filepath)
    bpy.data.scenes.remove(scene)
    bpy.data.collections.remove(collection)
    bpy.data.objects.remove(camera, do_unlink=True)
    bpy.data.objects.remove(sun, do_unlink=True)
    bpy.data.cameras.remove(camera_data)
    bpy.data.lights.remove(light_data)
    bpy.data.worlds.remove(world)
    return cameras


def audit_col_exterior202():
    assert sha(BASE) == BASE_SHA, 'v201 baseline changed'
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()
    state = state_function()
    collection = bpy.data.collections['COL_EXTERIOR']
    objects = list(collection.all_objects)
    original_names = set(bpy.data.objects.keys())
    original = {o.name: state(o) for o in bpy.data.objects if o.type == 'MESH'}
    visibility = {o.name: [o.hide_render, o.hide_viewport] for o in bpy.data.objects}
    previous = json.loads((ROOT / 'result/blender/col-exterior195/building-refinement.json').read_text())
    accepted = []
    for row in previous['replacements']:
        expected = previous['originalStates'][row['originalObject']]
        source = bpy.data.objects[row['originalObject']]
        obj = bpy.data.objects[row['replacement']]
        actual = state(obj)
        assert state(source) == expected
        assert actual['geometry'] == expected['geometry']
        assert all(actual['uv'][name] == value for name, value in expected['uv'].items())
        accepted.append(dict(object=obj.name, retainedSource=source.name, geometryAndOriginalUVPreserved=True,
                             sourceArchived=source.hide_render, replacementVisible=not obj.hide_render))
    cameras = render_views(collection)
    assert set(bpy.data.objects.keys()) == original_names
    assert all(state(bpy.data.objects[name]) == value for name, value in original.items())
    assert all([bpy.data.objects[name].hide_render, bpy.data.objects[name].hide_viewport] == value for name, value in visibility.items())
    assert sha(BASE) == BASE_SHA
    references = [dict(path=p, sha256=sha(ROOT / p), url=url, stage=stage, support=support)
                  for p, url, stage, support in REFERENCES]
    report = dict(version=202, status='read-only-no-new-supported-broad-correction',
                  baseline=str(BASE.relative_to(ROOT)), baselineSha256=BASE_SHA, targetCollection='COL_EXTERIOR',
                  componentProduced=False, addedObjects=[], archivedObjects=[], changedObjects=[],
                  baselineUnchanged=True, allOriginalMeshGeometryAndUVPreserved=True,
                  allObjectNamesAndVisibilityPreserved=True, originalMeshCount=len(original),
                  collectionObjectCount=len(objects), visibleCollectionObjects=[o.name for o in objects if not o.hide_render],
                  accepted195ReplacementChecks=accepted, references=references,
                  regions=[
                      dict(region='Main entrance', finding='Existing recessed closed timber double door, stone portal and adjacent three-column upper window reflect the handbook features. No new broad entrance correction supported.', limitation='Perspective/occlusion prevent reliable metric re-proportioning; carved detail exact placement remains approximate.'),
                      dict(region='Garrick entrance and shopfront', finding='Retain glazed chamfer entrance and existing sign zone. Dark glazing in the low-resolution source may contain reflection or interior shadow; it cannot justify solidifying the whole shopfront or changing transmission.', limitation='No new detailed built front-on doorway view establishes a different door/transom or glazing contract.'),
                      dict(region='Corner and lower facade', finding='v175 smooth ordinary piers, retained rusticated corner and v167 photographed first-floor three-column divisions remain; v195 stone/joinery finish retained.', limitation='Existing metric widths, stone courses and material colour are photo-guided estimates.'),
                      dict(region='Whole street elevation', finding='Do not add a new brick zone or reshape the roof/upper window rows using cropped ground-level photographs.', limitation='Full upper bay counts, seventh row, roof profile/height and unseen rear elevations remain unverified.'),
                  ],
                  cameras=cameras, previewScope='Current v201 COL exterior only; 16sample Cycles, AgX, retained HDR sky. No before/after improvement claim because no geometry or materials were modified.',
                  priorEvidence=['web/tools/refine_col_exterior195.py','web/tools/refine_col_exterior175.py','result/blender/col_detail167/report.md','result/blender/col_frontage154/audit.json','result/blender/col_envelope_next/audit.json'],
                  sourceOrganization='No data/collections/COL directory exists; canonical organized COL photographs are under data/建筑图片/COL_Columbia House, with collection-linked provenance in 图片索引.json.',
                  conclusion='No additional defensible broad COL exterior correction identified. Preserve accepted model and record remaining coverage limits.',
                  rendersActuallyInspected=False)
    (OUT / 'audit.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print('COL202_READONLY_AUDIT_READY', len(objects), len(accepted), flush=True)
    return report


if __name__ == '__main__':
    audit_col_exterior202()
