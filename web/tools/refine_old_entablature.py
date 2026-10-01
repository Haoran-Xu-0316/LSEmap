"""Correct OLD Houghton entablature and mansard windows from the 2024 project photograph.
Run in Blender Text Editor. Profiles and dimensions remain photo estimates.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import sys
import bpy
import bmesh
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage77'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v76.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
frame = json.loads((ROOT / 'result/blender/stage52/old-houghton-audit.json').read_text())
origin, right, outward = [Vector(frame[k]) for k in ['origin', 'right', 'outward']]
def point(x, depth, z):
    return origin + right*x + outward*depth + Vector((0, 0, z))
def fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        digest.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i', [loop.vertex_index for loop in obj.data.loops]).tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return digest.hexdigest()
before = {obj.name: fingerprint(obj) for obj in bpy.data.objects}
materials.clear()
materials['stone'] = bpy.data.materials['OLD_V52_stone'].copy()
materials['stone'].name = 'OLD_V77_stone'
materials['blue'] = bpy.data.materials['OLD_Blue_painted_steel'].copy()
materials['blue'].name = 'OLD_V77_blue'
materials['recess'] = bpy.data.materials['OLD_V52_vent'].copy()
materials['recess'].name = 'OLD_V77_recess'
brick = bpy.data.materials.new('OLD_V77_mansard_brick')
brick.use_nodes = True
brick.diffuse_color = (.105,.088,.067,1)
shader = brick.node_tree.nodes['Principled BSDF']
shader.inputs['Base Color'].default_value = brick.diffuse_color
shader.inputs['Roughness'].default_value = .9
pattern = brick.node_tree.nodes.new('ShaderNodeTexBrick')
uv = brick.node_tree.nodes.new('ShaderNodeTexCoord')
for key,value in [('Scale',1),('Brick Width',.225),('Row Height',.078),('Mortar Size',.003)]:
    pattern.inputs[key].default_value=value
pattern.inputs['Color1'].default_value=(.105,.088,.067,1)
pattern.inputs['Color2'].default_value=(.072,.061,.046,1)
pattern.inputs['Mortar'].default_value=(.20,.195,.175,1)
brick.node_tree.links.new(uv.outputs['UV'],pattern.inputs['Vector'])
brick.node_tree.links.new(pattern.outputs['Color'],shader.inputs['Base Color'])
materials['brick']=brick
batches = {}
def batch(family, key):
    name = family + '_' + key
    if name not in batches:
        batches[name] = Geometry('OLD', 'entablature77_' + name, key)
    return batches[name]
def box(family, key, x, depth, z, w, d, h):
    batch(family, key).box(point(x,depth,z),(w,d,h),math.atan2(right.y,right.x))
def tube(family, key, coords, radius=.012):
    vertices = []
    positions = [point(*p) for p in coords]
    for i, p in enumerate(positions):
        tangent = (positions[min(i+1,len(positions)-1)]-positions[max(0,i-1)]).normalized()
        side = tangent.cross(outward).normalized()
        for k in range(8):
            angle = math.tau*k/8
            vertices.append(p + radius*(side*math.cos(angle)+outward*math.sin(angle)))
    faces = [(i*8+k,i*8+(k+1)%8,(i+1)*8+(k+1)%8,(i+1)*8+k) for i in range(len(positions)-1) for k in range(8)]
    batch(family,key).add(vertices,faces)
hidden = ['OLD_Cornice_console_brackets', 'OLD_Cornice_console_flutes',
          'OLD_Entablature_dentils', 'OLD_Terrace_iron_infill', 'OLD_Terrace_parapet_piers',
          'OLD_Roof_slates', 'OLD_Mansard_blue_dormer_canopies']
for name in hidden:
    obj = bpy.data.objects[name]
    obj.hide_render = True
    obj.hide_set(True)
# Three recessed roundel panels between each of six consoles.
consoles = [-8.4, -5, -1.7, 1.7, 5, 8.4]
roundels = []
for a,b in zip(consoles,consoles[1:]):
    for j in range(3):
        x = a + (b-a)*(j+1)/4
        roundels.append(x)
        # Narrow dressed margins leave the original ashlar visible in the panel.
        for sign in [-1,1]:
            box('panel', 'stone', x+sign*.33,.265,19.03,.027,.06,.65)
            box('panel', 'stone', x,.265,19.03+sign*.325,.66,.06,.027)
        tube('roundel','stone',[(x+.155*math.cos(k*math.tau/40),.279,19.03+.155*math.sin(k*math.tau/40)) for k in range(41)],.018)
        tube('roundel','stone',[(x+.127*math.cos(k*math.tau/40),.255,19.03+.127*math.sin(k*math.tau/40)) for k in range(41)],.008)
# Curved console fronts replace flat rectangular blocks; shallow flutes follow
# their increasing projection towards the main cornice.
profile = [(.26,18.56),(.48,18.56),(.48,18.71),(.50,18.85),
           (.57,19.00),(.68,19.14),(.78,19.27),(.83,19.40),
           (.83,19.64),(.26,19.64)]
for x in consoles:
    vertices = [point(x+dx, depth,z) for dx in [-.22,.22] for depth,z in profile]
    n=len(profile)
    faces = [tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    batch('console','stone').add(vertices,faces)
    for side in [-1,1]:
        box('console','stone',x,.58,18.58+side*.025,.49,.65,.045)
    for offset in [-.12,0,.12]:
        tube('flute','stone',[(x+offset, depth+.015,z) for depth,z in profile[2:8]],.013)
    box('console','stone',x,.59,19.64,.52,.72,.08)
# Four arched iron screens and a broad central stone panel are visible in the
# project photograph. Keep the original lower rail and continuous coping.
box('parapet','stone',0,-.35,20.40,17.90,.40,.45)
pier_specs = [(-8.65,.42),(-5.20,.42),(0,3.90),(5.20,.42),(8.65,.42)]
for x,w in pier_specs:
    box('parapet','stone',x,-.35,21.13,w,.45,.90)
screens = [(-8.44,-5.41),(-4.99,-1.95),(1.95,4.99),(5.41,8.44)]
for a,b in screens:
    box('screen_back','recess',(a+b)/2,-.42,21.13,b-a,.035,.57)
    for z in [20.84,21.42]:
        box('screen','blue',(a+b)/2,-.29,z,b-a,.045,.028)
    # Repeated half-rounds crossed by low diagonals form the photographed fan grid.
    pitch=(b-a)/4
    for j in range(4):
        x=a+(j+.5)*pitch
        tube('screen','blue',[(x+pitch*.50*math.cos(k*math.pi/24),-.285,20.85+.51*math.sin(k*math.pi/24)) for k in range(25)],.016)
        for sign in [-1,1]:
            tube('screen','blue',[(x-sign*pitch*.42,-.275,20.85),(x+sign*pitch*.34,-.275,21.31)],.012)
# Diamond-pattern ventilation grilles below the five highest main-wall windows.
for x in [-6.7,-3.35,0,3.35,6.7]:
    box('vent','stone',x,.25,14.64,.46,.13,.29)
    box('vent_back','recess',x,.327,14.64,.36,.012,.21)
    for slope in [-1,1]:
        for k in [-2,-1,0,1,2]:
            points=[]
            for j in range(25):
                xx=-.18+j*.36/24
                zz=slope*xx+k*.085
                if abs(zz)<=.105:
                    points.append((x+xx,.340,14.64+zz))
            if len(points)>1:
                tube('vent','blue',points,.007)
# Cut ten real openings through the previously continuous mansard face.
# Retain the inherited roof rise and setback: this is a local facade correction.
dormers=[(x,y,z) for x in [-6.7,-3.35,0,3.35,6.7] for y,z in [(-1.9,23.2),(-3.1,26.2)]]
holes=[(x-.87,x+.87,z-1.06,z+1.06) for x,y,z in dormers]
xs=sorted({-8.9,8.9,*[v for a,b,c,d in holes for v in [a,b]]})
zs=sorted({21.60,28.15,*[v for a,b,c,d in holes for v in [c,d]]})
def slope(z):
    return -1.55-(z-21.85)*2.65/6.30
def face(family,key,vertices):
    vertices=[Vector(v) for v in vertices]
    if (vertices[1]-vertices[0]).cross(vertices[-1]-vertices[0]).dot(outward)<0:
        vertices.reverse()
    batch(family,key).add(vertices,[tuple(range(len(vertices)))])
for a,b in zip(xs,xs[1:]):
    for c,d in zip(zs,zs[1:]):
        if any(aa<(a+b)/2<bb and cc<(c+d)/2<dd for aa,bb,cc,dd in holes):
            continue
        face('mansard','brick',[point(x,slope(z),z) for x,z in [(a,c),(b,c),(b,d),(a,d)]])
for x,y,z in dormers:
    if z<25:
        box('dormer_canopy','blue',x,y+.1,z+1.08,2.15,.88,.15)
    for offset in [-1.54/6,1.54/6]:
        box('dormer_muntin','blue',x+offset,y+.01,z,.035,.11,1.9)
bars=bpy.data.objects['OLD_Window_sash_bars']
mesh=bmesh.new();mesh.from_mesh(bars.data)
seen=set();delete=[]
for v in list(mesh.verts):
    if v in seen:continue
    stack=[v];seen.add(v);component=[]
    while stack:
        a=stack.pop();component.append(a)
        for edge in a.link_edges:
            b=edge.other_vert(a)
            if b not in seen:seen.add(b);stack.append(b)
    positions=[]
    for v in component:
        p=bars.matrix_world@v.co-origin
        positions.append((p.dot(right),p.dot(outward),p.z))
    for x,y,z in dormers:
        if all(abs(xx-x)<.025 and abs(dd-(y+.01))<.07 and z-.96<zz<z+.96 for xx,dd,zz in positions):
            delete.extend(component);break
assert len(delete)==80,len(delete)
bmesh.ops.delete(mesh,geom=delete,context='VERTS')
mesh.to_mesh(bars.data);mesh.free();bars.data.update()
added=[]
for geometry in batches.values():
    obj=geometry.finish()
    if 'console_stone' in obj.name:
        mesh=bmesh.new();mesh.from_mesh(obj.data)
        bmesh.ops.recalc_face_normals(mesh,faces=list(mesh.faces))
        mesh.to_mesh(obj.data);mesh.free();obj.data.update()
    for modifier in list(obj.modifiers):
        obj.modifiers.remove(modifier)
    added.append(obj.name)
changed=[n for n,v in before.items() if fingerprint(bpy.data.objects[n])!=v]
assert changed==['OLD_Window_sash_bars'],changed
for filename in ['room-studies.json','room-spaces.json','building-review.json']:
    (OUT/filename).write_bytes((ROOT/'result/blender/stage76'/filename).read_bytes())
audit = {'version':77,'baseline':76,'roundelCount':15,'consoleCount':6,'parapetScreenCount':4,'upperVentCount':5,
         'hiddenPreviousObjects':hidden,'addedObjects':added,'changedExistingObjects':changed,'mansardWindowCount':10,'removedMansardMuntinVertices':80,
         'referenceUrl':'https://webbyates.com/projects/the-old-building/',
         'reference':'Damian Griffiths project photograph; refurbishment completed 2024, image published in 2025 upload path; exact capture date unknown',
         'limitations':['Houghton entablature, parapet and grille profiles photo-estimated, not scanned','Wall dimensions, window centres and cornice height retained; unseen roof and other elevations still require review','Ten mansard openings and three-column sashes corrected; only original mansard central muntins removed. Interiors retained, complete interiors not reconstructed']}
(OUT/'old-entablature-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v77.blend'))
print('OLD_ENTABLATURE_SAVED',len(added))
