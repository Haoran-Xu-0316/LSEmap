"""Photo-guided Columbia House oval door panels and inset stone name tablet.
Run in Blender Text Editor; dimensions and ornamental profiles are estimates.
"""
from pathlib import Path
import array, hashlib, json, math, sys
import bpy, bmesh
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage67'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v66.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
collection = bpy.data.collections['COL_EXTERIOR']
record = next(b for b in json.loads((ROOT / 'result/blender/site_geometry.json').read_text())['buildings'] if b['code'] == 'COL')
ring = record['rings'][0]
p, q = Vector((*ring[10], 0)), Vector((*ring[11], 0))
u = (q - p).normalized()
signed = sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ring, ring[1:]+ring[:1]))
n = Vector((u.y, -u.x, 0)) * (1 if signed > 0 else -1)
origin = p + u * ((q-p).length / 4 * 1.5)
angle = math.atan2(u.y, u.x)
def point(x, depth, z):
    return origin + u*x + n*depth + Vector((0,0,z))
def fingerprint(obj):
    h = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        h.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        h.update(array.array('i', [v.vertex_index for v in obj.data.loops]).tobytes())
    if obj.type == 'FONT':
        h.update(str((obj.data.size, obj.data.font.name, obj.data.extrude)).encode())
    h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return h.hexdigest()
before = {o.name: fingerprint(o) for o in bpy.data.objects}
hidden = ['COL_D4_door_raised_panels', 'COL_D4_door_panel_mouldings', 'COL_D4_door_brass_pushplates']
for name in hidden:
    obj = bpy.data.objects[name]
    obj.hide_render = True
    obj.hide_set(True)
materials.clear()
for key, color, roughness, metallic in [
    ('wood', (.045,.030,.027), .40, .06),
    ('recess', (.023,.019,.017), .56, 0),
    ('stone', (.64,.615,.555), .82, 0),
    ('trim', (.70,.67,.60), .76, 0),
    ('brass', (.43,.30,.105), .32, .72),
]:
    material = bpy.data.materials.new('COL_V67_'+key)
    material.use_nodes = True
    material.diffuse_color = (*color,1)
    shader = material.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = material.diffuse_color
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metallic
    materials[key] = material
bpy.data.objects['COL_D4_double_timber_door'].data.materials[0] = materials['wood']
batches = {}
def batch(key):
    if key not in batches:
        batches[key] = Geometry('COL', 'entry67_'+key, key)
    return batches[key]
def box(key, x, depth, z, width, thickness, height):
    batch(key).box(point(x,depth,z), (width,thickness,height), angle)
def oval(key, x, z, profile):
    count = 48
    vertices = [point(x+rx*math.cos(j*math.tau/count), depth, z+rz*math.sin(j*math.tau/count))
                for rx,rz,depth in profile for j in range(count)]
    faces = [(k*count+j,k*count+(j+1)%count,(k+1)*count+(j+1)%count,(k+1)*count+j)
             for k in range(len(profile)-1) for j in range(count)]
    for i, face in enumerate(faces):
        a,b,c = [vertices[j] for j in face[:3]]
        if (b-a).cross(c-a).dot(n) < 0:
            faces[i] = tuple(reversed(face))
    batch(key).add(vertices, faces)
# Two upper rectangular panels per leaf and one framed oval lower panel.
for side in [-1,1]:
    x = side * 1.65/4
    for z,height in [(2.60,.48), (1.70,.72), (.75,.72)]:
        box('recess', x, -.551, z, .60, .034, height)
        for sign in [-1,1]:
            box('wood', x+sign*.30, -.505, z, .032, .05, height+.045)
            box('wood', x, -.505, z+sign*height/2, .63, .05, .032)
    oval('wood', x, .75, [(.235,.29,-.528), (.224,.277,-.486), (.210,.260,-.528)])
    # Small round hardware replaces unsupported tall gold pushplates.
    oval('brass', side*.13, 1.40, [(.037,.037,-.528),(.040,.040,-.472),(.014,.014,-.452)])
    oval('recess', side*.13, 1.22, [(.012,.020,-.523),(.006,.013,-.510)])
# Moulded tablet surrounds a recessed title and two flanking circular ornaments.
# Keep the original solid backing and cornice; add the photographed inset profile.
for width,height,depth,thickness in [(2.43,.57,.568,.040),(2.28,.44,.582,.025)]:
    for side in [-1,1]:
        box('trim', side*width/2, depth, 3.92, thickness,.035,height)
        box('trim', 0, depth, 3.92+side*height/2,width,.035,thickness)
for side in [-1,1]:
    oval('stone', side*.91, 3.92, [(.055,.055,.550),(.046,.046,.580),(.025,.025,.550)])
name = bpy.data.objects['COL_D4_portal_name']
name.location += n*.035
name.data.size = .145
font_path = Path('/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf')
if font_path.exists():
    name.data.font = bpy.data.fonts.load(str(font_path))
name.data.extrude = .004
added = []
for geometry in batches.values():
    obj = geometry.finish()
    added.append(obj.name)
    for modifier in list(obj.modifiers):
        obj.modifiers.remove(modifier)
changed = [name for name,prior in before.items() if fingerprint(bpy.data.objects[name]) != prior]
assert set(changed) == {'COL_D4_double_timber_door','COL_D4_portal_name'}, changed
for filename in ['room-studies.json','room-spaces.json','building-review.json']:
    (OUT/filename).write_bytes((ROOT/'result/blender/stage66'/filename).read_bytes())
audit = {'version':67,'baseline':66,'changedExistingObjects':changed,'changedOtherObjects':[],
         'hiddenPreviousObjects':hidden,'addedObjects':added,'origin':list(origin),'right':list(u),'outward':list(n),
         'ovalPanels':2,'rectangularUpperPanels':4,'tabletRings':2,
         'reference':'data/建筑图片/COL_Columbia House/01_建筑实拍/small_round5_COL_handbook-000.png',
         'limitations':['2025/26 handbook photograph; exact capture date unknown',
                        'Panel proportions, mouldings and decorative ornaments estimated',
                        'Upper elevations, roof, unseen sides and complete interior remain unverified']}
(OUT/'columbia-entry-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v67.blend'))
print('COLUMBIA_ENTRY_SAVED',len(added))
