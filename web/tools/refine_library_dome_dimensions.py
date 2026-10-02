"""Correct the LRB skylight cap from the April 2025 roof survey sections.

Run in Blender Text Editor. Retain the registered atrium centre and all lower
interior geometry. The connection to the estimated old atrium is a tapered
transition, not a claim that its hidden ceiling structure has been surveyed.
"""
from pathlib import Path
import array, hashlib, json, math, shutil
import bpy
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage108'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v106.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
collection = bpy.data.collections['LRB_EXTERIOR']

def fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        digest.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i', [loop.vertex_index for loop in obj.data.loops]).tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return digest.hexdigest()

before = {obj.name: fingerprint(obj) for obj in bpy.data.objects}
source_shell = bpy.data.objects['LRB_V31_sliced_dome_shell']
points = [source_shell.matrix_world @ v.co for v in source_shell.data.vertices]
centre = [(min(p[i] for p in points) + max(p[i] for p in points)) / 2 for i in range(2)]
# Survey section A: deck 43.75, shell spring 45.66, apex 52.55 metres.
# Its drawn outer profile is a semicircle; the plan independently confirms a
# diameter near 13.8m at 1:100. Keep the existing local deck datum at 25.8m.
radius = 52.55 - 45.66
collar_height = 45.66 - 43.75
deck_height = 25.8
base_height = deck_height + collar_height
copies = {}

def owned_copy(name, suffix):
    source = bpy.data.objects[name]
    obj = source.copy(); obj.data = source.data.copy()
    obj.name = 'LRB_V108_' + suffix
    collection.objects.link(obj)
    source.hide_render = True; source.hide_set(True)
    obj.hide_render = False; obj.hide_set(False)
    obj['sharedInteriorRoof'] = True
    copies[name] = obj.name
    return obj

for name, suffix in [
    ('LRB_V31_sliced_dome_shell', 'survey_dome_shell'),
    ('LRB_V31_north_aperture_glass', 'survey_aperture_glass'),
    ('LRB_V31_dome_standing_seams_and_frame', 'survey_seams'),
    ('LRB_D5_mansard60_aperture_steel', 'survey_aperture_grid'),
]:
    obj = owned_copy(name, suffix)
    inverse = obj.matrix_world.inverted()
    for vertex in obj.data.vertices:
        p = obj.matrix_world @ vertex.co
        p.x = centre[0] + (p.x - centre[0]) * radius / 9.8
        p.y = centre[1] + (p.y - centre[1]) * radius / 9.8
        p.z = base_height + (p.z - deck_height) * radius / 9.0
        vertex.co = inverse @ p
    obj.data.update()
    obj['source_status'] = '2025 survey section spring/apex and circular profile; retained centre, aperture orientation and detailing remain approximate'

# Shrink only the circular boundary of the triangulated roof deck. Its perimeter,
# elevation and original outer mansard remain unchanged in this scoped revision.
deck = owned_copy('LRB_roof_deck_around_atrium', 'survey_deck_opening')
changed_hole_vertices = 0
for vertex in deck.data.vertices:
    p = deck.matrix_world @ vertex.co
    dx, dy = p.x-centre[0], p.y-centre[1]
    distance = math.hypot(dx, dy)
    if abs(distance-9.8) < .02:
        p.x = centre[0] + dx*radius/9.8
        p.y = centre[1] + dy*radius/9.8
        vertex.co = deck.matrix_world.inverted() @ p
        changed_hole_vertices += 1
assert changed_hole_vertices > 100
for polygon in deck.data.polygons:
    polygon.use_smooth = False
# Replace the old vertical 9.8m lightwell with a tapered lower connection and the
# surveyed raised spring collar. No lower floor opening or spiral stair moves.
lining = owned_copy('LRB_D5_mansard60_lining', 'survey_spring_collar')
vertices, faces = [], []
for i in range(128):
    a, b = i*2*math.pi/128, (i+1)*2*math.pi/128
    for low, high, rlow, rhigh in [(23.0, deck_height, 9.8, radius),
                                  (deck_height, base_height, radius, radius)]:
        start = len(vertices)
        for rdelta in [0, .12]:
            for angle, r, z in [(a,rlow,low),(b,rlow,low),(b,rhigh,high),(a,rhigh,high)]:
                vertices.append((centre[0]+(r+rdelta)*math.cos(angle), centre[1]+(r+rdelta)*math.sin(angle), z))
        faces.extend([tuple(start+j for j in [0,3,2,1]), tuple(start+j for j in [4,5,6,7]), tuple(start+j for j in [3,7,6,2])])
mesh = bpy.data.meshes.new('LRB_V108_raised_spring_and_transition')
from mathutils import Vector
vertices = [lining.matrix_world.inverted() @ Vector(p) for p in vertices]
mesh.from_pydata(vertices, [], faces); mesh.update()
for material in lining.data.materials: mesh.materials.append(material)
lining.data = mesh
assert all(fingerprint(bpy.data.objects[name]) == digest for name,digest in before.items())
for name in ['room-studies.json','room-spaces.json','building-review.json']:
    shutil.copyfile(ROOT/'result/blender/stage106'/name,OUT/name)
shutil.copyfile(ROOT/'web/public/models/catalogue.json',OUT/'catalogue-before.json')
source_pdf = ROOT/'data/collections/library-roof-2025/existing-roof-sections.pdf'
audit = {'version':108,'baselineNative':106,'originalFingerprints':before,'copies':copies,
         'centre':centre,'radius':radius,'height':radius,'deckHeight':deck_height,
         'collarHeight':collar_height,'baseHeight':base_height,'apexHeight':base_height+radius,
         'changedHoleVertices':changed_hole_vertices,'sourceIssueDate':'2025-04-17',
         'drawing':'4556-FBR-LR-ZZ-DR-A-115 P01',
         'sourceUrl':'https://idoxpa.westminster.gov.uk/online-applications/files/1FD876709F593BD722BC28CD60D1EEBA/pdf/25_03306_FULL-EXT_ROOF_SECTIONS-8631625.pdf',
         'sourcePdfSha256':hashlib.sha256(source_pdf.read_bytes()).hexdigest(),
         'surveyLevels':{'deck':43.75,'spring':45.66,'apex':52.55},
         'limits':['Existing centre retained pending full roof plan registration','North opening orientation and grid inherited, not fully registered to survey','Tapered lower ceiling connection estimated','Perimeter roof, dormers and current plant are pending reconstruction from 2025 drawings','Complete lower interiors remain unverified']}
(OUT/'library-dome-dimensions-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v108.blend'))
print('LIBRARY_SURVEY_DOME_SAVED', radius, collar_height, changed_hole_vertices, flush=True)
