"""Build an independent CLM.5.02 historical classroom from paired LSE records.

Run in Blender's Text Editor. Plan coordinates control 120 seats, 60 two-person
 desks and the door openings. Metric scale, height and obscured construction
are estimates. This does not open or modify the full campus source.
"""
from pathlib import Path
import hashlib
import json
import math
import sys
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from build_room_samples167 import RoomGeometry

BASELINE = ROOT / 'result/blender/LSE_campus_detailed_v196.blend'
BASELINE_SHA = '1c1185738e796221c6d30f06aec906b99829cad4867fbb2bced77d657afc298b'
OUTPUT = ROOT / 'result/blender/clm-room197'
COLLECTION = 'CLM502_ROOM197_study'
SCENE = 'ROOM197_CLM502'
SCALE = .036
PREFIX = 'CLM502_R197_'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def point(x, y):
    return ((x - 190) * SCALE, (y - 143) * SCALE)


def finish_color(g, key, color, roughness=.78):
    material = bpy.data.materials.new(PREFIX + key)
    material.use_nodes = True
    material.diffuse_color = (*color, 1)
    shader = material.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = material.diffuse_color
    shader.inputs['Roughness'].default_value = roughness
    g.materials[key] = material


def clm_chair(g, x, y):
    """Photo-visible pale shell with horizontal back slot and dark tubular legs."""
    g.box('120_pale_seat_shells', 'seat', (x, y, .455), (.415, .41, .045))
    # Four closed pieces preserve the photographed horizontal opening.
    g.box('120_slotted_chair_backs', 'seat', (x, y + .20, .775), (.43, .039, .20))
    g.box('120_slotted_chair_backs', 'seat', (x, y + .20, .605), (.43, .039, .065))
    for side in [-1, 1]:
        g.box('120_slotted_chair_backs', 'seat', (x + side * .19, y + .20, .665), (.05, .039, .055))
        for end in [-1, 1]:
            g.tube('dark_chair_legs', 'dark', (x + side * .18, y + end * .17, .025),
                   (x + side * .17, y + end * .14, .43), .013)


def build():
    assert digest(BASELINE) == BASELINE_SHA
    OUTPUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = SCENE
    collection = bpy.data.collections.new(COLLECTION)
    scene.collection.children.link(collection)
    g = RoomGeometry(collection, PREFIX)
    finish_color(g, 'oak', (.37, .22, .095), .67)
    finish_color(g, 'board', (.025, .085, .070), .82)
    finish_color(g, 'tile_light', (.31, .32, .31))
    finish_color(g, 'tile_dark', (.245, .255, .25))
    finish_color(g, 'projection', (.43, .56, .65), .9)
    finish_color(g, 'exit', (.025, .23, .075))
    finish_color(g, 'seat', (.70, .735, .73), .66)
    finish_color(g, 'white', (.82, .82, .76), .67)
    finish_color(g, 'wall', (.75, .76, .72))
    finish_color(g, 'steel', (.24, .27, .27), .45)
    finish_color(g, 'carpet', (.25, .26, .25))
    # Slight rear-wall taper follows the visible plan rather than a generic box.
    outline_px = [(26, 35), (355, 35), (355, 252), (285, 242), (26, 242)]
    g.prism('plan_outline_floor', 'carpet', [point(*p) for p in outline_px], -.13, .13)
    # Subtle alternating carpet tiles, derived from the photo. Kept planar and sparse.
    for ix in range(20):
        for iy in range(12):
            x, y = -5.57 + ix * .58, -3.46 + iy * .58
            if ix % 2 == iy % 2:
                g.box('carpet_tile_variation', 'tile_light', (x, y, .0015), (.576, .576, .003))
    front_y = point(0, 35)[1]
    left_x, right_x = point(26, 0)[0], point(355, 0)[0]
    height = 3.05
    doors_px = [(66, 97), (282, 314)]
    # Full teaching wall with actual holes; double doors swing out in the plan.
    spans = [(26, 66), (97, 282), (314, 355)]
    for start, end in spans:
        x = (point(start, 35)[0] + point(end, 35)[0]) / 2
        g.box('front_wall_piers', 'wall', (x, front_y - .10, height / 2), ((end - start) * SCALE, .20, height))
    for start, end in doors_px:
        x = point((start + end) / 2, 35)[0]
        width = (end - start) * SCALE
        g.box('door_lintels', 'wall', (x, front_y - .1, 2.63), (width, .20, .84))
        for side in [-1, 1]:
            leaf_x = x + side * width / 4
            g.box('two_oak_double_doors', 'oak', (leaf_x, front_y - .075, 1.08), (width / 2 - .012, .045, 2.16))
            g.box('door_vision_panels', 'glass', (leaf_x, front_y - .047, 1.47), (.10, .012, .73))
            g.tube('door_pull_handles', 'steel', (x + side * .065, front_y - .005, .89),
                   (x + side * .065, front_y - .005, 1.24), .012)
        g.box('exit_signs', 'exit', (x, front_y + .012, 2.30), (.37, .04, .17))
        # Abstract white egress figure rather than unreadable faux text.
        g.box('exit_sign_symbols', 'white', (x, front_y + .036, 2.3), (.14, .006, .035))
    # Side and rear wall cut down to expose the 120-seat arrangement. No invented windows.
    # Window symbols cannot be reliably distinguished in the low-resolution plan;
    # the supplied photo does not show the external side walls.
    g.box('left_cutaway_wall', 'wall', (left_x - .08, .13, .16), (.16, 8.03, .32))
    g.box('rear_cutaway_wall', 'wall', (0, 3.66, .16), (11.8, .16, .32))
    g.box('right_cutaway_wall', 'wall', (right_x + .08, .18, .16), (.16, 8.08, .32))
    # The narrow oak panel beside the right double door is photo-visible.
    # Its small plan swing is treated as an equipment cupboard, not a third exit.
    g.box('front_right_equipment_cupboard_door', 'oak', (5.12, front_y + .04, 1.06), (.47, .045, 2.12))
    g.tube('cupboard_pull', 'steel', (4.97, front_y + .08, .92), (4.97, front_y + .08, 1.15), .010)
    # White teaching surface plus two drop-down projection screens from the photo.
    g.box('central_whiteboard', 'white', (-.12, front_y + .015, 1.65), (5.25, .06, 1.35))
    for x in [-2.16, 2.16]:
        g.box('two_projection_screen_frames', 'dark', (x, front_y + .07, 1.82), (2.28, .055, 1.38))
        g.box('two_projection_screen_faces', 'screen', (x, front_y + .105, 1.82), (2.19, .022, 1.28))
        g.box('projection_bottom_bars', 'steel', (x, front_y + .12, 1.16), (2.33, .043, .055))
    # The far-right dark green board is visible in the photograph, past the oak doors.
    g.box('front_right_green_board', 'board', (5.25, front_y + .025, 1.59), (1.13, .065, 1.37))
    # Photo-visible teaching equipment at the far-right front; dimensions estimated.
    g.box('teaching_desk_top', 'white', (5.08, -3.26, .77), (1.08, .40, .045))
    g.box('teaching_desk_pedestal', 'dark', (5.08, -3.26, .38), (.66, .33, .73))
    g.box('teaching_monitor', 'dark', (5.08, -3.32, 1.02), (.42, .06, .29))
    g.box('monitor_stand', 'steel', (5.08, -3.30, .845), (.14, .16, .11))
    seats = []
    table_rectangles = []
    # Pixel coordinates read from the archived plan: 6 rows of 2+6+2 desks.
    row_starts = [71, 98, 124, 151, 177, 204]
    groups = [(39, 91, 2), (115, 273, 6), (296, 347, 2)]
    for row, py in enumerate(row_starts):
        for start, end, count in groups:
            module = (end - start) / count
            for desk in range(count):
                px = start + module * (desk + .5)
                x, y = point(px, py + 4)
                width = module * SCALE - .015
                g.box('60_two_person_desk_tops', 'white', (x, y, .755), (width, .56, .043))
                for sx in [-1, 1]:
                    for sy in [-1, 1]:
                        g.tube('desk_black_legs', 'dark', (x + sx * (width / 2 - .07), y + sy * .22, .025),
                               (x + sx * (width / 2 - .07), y + sy * .22, .733), .017)
                table_rectangles.append([x - width / 2, x + width / 2, y - .28, y + .28])
                for side in [-1, 1]:
                    seat = (x + side * module * SCALE / 4, y + .47)
                    clm_chair(g, *seat)
                    seats.append({'row': row + 1, 'planPixel': [px + side * module / 4, py + 4 + .47 / SCALE], 'center': list(seat)})
    # Ceiling services survive only as two narrow cutaway ribbons, preserving the view.
    for x in [-2.16, 2.16]:
        g.box('cutaway_ceiling_ribbons', 'wall', (x, -.10, 3.05), (.69, 7.0, .08))
        for y in [-2.25, -.55, 1.15, 2.85]:
            g.box('ceiling_recessed_lights', 'light', (x, y, 2.997), (.20, .20, .022))
        g.box('suspended_projector_bodies', 'white', (x, -1.40, 2.78), (.37, .28, .16))
        g.tube('projector_mounts', 'steel', (x, -1.40, 2.86), (x, -1.40, 3.01), .025)
        g.box('projector_lenses', 'dark', (x, -1.555, 2.77), (.10, .025, .07))
    for x in [-.12, -.075, -.03, .015]:
        g.box('linear_ceiling_vent_slots', 'dark', (x, -.15, 3.01), (.019, 7.1, .026))
    objects = g.finish()
    assert len(seats) == 120 and len(table_rectangles) == 60
    for obj in objects:
        obj['roomCode'] = 'CLM.5.02'
        obj['scope'] = 'Historical paired-source independent room; metric dimensions and concealed construction estimated'
    collection['studentSeatCount'] = 120
    collection['roomSample'] = True
    next(o for o in objects if '120_pale_seat_shells' in o.name)['studentSeatCount'] = 120
    scope = '依据LSE官方CLM.5.02历史平面与照片建立120座教室：6排、每排4+12+4座、60张双人桌、双纵向通道、双投影幕、教学墙与门。尺寸、层高及照片不可见构造估计；外侧窗洞无法可靠核实，侧后墙和顶面剖开；不推断整层连通，不代表2026年现状。'
    space = {'id': 'clm-502', 'code': 'CLM', 'collection': COLLECTION, 'label': 'CLM.5.02排式教室', 'scope': scope,
             'gallery': 'clm-502-interior', 'interiorStudy': {'kind': 'room-sample', 'label': 'CLM.5.02排式教室', 'scope': scope},
             'interiorView': {'position': [13.8, 11.2, -14.6], 'target': [0, 1, 0], 'fov': 48}}
    collection['authoringRecord'] = json.dumps(space, ensure_ascii=False)
    camera = bpy.data.objects.new(PREFIX + 'camera', bpy.data.cameras.new(PREFIX + 'camera'))
    scene.collection.objects.link(camera)
    camera.location = (13.8, 14.6, 11.2)
    camera.rotation_euler = (Vector((0, 0, 1)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 18.3
    scene.camera = camera
    scene.world = bpy.data.worlds.new(PREFIX + 'world')
    scene.world.color = (.80, .82, .83)
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'MATERIAL'
    scene.display.shading.studiolight_rotate_z = math.pi
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = 'BOTH'
    scene.display.shading.background_type = 'WORLD'
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(OUTPUT / 'clm502-cutaway.png')
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / 'component.blend'))
    bpy.ops.render.render(write_still=True)
    component_sha = digest(OUTPUT / 'component.blend')
    triangles = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objects)
    assert triangles < 40000, triangles
    # Desk edges and chair envelopes leave both longitudinal aisles empty.
    aisles_px = [(91, 115), (273, 296)]
    aisle_checks = []
    for lo, hi in aisles_px:
        a, b = point(lo, 0)[0], point(hi, 0)[0]
        occupied = [r for r in table_rectangles if r[1] > a and r[0] < b]
        seat_intrusions = [s for s in seats if s['center'][0] + .215 > a and s['center'][0] - .215 < b]
        assert not occupied and not seat_intrusions
        aisle_checks.append({'planPixels': [lo, hi], 'clearWidthMetres': b - a, 'deskIntrusions': 0, 'chairIntrusions': 0})
    front_clear = min(r[2] for r in table_rectangles) - front_y
    assert front_clear > 1.0
    teaching_desk_x = (5.08 - 1.08 / 2, 5.08 + 1.08 / 2)
    assert all(teaching_desk_x[0] >= point(b, 0)[0] or teaching_desk_x[1] <= point(a, 0)[0] for a, b in doors_px)
    spacing = min(math.dist(a['center'], b['center']) for i, a in enumerate(seats) for b in seats[i + 1:])
    assert spacing > .43
    sources = []
    for filename, url in [('778e00df6a31_CLM.5.02.jpg', 'https://www.lse.ac.uk/assets/roomInformation/images/photos/CLM.5.02.jpg'),
                          ('f8dc793765a6_CLM.5.02.GIF', 'https://www.lse.ac.uk/assets/roomInformation/images/CLM.5.02.GIF')]:
        path = ROOT / 'data/collections/interiors/images' / filename
        sources.append({'path': str(path.relative_to(ROOT)), 'sha256': digest(path), 'url': url, 'captureDate': 'Unknown; historical archive. Page refresh17Aug2022 is not image creation date.'})
    report = {'baselineSha256': BASELINE_SHA, 'componentPath': str((OUTPUT / 'component.blend').relative_to(ROOT)), 'componentSha256': component_sha,
              'targetCollection': COLLECTION, 'addedObjects': [o.name for o in objects], 'archivedObjects': [],
              'collectionSpec': {'name': COLLECTION, 'scene': SCENE, 'kind': 'independent-room'}, 'space': space,
              'studentSeatCount': 120, 'deskCount': 60, 'rows': 6, 'seatsPerRow': [4, 12, 4], 'seatPositions': seats,
              'planMapping': {'originPixel': [190, 143], 'metresPerPixel': SCALE, 'heightMetres': height, 'dimensionsAreEstimated': True,
                              'rowStartPixels': row_starts, 'deskGroupPixels': groups, 'doubleDoorPixels': doors_px,
                              'roomOutlinePixels': outline_px, 'windows': 'Not confidently identifiable in supplied plan/photo; unverified exterior wall sections cut away.'},
              'doorPassageChecks': {'frontClearDepthMetres': front_clear, 'doubleDoorClearWidthsMetres': [(b - a) * SCALE for a, b in doors_px],
                                    'doorSwings': 'Two room double doors outward per plan; narrow adjacent oak panel treated as equipment cupboard, not egress', 'teachingDeskDoesNotOverlapDoubleDoorApproaches': True, 'longitudinalAisles': aisle_checks},
              'minimumSeatCenterSpacingMetres': spacing, 'triangleCount': triangles, 'triangleBudget': 40000,
              'closedSolidProof': g.solid_proof, 'sources': sources,
              'limitations': ['Historical same-number plan and photo, no current2026 layout claim.', 'No measured dimensions; .036metres/pixel and3.05metre height estimated.',
                              'Door/window elevations outside photograph unverified; side/rearwalls and most ceiling intentionally sectioned.', 'Chair lower frame partly obscured; four dark tubular legs estimated from visible supports.', 'Narrow oak panel beside right double door treated as equipment cupboard; exact cupboard depth unverified.'],
              'preview': str((OUTPUT / 'clm502-cutaway.png').relative_to(ROOT))}
    names = sorted(report['addedObjects'])
    bpy.ops.wm.open_mainfile(filepath=str(OUTPUT / 'component.blend'))
    reopened = bpy.data.collections[COLLECTION]
    assert sorted(o.name for o in reopened.all_objects) == names
    assert len(bpy.data.scenes) == 1 and bpy.data.scenes[SCENE].collection.children.get(COLLECTION)
    assert reopened['studentSeatCount'] == 120
    assert digest(BASELINE) == BASELINE_SHA and digest(OUTPUT / 'component.blend') == component_sha
    report['reopenedVerification'] = {'objectNamesMatch': True, 'independentSceneOnly': True, 'studentSeatCount': 120, 'baselineUnchanged': True, 'componentSha256Match': True}
    (OUTPUT / 'audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'component': report['componentPath'], 'objects': len(names), 'triangles': triangles, 'seats': 120, 'reopened': True}))


if __name__ == '__main__':
    build()
