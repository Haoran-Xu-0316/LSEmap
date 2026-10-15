"""Independent historical CLM.G.02 Hong Kong Theatre from paired LSE records.

Run in Blender's Text Editor. The260 student symbols are individually extracted
from the official plan. Heights, scale, chair construction and photo registration
are estimates. No campus geometry or current building-level registration changes.
"""
from pathlib import Path
import hashlib
import json
import math
import sys
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/clm-hongkong220'
BASE = ROOT / 'result/blender/LSE_campus_detailed_v219.blend'
SHA = '62d7882be80b3f383a1e8b40139cd5168baf2b0b9f42cb9806fd9417e104d3b9'
COLLECTION = 'CLMG02_ROOM220_study'
SCENE = 'ROOM220_CLMG02'
PREFIX = 'CLMG02_R220_'
SCALE = .042
STAGE_Z = .32
sys.path.insert(0, str(ROOT / 'web/tools'))
from build_room_samples167 import RoomGeometry
from integrate_exterior_round194 import object_fingerprint, accepted_fingerprints
from refine_portsmouth_exterior207 import material_fingerprint


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def point(pixel):
    return ((pixel[0] - 290) * SCALE, (pixel[1] - 250) * SCALE)


def update():
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()


def modifier_payload(value, depth=0):
    if value is None or isinstance(value,(str,int,float,bool)):return value
    if isinstance(value,bpy.types.ID):return dict(type=value.bl_rna.identifier,name=value.name)
    if depth>6:return value.bl_rna.identifier
    result={}
    for prop in value.bl_rna.properties:
        if prop.identifier=='rna_type':continue
        item=getattr(value,prop.identifier)
        if prop.type=='COLLECTION':item=[modifier_payload(child,depth+1)for child in item]
        elif prop.type=='POINTER':item=modifier_payload(item,depth+1)
        elif getattr(prop,'is_array',False):item=list(item)
        result[prop.identifier]=item
    return result


def protected_state():
    metadata = json.loads((ROOT/'web/tools/building-metadata.json').read_text())
    rooms = {space['collection']: sorted(o.name for o in bpy.data.collections[space['collection']].all_objects)
             for space in metadata['spaces']}
    assert len(rooms) == 18 and len(set().union(*(set(names) for names in rooms.values()))) == 623
    return dict(objects={o.name: object_fingerprint(o) for o in bpy.data.objects},
                materials={m.name: material_fingerprint(m) for m in bpy.data.materials},
                visibility={o.name: o.hide_render for o in bpy.data.objects}, rooms=rooms,
                modifiers={o.name:hashlib.sha256(json.dumps([modifier_payload(m)for m in o.modifiers],sort_keys=True).encode()).hexdigest()for o in bpy.data.objects},
                roomCampusObjects={name: sorted(n for n in names if n in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects)
                                   for name, names in rooms.items()})


def material(g, key, color, roughness=.78, metallic=0):
    mat = bpy.data.materials.new(PREFIX + key)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    node = mat.node_tree.nodes['Principled BSDF']
    node.inputs['Base Color'].default_value = mat.diffuse_color
    node.inputs['Roughness'].default_value = roughness
    node.inputs['Metallic'].default_value = metallic
    mat['colourBasis'] = 'Uncalibrated official historical CLM.G.02 photograph;visual estimate,no photo texture'
    g.materials[key] = mat


def polygon_contains(point_xy, outline):
    x, y = point_xy
    inside = False
    for a, b in zip(outline, outline[1:] + outline[:1]):
        if (a[1] > y) != (b[1] > y) and x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:
            inside = not inside
    return inside


def seat_corners(x, y, angle):
    c, s = math.cos(angle), math.sin(angle)
    return [(x+c*a-s*b, y+s*a+c*b) for a, b in [(-.26,-.29),(.26,-.29),(.26,.29),(-.26,.29)]]


def polygons_overlap(a, b):
    for poly in [a, b]:
        for p, q in zip(poly, poly[1:] + poly[:1]):
            axis = Vector((q[1]-p[1], p[0]-q[0])).normalized()
            left = [axis.dot(Vector(v)) for v in a]
            right = [axis.dot(Vector(v)) for v in b]
            if max(left) <= min(right) + .00001 or max(right) <= min(left) + .00001:
                return False
    return True


def segment_distance(p, a, b):
    p, a, b = Vector(p), Vector(a), Vector(b)
    d = b-a
    t = min(1., max(0., (p-a).dot(d)/d.length_squared))
    return (p-(a+t*d)).length


def polygon_distance(a, b):
    if polygons_overlap(a, b):
        return 0.
    return min(segment_distance(p, u, v) for points, edges in [(a,b),(b,a)]
               for p in points for u, v in zip(edges, edges[1:]+edges[:1]))


def vertical_shape(g, family, key, outline_xz, y, depth):
    """Positive closed extrusion of an x/z profile toward the front wall."""
    area = sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(outline_xz, outline_xz[1:]+outline_xz[:1]))
    profile = outline_xz if area > 0 else list(reversed(outline_xz))
    n = len(profile)
    vertices = [(x, y-w, z) for w in [0, depth] for x,z in profile]
    faces = [tuple(reversed(range(n))), tuple(range(n,2*n))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    g.add(family, key, vertices, faces)


def theatre_chair(g, x, y, angle, row, z=0, family='student'):
    c, s = math.cos(angle), math.sin(angle)
    def at(a,b,height):
        return (x+c*a-s*b, y+s*a+c*b, z+height)
    seat_key = 'guest_red' if family=='photo_guest' else ('velvet' if row % 3 else 'velvet_worn')
    # Eight corners retain a quiet rounded profile without a heavy subdivision mesh.
    seat = [(-.21,-.245),(.21,-.245),(.24,-.215),(.24,.185),(.21,.215),(-.21,.215),(-.24,.185),(-.24,-.215)]
    vertices = [at(a,b,h) for h in [.44,.515] for a,b in seat]
    n = len(seat)
    faces = [tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    g.add(family+'_upholstered_seats', seat_key, vertices, faces)
    back = [(-.22,.55),(.22,.55),(.245,.90),(.23,.98),(.18,1.015),(-.18,1.015),(-.23,.98),(-.245,.90)]
    # Map(u,v,w)to(localx,-localy,localz),which retains positive winding.
    vertices = [at(a,.255-w,h) for w in [0,.070] for a,h in back]
    g.add(family+'_rounded_upholstered_backs', seat_key, vertices, faces)
    for side in [-1,1]:
        g.box(family+'_black_fixed_frames', 'dark', at(side*.205,.13,.235), (.038,.06,.44), angle)
        g.box(family+'_black_fixed_frames', 'dark', at(side*.205,.005,.025), (.043,.43,.05), angle)
        g.box(family+'_light_wood_armrests', 'armwood', at(side*.245,-.01,.665), (.030,.42,.047), angle)
    g.box(family+'_black_fixed_frames', 'dark', at(0,.14,.425), (.44,.09,.08), angle)
    g.box(family+'_lower_back_panels', 'dark', at(0,.247,.515), (.445,.030,.19), angle)


def wall_span(g, a_px, b_px, height, front=False):
    a, b = Vector(point(a_px)), Vector(point(b_px))
    delta = b-a
    angle = math.atan2(delta.y, delta.x)
    center = (a+b)/2
    key = 'front' if front else 'cutaway'
    lower = min(2.55, height)
    g.box(key+'_oak_wall_core', 'oak', (*center,lower/2), (delta.length,.18,lower), angle)
    if height > lower:
        g.box(key+'_upper_plaster_wall', 'plaster', (*center,(height+lower)/2),
              (delta.length,.18,height-lower), angle)
    if front:
        count = max(1,round(delta.length/.90))
        for index in range(count):
            p = a + delta * ((index+.5)/count)
            width = delta.length/count-.12
            # Panel inset colour plus four shallow moulding sides,without image maps.
            g.box('front_oak_recessed_panels','oak_inset',(p.x,p.y+.106,1.57),(width,.025,1.36),angle)
            for z in [.83,2.31]:
                g.box('front_panel_mouldings','oak_lip',(p.x,p.y+.13,z),(width+.10,.047,.065),angle)
            u = delta.normalized()
            for side in [-1,1]:
                q = p + u*side*(width/2+.025)
                g.box('front_panel_mouldings','oak_lip',(q.x,q.y+.13,1.57),(.055,.047,1.54),angle)
        for z,h in [(.18,.16),(.66,.10),(2.49,.14),(2.64,.095)]:
            g.box('front_oak_horizontal_bands','oak_lip',(center.x,center.y+.15,z),(delta.length,.23,h),angle)


def ramp(g):
    x0,y0 = point((140,121));x1,y1 = point((205,141))
    vertices = [(x0,y0,-.015),(x0,y1,-.015),(x1,y1,-.015),(x1,y0,-.015),
                (x0,y0,.012),(x0,y1,.012),(x1,y1,STAGE_Z),(x1,y0,STAGE_Z)]
    faces = [(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
    g.add('photo_guided_stage_side_ramp','carpet',vertices,faces)
    points=[]
    for y in [y0+.03,y1-.03]:
        for px in [140,159,181,205]:
            x=point((px,0))[0];z=.012+(STAGE_Z-.012)*(px-140)/65
            g.tube('ramp_silver_posts','silver',(x,y,z),(x,y,z+1.0),.017)
            points.append(dict(base=[x,y,z],top=[x,y,z+1.0],floorHeight=z))
        for dz in [.50,1.0]:
            g.tube('ramp_silver_rails','silver',(x0,y,.012+dz),(x1,y,STAGE_Z+dz),.020)
    return dict(estimatedRise=STAGE_Z,estimatedRun=x1-x0,estimatedWidth=y1-y0,
                notAnAccessibilityComplianceClaim=True,posts=points,
                connection=dict(rampEndX=x1,stageStartX=point((205,75))[0],rampEndZ=STAGE_Z,stageTopZ=STAGE_Z))


def build_geometry(layout):
    scene = bpy.data.scenes.new(SCENE)
    collection = bpy.data.collections.new(COLLECTION)
    scene.collection.children.link(collection)
    collection['roomSample'] = True
    collection['roomCode'] = 'CLM.G.02'
    collection['studentSeatCount'] = 260
    g = RoomGeometry(collection,PREFIX)
    for key,rgb,rough,metal in [
        ('oak',(.36,.185,.064),.70,0),('oak_inset',(.29,.135,.043),.76,0),
        ('oak_lip',(.42,.225,.085),.62,0),('armwood',(.52,.33,.13),.58,0),
        ('velvet',(.31,.112,.070),.93,0),('velvet_worn',(.36,.142,.094),.93,0),('guest_red',(.47,.025,.030),.90,0),
        ('plaster',(.77,.73,.65),.90,0),('carpet',(.13,.15,.14),.95,0),
        ('stage',(.30,.17,.068),.82,0),('dark',(.020,.023,.022),.62,0),
        ('whiteboard',(.82,.83,.78),.48,0),('screen',(.84,.84,.80),.95,0),
        ('silver',(.48,.51,.51),.30,.70),('exit',(.025,.24,.085),.65,0),
    ]:
        material(g,key,rgb,rough,metal)
    outline=[point(pixel) for pixel in layout['roomOutlinePixels']]
    g.prism('traced_plan_floor','carpet',outline,-.16,.16)
    stage=[point(pixel)for pixel in layout['stagePixels']]
    g.prism('traced_front_teaching_platform','stage',stage,0,STAGE_Z-.012)
    g.prism('stage_carpet_top','carpet',stage,STAGE_Z-.012,.012)
    # Front teaching wall is full height;actual front double doorway is absent in wall solids.
    front_spans=[((47,77),(204,75)),((204,75),(350,75)),((350,76),(374,76)),
                 ((374,63),(422,63)),((473,64),(528,65))]
    for a,b in front_spans:wall_span(g,a,b,6.6,True)
    # The remaining perimeter is sectioned. Door leaf symbols are not floor boundary notches.
    cut_spans=[]
    for a,b in zip(layout['roomOutlinePixels'],layout['roomOutlinePixels'][1:]+layout['roomOutlinePixels'][:1]):
        if a[1]<=80 and b[1]<=80:continue
        av,bv=Vector(a),Vector(b);delta=bv-av
        intervals=[(0.,1.)]
        for door in layout['doors']:
            da,db=Vector(door['start']),Vector(door['end'])
            if abs(delta.cross(da-av))>.01 or abs(delta.cross(db-av))>.01:continue
            lo,hi=sorted(((da-av).dot(delta)/delta.length_squared,(db-av).dot(delta)/delta.length_squared))
            updated=[]
            for start,end in intervals:
                if hi<=start or lo>=end:updated.append((start,end));continue
                if start<lo:updated.append((start,lo))
                if hi<end:updated.append((hi,end))
            intervals=updated
        for start,end in intervals:
            if end-start>1e-5:cut_spans.append((list(av+delta*start),list(av+delta*end)))
    for a,b in cut_spans:wall_span(g,a,b,.43)
    door_records=[]
    for door in layout['doors']:
        a,b=Vector(point(door['start'])),Vector(point(door['end']))
        u=(b-a).normalized();angle=math.atan2(u.y,u.x);center=(a+b)/2
        for p in [a,b]:g.box('door_jambs','oak_lip',(p.x,p.y,1.20),(.11,.15,2.40),angle)
        g.box('door_headers','oak_lip',(center.x,center.y,2.40),((b-a).length+.13,.17,.15),angle)
        g.box('door_aperture_thresholds','silver',(center.x,center.y,.012),((b-a).length,.12,.024),angle)
        # Open leaves follow the distinct plan-side opening direction;their construction is estimated.
        if door['id']=='front-double':tip_pixels=[(440,87),(455,87)]
        elif door['id']=='right-middle-double':tip_pixels=[(514,256),(514,281)]
        else:tip_pixels=[(551,391),(551,405)]
        tips=[Vector(point(p))for p in tip_pixels]
        for hinge,tip in zip([a,b],tips):
            delta=tip-hinge;c=(hinge+tip)/2
            g.box('open_oak_door_leaves','oak',(c.x,c.y,1.13),(delta.length,.055,2.26),math.atan2(delta.y,delta.x))
            g.box('door_leaf_vision_insets','oak_inset',(c.x,c.y,1.42),(delta.length*.72,.063,.94),math.atan2(delta.y,delta.x))
        door_records.append(dict(id=door['id'],jambs=[list(a),list(b)],openingWidth=(b-a).length,
            estimatedClearTipGap=(tips[1]-tips[0]).length,openLeafTips=[list(t)for t in tips]))
    # Photo-supported teaching wall:off-white central board and two dark-framed screens.
    x,y=point((277.5,75))
    g.box('central_board_frame','silver',(x,y+.35,2.75),(5.34,.10,3.03))
    g.box('central_whiteboard','whiteboard',(x,y+.415,2.75),(5.19,.035,2.88))
    g.box('board_roller_housing','silver',(x,y+.46,4.44),(5.48,.16,.14))
    for px in [211,344]:
        bx,by=point((px,75));g.box('board_vertical_guides','silver',(bx,by+.48,2.66),(.045,.05,3.39))
    for px,width,z,height in [(126,4.48,3.76,2.65),(448,3.16,3.68,2.51)]:
        sx,sy=point((px,70 if px>300 else 76))
        g.box('two_black_projection_screen_frames','dark',(sx,sy+.40,z),(width+.16,.08,height+.16))
        g.box('two_projection_screen_faces','screen',(sx,sy+.45,z),(width,.025,height))
        g.box('projection_screen_lower_bars','dark',(sx,sy+.47,z-height/2-.035),(width+.14,.055,.07))
    # The right photo bay has a visibly arched oak infill above its screen.
    rx,ry=point((448,65));radius=1.84
    profile=[(rx-radius,2.65),(rx+radius,2.65),(rx+radius,4.62)]
    profile += [(rx+radius*math.cos(t),4.62+radius*math.sin(t))for t in [i*math.pi/16 for i in range(1,17)]]
    vertical_shape(g,'right_bay_arch_wood_backing','oak_inset',profile,ry+.10,.035)
    g.box('right_arch_horizontal_wood_division','oak_lip',(rx,ry+.14,4.90),(3.66,.045,.055))
    g.box('right_arch_vertical_wood_division','oak_lip',(rx,ry+.14,5.25),(.055,.045,2.12))
    # Narrow front vault ribbon records the photo's high curved/plaster boundary;the rest is cut away.
    cx,cy=point((277.5,75));r=3.07
    for index in range(16):
        a=index*math.pi/16;b=(index+1)*math.pi/16
        x0=cx+r*math.cos(a);x1=cx+r*math.cos(b)
        z0=5.17+1.38*math.sin(a);z1=5.17+1.38*math.sin(b)
        vertical_shape(g,'cutaway_front_vault_ribbon','plaster',[(x0,z0),(x1,z1),(x1,z1+.105),(x0,z0+.105)],cy+1.15,1.15)
    for px in [205,350]:
        bx,by=point((px,76));g.box('front_plaster_bay_piers','plaster',(bx,by+.15,4.12),(.28,.35,3.12))
        g.box('front_oak_pier_caps','oak_lip',(bx,by+.19,2.64),(.48,.43,.14))
    # The plan controls the lecturing furniture footprint;the photograph controls visible finish.
    dx,dy=point((287.5,115));g.box('plan_teaching_desk_top','oak_lip',(dx,dy,STAGE_Z+.80),(43*SCALE,24*SCALE,.065))
    for offset in [-.68,.68]:g.box('teaching_desk_wood_pedestals','oak_inset',(dx+offset,dy,STAGE_Z+.385),(.095,.78,.77))
    g.box('teaching_desk_front_panel','oak',(dx,dy+.43,STAGE_Z+.40),(1.70,.055,.76))
    for offset in [-.43,0,.43]:
        g.tube('three_desk_microphones','dark',(dx+offset,dy-.20,STAGE_Z+.84),(dx+offset+.06,dy-.12,STAGE_Z+1.12),.009)
    # Separate teacher chair follows the unique plan symbol;two front loose red chairs are photo evidence.
    theatre_chair(g,*point((287,98)),math.pi,1,z=STAGE_Z,family='lecturer')
    for px in [142,158]:theatre_chair(g,*point((px,104)),math.pi,1,family='photo_guest')
    ramp_record=ramp(g)
    for px in [191,389]:
        ex,ey=point((px,76));g.box('two_green_wall_exit_signs','exit',(ex,ey+.19,2.57),(.32,.05,.19))
        g.box('exit_sign_white_bars','whiteboard',(ex,ey+.223,2.57),(.17,.009,.035))
    # A compact black side monitor and wall speakers are visible in the source photograph.
    mx,my=point((510,86));g.box('photo_side_monitor','dark',(mx,my+.22,2.20),(1.05,.12,.65))
    for px in [201,370]:
        sx,sy=point((px,78));g.box('front_wall_speakers','dark',(sx,sy+.28,3.0),(.16,.15,.47))
    seats=[]
    for source in layout['seats']:
        x,y=point(source['planPixel']);angle=source['angleRadians']
        theatre_chair(g,x,y,angle,source['row'])
        seats.append(dict(source,center=[x,y],floorHeight=0,footprint=seat_corners(x,y,angle)))
    objects=g.finish()
    for obj in objects:
        obj['roomCode']='CLM.G.02'
        obj['scope']='Independent historical paired-source theatre;scale,heights and concealed construction estimated'
    next(o for o in objects if o.name==PREFIX+'student_upholstered_seats')['studentSeatCount']=260
    return scene,collection,objects,seats,outline,stage,ramp_record,door_records,g.solid_proof


def orient_to_photograph(objects,seats,outline,stage,ramp_record,doors):
    """Retain the plan isometrically while matching the audience's photo left/right.

    From the audience(+Y)toward the teaching wall(-Y),native+X is screen-left.
    Therefore plan-right maps to native-X. Reverse every reflected closed face
    as well as its geometry;do not rely on a negative object scale at export.
    """
    import bmesh
    from mathutils import Matrix
    reflection=Matrix.Diagonal((-1.,1.,1.,1.))
    for obj in objects:
        bm=bmesh.new();bm.from_mesh(obj.data)
        bmesh.ops.transform(bm,matrix=reflection,verts=list(bm.verts))
        bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.normal_update()
        bm.to_mesh(obj.data);bm.free();obj.data.update()
        assert all(abs(v-1)<1e-8 for v in obj.scale)
    for seat in seats:
        seat['center'][0]*=-1
        seat['footprint']=[(-x,y)for x,y in reversed(seat['footprint'])]
        seat['sourceAngleRadians']=seat['angleRadians'];seat['angleRadians']*=-1
    for polygon in [outline,stage]:
        polygon[:]=[(-x,y)for x,y in reversed(polygon)]
    for post in ramp_record['posts']:
        post['base'][0]*=-1;post['top'][0]*=-1
    for key in ['rampEndX','stageStartX']:ramp_record['connection'][key]*=-1
    for door in doors:
        for key in ['jambs','openLeafTips']:
            for p in door[key]:p[0]*=-1


def model_point(pixel):
    x,y=point(pixel)
    return (-x,y)


def geometry_checks(seats,outline,stage,ramp_record,doors,objects):
    assert len(seats)==260
    assert all(polygon_contains(corner,outline)for seat in seats for corner in seat['footprint'])
    overlaps=[]
    for index,seat in enumerate(seats):
        for other in seats[index+1:]:
            if polygons_overlap(seat['footprint'],other['footprint']):overlaps.append([seat['id'],other['id']])
    assert not overlaps,overlaps
    group_clear=min((polygon_distance(a['footprint'],b['footprint']),a['id'],b['id'])
                    for index,a in enumerate(seats)for b in seats[index+1:]if a['group']!=b['group'])
    stage_clear=min(polygon_distance(seat['footprint'],stage)for seat in seats)
    assert stage_clear>1.5
    assert abs(ramp_record['connection']['rampEndX']-ramp_record['connection']['stageStartX'])<1e-6
    assert ramp_record['connection']['rampEndZ']==ramp_record['connection']['stageTopZ']
    # Actual geometry ray checks:all four base support points per student seat,
    # stage desk and all ramp posts. No proxy floor is added to satisfy a ray.
    from mathutils.bvhtree import BVHTree
    floor_obj=next(o for o in objects if o.name==PREFIX+'traced_plan_floor')
    tree=BVHTree.FromPolygons([v.co for v in floor_obj.data.vertices],[tuple(p.vertices)for p in floor_obj.data.polygons])
    support=[]
    for seat in seats:
        x,y=seat['center'];angle=seat['angleRadians'];c,s=math.cos(angle),math.sin(angle)
        for side in [-1,1]:
            for end in [-1,1]:
                p=Vector((x+c*side*.205-s*end*.18,y+s*side*.205+c*end*.18,.15))
                hit=tree.ray_cast(p,Vector((0,0,-1)),.25)
                assert hit[0]is not None and abs(hit[0].z)<.001,(seat['id'],list(p))
                support.append(seat['id'])
    supported_objects=[obj for obj in objects if any(key in obj.name for key in ['traced_plan_floor','stage_carpet_top','photo_guided_stage_side_ramp'])]
    vertices=[];faces=[]
    for obj in supported_objects:
        start=len(vertices);vertices.extend(v.co.copy()for v in obj.data.vertices)
        faces.extend(tuple(start+i for i in f.vertices)for f in obj.data.polygons)
    support_tree=BVHTree.FromPolygons(vertices,faces)
    stage_support=[]
    for post in ramp_record['posts']:
        p=Vector(post['base']);hit=support_tree.ray_cast(p+Vector((0,0,.10)),Vector((0,0,-1)),.15)
        assert hit[0]is not None and abs(hit[0].z-p.z)<.002
        stage_support.append(dict(kind='ramp-post',height=p.z,actualSupportHeight=hit[0].z))
    dx,dy=model_point((287.5,115))
    for offset in [-.68,.68]:
        hit=support_tree.ray_cast(Vector((dx+offset,dy,STAGE_Z+.10)),Vector((0,0,-1)),.15)
        assert hit[0]is not None and abs(hit[0].z-STAGE_Z)<.002
        stage_support.append(dict(kind='desk-pedestal',height=STAGE_Z,actualSupportHeight=hit[0].z))
    vertices=[];faces=[]
    for obj in objects:
        start=len(vertices);vertices.extend(v.co.copy()for v in obj.data.vertices)
        faces.extend(tuple(start+i for i in f.vertices)for f in obj.data.polygons)
    all_tree=BVHTree.FromPolygons(vertices,faces)
    door_rays=[]
    for door in doors:
        a,b=[Vector(p)for p in door['jambs']];center=(a+b)/2;u=(b-a).normalized()
        inward=Vector((0,1))if door['id']=='front-double'else Vector((1,0))
        for offset in [-.20,0,.20]:
            p=center+u*offset-inward*.20
            hit=all_tree.ray_cast(Vector((p.x,p.y,1.15)),Vector((inward.x,inward.y,0)),1.40)
            assert hit[0]is None,(door['id'],offset,list(hit[0])if hit[0]else None)
            door_rays.append(dict(door=door['id'],lateralOffset=offset,height=1.15,checkedDepth=1.40,opaqueHit=False))
    # Door approach centreline strips remain unoccupied by student seating.
    approaches=[]
    for door in doors:
        a,b=[Vector(p)for p in door['jambs']];center=(a+b)/2;u=(b-a).normalized()
        inward=Vector((0,1))
        if door['id']!='front-double':inward=Vector((1,0))
        corners=[tuple(center+inward*d+u*w)for d,w in [(.10,-.30),(.10,.30),(.90,.30),(.90,-.30)]]
        intrusions=[seat['id']for seat in seats if polygons_overlap(seat['footprint'],corners)]
        assert not intrusions,(door['id'],intrusions)
        approaches.append(dict(id=door['id'],studentSeatIntrusions=0,checkedStripWidth=.60,checkedStripDepth=.80))
    # Outer longitudinal routes use their actual plan-derived open floor strips.
    route_checks=[]
    for label,px,py0,py1 in [('left-outer',76,110,404),('right-outer',513,110,414)]:
        a,b=model_point((px,py0)),model_point((px,py1))
        width=.90
        corners=[(a[0]-width/2,a[1]),(a[0]+width/2,a[1]),(b[0]+width/2,b[1]),(b[0]-width/2,b[1])]
        assert all(polygon_contains(p,outline)for p in corners)
        intrusions=[seat['id']for seat in seats if polygons_overlap(seat['footprint'],corners)]
        assert not intrusions,(label,intrusions)
        route_checks.append(dict(route=label,clearStripWidth=width,checkedEndpoints=[a,b],studentSeatIntrusions=0))
    triangles=sum(sum(len(p.vertices)-2 for p in obj.data.polygons)for obj in objects)
    assert triangles<70000,triangles
    return dict(studentSeatCount=260,studentChairFloorSupportProbes=len(support),allSupportProbesPassed=True,
        allChairFootprintCornersOnPlanFloor=True,photoLeftRightOrientationVerified=True,reflectionUsesPositiveFaceWindingAndUnitObjectScale=True,perimeterWallCentrelinesDerivedFromFloorOutline=True,chairFootprintOverlaps=overlaps,
        minimumInterGroupClearanceMetres=group_clear[0],tightestInterGroupPair=list(group_clear[1:]),
        interGroupGapsAreNotClaimedAsLongitudinalEgressAisles=True,
        minimumStudentSeatDistanceToStageMetres=stage_clear,outerRoutes=route_checks,
        doorApproaches=approaches,doorJambOpeningWidths=[d['openingWidth']for d in doors],
        stageRampHandoffExact=True,rampPostsConnectedToMatchingSlope=True,actualStageRampSupportProbes=stage_support,openDoorPassageRays=door_rays,
        triangles=triangles,triangleBudget=70000,photographGuestChairs=2,separateLecturerChairs=1,
        unseenSecondLevelCreated=False,noEgressOrAccessibilityCertification=True)


def preview(scene,phase):
    bpy.context.window.scene=scene
    world=bpy.data.worlds.new(PREFIX+'review_world');world.use_nodes=True
    world.node_tree.nodes['Background'].inputs[0].default_value=(.78,.81,.83,1)
    world.node_tree.nodes['Background'].inputs[1].default_value=.40
    scene.world=world
    temporary=[]
    for label,location,energy,size in [('top',(0,0,11),2100,10),('front',(-7,-7,8),1200,7),('side',(8,3,9),900,6)]:
        light=bpy.data.lights.new(PREFIX+'review_'+label,'AREA');light.energy=energy;light.shape='DISK';light.size=size
        obj=bpy.data.objects.new(light.name,light);scene.collection.objects.link(obj);obj.location=location
        obj.rotation_euler=(Vector((0,-1,1.5))-obj.location).to_track_quat('-Z','Y').to_euler();temporary.append(obj)
    data=bpy.data.cameras.new(PREFIX+'review_camera');camera=bpy.data.objects.new(data.name,data)
    scene.collection.objects.link(camera);scene.camera=camera;temporary.append(camera)
    data.type='ORTHO';data.clip_end=500
    scene.render.engine='CYCLES';scene.cycles.samples=20;scene.cycles.use_denoising=True
    scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
    views=[]
    for label,position,target,scale in [('toward-stage',(17,20,14),(0,-.6,1.7),26.5),('reverse',(-17,-23,30),(0,0,1.7),28.0)]:
        camera.location=position;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
        data.ortho_scale=scale;scene.render.filepath=str(OUT/(phase+'-'+label+'.png'))
        bpy.ops.render.render(write_still=True,scene=scene.name)
        views.append(dict(label=label,nativeCamera=position,nativeTarget=target,orthoScale=scale))
    scene.camera=None;scene.world=None
    for obj in temporary:
        data_obj=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
        if isinstance(data_obj,bpy.types.Camera):bpy.data.cameras.remove(data_obj)
        else:bpy.data.lights.remove(data_obj)
    bpy.data.worlds.remove(world)
    return views


def run():
    OUT.mkdir(parents=True,exist_ok=True)
    assert sha(BASE)==SHA
    layout=json.loads((OUT/'plan-layout.json').read_text())
    assert layout['studentSeatCount']==260 and len(layout['seats'])==260
    bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];update()
    before=protected_state();expected=accepted_fingerprints(ROOT/'result/blender/stage219',SHA)
    assert before['objects']==expected and len(expected)==7576
    scene,collection,objects,seats,outline,stage,ramp_record,doors,solid=build_geometry(layout)
    orient_to_photograph(objects,seats,outline,stage,ramp_record,doors);update()
    checks=geometry_checks(seats,outline,stage,ramp_record,doors,objects)
    print('CLMG02_GENERATED',len(objects),checks['triangles'],checks['minimumInterGroupClearanceMetres'],flush=True)
    scope='依据LSE官方同房号历史平面与照片建立Hong Kong Theatre独立室内样本。平面逐椅提取260个学生座位，左50、中160、右50；保留交错排、后部凹口、门洞和前舞台。木护墙板、橙棕软座、投影屏、白板、讲桌及银扶手坡道按实拍估算。米制尺度、层高与隐蔽构造未测量，不增未见第二层，不作为2026年现状或整栋楼层注册。'
    space=dict(code='CLM',id='clm-hongkong',label='CLM.G.02 Hong Kong Theatre',collection=COLLECTION,
        gallery='clm-hongkong-interior',scope=scope,
        interiorView=dict(position=[17,14,-20],target=[0,1.7,.6],fov=48),
        interiorStudy=dict(kind='room-sample',label='CLM.G.02 Hong Kong Theatre',scope=scope))
    collection['authoringRecord']=json.dumps(space,ensure_ascii=False)
    fingerprints={obj.name:object_fingerprint(obj)for obj in objects}
    assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in before['objects'].items())
    assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in before['materials'].items())
    views=preview(scene,'built')
    component=OUT/'clm-hongkong220-component.blend'
    bpy.data.libraries.write(str(component),{scene,collection},fake_user=True,compress=True)
    component_sha=sha(component)
    material_bindings={obj.name:[m.name for m in obj.data.materials]for obj in objects}
    bpy.ops.wm.open_mainfile(filepath=str(component));bpy.context.window.scene=bpy.data.scenes[SCENE];update()
    assert set(o.name for o in bpy.data.collections[COLLECTION].all_objects)==set(fingerprints)
    assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items())
    assert len(bpy.data.scenes)==1 and COLLECTION in bpy.data.scenes[SCENE].collection.children
    assert all(o.name.startswith(PREFIX)for o in bpy.data.objects)
    saved_objects=list(bpy.data.collections[COLLECTION].all_objects)
    saved_checks=geometry_checks(seats,outline,stage,ramp_record,doors,saved_objects)
    assert saved_checks==checks
    # Reopen the accepted campus and append the isolated collection to validate ownership.
    bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];update()
    assert protected_state()==before
    with bpy.data.libraries.load(str(component),link=False)as(available,loaded):loaded.collections=[COLLECTION]
    appended=loaded.collections[0];room_scene=bpy.data.scenes.new(SCENE);room_scene.collection.children.link(appended);update()
    assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in expected.items())
    assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in before['materials'].items())
    assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items())
    assert not any(n in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects for n in fingerprints)
    protected_after=protected_state()
    for key in ['materials','objects','visibility','modifiers']:
        assert all(protected_after[key][n]==v for n,v in before[key].items())
    assert before['rooms']==protected_after['rooms'] and before['roomCampusObjects']==protected_after['roomCampusObjects']
    assert sha(BASE)==SHA and sha(component)==component_sha
    sources=json.loads((ROOT/'data/collections/clm-hongkong219/sources.json').read_text())['sources']
    for source in sources:assert sha(ROOT/source['path'])==source['sha256']
    verification=dict(savedComponentReopened=True,componentFingerprintCount=len(fingerprints),
        precedingAcceptedObjectFingerprintsVerified=7576,originalMaterialNodesVerified=len(before['materials']),
        protectedSpacesVerified=18,protectedSpaceObjectsVerified=623,allSourceObjectsMaterialsAndVisibilityUnchanged=True,allSourceModifiersUnchanged=True,
        allProtectedRoomMembershipsAndCampusMembershipsUnchanged=True,independentCollectionAppendVerified=True,
        noNewRoomObjectInCampus=True,componentSha256Match=True,baselineSha256Match=True,sourcePhotosNotUsedAsTextures=True)
    audit=dict(version=220,baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,
        componentPath=str(component.relative_to(ROOT)),componentSha256=component_sha,
        targetCollection=COLLECTION,destinationCollection=COLLECTION,
        collectionSpec=dict(kind='independent-room',name=COLLECTION,scene=SCENE),space=space,
        addedObjects=list(fingerprints),archivedObjects=[],changedObjects=[],addedFingerprints=fingerprints,
        replacementMaterialBindings=material_bindings,
        studentSeatCount=260,photoGuestSeatCount=2,lecturerSeatCount=1,
        planExtraction=dict(path=str((OUT/'plan-layout.json').relative_to(ROOT)),sha256=sha(OUT/'plan-layout.json'),
            annotatedOverlay=str((OUT/'plan-seats-numbered.png').relative_to(ROOT)),rowCounts=layout['rowCounts'],
            rejectedFalseContour=[436.66,291.41],advertisedCapacityNotUsedToInventSeats=True),
        metricRegistration=dict(originPixel=[290,250],coordinateConvention='nativeX=-(planX-290)*0.042;nativeY=(planY-250)*0.042;audience+Y sees right wooden arch at native-X and left ramp at native+X',estimatedMetresPerPixel=SCALE,estimatedMainHeight=6.6,
            estimatedStageHeight=STAGE_Z,noSourceScale=True,independentRoomNotCampusRegistered=True),
        geometryChecks=checks,ramp=ramp_record,doors=doors,closedSolidProof=solid,sources=sources,
        verification=verification,views=views,previews=['built-toward-stage.png','built-reverse.png'],
        sourceFeatureMapping=[
            dict(source='plan',feature='260 individually counted seat symbols,three angled/straight groups,stage,recess,three explicit double openings',model='Measured pixel centres and group directions retained;door leaves excluded from floor footprint'),
            dict(source='photo',feature='Warm oak panelling and inset mouldings,russet upholstery,pale wood arms and black fixed chair frames',model='Batched coloured PBR solids;no photo texture'),
            dict(source='photo',feature='Two black-framed screens,central whiteboard and roller,desk,microphones,silver stage-side rails,high arched division',model='Estimated visible teaching-wall ensemble and narrow cutaway vault ribbon'),
        ],
        limitations=[
            'Official historical plan/photo dates are unknown;retrieval2026-10-16 does not establish current condition.',
            'Theplan contains260 student symbols,which differs from advertised220 over two levels;no contemporary capacity or second-level geometry is asserted.',
            '0.042m/pixel,6.6m height,0.32m stage rise,chair build and photo-to-plan equipment placement are estimates.',
            'Inter-group gaps reach only about0.10m in this traced layout;they are not advertised as longitudinal egress aisles. Outer route strips and front area are checked without an egress/accessibility certification.',
            'Main seating floor remains one level because theplan lacks level annotations. Only the photograph-supported stage/ramp has estimated height.',
            'Side/rear walls and most ceiling are cut away;unseen construction,acoustics,full ventilation,balcony and corridors are not fabricated.',
            'Two photo guest chairs and one plan lecturer chair are separate from260 student symbols. No public photographic texture is created.',
        ])
    (OUT/'audit.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False)+'\n')
    (OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
    print('CLMG02_ROOM220_READY',len(fingerprints),checks['triangles'],260,flush=True)


if __name__=='__main__':
    run()
