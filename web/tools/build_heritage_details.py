"""Refine photographed King's Chambers and Cowdray street details locally.

Run inside Blender; preserves edition 08 and saves edition 09. The source archive
is read for footprint profiles only. Geometry is authored, never photo-projected.
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
OUT = ROOT / 'result/blender/stage09/heritage'
OUT.mkdir(parents=True, exist_ok=True)
profiles = [p for p in json.loads((ROOT/'result/blender/stage05/infill-geometry.json').read_text()) if p['code'] in {'KGS', 'COW'}]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v08.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
targets = {code+'_EXTERIOR' for code in ['KGS', 'COW']}

def fingerprint():
    digest = hashlib.sha256()
    for obj in sorted(bpy.data.objects, key=lambda item: item.name):
        if obj.type != 'MESH' or any(c.name in targets for c in obj.users_collection):
            continue
        digest.update(obj.name.encode())
        digest.update(array.array('f', [v for row in obj.matrix_world for v in row]).tobytes())
        coordinates = array.array('f', [0]) * (len(obj.data.vertices)*3)
        obj.data.vertices.foreach_get('co', coordinates)
        digest.update(coordinates.tobytes())
    return digest.hexdigest()

before = fingerprint()
materials.clear()
colors = {'brick': (.36,.12,.067), 'darkbrick': (.24,.073,.048),
          'stone': (.55,.51,.41), 'trim': (.70,.68,.60), 'frame': (.78,.77,.69),
          'glass': (.065,.115,.135), 'shadow': (.18,.18,.16), 'metal': (.065,.077,.078),
          'slate': (.15,.18,.19), 'wood': (.09,.054,.031), 'green': (.027,.10,.074),
          'gold': (.54,.36,.10), 'lead': (.31,.34,.34)}
for name,color in colors.items():
    material = bpy.data.materials.new('HERITAGE09_'+name)
    material.diffuse_color = (*color,1)
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    shader = nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = material.diffuse_color
    shader.inputs['Roughness'].default_value = .23 if name=='glass' else .74
    shader.inputs['Metallic'].default_value = .5 if name in {'metal','lead','gold'} else 0
    if name in {'brick','darkbrick'}:
        uv=nodes.new('ShaderNodeTexCoord'); brick=nodes.new('ShaderNodeTexBrick')
        for key,value in [('Scale',1),('Brick Width',.225),('Row Height',.078),('Mortar Size',.004)]:brick.inputs[key].default_value=value
        brick.inputs['Color1'].default_value=(*color,1)
        brick.inputs['Color2'].default_value=(*(v*.73 for v in color),1)
        brick.inputs['Mortar'].default_value=(.28,.25,.20,1)
        links.new(uv.outputs['UV'],brick.inputs['Vector']);links.new(brick.outputs['Color'],shader.inputs['Base Color'])
    materials[name]=material


def tube(facade, name, material, points, radius=.045):
    """Circular section following local x/z/depth points, used for real trim profiles."""
    points=[Vector(facade.point(*point)) for point in points]
    vertices=[]
    for i,p in enumerate(points):
        tangent=(points[min(i+1,len(points)-1)]-points[max(i-1,0)]).normalized()
        axis=tangent.cross(Vector((0,0,1)))
        if axis.length < .001:axis=tangent.cross(Vector((1,0,0)))
        axis.normalize();other=tangent.cross(axis).normalized()
        vertices.extend(tuple(p+radius*(axis*math.cos(j*math.tau/8)+other*math.sin(j*math.tau/8))) for j in range(8))
    faces=[(i*8+j,i*8+(j+1)%8,(i+1)*8+(j+1)%8,(i+1)*8+j) for i in range(len(points)-1) for j in range(8)]
    facade.group(name,material).add(vertices,faces)


def opening(f,x,z0,z1,width,pitch,bottom,top,masonry='brick',depth=0,bars=3):
    """Build masonry around an actual opening, with recessed panes and sash profiles."""
    for sign in [-1,1]:
        f.box('window_piers',masonry,x+sign*(pitch+width)/4,(z0+z1)/2,(pitch-width)/2,z1-z0,.36,depth-.17)
    f.box('window_spandrel',masonry,x,(bottom+z0)/2,pitch,z0-bottom,.36,depth-.17)
    f.box('window_head',masonry,x,(z1+top)/2,pitch,top-z1,.36,depth-.17)
    f.box('window_glass','glass',x,(z0+z1)/2,width,z1-z0,.04,depth-.18)
    for sign in [-1,1]:
        f.box('sash_outer_frame','frame',x+sign*width/2,(z0+z1)/2,.085,z1-z0,.13,depth-.005)
    for z in [z0,z1,(z0+z1)/2]:f.box('sash_meeting_rail','frame',x,z,width,.065,.12,depth+.005)
    for fraction in [-1/6,1/6] if bars==3 else [0]:
        f.box('sash_glazing_bar','frame',x+width*fraction,(z0+z1)/2,.028,z1-z0,.06,depth+.045)
    for fraction in [.25,.75]:f.box('sash_glazing_bar','frame',x,z0+(z1-z0)*fraction,width,.025,.06,depth+.045)
    f.box('projecting_sill','trim',x,z0-.07,width+.24,.14,.44,depth+.05)
    f.box('window_lintel','stone',x,z1+.09,width+.22,.18,.32,depth+.025)


def pediment(f,x,z,width,rise,depth):
    f.group('pediment_tympanum','stone').add([f.point(x-width/2,z,depth),f.point(x+width/2,z,depth),f.point(x,z+rise,depth)],[(0,1,2)])
    for dz,rad in [(0,.065),(.14,.075)]:
        tube(f,'pediment_raking_moulding','trim',[(x-width/2,z+dz,depth+.09),(x,z+rise+dz,depth+.09),(x+width/2,z+dz,depth+.09)],rad)
    f.box('pediment_base','trim',x,z,width+.2,.16,.42,depth)


def entrance(f,code):
    x=f.length/2
    width=3.4 if code=='KGS' else 1.9
    spring=3.0 if code=='KGS' else 2.9
    radius=width/2
    # A dark recessed rectangular door and fanlight have no masonry through the opening.
    f.box('entrance_recess','shadow',x,spring/2,width+.15,spring,.07,-.29)
    f.box('entrance_door','wood',x,1.35,width-.22,2.7,.10,-.12)
    for sign in [-1,1]:
        xx=x+sign*width*.245
        f.box('door_glass','glass',xx,1.82,width*.40,1.5,.035,-.048)
        f.box('door_bottom_panel','wood',xx,.50,width*.36,.55,.055,-.035)
        f.box('door_pull','gold',x+sign*.12,1.23,.035,.40,.085,.04)
        f.box('door_jamb','wood',x+sign*width/2,1.4,.14,2.8,.18,-.05)
    f.box('door_center_stile','wood',x,1.4,.12,2.8,.14,-.035)
    fan=[f.point(x,spring,-.12)]+[f.point(x+radius*math.cos(i*math.pi/48),spring+radius*math.sin(i*math.pi/48),-.12) for i in range(49)]
    f.group('arched_fanlight','green' if code=='KGS' else 'glass').add(fan,[(0,i+1,i+2) for i in range(48)])
    f.arch('portal_voussoirs','stone',x,spring,radius,.38,.46)
    f.arch('portal_inner_bead','trim',x,spring,radius-.035,.07,.50)
    for sign in [-1,1]:
        for j in range(8):
            f.box('rusticated_portal_pier','stone',x+sign*(radius+.34),.22+j*.39,.57,.375,.82,.10)
        f.box('portal_plinth','trim',x+sign*(radius+.34),.18,.79,.36,.95,.14)
        f.box('portal_capital','trim',x+sign*(radius+.34),3.0,.85,.26,1.0,.16)
        for j in range(3):f.box('portal_reeded_pilaster','trim',x+sign*(radius+.34)+(j-1)*.14,1.75,.042,1.82,.09,.55)
    f.box('portal_keystone','trim',x,spring+radius+.08,.32,.56,.67,.28)
    if code=='KGS':
        f.label("KING'S CHAMBERS",x,3.24,.205,'gold',.025)
        f.label('29     31',x,3.69,.22,'gold',.025)
        # Sunburst on the green fanlight follows the photographed entrance sign.
        for i in range(13):
            angle=math.pi*(.12+.76*i/12)
            verts=[f.point(x+.13*math.cos(angle-.08),4.32-.13*math.sin(angle-.08),.012),f.point(x+.13*math.cos(angle+.08),4.32-.13*math.sin(angle+.08),.012),f.point(x+.43*math.cos(angle),4.32-.43*math.sin(angle),.012)]
            f.group('fanlight_sunburst','gold').add(verts,[(0,1,2)])
        for sign in [-1,1]:
            # Broken segmental pediment leaves the centre open for the keystone.
            pts=[]
            for i in range(25):
                a=(.15+(.42-.15)*i/24)*math.pi
                pts.append((x+sign*2.25*math.cos(a),3.85+1.70*math.sin(a),.46))
            tube(f,'broken_pediment','trim',pts,.13)
            pts=[(x+sign*(1.67+.26*math.exp(-t*.22)*math.cos(t)),3.90+.26*math.exp(-t*.22)*math.sin(t),.61) for t in [i*math.pi/16 for i in range(65)]]
            tube(f,'portal_volutes','stone',pts,.085)
    else:
        f.box('portal_entablature','trim',x,4.42,width+1.42,.33,1.10,.18)
        for sign in [-1,1]:
            for j in range(3):f.box('portal_console','stone',x+sign*(radius+.26),3.81+j*.16,.30+j*.10,.16,.54+j*.13,.27)
        f.label('COWDRAY HOUSE',x,4.33,.18,'shadow',.735)
    for step in range(2):f.box('entrance_steps','stone',x,.06+step*.10,width+.85-step*.15,.12,1.0-step*.2,.35-step*.1)


def kgs_front(profile, wall, groups):
    f=Facade(profile,wall,groups);L=f.length
    levels=[0,4.9,8.9,12.9,15.2]
    bay_width=2.6; centers=[1.65,L-1.65]
    # Two canted, stone-clad bays are three faces each, not shallow rectangles.
    for cx in centers:
        for floor in [1,2]:
            lo,hi=levels[floor],levels[floor+1]
            for xa,da,xb,db in [(cx-bay_width/2,0,cx-.83,.66),(cx-.83,.66,cx+.83,.66),(cx+.83,.66,cx+bay_width/2,0)]:
                p,q=f.point(xa,0,da)[:2],f.point(xb,0,db)[:2]
                length=math.dist(p,q);u=Vector(q)-Vector(p);n=Vector((u.y,-u.x)).normalized()
                if n.dot(f.n)<0:n=-n
                side=Facade(profile,{'p':p,'q':q,'length':length,'outward':list(n)},groups)
                opening(side,length/2,lo+.50,hi-.36,length*.72,length,lo,hi,'stone',bars=2)
                for z in [lo,hi]:side.box('bay_string_course','trim',length/2,z,length+.04,.20,.46,.04)
        pediment(f,cx,15.25,3.15,.95,.12)
    # Narrow masonry strips close the returns to the central window range.
    left,right=centers[0]+bay_width/2,centers[1]-bay_width/2
    for floor in [1,2]:
        lo,hi=levels[floor],levels[floor+1];pitch=(right-left)/3
        for i in range(3):opening(f,left+(i+.5)*pitch,lo+.55,hi-.38,pitch*.62,pitch,lo,hi,'darkbrick')
        for a,b in [(0,.35),(L-.35,L)]:f.box('bay_end_pier','stone',(a+b)/2,(lo+hi)/2,b-a,hi-lo,.36,-.15)
    for i in range(9):opening(f,(i+.5)*L/9,13.43,14.72,.65,L/9,12.9,15.2,'darkbrick',bars=2)
    # Ground-floor shop glazing flanks the arched common entrance.
    for cx in centers:
        opening(f,cx,.40,4.18,2.40,3.3,0,4.9,'stone',bars=3)
        f.box('shop_transom','frame',cx,3.48,2.4,.10,.18,.06)
    x=L/2;r=1.7
    for a,b in [(3.3,x-r-.03),(x+r+.03,L-3.3)]:f.box('entrance_side_masonry','stone',(a+b)/2,2.45,b-a,4.9,.43,-.16)
    # Masonry fills only the area above the arched opening, never across its fanlight.
    for i in range(48):
        xx=x-r+(i+.5)*2*r/48;bottom=3+math.sqrt(max(0,r*r-(xx-x)**2))
        f.box('arch_spandrel','stone',xx,(bottom+4.9)/2,2*r/48+.002,4.9-bottom,.40,-.19)
    for z,w,d in [(4.9,.30,.72),(12.9,.36,.66),(15.2,.27,.60)]:f.box('front_cornice','trim',L/2,z,L,w,d,.12)
    entrance(f,'KGS')
    # Lead-covered ribbed corner dome, based on its photographed silhouette.
    cx=L-1.65;cz=16.00;radius=1.62;rise=2.03
    for seg in range(48):
        a,b=seg*math.tau/48,(seg+1)*math.tau/48
        f.group('dome_support_drum','stone').add([f.point(cx+radius*math.cos(t),z,-.67+radius*math.sin(t)) for z,t in [(15.22,a),(15.22,b),(cz,b),(cz,a)]],[(0,1,2,3)])
    for ring in range(16):
        a,b=ring*math.pi/32,(ring+1)*math.pi/32
        for seg in range(48):
            u,v=seg*math.tau/48,(seg+1)*math.tau/48
            verts=[f.point(cx+radius*math.cos(t)*math.cos(phi),cz+rise*math.sin(t),-.67+radius*math.cos(t)*math.sin(phi)) for t,phi in [(a,u),(a,v),(b,v),(b,u)]]
            f.group('lead_dome','lead').add(verts,[(0,1,2,3)])
    for j in range(12):
        phi=j*math.tau/12
        tube(f,'dome_standing_seams','trim',[(cx+(radius+.025)*math.cos(t)*math.cos(phi),cz+(rise+.025)*math.sin(t),-.67+(radius+.025)*math.cos(t)*math.sin(phi)) for t in [i*math.pi/48 for i in range(25)]],.035)
    tube(f,'dome_base_ring','lead',[(cx+radius*math.cos(t),cz,-.67+radius*math.sin(t)) for t in [i*math.tau/64 for i in range(65)]],.09)
    f.box('dome_finial_stem','metal',cx,18.33,.10,.66,.10,-.67)
    # Faceted globe is an authored ornamental cap, with no external mesh asset.
    for j in range(16):
        a,b=j*math.tau/16,(j+1)*math.tau/16
        for sign in [-1,1]:f.group('dome_finial_globe','metal').add([f.point(cx+.19*math.cos(a),18.40,-.67+.19*math.sin(a)),f.point(cx+.19*math.cos(b),18.40,-.67+.19*math.sin(b)),f.point(cx,18.40+sign*.23,-.67)],[(0,1,2)])
    return f


records=[]
for profile in profiles:
    code=profile['code'];height=profile['height'];groups={}
    collection=bpy.data.collections[code+'_EXTERIOR']
    for obj in list(collection.all_objects):bpy.data.objects.remove(obj,do_unlink=True)
    front=None
    for wall in profile['walls']:
        f=Facade(profile,wall,groups);L=f.length
        if wall['front']:front=f
        if code=='KGS' and wall['front']:
            front=kgs_front(profile,wall,groups);continue
        if wall['party'] or L<1.8:
            f.box('party_wall','brick' if code=='COW' else 'darkbrick',L/2,height/2,L,height);continue
        count=max(1,round(L/(2.85 if code=='COW' else 2.5)));pitch=L/count
        levels=[0,4.9,9.6,14.0,18] if code=='COW' else [0,4.5,8.2,11.9,15.2]
        for floor,(bottom,top) in enumerate(zip(levels,levels[1:])):
            for i in range(count):
                x=(i+.5)*pitch
                if code=='COW' and wall['front'] and floor==0:continue
                width=min(1.62,pitch*.61);low=bottom+.82;high=top-.63
                material='stone' if code=='COW' and floor==0 else 'brick' if code=='COW' else 'darkbrick'
                opening(f,x,low,high,width,pitch,bottom,top,material,bars=3)
                if code=='COW' and wall['front'] and floor==1:
                    for sign in [-1,1]:f.box('corner_window_architrave','trim',x+sign*(width/2+.20),(low+high)/2,.22,high-low+.4,.40,.12)
                    f.box('corner_window_pediment','trim',x,high+.32,width+.84,.24,.62,.18)
                    for sign in [-1,1]:f.box('corner_sill_bracket','stone',x+sign*.59,low-.37,.25,.42,.57,.16)
        if code=='COW' and wall['front']:
            radius=.95;x=L/2
            for a,b in [(0,x-radius),(x+radius,L)]:f.box('corner_portal_masonry','stone',(a+b)/2,2.45,b-a,4.9,.36,-.18)
            for i in range(40):
                xx=x-radius+(i+.5)*2*radius/40;bottom=2.9+math.sqrt(max(0,radius**2-(xx-x)**2))
                f.box('corner_arch_spandrel','stone',xx,(bottom+4.9)/2,2*radius/40+.002,4.9-bottom,.36,-.18)
            entrance(f,'COW')
        for z,w,d in [(levels[1],.23,.49),(height-.36,.16,.48),(height-.12,.18,.72),(height+.08,.12,.82)]:f.box('layered_cornice','trim',L/2,z,L+.08,w,d,.10)
        if code=='COW':
            # Corner bands retain brick gaps; fine cornice dentils read at closer range.
            for x in [.26,L-.26]:
                for j in range(15):f.box('alternating_quoins','stone',x,5.22+j*.81,.52 if j%2 else .76,.32,.18,-.035)
            for i in range(max(1,int(L/.42))):f.box('cornice_dentils','stone',(i+.5)*L/max(1,int(L/.42)),height-.28,.18,.25,.38,.33)
            tube(f,'eaves_gutter','metal',[(0,height+.16,.47),(L,height+.16,.47)],.065)
            # Dormer with side cheeks, six-pane sash and a pitched lead cap.
            count=1 if wall['front'] else max(1,round(L/4.6))
            for i in range(count):
                x=(i+.5)*L/count;z=height+.34
                f.box('dormer_back','slate',x,z+1.05,1.48,2.1,.25,-1.25)
                for sign in [-1,1]:f.box('dormer_cheek','lead',x+sign*.68,z+1.02,.17,2.05,1.26,-.70)
                opening(f,x,z+.20,z+1.90,.96,1.36,z,z+2.13,'stone',depth=-.04,bars=3)
                pediment(f,x,z+2.18,1.66,.34,.05)
                for sign in [-1,1]:
                    f.group('dormer_pitched_cap','lead').add([f.point(x,z+2.58,.28),f.point(x+sign*.91,z+2.20,.28),f.point(x+sign*.91,z+2.20,-1.44),f.point(x,z+2.58,-1.44)],[(0,1,2,3)])
    roof=Geometry(code,'roof','slate');center=Vector(profile['building']['center'])
    if code=='COW':
        ring=profile['building']['rings'][0]
        for a,b in zip(ring,ring[1:]+ring[:1]):
            ai=center+(Vector(a)-center)*.77;bi=center+(Vector(b)-center)*.77
            roof.add([(*a,height),(*b,height),(*bi,height+2.9),(*ai,height+2.9)],[(0,1,2,3)])
        for triangle in profile['building']['triangles']:
            roof.add([(*(center+(Vector(p)-center)*.77),height+2.9) for p in triangle],[(0,1,2)])
        # Two stacks on the visible roof shoulders; pots and caps follow the reference silhouette.
        for x in [front.length*.5]:
            for depth in [-3.2,-9.1]:
                front.box('chimney_brick_stack','brick',x,20.70,1.80,2.4,.75,depth)
                front.box('chimney_cap','stone',x,21.94,2.02,.18,.96,depth)
                for i in range(4):tube(front,'chimney_pots','brick',[(x+(i-1.5)*.40,22.03,depth),(x+(i-1.5)*.40,22.48,depth)],.12)
    else:
        for triangle in profile['building']['triangles']:roof.add([(x,y,height+.05) for x,y in triangle],[(0,1,2)])
    groups['roof']=roof
    for geometry in groups.values():geometry.finish()
    records.append({'code':code,'exteriorDirection':[front.n.x,.60,-front.n.y],
                    'scope':'Photographed heritage facade details; footprint retained. Heights, ornamental profiles, roof depth and unseen elevations remain estimates. No surveyed interior claim.',
                    'detailView': {'label':'入口细节', 'position': list(front.point(front.length/2,4.4,14.0)), 'target': list(front.point(front.length/2,3.7,0)), 'fov':46},
                    'reference':profile['reference'],'components':sum(g.parts for g in groups.values()),
                    'features': ['canted stone bays','ribbed lead dome','broken pediment','arched green entrance sign'] if code=='KGS' else ['six-pane sashes','layered dentil cornice','pitched dormers','rusticated corner portal','chimneys']})
bpy.context.view_layer.update()
assert fingerprint()==before,'Geometry outside the two heritage studies changed'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v09.blend'))
(OUT/'heritage-manifest.json').write_text(json.dumps({'protectedGeometrySha256':before,'buildings':records},indent=2)+'\n')
print('HERITAGE_DETAILS_COMPLETE',records,flush=True)
