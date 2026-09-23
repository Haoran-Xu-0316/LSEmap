"""Version 16: finish each archived facade without changing its attribution.

Run in Blender's Text Editor after build_portsmouth_details.py. Detail locations
come from existing glazing faces, not a new assumed grid. Dimensions are design
estimates. Source photographs remain private inspection references.
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
from facade_geometry import Geometry, Facade, materials

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage16'
# Explicit selection excludes roof glass, balustrades and interior cutaways.
# style, source mesh names, finish colour, building-specific refinement description
BUILDINGS = {
 '61A': ('bronze', ['D5_glazing_glass'], (.22,.17,.10), 'Bronze perimeter beads, recessed seals and drained lower glazing channels'),
 'CBG': ('curtain', ['curtain_wall_glazing','end_wall_glazing'], (.39,.41,.40), 'Curtain-wall pressure caps, dark perimeter seals and sill drainage outlets'),
 'CKK': ('stone', ['EXTERIOR_Glazing_bays'], (.65,.63,.57), 'LIF window reveal beads, separate sill noses and end returns'),
 'CLM': ('stone', ['D3_window_glass'], (.62,.57,.47), 'Masonry window rebates, stone sill drips and dressed sill returns'),
 'COL': ('stone', ['D4_recessed_glass'], (.58,.55,.47), 'Recessed glazing beads and projecting sill-edge water checks'),
 'CON': ('stone', ['D4_recessed_glass'], (.62,.59,.51), 'Street-window reveal beads, sill noses and masonry sill returns'),
 'COW': ('sash', ['D5_window_glass_glass'], (.66,.64,.57), 'Sash putty beads, lower weatherboards and paired sill end grains'),
 'FAW': ('ribbon', ['D3_recessed_window_bands'], (.28,.30,.29), 'Continuous ribbon-window seals, metal sill caps and spaced drain slots'),
 'KGS': ('sash', ['D5_window_glass_glass'], (.59,.58,.51), 'Inset sash putty edges, bottom weatherboards and end-grain sill joints'),
 'KSW': ('stone', ['D3_window_glass'], (.58,.54,.44), 'Stone-framed window rebates with projecting drip edges and sill end blocks'),
 'LAK': ('sash', ['D5_sash_glass_glass','D5_dormer_glass_glass'], (.67,.65,.59), 'Street, plaza and dormer sash beads and weathered sill edges'),
 'LCH': ('sash', ['D5_recessed_glass_glass'], (.64,.62,.56), 'Upper sash recess beads, low sill weatherboards and edge joints'),
 '5LF': ('sash', ['D5_glass_glass'], (.72,.70,.64), 'Georgian sash perimeter putty and projecting painted sill noses'),
 '49L': ('sash', ['D5_window_glass'], (.71,.70,.64), 'Coopers sash beads and sill drips behind the existing shutters'),
 '50L': ('sash', ['D5_window_glass'], (.68,.67,.61), 'Tall sash perimeter beads, lower weatherboards and sill end joints'),
 '51L': ('stone', ['D5_recessed_glass_glass'], (.65,.60,.50), 'Stone-window inner rebates and projecting sill-edge returns'),
 'LRB': ('curtain', ['EXTERIOR_Glazing_bays'], (.28,.31,.31), 'Library external glazing pressure caps and sill-channel drain details'),
 'MAR': ('bronze', ['MAR_recessed_window_glass'], (.29,.25,.20), 'Upper facade recessed window beads, sill channels and fine drain slots'),
 'OLD': ('stone', ['OLD_Window_glazing'], (.62,.58,.49), 'Historic masonry window rebates and dressed sill drip courses'),
 'OCS': ('timber', ['D3_upper_sash_glass','D3_shop_display_glass'], (.045,.115,.07), 'Green timber glazing beads and separate shop-window sill weatherboards'),
 'PAN': ('ribbon', ['D3_recessed_window_bands'], (.31,.32,.30), 'Long window-band seals, lower aluminium caps and drain slots'),
 'PAR': ('sash', ['D5_recessed_glass_glass','D5_dormer_glass_glass'], (.64,.63,.57), 'Hall and dormer sash putty beads, sill weatherboards and end joints'),
 'PEA': ('metal', ['D5_recessed_glass_glass'], (.15,.17,.16), 'Theatre window gasket lines and metal sill channels; canopy soffit ribs'),
 'PEL': ('ribbon', ['D5_recessed_glass_glass'], (.13,.15,.14), 'Dark window seals, slim sill caps and drainage joints along the curved envelope'),
 'POR': ('timber', ['D5_sash_glass_glass','D5_shop_display_glass'], (.62,.62,.53), 'Rebuilt chamfered bookshop entrance, leaded shopfronts, street plaques and sash finish'),
 'SAR': ('sash', ['D5_recessed_glass_glass'], (.68,.66,.60), 'Recessed sash putty beads and white sill weatherboards with end joints'),
 'SAW': ('metal', ['SAW_recessed_window_glass'], (.18,.20,.19), 'Recessed glazing gasket edges and drained metal sills behind the folded brick screen'),
 'SHF': ('sash', ['D5_recessed_glass_glass'], (.70,.68,.62), 'Street sash putty beads, projecting sill noses and painted sill end joints'),
 'SAL': ('stone', ['SAL_Window_glazing'], (.64,.59,.49), 'Stone-window inner beads, sill drip courses and dressed end returns'),
 'STC': ('metal', ['D5_recessed_glass_glass','D5_attic_glass_glass'], (.38,.38,.34), 'Clare Market and attic window seals, metal sill channels and drainage outlets'),
}
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_portsmouth_v16.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
bpy.context.view_layer.update()
references = json.loads((OUT/'review/references.json').read_text())

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

protected = [o for o in bpy.data.objects if not any(c.name.endswith('_EXTERIOR') or c.name.startswith('35L_CONSTRUCTION') for c in o.users_collection)]
protected_before = digest(protected)

def material(name, color, metallic=0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*color,1)
    shader = mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = mat.diffuse_color
    shader.inputs['Roughness'].default_value = .48 if metallic else .72
    shader.inputs['Metallic'].default_value = metallic
    materials[name] = mat
    return name

seal = material('V16_recessed_seal', (.025,.031,.029))

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

records = []
for code,(style,names,color,description) in BUILDINGS.items():
    col = bpy.data.collections[code+'_EXTERIOR']
    originals = list(col.all_objects)
    before = digest(originals)
    points = [o.matrix_world @ Vector(p) for o in originals if o.type=='MESH' for p in o.bound_box]
    center = sum(points, Vector())/len(points)
    finish = material('V16_'+code+'_finish',color,.35 if style in {'metal','bronze','curtain','ribbon'} else 0)
    groups = {}
    def box(family,mat,c,u,n,x,z,width,height,depth,offset):
        key = (family,mat)
        if key not in groups: groups[key]=Geometry(code,'V16_'+family,mat)
        p = c+u*x+n*offset+Vector((0,0,z))
        groups[key].box(p,(width,depth,height),math.atan2(u.y,u.x))
    panes = 0
    for obj in originals:
        if obj.type!='MESH' or not any(name in obj.name for name in names): continue
        for c,u,n,w,h in pane_faces(obj,center):
            panes += 1
            # Putty/seal is inset within existing frames; it does not cover the pane.
            bead = .020 if style in {'sash','timber','stone'} else .028
            for side in [-1,1]:
                box('glazing_seal',seal,c,u,n,side*(w/2-.009),0,.018,h,.016,.008)
                box('reveal_bead',finish,c,u,n,side*(w/2-.031),0,bead,h-.035,.032,.025)
            for side in [-1,1]:
                box('glazing_seal',seal,c,u,n,0,side*(h/2-.009),w,.018,.016,.008)
                box('reveal_bead',finish,c,u,n,0,side*(h/2-.031),w-.035,bead,.032,.025)
            if style=='stone':
                box('stone_sill_drip',finish,c,u,n,0,-h/2-.055,w+.16,.055,.24,.085)
                for side in [-1,1]:box('sill_end_return',finish,c,u,n,side*(w/2+.045),-h/2-.023,.07,.10,.24,.085)
            elif style in {'sash','timber'}:
                box('timber_weatherboard',finish,c,u,n,0,-h/2-.029,w+.11,.065,.18,.052)
                for side in [-1,1]:box('sill_end_joint',seal,c,u,n,side*(w/2+.018),-h/2-.030,.009,.041,.018,.148)
            else:
                box('metal_sill_channel',finish,c,u,n,0,-h/2-.028,w+.035,.045,.15,.055)
                count = max(2,math.ceil(w/2.4))
                for i in range(count):box('sill_drain_slot',seal,c,u,n,-w/2+(i+.5)*w/count,-h/2-.030,.050,.014,.014,.137)
    assert panes, f'No eligible source panes for {code}'
    if code == 'PEA':
        profile = next(p for p in json.loads((ROOT/'result/blender/stage05/infill-geometry.json').read_text()) if p['code']=='PEA')
        facade = Facade(profile, next(w for w in profile['walls'] if w['front']), groups)
        for i in range(max(2, round(facade.length/.8))):
            facade.box('V16_canopy_soffit_rib',finish,(i+.5)*facade.length/max(2,round(facade.length/.8)),3.325,.035,.045,1.96,.65)
        facade.box('V16_canopy_lower_lip',finish,facade.length/2,3.34,facade.length+.3,.045,.055,1.74)
    for group in groups.values():
        obj = group.finish()
        # These sub-centimetre details need no subdivision-heavy bevel modifier.
        obj.modifiers.clear()
        obj['scope'] = description+'; positions follow the existing study, sizes remain estimates.'
    assert digest(originals)==before, code+' original envelope changed'
    records.append({'code':code,'description':description,'sourcePaneCount':panes,'newComponents':sum(g.parts for g in groups.values()),'originalGeometrySha256':before,'afterGeometrySha256':digest(col.all_objects),'scope':'Source-informed finish study; dimensions and unseen elevations estimated.'})
    print('REFINED',code,panes,records[-1]['newComponents'],flush=True)

# Construction remains schematic. Detail only the already modeled hoarding:
# panel seams, cap rails and base shoes, with no guessed active workstage.
code='35L'
col=next(c for c in bpy.data.collections if c.name.startswith('35L_CONSTRUCTION'))
originals=list(col.all_objects);before=digest(originals)
# Geometry helper expects EXTERIOR; point its output to the existing construction collection.
finish=material('V16_35L_hoarding_finish',(.085,.10,.095),.1)
bpy.data.collections.new('35L_EXTERIOR')
seams=Geometry(code,'V16_hoarding_panel_seams',finish);seams.collection=col
caps=Geometry(code,'V16_hoarding_cap_rails',finish);caps.collection=col
for obj in originals:
    if obj.type!='MESH' or 'hoarding' not in obj.name: continue
    vertices=[obj.matrix_world@v.co for v in obj.data.vertices]
    low=min(p.z for p in vertices);high=max(p.z for p in vertices)
    base=[p for p in vertices if abs(p.z-low)<.01]
    a,b=max(((a,b) for a in base for b in base),key=lambda pair:(pair[1]-pair[0]).length)
    u=(b-a).normalized();length=(b-a).length;angle=math.atan2(u.y,u.x)
    count=max(1,round(length/1.2))
    for i in range(count+1):
        p=a+u*(i*length/count);p.z=(low+high)/2
        seams.box(p,(.045,.065,high-low),angle)
    p=(a+b)/2;p.z=high+.035;caps.box(p,(length,.15,.07),angle)
for group in [seams,caps]:group.finish().modifiers.clear()
bpy.data.collections.remove(bpy.data.collections['35L_EXTERIOR'])
records.append({'code':'35L','description':'Indicative hoarding panel seams and cap rails; no claim about current construction progress','newComponents':seams.parts+caps.parts,'originalGeometrySha256':before,'afterGeometrySha256':digest(col.all_objects),'scope':'Construction site representation only; panel spacing estimated.'})
assert digest(protected)==protected_before,'Interior or context geometry changed'
assert len(records)==31 and all(r['newComponents']>0 for r in records)
for record in records:
    record['reference'] = ('Existing indicative hoarding from code/blender/build_campus.py; not the historical building photograph' if record['code']=='35L' else next((r['reference'] for r in references if r['code']==record['code']),None))
# Clear old startup notes that referred to unresolved footprints from version 2.
note=bpy.data.texts.get('START_HERE_EDITION_16') or bpy.data.texts.new('START_HERE_EDITION_16')
note.write('Local edition 16. All 31 catalogue records received individual exterior finish work. POR rebuilt from the archived corner-bookshop photograph. Interior geometry preserved. All dimensions remain estimates; 61A attribution is provisional; 35L shows indicative hoarding, not a surveyed current workstage. No public deployment. See stage16/all-buildings-manifest.json.')
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v16.blend'))
(OUT/'all-buildings-manifest.json').write_text(json.dumps({'version':16,'protectedGeometrySha256':protected_before,'buildings':records},indent=2)+'\n')
print('ALL_31_REFINED',flush=True)
