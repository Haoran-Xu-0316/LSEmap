"""Reconstruct a private CBG highest-roof component in the independent202 frame.

Run build_candidate() in Blender's Text Editor. Fixed local files only. The203
campus and202 component are read-only; no published assets are written. Plan
landmarks supply XY boundaries, while all Z values remain inherited estimates.
"""
from pathlib import Path
import hashlib
import json
import math
import sys
import bpy
import bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from integrate_exterior_round194 import object_fingerprint
from refine_ground_orientation199 import closed_islands, signed_volume
from refine_cbg_roof_envelope import components, CORNERS, BOX_FACES

BASE = ROOT / 'result/blender/LSE_campus_detailed_v203.blend'
BASE_SHA = '976e645ef4b58e19485feff1fe3ff2fb64d9b5d497739642a2429548d821df8a'
SOURCE = ROOT / 'result/blender/cbg-envelope202/cbg-envelope202-component.blend'
OUT = ROOT / 'result/blender/cbg-roof203'
PREFIX = 'CBG203_ROOF_'
HEIGHT = 52.2
STEP = HEIGHT / 13
END_DECK = 11 * STEP
REAR_DECK = 12 * STEP
EPS = 3e-5


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frame(mapping):
    f = mapping['frame']
    origin = Vector((*f['origin_G7_SW_world'], 0))
    ex = Vector((*f['x_unit_SW'], 0))
    ey = Vector((*f['y_unit_SE_rear'], 0))
    def local(point):
        delta = point - origin
        return Vector((delta.dot(ex), delta.dot(ey), point.z))
    def world(point):
        return origin + ex * point[0] + ey * point[1] + Vector((0, 0, point[2]))
    return local, world


def volume_planes(polygon, bottom, top):
    """Convex footprint half spaces; interior is n.dot(point)>=offset."""
    polygon = [Vector((x, y, 0)) for x, y in polygon]
    area = sum(a.x * b.y - a.y * b.x for a, b in zip(polygon, polygon[1:] + polygon[:1]))
    if area < 0:
        polygon.reverse()
    planes = []
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        edge = b - a
        normal = Vector((-edge.y, edge.x, 0)).normalized()
        planes.append((normal, normal.dot(a)))
    planes.extend([(Vector((0, 0, 1)), bottom), (Vector((0, 0, -1)), -top)])
    return planes


def clip_polygon(polygon, normal, offset):
    retained, crossings = [], []
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        da, db = normal.dot(a[0]) - offset, normal.dot(b[0]) - offset
        if da >= -EPS:
            retained.append(a)
        if (da > EPS and db < -EPS) or (da < -EPS and db > EPS):
            fraction = da / (da - db)
            point = (a[0].lerp(b[0], fraction), [u.lerp(v, fraction) for u, v in zip(a[1], b[1])])
            retained.append(point)
            crossings.append(point)
    unique = {}
    for point in retained:
        unique.setdefault(tuple(round(v, 5) for v in point[0]), point)
    retained = list(unique.values())
    if len(retained) < 3:
        return [], crossings
    area = sum(((retained[i][0] - retained[0][0]).cross(retained[i + 1][0] - retained[0][0]) for i in range(1, len(retained) - 1)), Vector()).length
    return (retained if area > 1e-9 else []), crossings


def clip_shell(faces, normal, offset, closed):
    retained, crossings = [], []
    for polygon, material, smooth in faces:
        clipped, cuts = clip_polygon(polygon, normal, offset)
        if clipped:
            retained.append((clipped, material, smooth))
        crossings.extend(cuts)
        crossings.extend(point for point in clipped if abs(normal.dot(point[0])-offset)<EPS)
    if closed and retained:
        unique = {}
        for point in crossings:
            key = tuple(round(v, 5) for v in point[0])
            unique.setdefault(key, point)
        points = list(unique.values())
        if len(points) >= 3:
            centre = sum((p[0] for p in points), Vector()) / len(points)
            u = normal.cross(Vector((0, 0, 1)))
            if u.length < .1:
                u = Vector((1, 0, 0))
            u.normalize()
            v = normal.cross(u).normalized()
            points.sort(key=lambda p: math.atan2((p[0] - centre).dot(v), (p[0] - centre).dot(u)))
            if (points[1][0] - points[0][0]).cross(points[2][0] - points[0][0]).dot(normal) > 0:
                points.reverse()
            retained.append((points, faces[0][1], False))
    return retained


def subtract_volume(faces, planes, closed):
    remaining, outside = faces, []
    for normal, offset in planes:
        if not remaining:
            break
        distances = [normal.dot(point[0]) - offset for polygon, _, _ in remaining for point in polygon]
        if min(distances) >= -EPS:
            continue
        if max(distances) <= EPS:
            outside.append(remaining)
            return outside
        exterior = clip_shell(remaining, -normal, -offset, closed)
        if exterior:
            outside.append(exterior)
        remaining = clip_shell(remaining, normal, offset, closed)
    return outside


def trim_object(source, local, world, volumes):
    """Keep untouched islands exactly; clip only overlapping native islands.

    Each resulting prism fragment is closed independently. This preserves
    material cornerUVs and avoids an ExactBoolean on disconnected facade parts.
    Shared internal partition faces are retained as a documented limitation.
    """
    mesh = source.data
    points = [local(source.matrix_world @ vertex.co) for vertex in mesh.vertices]
    if max(p.z for p in points) < END_DECK - .3:
        return None
    faces_at_vertex = {i: [] for i in range(len(points))}
    for face in mesh.polygons:
        for index in face.vertices:
            faces_at_vertex[index].append(face)
    vertices, polygons, indices, smoothing = [], [], [], []
    uv_values = [[] for _ in mesh.uv_layers]
    altered, rejected = 0, []
    for group in components(mesh):
        original_faces = {face.index: face for i in group for face in faces_at_vertex[i]}
        edge_counts = {}
        for face in original_faces.values():
            vv = list(face.vertices)
            for a, b in zip(vv, vv[1:] + vv[:1]):
                key = tuple(sorted((a, b)))
                edge_counts[key] = edge_counts.get(key, 0) + 1
        closed = all(count == 2 for count in edge_counts.values())
        faces = [([(points[mesh.loops[i].vertex_index], [Vector(layer.data[i].uv) for layer in mesh.uv_layers]) for i in face.loop_indices], face.material_index, face.use_smooth) for face in original_faces.values()]
        applicable = []
        for volume in volumes:
            if all(max(normal.dot(points[index]) - offset for index in group) > EPS for normal, offset in volume):
                applicable.append(volume)
        if not applicable:
            pieces = [faces]
        elif (not closed and len(faces) != 1) or len(faces)>32:
            rejected.append({'vertices': len(group), 'faces': len(faces), 'reason': 'Nonconvex/open connected component requires separate remodelling'})
            pieces = [faces]
        else:
            pieces = [faces]
            for volume in applicable:
                pieces = [part for piece in pieces for part in subtract_volume(piece, volume, closed)]
        changed = pieces != [faces]
        altered += changed
        if not changed:
            index_map = {index: len(vertices) + offset for offset, index in enumerate(sorted(group))}
            vertices.extend((source.matrix_world @ mesh.vertices[index].co) for index in sorted(group))
            for face in original_faces.values():
                polygons.append(tuple(index_map[i] for i in face.vertices))
                indices.append(face.material_index)
                smoothing.append(face.use_smooth)
                for layer, values in zip(mesh.uv_layers, uv_values):
                    values.extend(Vector(layer.data[i].uv) for i in face.loop_indices)
            continue
        for piece in pieces:
            indexed = {}
            snapped_points = []
            for polygon, material, smooth in piece:
                vv = []
                clean_polygon = []
                for point, uv in polygon:
                    match = next((row for row in snapped_points if (row[0]-point).length<EPS), None)
                    if match is None:
                        match = (point, len(vertices))
                        snapped_points.append(match)
                        vertices.append(world(point))
                    if match[1] not in vv:
                        vv.append(match[1])
                        clean_polygon.append((point, uv))
                if len(vv) < 3:
                    continue
                polygons.append(tuple(vv))
                indices.append(material)
                smoothing.append(smooth)
                for j, values in enumerate(uv_values):
                    values.extend(point[1][j] for point in clean_polygon)
    if not altered:
        return None
    data = bpy.data.meshes.new(PREFIX + source.name + '_mesh')
    data.from_pydata(vertices, [], polygons)
    for material in mesh.materials:
        data.materials.append(material)
    for face, material, smooth in zip(data.polygons, indices, smoothing):
        face.material_index, face.use_smooth = material, smooth
    for old_layer, values in zip(mesh.uv_layers, uv_values):
        layer = data.uv_layers.new(name=old_layer.name)
        assert len(layer.data) == len(values)
        for corner, value in zip(layer.data, values):
            corner.uv = value
        layer.active_render = old_layer.active_render
    bm = bmesh.new()
    bm.from_mesh(data)
    bm.normal_update()
    for faces, is_closed in closed_islands(bm):
        if is_closed and signed_volume(faces) < 0:
            bmesh.ops.reverse_faces(bm, faces=list(faces))
    bm.to_mesh(data)
    bm.free()
    data.update()
    target = bpy.data.objects.new(PREFIX + source.name.removeprefix('CBG202_'), data)
    target['originalObject'] = source['originalObject']
    target['replaces202Object'] = source.name
    target['candidateScope'] = 'Registered highest roof cutbacks; lower transformed202 parts retained'
    return target, {'source202': source.name, 'sourceNative': source['originalObject'], 'target': target.name, 'alteredIslands': altered, 'skippedIslands': rejected}


def review(scene, collection, world, name, viewpoint, focus=(-20,8,45), scale=58):
    camera = bpy.data.objects.new(PREFIX + name + '_camera', bpy.data.cameras.new(PREFIX + name + '_camera'))
    scene.collection.objects.link(camera)
    target = world(focus)
    camera.location = world(viewpoint)
    camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = scale
    scene.camera = camera
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'MATERIAL'
    scene.display.shading.show_cavity = True
    scene.display.shading.show_shadows = True
    scene.display.shading.background_type = 'WORLD'
    scene.world = bpy.data.worlds.new(PREFIX + name + '_world')
    scene.world.color = (.8, .82, .84)
    scene.render.resolution_x, scene.render.resolution_y = 1400, 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(OUT / (name + '.png'))
    bpy.ops.render.render(write_still=True, scene=scene.name)
    bpy.data.objects.remove(camera, do_unlink=True)
    scene.camera = None


def build_candidate():
    OUT.mkdir(parents=True, exist_ok=True)
    assert digest(BASE) == BASE_SHA
    mapping_path = ROOT / 'result/blender/cbg-georegistration202/rebuild-mapping.json'
    mapping = json.loads(mapping_path.read_text())
    audit202 = json.loads((SOURCE.parent / 'audit.json').read_text())
    assert digest(SOURCE) == audit202['componentSha256']
    local, world = frame(mapping)
    landmarks = mapping['tower']['traced_roof_landmarks_local']
    landmark = lambda name: landmarks[name]['local']
    rear_polygon = [landmark(n) for n in ['roofTerraceFrontCoreCorner', 'roofTerraceFrontFarCorner', 'roofTerraceRearFarCorner', 'roofTerraceRearCoreCorner']]
    roof = mapping['tower']['design_roof_envelope_local']
    core_front, core_rear = landmark('coreEndFrontCorner'), landmark('coreEndRearCorner')
    end_polygon = [core_front, [roof[0][0] + .10, core_front[1] -.3], [roof[3][0] + .1, roof[3][1] + .1], core_rear]
    canopy_polygon = [[-6, -1.2], [1.65, -1.2], [1.65, core_front[1]], [-6, core_front[1]]]
    stair_polygon = [landmark(n) for n in ['upperStairFrontRight', 'upperStairFrontLeft', 'upperStairRearLeft', 'upperStairRearRight']]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = 'CBG203_PRIVATE_ROOF_REVIEW'
    context = bpy.data.collections.new('CBG203_CONTEXT202')
    candidate = bpy.data.collections.new('CBG203_PRIVATE_COMPONENT')
    scene.collection.children.link(context)
    scene.collection.children.link(candidate)
    with bpy.data.libraries.load(str(SOURCE), link=False) as (src, dst):
        dst.objects = list(audit202['addedObjects'])
    sources = list(dst.objects)
    for obj in sources:
        context.objects.link(obj)
    for layer in scene.view_layers:
        layer.update()
    before = {o.name: object_fingerprint(o) for o in sources}
    replacements = []
    source_owners = {r['source']: r['sourceOwners'] for r in audit202['records']}
    for source in sources:
        if source.type != 'MESH':
            continue
        name = source['originalObject']
        glass = any(m and ('glass' in m.name.lower() or m.get('webOpacity', 1) < 1) for m in source.data.materials)
        cut_z = REAR_DECK - .01 if glass else REAR_DECK + .30
        volumes = [volume_planes(rear_polygon, cut_z, 56), volume_planes(end_polygon, cut_z, 56)]
        if not any(tag in name for tag in ['external_I_columns', 'roof_and_ground_plates', 'red_roof_recess']):
            volumes.append(volume_planes(canopy_polygon, END_DECK - .01 if glass else END_DECK + .4, 56 if glass else HEIGHT - .38))
        if any(tag in name for tag in ['tower_floor_plates', 'tower_front_galleries']):
            volumes.append(volume_planes(stair_polygon, REAR_DECK - .35, REAR_DECK + .18))
        result = trim_object(source, local, world, volumes)
        if result:
            target, record = result
            record['sourceOwners'] = source_owners.get(name, ['CBG_EXTERIOR'])
            candidate.objects.link(target)
            source.hide_render = True
            replacements.append(record)
            print('ROOF203_TRIM', name, record['alteredIslands'], flush=True)
    material_source = lambda text: next(m for m in bpy.data.materials if text in m.name)
    concrete = material_source('exposed_concrete')
    steel = material_source('charcoal_thermal_frames')
    glazing = next(o for o in sources if 'neutral_end_wall_glazing' in o.name).data.materials[0].copy()
    glazing.name = PREFIX + 'terrace_guard_glass'
    glazing.diffuse_color = (.38, .61, .62, 1)
    glazing['webOpacity'] = .28
    glazing['webClosedGlazing'] = True
    paving = concrete.copy()
    paving.name = PREFIX + 'paving'
    paving.diffuse_color = (.61, .59, .51, 1)
    mesh_records = []
    def mesh_object(name, vertices, faces, material, role, owner='CBG_EXTERIOR'):
        mesh = bpy.data.meshes.new(PREFIX + name)
        mesh.from_pydata([world(p) for p in vertices], [], faces)
        mesh.materials.append(material)
        mesh.update()
        uv = mesh.uv_layers.new(name='SurfaceUV')
        for face in mesh.polygons:
            for index in face.loop_indices:
                p = vertices[mesh.loops[index].vertex_index]
                uv.data[index].uv = (p[0], p[1])
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.normal_update()
        for ff, closed in closed_islands(bm):
            assert closed, name
            if signed_volume(ff) < 0:
                bmesh.ops.reverse_faces(bm, faces=list(ff))
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(mesh.name, mesh)
        obj['candidateScope'] = role
        obj['destinationCollection'] = owner
        obj['zEvidence'] = 'Inherited52.2m/13equalstoreys; provisional, not measured from2016plan'
        candidate.objects.link(obj)
        mesh_records.append({'target': obj.name, 'sourceOwners': [owner], 'role': role})
        return obj
    def prism(name, poly, bottom, top, material, role):
        n = len(poly)
        vertices = [(x, y, z) for z in [bottom, top] for x, y in poly]
        faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
        faces.extend((i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n))
        return mesh_object(name, vertices, faces, material, role)
    def strip(name, a, b, width, bottom, top, material, role):
        a, b = Vector(a), Vector(b)
        direction = (b - a).normalized()
        normal = Vector((-direction.y, direction.x)) * width / 2
        poly = [tuple(a-normal), tuple(b-normal), tuple(b+normal), tuple(a+normal)]
        return prism(name, poly, bottom, top, material, role)
    def box(name, lo, hi, material, role):
        return mesh_object(name, [tuple(lo[i]+(hi[i]-lo[i])*bit[i] for i in range(3)) for bit in CORNERS], BOX_FACES, material, role)
    prism('registered_rear_terrace_deck', rear_polygon, REAR_DECK -.08, REAR_DECK + .04, concrete, 'Four202registered2016planlandmarks; inheritedZ')
    inset = [(x + (-.08 if x > -30 else .08), y + (.06 if y < 12 else -.06)) for x, y in rear_polygon]
    prism('registered_rear_terrace_paving', inset, REAR_DECK + .04, REAR_DECK + .075, paving, 'Photographedpavedterrace; exacttilegridunverified')
    prism('registered_end_setback_deck', end_polygon, REAR_DECK -.08, REAR_DECK + .04, concrete, 'Registeredcoreendsetback; provisionalZ')
    prism('open_canopy_terrace_deck', [[-6,.05],[.38,.05],[.9,7.92],[-5.78,8.2]], END_DECK + .05, END_DECK + .17, concrete, 'PhotographedopenG6G7deck; parapetdimensionsestimated')
    for i, (a, b) in enumerate(zip(rear_polygon, rear_polygon[1:] + rear_polygon[:1])):
        if i == 3:
            continue
        if i == 0:
            strip('terrace_enclosure_glass', a, b, .04, REAR_DECK+.11, HEIGHT-.2, glazing, 'Planofficeedgeenclosure; detailmoduleunverified')
            strip('terrace_enclosure_sill', a, b, .12, REAR_DECK+.05, REAR_DECK+.15, steel, 'Estimatedenclosuresill')
            strip('terrace_enclosure_head', a, b, .12, HEIGHT-.24, HEIGHT-.15, steel, 'Estimatedenclosurehead')
            for p in range(9):
                t=p/8
                point = Vector(a).lerp(Vector(b), t)
                box('terrace_enclosure_post_'+str(p), (*tuple(point-Vector((.04,.04))),REAR_DECK+.1),(*tuple(point+Vector((.04,.04))),HEIGHT-.15),steel,'Estimatedmodule; notmeasured')
        else:
            strip('rear_terrace_glass_guard_'+str(i), a, b, .03, REAR_DECK+.15, REAR_DECK+1.18, glazing, 'Photographedroofguard; estimatedheight')
            strip('rear_terrace_guard_shoe_'+str(i), a, b, .13, REAR_DECK+.05, REAR_DECK+.15, steel, 'Estimatedguardshoe')
    for i,(a,b) in enumerate([([-.02,.02], [.55,7.95]), ([-5.9,.01],[.35,.01])]):
        strip('open_end_glass_guard_'+str(i),a,b,.03,END_DECK+.22,END_DECK+1.30,glazing,'Builtphotographopenendguard; estimatedheight')
        strip('open_end_guard_shoe_'+str(i),a,b,.12,END_DECK+.15,END_DECK+.24,steel,'Estimatedguardshoe')
    # Core end follows its traced slanted front/rear edge. Screen is a visible
    # four-row photographic envelope only; no equipment function is invented.
    screen = glazing.copy()
    screen.name = PREFIX+'pale_green_screen'
    screen.diffuse_color = (.42,.57,.55,1)
    screen['webOpacity'] = .8
    a,b=Vector(core_front),Vector(core_rear)
    for col in range(4):
        lo=a.lerp(b,(col+.04)/4)
        hi=a.lerp(b,(col+.96)/4)
        for row in range(4):
            strip('screen_'+str(col)+'_'+str(row),lo,hi,.027,REAR_DECK+.24+row*.885,REAR_DECK+.24+row*.885+.865,screen,'Builtendphotographscreen; XYregisteredcoreedge; heightestimated')
    # Twin suspended folded forms are visible in the archived built end
    # photograph. Their function and absolute dimensions remain unidentified.
    metal=steel.copy()
    metal.name=PREFIX+'folded_canopy_metal'
    metal.diffuse_color=(.29,.32,.33,1)
    for assembly,y in enumerate([.55,4.05]):
        x0,x1=-5.65,-.45
        low,high=48.90,51.55
        points=[(x0,y,low),(x1,y,high),(x1,y+2.80,high),(x0,y+2.80,low),
                (x0,y,low+.22),(x1,y,high+.22),(x1,y+2.80,high+.22),(x0,y+2.80,low+.22)]
        mesh_object('suspended_folded_canopy_'+str(assembly),points,BOX_FACES,metal,'Builtendphotographtwinfoldedsilhouette; equipmentfunctionanddimensionsunverified')
        box('suspended_folded_end_return_'+str(assembly),(x1-.16,y,50.65),(x1+.02,y+2.80,51.77),metal,'Photographicfoldedassemblyendreturn; estimateddimensions')
        for rib in range(8):
            x=x0+.18+rib*.68
            z=low+(x-x0)*(high-low)/(x1-x0)
            box('suspended_folded_underside_rib_'+str(assembly)+'_'+str(rib),(x,y-.025,z-.10),(x+.055,y+2.825,z+.025),steel,'Photographicundersiderib; countandwidthestimated')
    gravel=paving.copy()
    gravel.name=PREFIX+'core_roof_gravel'
    gravel.diffuse_color=(.41,.39,.33,1)
    turf=paving.copy()
    turf.name=PREFIX+'core_green_roof'
    turf.diffuse_color=(.17,.29,.045,1)
    core_polygon=[rear_polygon[0],core_front,core_rear,rear_polygon[3]]
    core_centre=sum((Vector(p) for p in core_polygon),Vector((0,0)))/4
    inner_core=[tuple(Vector(p).lerp(core_centre,.06)) for p in core_polygon]
    green_core=[tuple(Vector(p).lerp(core_centre,.12)) for p in core_polygon]
    prism('registered_core_roof_gravel',inner_core,HEIGHT+.015,HEIGHT+.075,gravel,'Builtphotographcoregreencap;202registeredcoreoutline; heightsestimated')
    prism('registered_core_green_cap',green_core,HEIGHT+.075,HEIGHT+.125,turf,'Photographedgreenroofmass; speciesandcurrentplantlayoutunverified')
    # Return-stair XY comes from all four independently registered corners.
    # Its28treads and equalrise remain design-envelope estimates.
    front_right, front_left, rear_left, rear_right = [Vector(p) for p in stair_polygon]
    wood=material_source('oak')
    tread_vertices,tread_faces=[],[]
    def stair_point(u,v,z):
        return tuple(front_left.lerp(front_right,u).lerp(rear_left.lerp(rear_right,u),v))+ (z,)
    for flight in range(2):
        u0,u1=(.53,.95) if flight==0 else (.05,.47)
        for step in range(14):
            v0=1-step*.72/14 if flight==0 else .28+step*.72/14
            v1=v0-.72/14 if flight==0 else v0+.72/14
            top=END_DECK+(flight*14+step+1)*STEP/28
            points=[stair_point(u,v,z) for z in [top-.12,top] for u,v in [(u0,v0),(u1,v0),(u1,v1),(u0,v1)]]
            start=len(tread_vertices)
            tread_vertices.extend(points)
            tread_faces.extend(tuple(start+i for i in f) for f in BOX_FACES)
    mesh_object('registered_upper_return_stair_treads',tread_vertices,tread_faces,wood,'202fourcornerstairwell;28treadsandinheritedlevelriseestimated')
    prism('registered_upper_return_stair_mid_landing',[stair_point(u,v,0)[:2] for u,v in [(0,0),(1,0),(1,.28),(0,.28)]],END_DECK+STEP/2-.17,END_DECK+STEP/2,concrete,'Designreturnstairmidlanding; dimensionsestimated')
    # Crop only the obsolete ninth straight flight in202 counterparts. Lower
    # flights remain untouched and do not imply a verified upper connection.
    stair_parts={'tower_meandering_stair_treads':24,'tower_stair_stringers':2,'tower_stair_handrails':2,'tower_stair_slotted_pale_guards':90,'tower_stair_landing_platforms':1}
    for source in sources:
        key=next((k for k in stair_parts if source['originalObject'].endswith(k)),None)
        if key is None:
            continue
        previous=next((r for r in replacements if r['source202']==source.name),None)
        if previous:
            bpy.data.objects.remove(bpy.data.objects[previous['target']],do_unlink=True)
            replacements.remove(previous)
        target=source.copy()
        target.data=source.data.copy()
        target.name=PREFIX+'lower_retained_'+source['originalObject']
        target['originalObject']=source['originalObject']
        target['replaces202Object']=source.name
        target.hide_render=False
        bm=bmesh.new()
        bm.from_mesh(target.data)
        bm.verts.ensure_lookup_table()
        count=stair_parts[key]*8
        bmesh.ops.delete(bm,geom=list(bm.verts)[-count:],context='VERTS')
        bm.to_mesh(target.data)
        bm.free()
        candidate.objects.link(target)
        source.hide_render=True
        replacements.append({'source202':source.name,'sourceNative':source['originalObject'],'target':target.name,'removedObsoleteUpperComponents':stair_parts[key],'sourceOwners':source_owners[source['originalObject']]})
    assert all(object_fingerprint(obj)==before[obj.name] for obj in sources)
    added=list(candidate.objects)
    # Validate native outward solids and reject degenerate geometry.
    topology=[]
    for obj in added:
        assert all(math.isfinite(value) for vertex in obj.data.vertices for value in vertex.co)
        assert all(face.area>1e-10 for face in obj.data.polygons),obj.name
        bm=bmesh.new()
        bm.from_mesh(obj.data)
        bm.normal_update()
        islands=closed_islands(bm)
        inward=sum(closed and signed_volume(ff)<-1e-7 for ff,closed in islands)
        assert inward==0,(obj.name,inward)
        topology.append({'object':obj.name,'closedIslands':sum(c for _,c in islands),'openIslands':sum(not c for _,c in islands),'inwardClosedIslands':inward})
        bm.free()
    # Rays start above each open area. Hidden originals are excluded, so this
    # proves the restored terrace is not covered by an inherited52.2mplate.
    trees=[]
    for obj in scene.objects:
        if obj.type=='MESH' and not obj.hide_render:
            trees.append((obj.name,BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],[list(f.vertices) for f in obj.data.polygons],all_triangles=False)))
    geometric_checks=[]
    def raycheck(label,xy,start_z,expected_z):
        origin=world((*xy,start_z))
        hits=[]
        for name,tree in trees:
            point,normal,index,distance=tree.ray_cast(origin,Vector((0,0,-1)),20)
            if point is not None:
                hits.append((distance,name,point.z))
        hit=min(hits)
        assert abs(hit[2]-expected_z)<.20,(label,hit,expected_z)
        geometric_checks.append({'sample':label,'localXY':list(xy),'startZ':start_z,'firstHitObject':hit[1],'hitZ':hit[2],'expectedZ':expected_z,'toleranceMetres':.20})
    for t in [.25,.5,.75]:
        aa=Vector(rear_polygon[0]).lerp(Vector(rear_polygon[1]),t)
        bb=Vector(rear_polygon[3]).lerp(Vector(rear_polygon[2]),t)
        raycheck('rear_terrace_'+str(t),aa.lerp(bb,.5),56,REAR_DECK+.075)
    centre=sum((Vector(p) for p in end_polygon),Vector((0,0)))/4
    raycheck('core_end_setback',centre,56,REAR_DECK+.04)
    raycheck('canopy_void_between_folded_assemblies',Vector((-2,3.7)),HEIGHT-.5,END_DECK+.17)
    raycheck('canopy_void_below_folded_assembly',Vector((-2,3)),48.6,END_DECK+.17)
    review(scene,candidate,world,'registered-roof-front',(-80,-60,86))
    review(scene,candidate,world,'registered-roof-rear',(-65,68,100))
    review(scene,candidate,world,'registered-open-end',(24,4,47),focus=(-2,4,49),scale=22)
    review_path=OUT/'cbg-roof203-review.blend'
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(review_path),check_existing=False)
    path=OUT/'cbg-roof203-component.blend'
    bpy.data.libraries.write(str(path),set(added),fake_user=True,compress=True)
    fingerprints={obj.name:object_fingerprint(obj) for obj in added}
    report={'status':'private-partial-reconstruction-not-for-release','baselineSha256':BASE_SHA,'source202Sha256':digest(SOURCE),'mappingSha256':digest(mapping_path),'reviewPath':str(review_path.relative_to(ROOT)),'reviewSha256':digest(review_path),'componentPath':str(path.relative_to(ROOT)),'componentSha256':digest(path),'targetCollection':'CBG_EXTERIOR','addedObjects':[obj.name for obj in added],'archivedObjects':sorted({r['sourceNative'] for r in replacements}),'changedObjects':[],'replacements':replacements,'newGeometry':mesh_records,'cutbackFootprints':{'rearTerrace':rear_polygon,'coreEndSetback':end_polygon,'openCanopy':canopy_polygon,'upperStairWell':stair_polygon},'inheritedProvisionalHeights':{'top':HEIGHT,'rearDeck':REAR_DECK,'canopyDeck':END_DECK},'references':[{'path': 'data/collections/cbg_roof_registration/level12-plan-rshp-2016.jpg', 'sha256': '5dc5b500a66ebcd630031c999f8a347a0de21daab443d3f009908337c32c29cc', 'role': 'published2016designplan; XYonly', 'captureDate': 'unknown'}, {'path': 'data/collections/campus_photos_round2/images/CBG/CBG_cbg_joas_05.jpg', 'sha256': '175417c5a88f5d6278476a8edf5b95891ea8d028dc51a8bb794aa91663d65b39', 'role': 'builtphotograph; openend,screen,twinfoldedcanopy', 'captureDate': 'unknown'}, {'path': 'data/collections/campus_photos_round2/images/CBG/CBG_cbg_joas_17.jpg', 'sha256': '57793c8e36552b4d60558f525b9df35ced609eba655647a1b06965e8cfa3d86e', 'role': 'builtphotograph; greencap,boundedroofgarden', 'captureDate': 'unknown'}],'heightEvidence':'Inherited52.2m/13equalstoreys; no new current measured elevation established','topology':topology,'geometricChecks':geometric_checks,'remainingBeforeRelease':['Boundedgardenbeds,furniture,coreterraceaccessandserviceequipmentremainunmodelled.', 'Reconcile nonuniform actual upper floor heights and screen/canopy elevations against current measured evidence.','Integrate roof voids after independent office module reconstruction; do not overwrite its lower facade objects.','Twin folded canopy forms now reproduce the photographedsilhouette; exactdimensions,equipmentfunctionandconnectionsremainunverified.','Upper stair finalguards,stringers,toplandingandconnectionremainunverified; lower eighth flight not connected by this candidate.','Shared internal partition faces between independently closed trim fragments remain; no boolean-union claim.']}
    (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(path),link=False) as (src,dst):
        dst.objects=list(fingerprints)
    for obj in dst.objects:
        bpy.context.scene.collection.objects.link(obj)
    for layer in bpy.context.scene.view_layers:
        layer.update()
    assert all(object_fingerprint(obj)==fingerprints[obj.name] for obj in dst.objects)
    report['verification']={'componentReopened':True,'allAddedFingerprintsMatch':True,'baselineUnchanged':digest(BASE)==BASE_SHA,'source202Unchanged':digest(SOURCE)==audit202['componentSha256'],'all202SourceFingerprintsPreserved':True,'inwardClosedIslands':0,'geometricAreasFinitePositive':True}
    bpy.ops.wm.open_mainfile(filepath=str(review_path))
    for layer in bpy.context.scene.view_layers:
        layer.update()
    assert all(object_fingerprint(bpy.data.objects[name])==expected for name,expected in fingerprints.items())
    assert all(object_fingerprint(bpy.data.objects[name])==expected for name,expected in before.items())
    report['verification']['nativeReviewMainfileSavedAndReopened']=True
    (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('CBG203_ROOF_REOPENED',len(added),len(replacements),flush=True)


if __name__=='__main__':
    build_candidate()
