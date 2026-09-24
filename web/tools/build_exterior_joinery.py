"""Edition 17: deepen the existing facade joinery without inventing new openings.
Run in Blender's Text Editor. Reads v16 and saves a separate v17 study.
Profiles are construction interpretations, not surveyed fabrication details.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import sys
import bpy
from mathutils import Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage17'
OUT.mkdir(parents=True, exist_ok=True)
PROFILES = json.loads((Path(__file__).parent/'exterior-joinery.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v16.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
bpy.context.view_layer.update()

def digest(objects):
    value = hashlib.sha256()
    for obj in sorted(objects, key=lambda o:o.name):
        if obj.type != 'MESH': continue
        value.update(obj.name.encode())
        value.update(array.array('f', [v for row in obj.matrix_world for v in row]).tobytes())
        coords = array.array('f', [0])*(len(obj.data.vertices)*3)
        obj.data.vertices.foreach_get('co', coords)
        value.update(coords.tobytes())
    return value.hexdigest()

def pane_faces(obj, center):
    """Extract disconnected planar rectangular panes from a batched mesh."""
    mesh = obj.data
    parent = list(range(len(mesh.vertices)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for edge in mesh.edges:
        a,b = map(find, edge.vertices); parent[a] = b
    components = {}
    for polygon in mesh.polygons:
        components.setdefault(find(polygon.vertices[0]), []).append(polygon)
    matrix = obj.matrix_world
    normals = matrix.to_3x3().inverted().transposed()
    for polygons in components.values():
        candidates = []
        for polygon in polygons:
            n = (normals @ polygon.normal).normalized()
            if len(polygon.vertices) != 4 or abs(n.z) > .04: continue
            points = [matrix @ mesh.vertices[i].co for i in polygon.vertices]
            c = sum(points, Vector())/4
            candidates.append((polygon.area, n.dot(c-center), points, n))
        if not candidates: continue
        area = max(item[0] for item in candidates)
        _,_,points,n = max((item for item in candidates if item[0] >= area*.96),key=lambda item:item[1])
        u = Vector((-n.y,n.x,0)).normalized()
        c = sum(points,Vector())/4
        width = max(p.dot(u) for p in points)-min(p.dot(u) for p in points)
        height = max(p.z for p in points)-min(p.z for p in points)
        if not (.25 < width < 50 and .35 < height < 14): continue
        # Reject skewed polygons, which require individual bespoke profiles.
        if any(abs(abs((p-c).dot(u))-width/2)>.025 or abs(abs(p.z-c.z)-height/2)>.025 for p in points): continue
        yield c,u,n,width,height

originals = list(bpy.data.objects)
before = digest(originals)
references = {r['code']:r['reference'] for r in json.loads((ROOT/'result/blender/stage16/review/references.json').read_text())}
records = []
for code, profile in PROFILES.items():
    collection = bpy.data.collections[code+'_EXTERIOR']
    source_objects = list(collection.all_objects)
    corners = [o.matrix_world@Vector(p) for o in source_objects if o.type=='MESH' for p in o.bound_box]
    center = sum(corners, Vector())/len(corners)
    style = profile['style']
    for suffix, color, metal in [('finish', profile['color'], .45 if style in {'metal','bronze','curtain','ribbon'} else 0), ('shadow', [.035,.04,.038], 0)]:
        name = 'V17_'+code+'_'+suffix
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        mat.diffuse_color = (*color,1)
        shader = mat.node_tree.nodes['Principled BSDF']
        shader.inputs['Base Color'].default_value = mat.diffuse_color
        shader.inputs['Metallic'].default_value = metal
        shader.inputs['Roughness'].default_value = .48 if metal else .7
        materials[name] = mat
    groups = {}
    def box(family, c, u, n, x, z, width, height, depth, offset, shadow=False):
        key = family
        if key not in groups:
            groups[key] = Geometry(code, 'V17_'+family, 'V17_'+code+('_shadow' if shadow else '_finish'))
        pos = c+u*x+n*offset+Vector((0,0,z))
        groups[key].box(pos,(width,depth,height),math.atan2(u.y,u.x))
    panes = 0
    for obj in source_objects:
        if obj.type != 'MESH' or not any(name in obj.name for name in profile['sourceMeshes']): continue
        for c,u,n,w,h in pane_faces(obj,center):
            panes += 1
            if style in {'sash','timber'}:
                # Split sash-box section: outer lining, recessed parting groove,
                # inner stop. These sit outside the glass, preserving existing bars.
                for side in [-1,1]:
                    box('sash_box_lining',c,u,n,side*(w/2+.035),0,.055,h+.08,.17,.035)
                    box('parting_groove',c,u,n,side*(w/2+.014),0,.012,h,.022,.126,True)
                    box('inner_sash_stop',c,u,n,side*(w/2-.009),0,.026,h,.04,.124)
                box('head_lining',c,u,n,0,h/2+.023,w+.1,.046,.17,.035)
                box('sill_apron',c,u,n,0,-h/2-.13,w+.13,.075,.115,.027)
                box('sill_undercut',c,u,n,0,-h/2-.096,w+.10,.012,.018,.075,True)
            elif style == 'stone':
                # Three-step masonry return makes the reveal legible obliquely.
                for side in [-1,1]:
                    for step,(width,depth,offset) in enumerate([(.065,.25,.01),(.032,.12,.12)]):
                        box('stepped_jamb_'+str(step),c,u,n,side*(w/2+.04+step*.04),0,width,h+.12,depth,offset)
                box('lintel_inner_soffit',c,u,n,0,h/2+.045,w+.15,.07,.25,.025)
                for side in [-1,1]:
                    box('sill_bearing',c,u,n,side*(w/2-.14),-h/2-.16,.16,.15,.22,.025)
                box('sill_shadow_rebate',c,u,n,0,-h/2-.11,w+.1,.018,.025,.11,True)
            else:
                # Folded aluminium/bronze return, separated from the thin v16 seal.
                for side in [-1,1]:
                    box('folded_jamb_return',c,u,n,side*(w/2+.024),0,.035,h+.045,.18,.065)
                    box('cap_shadow_joint',c,u,n,side*(w/2+.045),0,.012,h,.018,.164,True)
                box('head_flashing',c,u,n,0,h/2+.028,w+.08,.04,.24,.075)
                box('flashing_downstand',c,u,n,0,h/2+.002,w+.08,.055,.026,.183)
                box('sill_front_fascia',c,u,n,0,-h/2-.09,w+.06,.09,.035,.135)
                # Segmented fascia and cover-plate end caps follow wide ribbon bays.
                count=max(1,math.ceil(w/2.8))
                for i in range(1,count):
                    box('sill_expansion_joint',c,u,n,-w/2+w*i/count,-h/2-.09,.012,.08,.015,.157,True)
    made = []
    for group in groups.values():
        obj=group.finish()
        # Small shared mesh families avoid thousands of independent draw objects.
        for mod in obj.modifiers:
            if mod.type=='BEVEL': mod.width=.003; mod.segments=1
        made.append(obj)
    assert panes and made, code+' has no matched openings'
    families=list(groups)
    records.append({'code':code,'sourcePanes':panes,'style':style,'families':families,
        'newComponents':sum(g.parts for g in groups.values()),
        'description':'; '.join(f.replace('_',' ') for f in families),
        'scope':'Construction interpretation anchored to existing photographed openings; dimensions estimated. No new opening locations or interior changes.',
        'reference':references.get(code),'originalGeometrySha256':digest(source_objects),'afterGeometrySha256':digest(collection.all_objects)})
    print('JOINERY',code,panes,records[-1]['newComponents'],flush=True)
# Keep the construction site indicative: add only foot plates to existing posts.
col=next(c for c in bpy.data.collections if c.name.startswith('35L_CONSTRUCTION'))
source_objects=list(col.all_objects)
mat=bpy.data.materials.new('V17_35L_base_metal');mat.diffuse_color=(.16,.18,.17,1);materials[mat.name]=mat
placeholder=bpy.data.collections.new('35L_EXTERIOR')
feet=Geometry('35L','V17_hoarding_post_feet',mat.name);feet.collection=col
for obj in source_objects:
    if obj.type!='MESH' or 'hoarding' not in obj.name.lower() or 'V16' in obj.name:continue
    points=[obj.matrix_world@Vector(p) for p in obj.bound_box]
    low=min(p.z for p in points)
    base=[p for p in points if abs(p.z-low)<.01]
    a,b=max(((a,b) for a in base for b in base),key=lambda pair:(pair[1]-pair[0]).length)
    delta=b-a;length=delta.length
    if length<.1:continue
    u=delta.normalized();count=max(1,round(length/2.4))
    for i in range(count+1):
        p=a+u*(length*i/count);p.z=low+.035
        feet.box(p,(.28,.32,.07),math.atan2(u.y,u.x))
feet.finish().modifiers.clear();bpy.data.collections.remove(placeholder)
records.append({'code':'35L','newComponents':feet.parts,'description':'Indicative hoarding post foot plates','scope':'Schematic construction boundary only, not the current workstage','reference':None})
assert digest(originals)==before,'Existing geometry changed'
assert len(records)==31 and all(r['newComponents']>0 for r in records)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v17.blend'))
(OUT/'all-buildings-manifest.json').write_text(json.dumps({'version':17,'preservedGeometrySha256':before,'buildings':records},indent=2)+'\n')
print('EDITION17_COMPLETE',flush=True)
