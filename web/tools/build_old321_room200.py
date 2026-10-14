"""Build the independent historical OLD.3.21 classroom component.

Run this file in Blender's Text Editor. The paired archived plan controls the
32 student positions, four table groups, and opening locations. Photo controls
broad finishes and teaching equipment. Scale, elevations, furniture sizes and
concealed boundaries are estimates. No campus file is opened or modified.
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

BASELINE = ROOT / 'result/blender/LSE_campus_detailed_v199.blend'
BASELINE_SHA = '23a119c5b1235f780a8f17f29c8a02ff1d6a2036e269312bb7d5c459c4216877'
OUTPUT = ROOT / 'result/blender/old-room200'
COLLECTION = 'OLD321_ROOM200_study'
SCENE = 'ROOM200_OLD321'
PREFIX = 'OLD321_R200_'
SCALE = .043
PLAN_ORIGIN = (300, 270)
SOURCE_FILES = [
    ('94d25854fd0e_OLD.3.21.GIF', '7c531c95f25e28f1118fa25f992397d28cbc6477837748de896525a3f8efb5c5',
     'https://www.lse.ac.uk/assets/roomInformation/images/OLD.3.21.GIF'),
    ('0382f7841a70_OLD.3.21.jpg', '839e32a84e5af2217ec2323ddd4aed91b4951aa0be53712ea6d9eebe7066d1cf',
     'https://www.lse.ac.uk/assets/roomInformation/images/photos/OLD.3.21.jpg'),
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def point(px, py):
    """Map page-right to X and page-up to Y; teaching wall is south."""
    return ((px - PLAN_ORIGIN[0]) * SCALE, (PLAN_ORIGIN[1] - py) * SCALE)


def color(g, key, value, roughness=.78):
    material = bpy.data.materials.new(PREFIX + key)
    material.use_nodes = True
    material.diffuse_color = (*value, 1)
    shader = material.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = material.diffuse_color
    shader.inputs['Roughness'].default_value = roughness
    g.materials[key] = material


def chair(g, x, y, angle):
    """Photo-visible black shell and four light metal supports, without microdetail."""
    c, s = math.cos(angle), math.sin(angle)
    def at(dx, dy, z):
        return (x + c * dx - s * dy, y + s * dx + c * dy, z)
    g.box('32_black_student_seats', 'dark', at(0, 0, .465), (.46, .43, .05), angle)
    g.box('32_black_student_backs', 'dark', at(0, .21, .745), (.46, .055, .39), angle)
    for side in [-1, 1]:
        for end in [-1, 1]:
            g.tube('student_chair_metal_legs', 'steel', at(side * .20, end * .19, .025),
                   at(side * .17, end * .16, .445), .014)


def curve_panel(g, family, controls):
    """Closed, separate wall segments trace a plan-supported curved teaching face."""
    points = []
    for step in range(17):
        t = step / 16
        px = (1 - t) ** 2 * controls[0][0] + 2 * t * (1 - t) * controls[1][0] + t ** 2 * controls[2][0]
        py = (1 - t) ** 2 * controls[0][1] + 2 * t * (1 - t) * controls[1][1] + t ** 2 * controls[2][1]
        points.append(point(px, py))
    for a, b in zip(points, points[1:]):
        length = math.dist(a, b)
        g.box(family, 'white', ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 1.45),
              (length, .075, 2.50), math.atan2(b[1] - a[1], b[0] - a[0]))
    return controls


def verify_closed_meshes(objects):
    """Recheck saved mesh connectivity, edge winding and every component volume."""
    records = []
    for obj in objects:
        mesh = obj.data
        edges = {}
        adjacency = {i: set() for i in range(len(mesh.vertices))}
        for polygon in mesh.polygons:
            face = list(polygon.vertices)
            for a, b in zip(face, face[1:] + face[:1]):
                key = (min(a, b), max(a, b))
                count, balance = edges.get(key, (0, 0))
                edges[key] = (count + 1, balance + (1 if a < b else -1))
                adjacency[a].add(b)
                adjacency[b].add(a)
        assert all(count == 2 and balance == 0 for count, balance in edges.values()), obj.name
        components, owner, unseen = [], {}, set(adjacency)
        while unseen:
            seed = unseen.pop()
            connected, pending = {seed}, [seed]
            while pending:
                for neighbor in adjacency[pending.pop()]:
                    if neighbor in unseen:
                        unseen.remove(neighbor)
                        connected.add(neighbor)
                        pending.append(neighbor)
            index = len(components)
            center = sum((mesh.vertices[i].co for i in connected), Vector()) / len(connected)
            components.append({'center': center, 'volume': 0.0})
            for i in connected:
                owner[i] = index
        for polygon in mesh.polygons:
            face = list(polygon.vertices)
            component = components[owner[face[0]]]
            center = component['center']
            a = mesh.vertices[face[0]].co - center
            for i in range(1, len(face) - 1):
                component['volume'] += a.dot((mesh.vertices[face[i]].co - center).cross(mesh.vertices[face[i + 1]].co - center)) / 6
        volumes = [component['volume'] for component in components]
        assert min(volumes) > 1e-9, (obj.name, min(volumes))
        records.append({'object': obj.name, 'closedComponents': len(volumes),
                        'minimumSignedVolume': min(volumes), 'allEdgesOppositelyPaired': True})
    return records


def build():
    assert digest(BASELINE) == BASELINE_SHA
    sources = []
    for name, expected, url in SOURCE_FILES:
        path = ROOT / 'data/collections/interiors/images' / name
        assert path.is_file() and digest(path) == expected
        sources.append({'path': str(path.relative_to(ROOT)), 'sha256': expected, 'url': url,
                        'retrievedDate': '2026-09-12', 'creationDate': 'Unknown; historical official record, not a2026survey.'})
    OUTPUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = SCENE
    collection = bpy.data.collections.new(COLLECTION)
    scene.collection.children.link(collection)
    g = RoomGeometry(collection, PREFIX)
    color(g, 'wall', (.77, .77, .72))
    color(g, 'white', (.86, .86, .79))
    color(g, 'dark', (.025, .028, .025), .56)
    color(g, 'carpet', (.28, .27, .25))
    color(g, 'tile', (.33, .32, .30))
    color(g, 'projection', (.40, .43, .61))
    color(g, 'oak', (.32, .26, .17))
    height = 2.85
    x0, rear_y = point(173, 145)
    x1, front_y = point(435, 395)
    # Main student room cut away at its rear. Adjacent3.21A,3.2B and REF AREA
    # are intentionally outside this independent component; this is not an
    # asserted complete wall footprint or surrounding floor-plan reconstruction.
    outline_px = [(173, 145), (431, 145), (431, 194), (422, 194),
                  (422, 237), (431, 237), (431, 395), (173, 395)]
    g.prism('main_room_section_floor', 'carpet', [point(*p) for p in outline_px], -.14, .14)
    # Rear boundary is an explicit low section line, not a fabricated full wall.
    rear_door_px = (173, 201)
    rx0, rx1 = point(rear_door_px[0], 145)[0], point(rear_door_px[1], 145)[0]
    g.box('rear_cutaway_boundary', 'wall', ((rx1 + point(431, 145)[0]) / 2, rear_y + .045, .15),
          (point(431, 145)[0] - rx1, .09, .30))
    g.box('rear_left_doorway_plan_threshold', 'steel', ((rx0 + rx1) / 2, rear_y, .018),
          (rx1 - rx0, .09, .036))
    # Blue plan symbol supports a left-side window. Elevations are estimates.
    wy0, wy1 = point(173, 212)[1], point(173, 145)[1]
    g.box('left_window_sill_wall', 'wall', (x0 - .08, (wy0 + wy1) / 2, .40), (.16, wy1 - wy0, .80))
    g.box('left_window_head_wall', 'wall', (x0 - .08, (wy0 + wy1) / 2, 2.675), (.16, wy1 - wy0, .35))
    for y in [wy0, wy1]:
        g.box('left_window_jambs', 'wall', (x0 - .08, y, 1.65), (.16, .15, 1.70))
    g.box('left_window_glazing', 'glass', (x0 - .025, (wy0 + wy1) / 2, 1.65), (.018, wy1 - wy0 - .15, 1.70))
    # One central mullion is an estimated subdivision rather than a verified count.
    g.box('estimated_window_mullion', 'steel', (x0, (wy0 + wy1) / 2, 1.65), (.04, .04, 1.70))
    g.box('left_front_cutaway_wall', 'wall', (x0 - .075, (wy0 + front_y) / 2, .15),
          (.15, wy0 - front_y, .30))
    for start, end in [(145, 194), (237, 395)]:
        a, b = point(431, start), point(431, end)
        g.box('right_cutaway_wall', 'wall', (a[0] + .075, (a[1] + b[1]) / 2, .15), (.15, abs(a[1] - b[1]), .30))
    # Right-side recess is retained only as a low plan outline; its side door is
    # beyond the reliable main-room boundary, so no invented opening is added.
    recess_x = point(422, 0)[0]
    g.box('right_recess_cutaway', 'wall', (recess_x + .075, (point(0, 194)[1] + point(0, 237)[1]) / 2, .15),
          (.15, 43 * SCALE, .30))
    for py in [194, 237]:
        g.box('right_recess_returns', 'wall', ((point(431, py)[0] + recess_x) / 2, point(0, py)[1], .15),
              (9 * SCALE, .15, .30))
    # Front-right double-door opening is directly legible in the plan.
    front_door_px = (404, 435)
    door_left, door_right = [point(px, 395)[0] for px in front_door_px]
    g.box('front_teaching_wall_backing', 'wall', ((x0 + door_left) / 2, front_y - .09, height / 2),
          (door_left - x0, .18, height))
    g.box('front_double_door_lintel', 'wall', ((door_left + door_right) / 2, front_y - .09, 2.525),
          (door_right - door_left, .18, .65))
    # Open leaves swing inward toward the unobstructed front zone per green arcs.
    door_width = door_right - door_left
    for index, hinge in enumerate([door_left, door_right]):
        angle = math.pi / 2 if index == 0 else -math.pi / 2
        leaf_center = (hinge, front_y + door_width / 4, 1.10)
        g.box('front_double_door_open_leaves', 'oak', leaf_center, (door_width / 2 - .012, .045, 2.20), angle)
    g.box('front_door_clear_threshold', 'steel', ((door_left + door_right) / 2, front_y, .017),
          (door_width, .10, .034))
    curve_controls = [((180, 317), (183, 350), (216, 372)),
                      ((398, 317), (394, 349), (366, 372))]
    for index, controls in enumerate(curve_controls):
        curve_panel(g, 'two_curved_teaching_panels', controls)
    sx = point(296, 395)[0]
    g.box('central_projection_white_surface', 'white', (sx, front_y + .025, 1.58), (3.23, .07, 1.93))
    g.box('photo_projection_color_field', 'projection', (sx, front_y + .067, 1.58), (2.36, .009, 1.60))
    # A small framed white teaching board is seen beside the projection.
    g.box('front_left_whiteboard_frame', 'oak', (sx - 2.35, front_y + .04, 1.57), (1.02, .09, 1.45))
    g.box('front_left_whiteboard', 'white', (sx - 2.35, front_y + .095, 1.57), (.94, .015, 1.37))
    # The archived plan locates its teaching desk on the opposite side from
    # the photograph's AV lectern; preserve plan position and report mismatch.
    lx, ly = point(242, 340)
    g.box('plan_teaching_desk_top', 'white', (lx, ly, .77), (1.38, .67, .05))
    g.box('teaching_desk_av_body', 'dark', (lx, ly, .385), (1.05, .56, .72))
    g.box('lectern_monitor', 'dark', (lx + .18, ly - .11, 1.04), (.43, .06, .29))
    g.tube('lectern_monitor_stand', 'steel', (lx + .18, ly - .07, .80), (lx + .18, ly - .07, .925), .019)
    seats, groups, envelopes = [], [], []
    group_pixels = [(238, 178), (343, 178), (237, 278), (343, 278)]
    table_width, table_depth = 34 * SCALE, 30 * SCALE
    angle = math.radians(14)
    c, s = math.cos(angle), math.sin(angle)
    for group_index, pixel in enumerate(group_pixels, 1):
        x, y = point(*pixel)
        def at(dx, dy, z):
            return (x + c * dx - s * dy, y + s * dx + c * dy, z)
        # Each plan cluster has a seam through its top; two adjacent slabs.
        for half in [-1, 1]:
            g.box('eight_paired_pale_table_slabs', 'white', at(0, half * table_depth / 4, .755),
                  (table_width, table_depth / 2 - .006, .05), angle)
            for side in [-1, 1]:
                for end in [-1, 1]:
                    g.tube('paired_table_metal_legs', 'steel', at(side * (table_width / 2 - .09), half * table_depth / 4 + end * (table_depth / 4 - .07), .025),
                           at(side * (table_width / 2 - .09), half * table_depth / 4 + end * (table_depth / 4 - .07), .729), .022)
        members = []
        for side in [-1, 1]:
            # Two chairs on each of the four sides; exact8symbols per group.
            for along in [-.34, .34]:
                for dx, dy, outward in [(along, side * (table_depth / 2 + .32), math.pi / 2 if side > 0 else -math.pi / 2),
                                        (side * (table_width / 2 + .32), along, 0 if side > 0 else math.pi)]:
                    px, py, _ = at(dx, dy, 0)
                    chair_angle = angle + outward - math.pi / 2
                    chair(g, px, py, chair_angle)
                    # Axis-aligned envelope is computed from the actual shell.
                    corners = []
                    for a in [-.23, .23]:
                        for b in [-.215, .2375]:
                            corners.append((px + math.cos(chair_angle) * a - math.sin(chair_angle) * b,
                                            py + math.sin(chair_angle) * a + math.cos(chair_angle) * b))
                    envelope = [min(q[0] for q in corners), max(q[0] for q in corners), min(q[1] for q in corners), max(q[1] for q in corners)]
                    seat = {'group': group_index, 'center': [px, py], 'angleRadians': chair_angle, 'envelope': envelope}
                    seats.append(seat)
                    members.append(seat)
                    envelopes.append(envelope)
        groups.append({'group': group_index, 'planCenterPixel': list(pixel), 'center': [x, y],
                       'studentSeats': len(members), 'tableSlabs': 2, 'angleRadians': angle})
    # Photo-visible low front soffit and projector. Most ceiling is cut away.
    g.box('front_low_ceiling_soffit', 'wall', (sx, front_y + .60, 2.77), (8.17, 1.17, .16))
    for x in [sx - 3.0, sx - 1.5, sx, sx + 1.5, sx + 3.0]:
        g.box('front_recessed_light_diffusers', 'light', (x, front_y + .60, 2.682), (.19, .19, .019))
    g.box('ceiling_projector_body', 'dark', (sx, front_y + 1.22, 2.56), (.39, .31, .19))
    g.tube('projector_ceiling_mount', 'steel', (sx, front_y + 1.22, 2.655), (sx, front_y + 1.22, 2.85), .023)
    g.box('projector_lens', 'steel', (sx, front_y + 1.055, 2.55), (.09, .025, .09))
    objects = g.finish()
    assert len(seats) == 32 and all(group['studentSeats'] == 8 for group in groups)
    for obj in objects:
        obj['roomCode'] = 'OLD.3.21'
        obj['scope'] = 'Historical paired-source independent main student-room section; metric scale and concealed boundaries estimated'
    collection['studentSeatCount'] = 32
    collection['roomSample'] = True
    next(obj for obj in objects if '32_black_student_seats' in obj.name)['studentSeatCount'] = 32
    scope = '依据LSE官方OLD.3.21历史平面与照片建立32座教室：2×2四组、每组8座、浅色拼桌、黑色椅子、中央投影与两侧弧形教学面、前右双门和左侧窗。尺寸、层高及门窗立面估计；后部为明确剖切边界，3.21A、3.2B与REF AREA不计入学生教室，不推断整层连通，不代表2026年现状。'
    space = {'id': 'old-321', 'code': 'OLD', 'collection': COLLECTION, 'label': 'OLD.3.21分组教室',
             'gallery': 'old-321-interior', 'scope': scope,
             'interiorView': {'position': [15.2, 13.6, -17.8], 'target': [0, 1, 0], 'fov': 48},
             'interiorStudy': {'kind': 'room-sample', 'label': 'OLD.3.21分组教室', 'scope': scope}}
    collection['authoringRecord'] = json.dumps(space, ensure_ascii=False)
    # Main axial aisle and front approaches use full chair envelopes.
    left = [r for seat, r in zip(seats, envelopes) if seat['group'] in [1, 3]]
    right = [r for seat, r in zip(seats, envelopes) if seat['group'] in [2, 4]]
    aisle_low, aisle_high = max(r[1] for r in left), min(r[0] for r in right)
    assert aisle_high - aisle_low > 1.20
    front_clear = min(r[2] for r in envelopes) - front_y
    assert front_clear > 2.0
    # Door leaves are fully inside the front zone, clear of seats and lectern.
    assert front_y + door_width / 2 < min(r[2] for r in envelopes)
    assert lx + 1.38 / 2 < door_left
    assert door_width > 1.2
    rear_clear = rear_y - max(r[3] for r in envelopes)
    assert rear_clear > .05
    # No pair of chair shell envelopes intersects; corner seating also stays clear.
    collisions = [(i, j) for i, a in enumerate(envelopes) for j, b in enumerate(envelopes[i + 1:], i + 1)
                  if min(a[1], b[1]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[2], b[2])]
    assert not collisions, collisions
    triangles = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objects)
    assert triangles < 40000
    camera = bpy.data.objects.new(PREFIX + 'camera', bpy.data.cameras.new(PREFIX + 'camera'))
    scene.collection.objects.link(camera)
    camera.location = (15.2, 17.8, 13.6)
    camera.rotation_euler = (Vector((0, 0, .95)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 20.6
    scene.camera = camera
    scene.world = bpy.data.worlds.new(PREFIX + 'world')
    scene.world.color = (.82, .83, .82)
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'MATERIAL'
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = 'BOTH'
    scene.display.shading.background_type = 'WORLD'
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(OUTPUT / 'old321-cutaway.png')
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / 'component.blend'))
    bpy.ops.render.render(write_still=True)
    # A second orthographic view makes the32-seat and circulation checks reviewable.
    # The saved component retains its original cutaway camera.
    camera.location = (0, 0, 24)
    camera.rotation_euler = (0, 0, 0)
    camera.data.ortho_scale = 13.5
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1000
    scene.render.filepath = str(OUTPUT / 'old321-plan-check.png')
    bpy.ops.render.render(write_still=True)
    component_sha = digest(OUTPUT / 'component.blend')
    report = {'baselineSha256': BASELINE_SHA,
              'componentPath': str((OUTPUT / 'component.blend').relative_to(ROOT)), 'componentSha256': component_sha,
              'targetCollection': COLLECTION, 'addedObjects': [o.name for o in objects], 'archivedObjects': [],
              'collectionSpec': {'name': COLLECTION, 'scene': SCENE, 'kind': 'independent-room'}, 'space': space,
              'studentSeatCount': 32, 'groupCount': 4, 'seatsPerGroup': 8, 'tableSlabCount': 8,
              'seatPositions': seats, 'groups': groups, 'sources': sources,
              'planMapping': {'originPixel': list(PLAN_ORIGIN), 'metresPerPixel': SCALE, 'pageYIsNegativeWorldY': True,
                              'heightMetres': height, 'dimensionsAreEstimated': True, 'mainRoomSectionOutlinePixels': outline_px,
                              'frontDoubleDoorPixels': list(front_door_px), 'rearLeftDoorwayPixels': list(rear_door_px),
                              'leftWindowPlanPixels': {'x': 164, 'yRange': [139, 212], 'mainSectionRange': [145, 212]},
                              'curvedTeachingPanelPixels': curve_controls},
              'doorPassageChecks': {'frontDoubleDoorClearWidthMetres': door_width,
                                    'frontSeatClearDepthMetres': front_clear, 'doorLeavesClearOfStudentFurniture': True,
                                    'teachingDeskClearOfDoorApproach': True, 'rearSectionSeatClearDepthMetres': rear_clear,
                                    'centralAisleBoundsMetres': [aisle_low, aisle_high],
                                    'centralAisleClearWidthMetres': aisle_high - aisle_low,
                                    'chairEnvelopeIntersections': 0},
              'triangleCount': triangles, 'triangleBudget': 40000, 'closedSolidProof': g.solid_proof,
              'limitations': ['Official plan and photo share room number, but creation dates are unknown; no current2026layout claim.',
                              'Metric scale .043metres/pixel,2.85metre height and furniture sizes estimated, not surveyed.',
                              'Rear is a section boundary. Adjacent3.21A,3.2B,REF AREA and right-side external doorway are excluded, not attributed to this student room.',
                              'Only the left blue main-room window symbol is modeled; windows belonging to3.2B are excluded. Window height and one mullion estimated.',
                              'Rear-left doorway is a threshold marker only; concealed leaf, exact curved rear partition and corridor are not fabricated.',
                              'Photo lectern is on image-right, whereas plan teaching desk is on front-left. Plan position is preserved; broad AV equipment is photo-derived.',
                              'Two slabs per group follow central plan seam; furniture construction and legs remain approximations.',
                              'Teaching-panel curvature traced from plan but elevations estimated; most ceiling and side/rear walls sectioned.'],
              'preview': str((OUTPUT / 'old321-cutaway.png').relative_to(ROOT)),
              'planPreview': str((OUTPUT / 'old321-plan-check.png').relative_to(ROOT))}
    names = sorted(report['addedObjects'])
    bpy.ops.wm.open_mainfile(filepath=str(OUTPUT / 'component.blend'))
    reopened = bpy.data.collections[COLLECTION]
    reopened_objects = list(reopened.all_objects)
    assert sorted(o.name for o in reopened_objects) == names
    assert len(bpy.data.scenes) == 1 and bpy.data.scenes[SCENE].collection.children.get(COLLECTION)
    assert reopened['studentSeatCount'] == 32
    assert digest(BASELINE) == BASELINE_SHA and digest(OUTPUT / 'component.blend') == component_sha
    closed = verify_closed_meshes(reopened_objects)
    assert sum(record['closedComponents'] for record in closed) == sum(record['closedComponents'] for record in g.solid_proof.values())
    report['reopenedVerification'] = {'objectNamesMatch': True, 'independentSceneOnly': True, 'studentSeatCount': 32,
                                      'baselineUnchanged': True, 'componentSha256Match': True, 'allMeshesClosedAndOutward': True,
                                      'meshProof': closed}
    (OUTPUT / 'audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'component': report['componentPath'], 'objects': len(names), 'triangles': triangles, 'seats': 32, 'reopened': True}))


if __name__ == '__main__':
    build()
