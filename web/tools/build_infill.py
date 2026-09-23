"""Build the remaining photographed street envelopes without changing prior studies.

Run in Blender's Text Editor. Read the prepared local footprint file and preserve
version 04; save the additional work as version 05. No reference image is embedded.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import bpy
from mathutils import Matrix, Vector
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, Facade, materials

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage05'
profiles = json.loads((OUT / 'infill-geometry.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v04.blend'))
main_scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
targets = {p['code'] + '_EXTERIOR' for p in profiles}

def fingerprint():
    digest = hashlib.sha256()
    for obj in sorted(bpy.data.objects, key=lambda o: o.name):
        if obj.type != 'MESH' or any(c.name in targets for c in obj.users_collection):
            continue
        digest.update(obj.name.encode())
        digest.update(array.array('f', [v for row in obj.matrix_world for v in row]).tobytes())
        coords = array.array('f', [0]) * (len(obj.data.vertices) * 3)
        obj.data.vertices.foreach_get('co', coords)
        digest.update(coords.tobytes())
    return digest.hexdigest()

before = fingerprint()
materials.clear()
colors = {
    'red': (.40, .13, .065), 'dark-red': (.24, .075, .048),
    'brown': (.23, .17, .105), 'white': (.72, .70, .65),
    'stone': (.60, .55, .43), 'concrete': (.43, .43, .40),
    'glass': (.085, .15, .18), 'frame': (.69, .68, .61),
    'metal': (.055, .065, .061), 'slate': (.10, .125, .14),
    'wood': (.21, .08, .027), 'green': (.04, .11, .075),
    'gold': (.59, .40, .12), 'lse-red': (.61, .016, .027),
}
for name, color in colors.items():
    mat = bpy.data.materials.new('INFILL_' + name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    principled = mat.node_tree.nodes.get('Principled BSDF')
    principled.inputs['Base Color'].default_value = mat.diffuse_color
    principled.inputs['Roughness'].default_value = .28 if name in {'glass', 'metal', 'gold'} else .75
    principled.inputs['Metallic'].default_value = .35 if name in {'glass', 'metal', 'gold'} else 0
    if name in {'red', 'dark-red', 'brown'}:
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        uv = nodes.new('ShaderNodeTexCoord')
        brick = nodes.new('ShaderNodeTexBrick')
        brick.inputs['Scale'].default_value = 1
        brick.inputs['Brick Width'].default_value = .225
        brick.inputs['Row Height'].default_value = .078
        brick.inputs['Mortar Size'].default_value = .006
        brick.inputs['Color1'].default_value = (*color, 1)
        brick.inputs['Color2'].default_value = (*(v * .76 for v in color), 1)
        brick.inputs['Mortar'].default_value = (.20, .18, .14, 1)
        links.new(uv.outputs['UV'], brick.inputs['Vector'])
        links.new(brick.outputs['Color'], principled.inputs['Base Color'])
    materials[name] = mat

report = []
for profile in profiles:
    code, height, floors = profile['code'], profile['height'], profile['floors']
    collection = bpy.data.collections[code+'_EXTERIOR']
    bpy.data.batch_remove(ids=list(collection.objects))
    groups = {}
    front = None
    for wall in profile['walls']:
        facade = Facade(profile, wall, groups)
        length = wall['length']
        if wall['front']:
            front = facade
        if wall['party'] or length < 1.8:
            facade.box('party_walls', profile['material'], length/2,height/2,length,height)
            continue
        floor_height = height/floors
        bays = max(1,round(length/profile['pitch']))
        pitch = length/bays
        for floor in range(floors):
            z0 = floor*floor_height
            for bay in range(bays):
                x = (bay+.5)*pitch
                shop = floor == 0 and code in {'LAK','LCH','POR','SHF','PEA'}
                width = pitch*(.83 if shop else .58)
                lower, upper = z0+(.30 if shop else .82), z0+floor_height-.62
                if code == 'PEL': lower, upper = z0+1.22, z0+floor_height-.13
                if code == 'PAR' and wall['front'] and x < length*.54:
                    facade.box('hall_brick_front','red',x,z0+floor_height/2,pitch,floor_height)
                    continue
                projection = .38 if code == 'KGS' and wall['front'] and bay in {0,bays-1} and floor>0 else 0
                material = 'stone' if (floor==0 and code in {'COW','51L'}) or (code=='KGS' and projection>0) else profile['material']
                facade.box('brick_piers' if material in {'red','brown','dark-red'} else 'masonry_piers', material,
                           x-pitch/2+(pitch-width)/4,(lower+upper)/2,(pitch-width)/2,upper-lower,offset=projection-.12)
                facade.box('brick_piers' if material in {'red','brown','dark-red'} else 'masonry_piers', material,
                           x+pitch/2-(pitch-width)/4,(lower+upper)/2,(pitch-width)/2,upper-lower,offset=projection-.12)
                facade.box('spandrels',material,x,(z0+lower)/2,pitch,lower-z0,offset=projection-.12)
                facade.box('heads',material,x,(upper+z0+floor_height)/2,pitch,z0+floor_height-upper,offset=projection-.12)
                facade.box('recessed_glass','glass',x,(lower+upper)/2,width,upper-lower,.035,projection-.18)
                frame_material = 'metal' if code=='PEL' else 'frame'
                for side in [-1,1]:
                    facade.box('window_jambs',frame_material,x+side*width/2,(lower+upper)/2,.065,upper-lower,.14,projection-.02)
                for z in [lower,upper,(lower+upper)/2]:
                    facade.box('sash_rails',frame_material,x,z,width,.05,.13,projection)
                facade.box('sash_verticals',frame_material,x,(lower+upper)/2,.05,upper-lower,.12,projection)
                if code in {'LAK','POR','SHF','SAR'}:
                    for part in [.25,.75]: facade.box('sash_fine_bars',frame_material,x,lower+(upper-lower)*part,width,.025,.07,projection+.02)
                if code!='PEL':
                    facade.box('stone_sills','stone',x,lower-.05,width+.22,.12,.40,projection+.02)
                    facade.box('stone_lintels','stone',x,upper+.07,width+.16,.14,.29,projection+.02)
        courses = [height/floors,height-.22,height+.05]
        if code == 'KGS' and wall['front']: courses += [height*i/floors for i in range(2,floors)]
        for z in courses:
            facade.box('cornices','stone' if code!='PEL' else 'concrete',length/2,z,length+.06,.20,.46,.035)
        if code in {'COW','51L'}:
            for x in [.24,length-.24]:
                for j in range(int(height/.62)):
                    facade.box('corner_quoins','stone',x,j*.62+.25,.48 if j%2 else .72,.28,.30,.065)
        if code=='PEL':
            for floor in range(floors):
                facade.box('precast_horizontal_joints','metal',length/2,floor*floor_height+.02,length,.014,.015,.015)
            for j in range(1,bays):facade.box('precast_vertical_joints','metal',j*pitch,height/2,.013,height,.012,.015)

    # The existing footprint closes the shell with an estimated flat roof.
    roof = Geometry(code,'roof_slab','slate')
    for triangle in profile['building']['triangles']:
        roof.add([(x,y,height+.12) for x,y in triangle],[(0,1,2)])
    groups['roof_slab'] = roof
    length = front.length
    door_width = min(2.1,length*.45)
    x = length*.28 if code == 'PAR' else length/2
    front.box('entrance_door','wood' if code not in {'STC','PEL','PEA'} else 'glass',x,1.42,door_width,2.8,.08,.03)
    for side in [-1,1]:
        front.box('entrance_jambs','stone',x+side*(door_width/2+.16),1.6,.26,3.2,.42,.10)
        front.box('door_leaves','frame',x+side*door_width*.24,1.60,door_width*.42,1.9,.035,.09)
        front.box('door_inset_glass','glass',x+side*door_width*.24,1.75,door_width*.32,1.5,.025,.115)
        front.box('door_handles','gold',x+side*.12,1.05,.035,.34,.06,.19)
    front.box('threshold','stone',x,.08,door_width+.55,.16,.70,.24)
    if code in {'COW','KGS','LCH','50L','51L','PAR'}:
        front.arch('arched_portal','stone',x,2.72,door_width/2,.22)
        front.box('portal_keystone','stone',x,2.72+door_width/2+.06,.26,.38,.40,.14)
    if code=='PAR':
        front.arch('hall_blind_arch','stone',x,3.5,min(2.65,length*.20),.20,.20)
        front.box('hall_glass_entry','glass',x,1.5,min(4.8,length*.36),2.85,.035,.06)
        front.box('hall_door_vertical','frame',x,1.5,.10,2.85,.10,.14)
        front.box('hall_transom','stone',x,3.04,min(5.2,length*.4),.30,.42,.16)
    if code=='LCH':
        for side in [-1,1]: front.arch('side_arches','stone',x+side*min(2.5,length*.32),2.15,.70,.16)
        front.box('green_name_board','green',x,4.02,min(length-.4,6.3),.48,.08,.17)
        front.label(profile['sign'],x,3.9,.27,'gold')
    elif code=='PEL':
        for side in [-1,1]:front.box('yellow_portal','gold',x+side*(door_width/2+.35),1.75,.30,3.5,.38,.18)
        front.box('yellow_portal_header','gold',x,3.48,door_width+.96,.24,.42,.2)
        front.label(profile['sign'],x,3.04,.14)
    elif code=='PEA':
        front.box('theatre_canopy','metal',length/2,3.75,length+.3,.80,2.15,.65)
        front.label(profile['sign'],length/2,3.52,min(.32,length/48),'gold',1.74)
        front.box('vertical_theatre_sign','white',.25,height*.65,.70,height*.48,.35,.48)
        for i,char in enumerate('THEATRE'):front.label(char,.25,height*.85-i*.68,.48,'metal',.69)
        for side in [-1,1]:front.box('poster_cases','metal',x+side*(door_width/2+1.0),1.75,.9,1.65,.18,.20)
    elif code=='STC':
        front.box('red_entry_marker','lse-red',x-door_width/2-.3,1.6,.42,3.2,.32,.26)
        front.box('entry_name_fascia','metal',x,3.25,door_width+1.2,.60,.30,.24)
        front.label(profile['sign'],x,3.13,.26,'frame',.42)
    else:
        front.box('name_board','green' if code in {'LAK','SHF','POR'} else 'stone',x,3.94,min(length-.2,6),.44,.10,.26)
        front.label(profile['sign'],x,3.83,min(.26,(length-.4)/max(1,len(profile['sign'])*.65)), 'gold' if code in {'LAK','SHF','POR'} else 'metal',.33)
    if code=='COW':
        # Mansard depth is estimated; dormer rhythm follows the archived street view.
        center=Vector(profile['building']['center']);ring=profile['building']['rings'][0]
        mansard=Geometry(code,'mansard_roof','slate')
        for a,b in zip(ring,ring[1:]+ring[:1]):
            ai=center+(Vector(a)-center)*.77;bi=center+(Vector(b)-center)*.77
            mansard.add([(*a,height),(*b,height),(*bi,height+2.6),(*ai,height+2.6)],[(0,1,2,3)])
        for triangle in profile['building']['triangles']:
            top = [center+(Vector(p)-center)*.77 for p in triangle]
            mansard.add([(*p,height+2.6) for p in top],[(0,1,2)])
        groups['mansard_roof']=mansard
        for wall in profile['walls']:
            if wall['party'] or wall['length']<6:continue
            facade=Facade(profile,wall,groups)
            count=max(1,round(wall['length']/5))
            for j in range(count):
                xx=(j+.5)*wall['length']/count
                facade.box('dormer_stone','stone',xx,height+1.0,1.25,1.8,.6,-.55)
                facade.box('dormer_glass','glass',xx,height+1.05,.77,1.15,.03,-.23)
                facade.box('dormer_coping','stone',xx,height+1.95,1.4,.18,.72,-.52)
    if code in {'PAR','KGS'}:
        # Street-facing gables and stone coping, without invented roof equipment.
        gx=length*.28 if code=='PAR' else length*.75
        base=height-2.1 if code=='PAR' else height
        span=min(6,length*.55);rise=2.7 if code=='PAR' else 1.3
        front.group('street_gable',profile['material']).add([front.point(gx-span/2,base,.12),front.point(gx+span/2,base,.12),front.point(gx,base+rise,.12)],[(0,1,2)])
        for direction in [-1,1]:
            for i in range(18):
                xx=gx+direction*span/2*(i+.5)/18;zz=base+rise*(1-(i+.5)/18)
                front.box('gable_coping','stone',xx,zz,span/18+.08,.18,.40,.19)
        if code=='PAR': front.box('chimney_stack',profile['material'],length*.7,height+1.7,.85,4.7,.8,-.5)
    for geometry in groups.values():geometry.finish()
    # Store an outward camera direction for consistent street-facing web selection.
    profile['exteriorDirection']=[front.n.x,.65,-front.n.y]
    report.append({k:profile[k] for k in ['code','height','floors','exteriorDirection','scope','reference']})
    report[-1]['components']=sum(g.parts for g in groups.values())
    print('BUILT',code,report[-1]['components'],flush=True)

bpy.context.window.scene=main_scene
bpy.context.view_layer.update()
assert fingerprint()==before,'An existing building outside the infill scope changed'
output=ROOT/'result/blender/LSE_campus_detailed_v05.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output))
(OUT/'infill-manifest.json').write_text(json.dumps({'protectedGeometrySha256':before,'buildings':report},ensure_ascii=False,indent=2)+'\n')
print('INFILL_COMPLETE',output,flush=True)
