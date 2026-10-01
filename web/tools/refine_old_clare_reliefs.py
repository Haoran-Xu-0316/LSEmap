"""Model the five frontal Clare Market bas reliefs from attributed photographs.
Run in Blender Text Editor. Original objects remain intact; the sixth side panel remains unmodeled. Relief profiles are authored estimates, not scanned sculpture.
"""
from pathlib import Path
import array, hashlib, json, math, shutil, sys
import bpy, bmesh
from mathutils import Vector
from mathutils.geometry import tessellate_polygon, intersect_line_line_2d

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage89'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v88.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']

def fingerprint(obj):
    digest = hashlib.sha256(str([list(r) for r in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        digest.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i', [l.vertex_index for l in obj.data.loops]).tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return digest.hexdigest()

before = {obj.name: fingerprint(obj) for obj in bpy.data.objects}
ring = next(b for b in json.loads((ROOT / 'result/blender/site_geometry.json').read_text())['buildings'] if b['code'] == 'OLD')['rings'][0]
a, b = Vector((*ring[7], 0)), Vector((*ring[8], 0))
origin, right = (a+b)/2, (a-b).normalized()
outward = Vector((right.y, -right.x, 0))
length = (a-b).length
width = length/5 - .92
centres = [-length/2 + length*(i+.5)/5 for i in range(5)]
materials.clear()
# Reuse the actual retained limestone finish, including procedural descriptor.
materials['stone'] = bpy.data.objects['OLD_V53_Clare_edge'].data.materials[0]
groups = []
records = []

def build_panel(index, outline, limbs, head, waves):
    group = Geometry('OLD', 'clare89_pose_' + str(index+1), 'stone')
    group.name = 'OLD_D5_clare89_pose_' + str(index+1)
    def point(x, z, depth):
        return origin + right*(centres[index]+x*width*.44) + outward*depth + Vector((0,0,5.37+z*.96))
    # Closed torso and folded-leg profile. It retains a shallow volume behind
    # the rounded limbs rather than constructing a full freestanding person.
    # Reject self-crossing silhouette contours before tessellation.
    for i in range(len(outline)):
        for j in range(i+1,len(outline)):
            if j == i+1 or (i == 0 and j == len(outline)-1):
                continue
            assert intersect_line_line_2d(Vector(outline[i]),Vector(outline[(i+1)%len(outline)]),
                                          Vector(outline[j]),Vector(outline[(j+1)%len(outline)])) is None
    polygon = [Vector((x,z,0)) for x,z in outline]
    triangles = tessellate_polygon([polygon])
    vertices = [point(x,z,d) for d in [.075,.13] for x,z in outline]
    count = len(outline)
    faces = [tuple(reversed(t)) for t in triangles]
    faces += [tuple(v+count for v in t) for t in triangles]
    faces += [(i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count)]
    group.add(vertices,faces)

    def tube(path, radius, depth=.14, flattened=.5):
        vertices = []
        for j,(x,z) in enumerate(path):
            previous = Vector(path[max(0,j-1)])
            following = Vector(path[min(len(path)-1,j+1)])
            tangent = (following-previous).normalized()
            perpendicular = Vector((-tangent.y,tangent.x))
            r = radius[j] if isinstance(radius,list) else radius
            for k in range(12):
                angle = k*math.tau/12
                offset = perpendicular*(r*math.cos(angle))
                vertices.append(point(x+offset.x,z+offset.y,depth+r*flattened*math.sin(angle)))
        faces = [(j*12+k,j*12+(k+1)%12,(j+1)*12+(k+1)%12,(j+1)*12+k) for j in range(len(path)-1) for k in range(12)]
        faces += [tuple(reversed(range(12))),tuple(range((len(path)-1)*12,len(path)*12))]
        group.add(vertices,faces)

    for path,radius in limbs:
        tube(path,radius)
    hx,hz = head
    # Closed flattened head: enough silhouette and brow definition for this
    # small architectural relief, without claiming a sculpted likeness.
    segments,rings = 24,12
    vertices = []
    for j in range(rings+1):
        latitude = math.pi*(j+.001)/(rings+.002)
        for k in range(segments):
            longitude = k*math.tau/segments
            vertices.append(point(hx+.112*math.sin(latitude)*math.cos(longitude),
                                  hz+.135*math.cos(latitude),
                                  .15+.067*math.sin(latitude)*math.sin(longitude)))
    faces = [(j*segments+k,j*segments+(k+1)%segments,(j+1)*segments+(k+1)%segments,(j+1)*segments+k) for j in range(rings) for k in range(segments)]
    faces += [tuple(reversed(range(segments))),tuple(range(rings*segments,(rings+1)*segments))]
    group.add(vertices,faces)
    tube([(hx-.075,hz+.01),(hx-.025,hz+.03),(hx+.045,hz+.015)],.011,.208,.45)
    tube([(hx+.005,hz+.015),(hx-.018,hz-.035),(hx+.025,hz-.045)],.013,.208,.45)
    tube([(hx-.03,hz-.073),(hx+.023,hz-.076)],.006,.208,.4)
    # Ribbons belong to each distinct relief composition, not copied templates.
    for path in waves:
        tube(path,.023,.10,.32)
    obj = group.finish()
    for modifier in list(obj.modifiers):
        obj.modifiers.remove(modifier)
    mesh = bmesh.new();mesh.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(mesh,faces=list(mesh.faces))
    mesh.to_mesh(obj.data);mesh.free()
    for face in obj.data.polygons:
        face.use_smooth = len(face.vertices) == 4
    obj['reference_panel'] = index+1
    obj['scope'] = 'Unique reclining silhouette from attributed Clare Market photos; unmeasured shallow profiles estimated'
    groups.append(obj.name)
    records.append({'panel':index+1,'centre':centres[index],'outline':outline,'head':head,
                    'limbs':limbs,'waves':waves,'name':obj.name})
    return obj

# Frontage order is independently visible in study photo C:
# G, E, F, D, H. User photo corroborates G and E. Side panel is unillustrated.
build_panel(0,
 [(-.30,.20),(-.05,.19),(.36,.40),(.53,.56),(.46,.66),(.21,.60),(-.06,.42),(-.32,.32)],
 [
  ([(.37,.54),(.14,.42),(-.14,.28)],[.13,.13,.12]),
  ([(-.25,.24),(-.57,.25),(-.79,.18),(-.88,.51),(-.95,.79)],[.12,.11,.082,.06,.04]),
  ([(-.14,.18),(-.48,.12),(-.73,.14),(-.81,.47),(-.84,.78)],[.10,.09,.064,.045,.035]),
  ([(.40,.54),(.25,.41),(.02,.35),(-.19,.35)],[.065,.06,.042,.033]),
  ([(.51,.53),(.79,.32),(.93,.41),(.90,.68)],[.066,.065,.053,.032])
 ],(.68,.72),
 [
  [(-1.02,.93),(-.77,.92),(-.56,.83),(-.27,.77),(.01,.82),(.29,.93)],
  [(-1.02,.025),(-.74,.03),(-.44,.05),(-.17,.085),(.09,.06),(.39,.14),(.76,.07),(.99,.15)]
 ])
build_panel(1,
 [(-.98,.13),(-.73,.10),(-.43,.15),(-.20,.14),(.02,.23),(.30,.27),(.53,.42),(.67,.58),(.56,.67),(.32,.55),(.15,.43),(-.03,.43),(-.35,.66),(-.60,.73),(-.83,.59),(-.89,.28)],
 [
  ([(.48,.48),(.28,.37),(.04,.30)],[.125,.13,.12]),
  ([(-.05,.30),(-.40,.62),(-.64,.63),(-.87,.34),(-.91,.15)],[.11,.11,.09,.062,.037]),
  ([(.13,.26),(-.29,.28),(-.60,.36),(-.80,.21),(-.86,.12)],[.10,.105,.082,.055,.033]),
  ([(.49,.51),(.64,.63),(.91,.76),(.79,.87),(.67,.82)],[.07,.068,.06,.048,.035]),
  ([(.30,.41),(.18,.35),(.36,.25),(.52,.20)],[.06,.053,.044,.031])
 ],(.69,.67),
 [
  [(-1.02,.92),(-.71,.87),(-.43,.83),(-.15,.77),(.14,.80),(.40,.93)],
  [(-1.02,.055),(-.74,.045),(-.42,.075),(-.12,.13),(.19,.09),(.47,.075),(.76,.08),(.99,.06)]
 ])
build_panel(2,
 [(-.47,.17),(-.16,.14),(.22,.37),(.23,.60),(.05,.67),(-.19,.63),(-.38,.46)],
 [
  ([(.08,.55),(-.16,.43),(-.33,.28)],[.13,.13,.12]),
  ([(-.27,.20),(.17,.28),(.39,.42),(.68,.21),(.96,.075)],[.115,.12,.10,.069,.038]),
  ([(-.33,.19),(-.07,.12),(.19,.105),(.34,.08)],[.095,.08,.053,.032]),
  ([(-.15,.56),(-.67,.56),(-.73,.33),(-.70,.09)],[.073,.07,.047,.036]),
  ([(.21,.52),(.49,.34),(.43,.49)],[.073,.055,.038])
 ],(.045,.76),
 [
  [(-1.0,.88),(-.74,.90),(-.41,.87),(-.13,.83)],
  [(.35,.93),(.63,.90),(.68,.73),(.58,.66),(.52,.79),(.67,.94),(.87,.85),(.90,.46),(.99,.30)],
  [(-1.02,.05),(-.78,.045),(-.44,.065),(-.08,.08),(.28,.055),(.57,.04),(.99,.035)]
 ])
build_panel(3,
 [(-.28,.21),(-.03,.20),(.38,.40),(.57,.56),(.49,.67),(.24,.61),(-.02,.42),(-.31,.33)],
 [
  ([(.46,.53),(.20,.43),(-.03,.29)],[.13,.13,.12]),
  ([(-.11,.22),(-.42,.20),(-.74,.17),(-.88,.46),(-.94,.82)],[.12,.11,.078,.057,.038]),
  ([(-.21,.19),(-.55,.12),(-.70,.14),(-.75,.52),(-.83,.77)],[.10,.088,.067,.048,.033]),
  ([(.49,.58),(.42,.36),(.36,.24),(.67,.12),(.89,.09)],[.07,.064,.06,.043,.032]),
  ([(.61,.53),(.94,.42),(.92,.63),(.67,.63)],[.065,.061,.047,.035])
 ],(.76,.73),
 [
  [(-1.02,.94),(-.74,.86),(-.45,.79),(-.14,.86),(.10,.91),(.33,.95)],
  [(-1.02,.04),(-.75,.045),(-.40,.04),(-.10,.07),(.24,.08),(.59,.06),(.99,.05)]
 ])
build_panel(4,
 [(-1.01,.08),(-.70,.07),(-.39,.09),(-.12,.17),(.17,.25),(.44,.45),(.58,.60),(.44,.66),(.23,.57),(.05,.42),(-.24,.51),(-.55,.60),(-.80,.54),(-.85,.27),(-.95,.13)],
 [
  ([(.41,.50),(.17,.37),(-.09,.26)],[.13,.13,.12]),
  ([(-.07,.23),(-.47,.49),(-.75,.52),(-.82,.34),(-.85,.10)],[.115,.115,.087,.055,.035]),
  ([(-.16,.19),(-.49,.15),(-.75,.13),(-.95,.11)],[.11,.10,.067,.034]),
  ([(.27,.54),(.01,.68),(-.13,.85),(-.29,.93)],[.074,.065,.054,.033]),
  ([(.50,.54),(.78,.18),(.94,.21),(.91,.61),(.81,.73)],[.074,.07,.06,.046,.032])
 ],(.64,.74),
 [
  [(-1.02,.94),(-.78,.89),(-.54,.83),(-.25,.94)],
  [(-1.02,.67),(-.76,.71),(-.46,.66),(-.22,.70),(.02,.80),(.27,.86)],
  [(-1.02,.035),(-.70,.025),(-.39,.045),(-.08,.05),(.26,.075),(.56,.07),(.86,.05),(.99,.12)]
 ])

assert all(fingerprint(bpy.data.objects[n]) == value for n,value in before.items())
for name in ['room-studies.json','room-spaces.json','building-review.json']:
    shutil.copyfile(ROOT / 'result/blender/stage88' / name,OUT / name)
if not (OUT / 'catalogue-before.json').exists():
    shutil.copyfile(ROOT / 'web/public/models/catalogue.json',OUT / 'catalogue-before.json')
audit = {'version':89,'baseline':88,'baselineFingerprint':before,'addedObjects':groups,
         'frame':{'origin':list(origin),'right':list(right),'outward':list(outward)},
         'width':width,'panels':records,'reference':'User frontal photo corroborates panels G and E; Jeremy Haslam architectural sculpture study photos C-H document all five main frontage poses and registration, publication 2010-01, image capture dates unknown',
         'attributionUrl':'https://www.lse.ac.uk/Events/Arts-and-music/art-on-campus/art-on-campus',
         'studyUrl':'https://jeremyhaslam.wordpress.com/wp-content/uploads/2010/01/architectural-sculpture-part-2-8-pdf.pdf',
         'frontageOrder':['G','E','F','D','H'],
         'limitations':['Five main frontage panels interpreted separately; sixth side panel unillustrated in the study and not reconstructed',
                        'Sculptural contours, faces and relief depth are authored estimates, not a scan',
                        'No source photographs or photo textures exported; original architecture and other buildings preserved']}
(OUT/'old-clare-reliefs-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v89.blend'))
print('OLD_CLARE_RELIEFS_SAVED',groups,flush=True)
