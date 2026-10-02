"""Correct OLD's Houghton frontage using the July 2024 planning elevation.
Run in Blender Text Editor. Labelled AOD heights define levels; horizontal
registration, window edges and roof depths are visual estimates, not a survey.
Original geometry is archived intact. Other street elevations are retained.
"""
from pathlib import Path
import array, hashlib, json, math, shutil, sys
import bpy, bmesh
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage112'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v111.blend'))
for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
collection = bpy.data.collections['OLD_EXTERIOR']
frame = json.loads((ROOT / 'result/blender/stage52/old-houghton-audit.json').read_text())
origin, right, outward = [Vector(frame[k]) for k in ['origin', 'right', 'outward']]
angle = math.atan2(right.y, right.x)


def fingerprint(obj):
    h = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        vertices = array.array('f', [0]) * (3 * len(obj.data.vertices))
        indices = array.array('i', [0]) * len(obj.data.loops)
        obj.data.vertices.foreach_get('co', vertices)
        obj.data.loops.foreach_get('vertex_index', indices)
        h.update(vertices.tobytes()); h.update(indices.tobytes())
    h.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return h.hexdigest()


before = {o.name: fingerprint(o) for o in bpy.data.objects}
visibility = {o.name: o.hide_render for o in bpy.data.objects}
# The entire collinear frontage includes ring 11->12, omitted by the old builder.
left, end = -34.50, 22.48
length = end - left
px = lambda p: left + (p - 240) / 1294 * length
entry_centre = px(424)
entry_width = px(608) - left
width_scale = entry_width / 17.8
# Ground street L-GL is 18.100AOD; the entrance landing is 19.345AOD.
landing = 1.245
height_scale = (34.600 - 18.100 - landing) / (19.6 - .70)
base_offset = landing - .70 * height_scale
basis = Matrix((right, outward, Vector((0, 0, 1)))).transposed().to_4x4()
transform = (Matrix.Translation(origin + right * entry_centre + Vector((0, 0, base_offset)))
             @ basis @ Matrix.Diagonal((width_scale, 1, height_scale, 1))
             @ basis.inverted() @ Matrix.Translation(-origin))
replaced, copies, clipped = [], [], []


def archive(source):
    source.hide_render = True
    source.hide_set(True)
    replaced.append(source.name)


def copy_object(source, mesh=None, move=False, label='retained'):
    obj = source.copy()
    obj.data = mesh if mesh is not None else source.data.copy()
    obj.name = 'OLD_V112_' + label + '_' + source.name.removeprefix('OLD_')
    collection.objects.link(obj)
    if move:
        obj.matrix_world = transform @ source.matrix_world
    obj.hide_render = False
    obj.hide_set(False)
    copies.append(obj.name)
    return obj


# Bespoke entry details move together: joints, panes, names, vector plaques and
# open sculpture strands. Roof and terrace parts are rebuilt, not transformed.
portal_prefixes = ('OLD_V52_Houghton_', 'OLD_D5_entry65_', 'OLD_D5_arch69_',
                   'OLD_D5_arms74_', 'OLD_D5_portal78_', 'OLD_D5_portal79_',
                   'OLD_D5_finalsale84_', 'OLD_V97_', 'OLD_V100_', 'OLD_V103_', 'OLD_V111_')
portal_names = {'OLD_Arch_spandrels', 'OLD_Ashlar_course_shadow_lines',
                'OLD_Door_inner_shadow', 'OLD_D5_windows85_retained_V52_Houghton_blue'}
roof_names = {'OLD_Terrace_parapet_lower_rail', 'OLD_Terrace_parapet_coping',
              'OLD_Mansard_dormer_cheeks', 'OLD_Mansard_top_coping'}
originals = list(collection.all_objects)
for source in originals:
    if source.hide_render:
        continue
    if source.name in roof_names or source.name.startswith('OLD_D5_wings79_'):
        archive(source)
    elif source.name.startswith('OLD_D5_entablature77_'):
        if any(k in source.name for k in ['parapet', 'screen', 'mansard', 'dormer']):
            archive(source)
        else:
            copy_object(source, move=True, label='entry'); archive(source)
    elif source.name in portal_names or source.name.startswith(portal_prefixes):
        # The obsolete small stair flight is replaced by six continuous risers.
        if source.name != 'OLD_D5_entry65_stone':
            copy_object(source, move=True, label='entry')
        archive(source)

# Shared window/cornice batches contain all elevations. Split their old entry
# parts from other street faces, then erase only the obsolete Houghton strip.
shared_prefixes = ('OLD_Window_', 'OLD_D5_V16_', 'OLD_D5_V17_', 'OLD_D5_windows85_')
for source in originals:
    if source.hide_render or source.type != 'MESH':
        continue
    if not (source.name.startswith(shared_prefixes) or source.name in
            {'OLD_Secondary_stone_facades', 'OLD_Secondary_roof_deck', 'OLD_Cornices_and_stringcourses'}):
        continue
    roof = source.name == 'OLD_Secondary_roof_deck'
    plane_depth = -8 if roof else -.72
    mesh = source.data.copy()
    bm = bmesh.new(); bm.from_mesh(mesh)
    inv = source.matrix_world.inverted()
    # Bisect the broad roof triangles and side returns before selecting faces.
    for location, normal in [(origin + outward * plane_depth, outward),
                             (origin + right * left, right),
                             (origin + right * end, right),
                             *([] if roof else [(origin-right*9.15,right),(origin+right*9.15,right),
                                                (origin+Vector((0,0,20)),Vector((0,0,1)))])]:
        bmesh.ops.bisect_plane(bm, geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
                              plane_co=inv @ location,
                              plane_no=source.matrix_world.to_3x3().transposed() @ normal, dist=1e-6)
    entry_faces, street_faces = [], []
    for face in bm.faces:
        p = source.matrix_world @ face.calc_center_median() - origin
        x, depth, z = p.dot(right), p.dot(outward), p.z
        bespoke_window = source.name.startswith('OLD_D5_windows85_casements')
        central = abs(x) < 9.15 and depth > -4.6
        if central and not roof and source.name != 'OLD_Secondary_stone_facades':
            street_faces.append(face)
            if z < 20 and (depth > -.72 or bespoke_window):
                entry_faces.append(face)
        elif left - 1e-5 <= x <= end + 1e-5 and depth >= plane_depth - 1e-5:
            street_faces.append(face)
    if not street_faces:
        bm.free(); bpy.data.meshes.remove(mesh); continue
    if entry_faces:
        selected = set(entry_faces)
        moved_mesh = source.data.copy()
        bm.to_mesh(mesh)
        moving = bmesh.new(); moving.from_mesh(mesh)
        # Face order is maintained by from_mesh after the preceding bisects.
        bm.faces.ensure_lookup_table(); bm.faces.index_update(); moving.faces.ensure_lookup_table()
        keep = {f.index for f in selected}
        bmesh.ops.delete(moving, geom=[f for f in moving.faces if f.index not in keep], context='FACES')
        moving.to_mesh(moved_mesh); moving.free(); moved_mesh.update()
        copy_object(source, moved_mesh, move=True, label='entry')
    bmesh.ops.delete(bm, geom=street_faces, context='FACES')
    bm.to_mesh(mesh); bm.free(); mesh.update()
    if mesh.polygons:
        retained = copy_object(source, mesh)
    else:
        bpy.data.meshes.remove(mesh); retained = None
    clipped.append({'source': source.name, 'removedFaces': len(street_faces),
                    'entryFaces': len(entry_faces), 'retained': retained.name if retained else None})
    archive(source)

# Re-anchor the two low railing posts to the newly exposed second tread.
# Door-frame members and the top rail stay intact; only the post feet and their
# small steel base plates receive the change in height.
for family in ['frame', 'steel']:
    obj=bpy.data.objects['OLD_V112_entry_D5_entry65_'+family]
    source=bpy.data.objects['OLD_D5_entry65_'+family]
    inverse=obj.matrix_world.inverted().to_3x3()
    for start in range(0,len(source.data.vertices),8):
        verts=list(source.data.vertices[start:start+8])
        if len(verts)!=8:continue
        positions=[source.matrix_world@v.co-origin for v in verts]
        depth=sum(p.dot(outward)for p in positions)/8
        x=sum(p.dot(right)for p in positions)/8
        if abs(depth-2.55)>.03 or min(abs(x+4.2),abs(x-1.5))>.03:continue
        low=min(p.z for p in positions)
        if low>.05:continue
        # Lower frame vertices form a vertical post; the steel plate translates
        # as a whole so its thickness and its connection remain unchanged.
        delta=landing*2/6-(base_offset+low*height_scale)
        for index,p in enumerate(positions):
            if family=='steel' or abs(p.z-low)<1e-5:
                obj.data.vertices[start+index].co+=inverse@Vector((0,0,delta))
    obj.data.update()

materials.clear()
for key, source_name in [('stone', 'OLD_V52_stone'), ('blue', 'OLD_Blue_painted_steel'),
                         ('brick', 'OLD_V77_mansard_brick')]:
    materials[key] = bpy.data.materials[source_name].copy()
    materials[key].name = 'OLD_V112_' + key
for key, colour, roughness, metallic in [('glass', (.18, .23, .25), .19, .08),
                                       ('roof', (.22, .23, .22), .85, 0),
                                       ('iron', (.09, .11, .12), .55, .45)]:
    m = bpy.data.materials.new('OLD_V112_' + key); m.use_nodes = True
    m.diffuse_color = (*colour, 1)
    p = m.node_tree.nodes['Principled BSDF']; p.inputs['Base Color'].default_value = m.diffuse_color
    p.inputs['Roughness'].default_value = roughness; p.inputs['Metallic'].default_value = metallic
    materials[key] = m
batches = {}


def point(x, depth, z):
    return origin + right * x + outward * depth + Vector((0, 0, z))


def batch(family, material):
    key = family + '_' + material
    if key not in batches:
        batches[key] = Geometry('OLD', 'houghton112_' + key, material)
    return batches[key]


def box(family, material, x, depth, z, w, d, h):
    if min(w, d, h) > 1e-6:
        batch(family, material).box(point(x, depth, z), (w, d, h), angle)


openings = []


def window(x, w, low, high, columns, rows, zone, depth=-.10):
    box(zone, 'glass', x, depth, (low + high) / 2, w, .04, high-low)
    for sign in [-1, 1]:
        box(zone, 'blue', x + sign * (w/2-.025), depth+.06, (low+high)/2, .05, .075, high-low)
    for z in [low, high]:
        box(zone, 'blue', x, depth+.06, z, w, .075, .05)
    for i in range(1, columns):
        box(zone, 'blue', x-w/2+w*i/columns, depth+.075, (low+high)/2, .035, .08, high-low)
    for i in range(1, rows):
        box(zone, 'blue', x, depth+.075, low+(high-low)*i/rows, w, .08, .032)
    for sign in [-1, 1]:
        box(zone, 'stone', x+sign*(w/2+.06), depth+.14, (low+high)/2, .12, .20, high-low+.14)
    for z in [low-.07, high+.07]:
        box(zone, 'stone', x, depth+.15, z, w+.28, .25, .14)
    openings.append({'x': x, 'width': w, 'low': low, 'high': high, 'columns': columns,
                     'rows': rows, 'zone': zone, 'depth': depth})


def wall(zone, material, a, b, low, high, depth=-.23, thickness=.46):
    holes = [o for o in openings if o['zone'] == zone]
    levels = sorted({low, high, *[max(low, min(high, o[k])) for o in holes for k in ['low', 'high']]})
    for lo, hi in zip(levels, levels[1:]):
        active = sorted((o['x']-o['width']/2-.015, o['x']+o['width']/2+.015)
                        for o in holes if o['low'] < (lo+hi)/2 < o['high'])
        cursor = a
        for start, stop in active + [(b, b)]:
            start, stop = max(a, start), min(b, stop)
            if start > cursor:
                box(zone, material, (cursor+start)/2, depth, (lo+hi)/2, start-cursor, thickness, hi-lo)
            cursor = max(cursor, stop)


# Long middle section: ten lower bays, nine upper bays, two terrace levels.
central = [px(p) for p in [631, 698, 764, 831, 898, 963, 1030, 1095, 1163, 1228]]
for index, (low, high) in enumerate([(4.48, 6.95), (8.32, 10.82), (12.30, 14.12), (15.45, 16.82)]):
    for x in central if index < 2 else central[1:]:
        window(x, 1.30, low, high, 3, 6 if index < 2 else 4, 'middle')
for x in central:
    window(x, 1.35, .05, 1.42, 3, 2, 'middle')
wall('middle', 'stone', px(608), px(1250), 0, 19.45)
for z, h in [(1.9, .18), (3.75, .20), (7.4, .24), (11.6, .24), (14.7, .25), (18.4, 1.04)]:
    box('middle', 'stone', (px(608)+px(1250))/2, .09, z, px(1250)-px(608), .55, h)
# Five-bay Clare Market end pavilion has the historic tall second-storey lights.
corner_centres = [px(p) for p in [1296, 1360, 1424, 1488]]
for low, high in [(4.48, 6.95), (8.20, 12.00), (13.65, 15.62), (17.54, 19.37)]:
    for x in corner_centres:
        window(x, 1.24, low, high, 3, 6 if high-low > 2 else 4, 'corner')
for x in corner_centres:
    window(x, 1.3, .04, 1.44, 3, 2, 'corner')
wall('corner', 'stone', px(1250), end, 0, 20.10)
for z, h in [(1.9, .2), (3.8, .25), (12.55, .26), (16.4, .35), (20.1, .27)]:
    box('corner', 'stone', (px(1250)+end)/2, .12, z, end-px(1250), .64, h)
# The right pavilion actually has four full bays; the transition bay belongs to
# the centre. Source drawings distinguish it from the five-bay entrance wing.
# Close the basement plinth beneath the lifted entrance wing. It meets the
# existing street datum while the door landing remains at the labelled GF level.
box('entry-base', 'stone', entry_centre, -.23, base_offset/2, entry_width, .46, base_offset)
# Front landing and six risers replace the displaced generic four-step flight.
for i in range(6):
    height = landing * (i+1)/6
    box('steps', 'stone', entry_centre, 2.9-i*.30, height/2, 8.0, .30, height)
box('steps', 'stone', entry_centre, .275, landing/2, 8, 1.95, landing)
# Entrance upper storey: five ordinary windows below the two-row mansard.
for c in [299, 365, 429, 490, 553]:
    window(px(c), 1.24, 18.18, 19.49, 3, 4, 'entry-attic', depth=-.48)
wall('entry-attic', 'stone', left, px(608), 17.0, 20.10, depth=-.61, thickness=.30)
for z, h in [(17.02, .25), (20.10, .25)]:
    box('entry-attic', 'stone', (left+px(608))/2, -.36, z, entry_width, .50, h)
# Low iron balconies below four windows, as shown in the architect elevation.
for c in [299, 365, 490, 553]:
    x = px(c)
    for z in [17.45, 17.96]:
        box('balcony', 'iron', x, -.04, z, 1.8, .04, .04)
    for i in range(7):
        box('balcony', 'iron', x-.9+i*.3, -.04, 17.70, .028, .035, .50)
# Twelve dormers: lower triangular stone pediments, upper modest flush caps.
roof_low, roof_high = 20.10, 27.14
mansard = []
for row, (lo, hi, depth) in enumerate([(21.12, 23.13, -1.20), (24.78, 26.55, -2.98)]):
    for c in [247, 307, 369, 430, 491, 553]:
        x = px(c); w = 1.27
        # The far-left dormer meets Connaught's silhouette; keep its stone casing
        # inside the old-building frontage rather than projecting across GIS.
        if c == 247:
            x = max(x, left + .85)
        window(x, w, lo, hi, 2, 2, 'mansard', depth=depth)
        mansard.append(openings[-1])
        for sign in [-1, 1]:
            edge = x+sign*(w/2+.14)
            batch('mansard', 'stone').add([point(edge, depth, lo-.07), point(edge, depth-.27, lo-.07),
                                          point(edge, depth-.42, hi+.11), point(edge, depth, hi+.11)], [(0, 1, 2, 3)])
        if row == 0:
            # Closed triangular prism, clear of the rectangular glazed opening.
            v = [point(x+dx, d, z) for d in [depth-.12, depth+.21]
                 for dx, z in [(-.94, hi+.16), (.94, hi+.16), (0, hi+.99)]]
            batch('pediments', 'stone').add(v, [(0,2,1),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)])
        else:
            box('upper-caps', 'stone', x, depth+.03, hi+.14, w+.28, .39, .14)
# Cut the sloping brown tiled surface around all dormer windows.
def slope_depth(z):
    return -.44 - 3.05*(z-roof_low)/(roof_high-roof_low)
levels = sorted({roof_low, roof_high, *[o[k] for o in mansard for k in ['low','high']]})
for lo, hi in zip(levels, levels[1:]):
    active = sorted((o['x']-o['width']/2-.14, o['x']+o['width']/2+.14)
                    for o in mansard if o['low'] < (lo+hi)/2 < o['high'])
    cursor = left
    for start, stop in active+[(px(608), px(608))]:
        start, stop = max(left,start), min(px(608),stop)
        if start > cursor:
            v = [point(cursor,slope_depth(lo),lo),point(start,slope_depth(lo),lo),
                 point(start,slope_depth(hi),hi),point(cursor,slope_depth(hi),hi)]
            batch('mansard', 'brick').add(v, [(0,1,2,3)])
        cursor = max(cursor,stop)
box('roof-coping', 'stone', (left+px(608))/2, -3.49, 27.14, entry_width, .36, .17)
# Front roof depth is estimated. The old continuous 24.55m roof is erased only
# in this eight-metre street strip, leaving unsurveyed rear structures archived.
for a,b,z in [(left,px(608),27.14),(px(608),px(1081),23.79),(px(1081),end,20.10)]:
    batch('terrace-decks','roof').add([point(a,-8,z),point(b,-8,z),point(b,-3.50 if a==left else -1.10,z),point(a,-3.50 if a==left else -1.10,z)],[(0,1,2,3)])
# Three broad modern glazed fields above the central terrace, with stone piers.
for a,b in [(618,729),(739,944),(955,1081)]:
    window((px(a)+px(b))/2,px(b)-px(a),21.03,23.17,3 if b-a<130 else 6,1,'roof-glazing',depth=-2)
wall('roof-glazing','stone',px(608),px(1081),20.1,23.79,depth=-2.15,thickness=.3)
for z in [20.1,23.79]:
    box('roof-glazing','stone',(px(608)+px(1081))/2,-1.80,z,px(1081)-px(608),.7,.25)
# Open metal terrace rails; no solid wall in front of the upper glazing.
for a,b,z,d in [(px(608),px(1250),19.45,-.11),(px(608),px(1190),23.79,-1.10),(px(1081),end,20.1,-1.1)]:
    for h in [.08,.98]:box('roof-rails','iron',(a+b)/2,d,z+h,b-a,.045,.045)
    count=max(1,round((b-a)/1.25))
    for i in range(count+1):box('roof-rails','iron',a+(b-a)*i/count,d,z+.53,.045,.045,1.05)

added=[]
for g in batches.values():
    obj=g.finish();added.append(obj.name)
    for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
    obj['scope']='2024 proposed elevation; labelled AOD heights, estimated GIS registration and unlabelled profiles'
for scene in bpy.data.scenes:
    for layer in scene.view_layers:layer.update()
assert all(fingerprint(bpy.data.objects[n])==h for n,h in before.items())
for name in ['room-studies.json','room-spaces.json','building-review.json']:
    shutil.copyfile(ROOT/'result/blender/stage111-old'/name,OUT/name)
audit={'version':112,'baseline':111,'originalFingerprints':before,'originalVisibility':visibility,
       'archived':replaced,'copies':copies,'clipped':clipped,'addedObjects':added,
       'origin':list(origin),'right':list(right),'outward':list(outward),'entryCentre':entry_centre,
       'entryWidth':entry_width,'widthScale':width_scale,'heightScale':height_scale,'landing':landing,'baseOffset':base_offset,
       'frontage':[left,end],'openings':openings,'mansardCount':len(mansard),'pedimentCount':6,
       'drawing':'LSEOLD-HBA-V1-XX-DR-A-080251 P2, 12 July 2024',
       'source':'data/collections/old-roof-2024/proposed-south.pdf',
       'limits':['Planning proposal, not an as-built survey or 2026 condition record',
                 'Horizontal GIS registration, window edges, roof depths and ornament profiles estimated',
                 'Rear roof, north/east/west elevations and complete interior levels remain unresolved']}
(OUT/'old-houghton-frontage-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v112.blend'))
print('OLD_HOUGHTON_FRONTAGE_SAVED',len(openings),len(copies),flush=True)
