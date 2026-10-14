"""Build the independent historical MAR.1.07 twenty-seat seminar room.

Run in Blender's Text Editor. The archived plan controls twenty student seats,
ten two-person table modules, the rear bay and single inward-opening door.
Metric scale and photo-to-plan wall registration are explicitly estimates.
No campus source is opened, saved or modified.
"""
from pathlib import Path
import hashlib
import json
import math
import sys
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from build_room_samples167 import RoomGeometry

OUTPUT = ROOT / 'result/blender/mar-room200'
BASELINE = ROOT / 'result/blender/LSE_campus_detailed_v199.blend'
BASELINE_SHA = '23a119c5b1235f780a8f17f29c8a02ff1d6a2036e269312bb7d5c459c4216877'
COLLECTION = 'MAR107_ROOM200_study'
SCENE = 'ROOM200_MAR107'
PREFIX = 'MAR107_R200_'
SCALE = .024
SOURCE_FILES = [
    ('09af1c951314_MAR.1.07.gif', '6e375ccf2b3eb9e62ad84e0f4822c42a2dd8b554b394f1a8a42dd37fbc1f612f', 'https://www.lse.ac.uk/assets/roomInformation/images/MAR.1.07.gif'),
    ('fcb35a206797_MAR.1.07.jpg', '6012d9d48fbcfa2d77708fb44f7c7b290257eb40023691be051497444da5b53b', 'https://www.lse.ac.uk/assets/roomInformation/images/photos/MAR.1.07.jpg'),
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def point(px, py):
    # Rotate plan180degrees so the open end of the U faces the teaching wall.
    return ((325 - px) * SCALE, (475 - py) * SCALE)


def color(g, key, rgb, roughness=.78):
    mat = g.materials.get(key) or bpy.data.materials.new(PREFIX + key)
    mat.use_nodes = True
    mat.diffuse_color = (*rgb, 1)
    shader = mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = mat.diffuse_color
    shader.inputs['Roughness'].default_value = roughness
    g.materials[key] = mat


def chair(g, px, py, angle, family='student'):
    x, y = point(px, py)
    c, s = math.cos(angle), math.sin(angle)
    def at(a, b, z):
        return (x + c*a - s*b, y + s*a + c*b, z)
    g.box(family + '_black_seats', 'dark', at(0, 0, .455), (.46, .43, .045), angle)
    g.box(family + '_mesh_back_panels', 'mesh', at(0, .225, .73), (.405, .024, .31), angle)
    for a in [-.224, .224]:
        g.box(family + '_black_back_frames', 'dark', at(a, .225, .73), (.042, .035, .38), angle)
    g.box(family + '_black_back_frames', 'dark', at(0, .225, .905), (.46, .035, .035), angle)
    for a in [-.18, .18]:
        for b in [-.16, .16]:
            g.tube(family + '_chair_legs', 'dark', at(a, b, .03), at(a, b, .43), .015)
    return [x, y]


def table(g, rectangle):
    a, b, c, d = rectangle
    x0, y0 = point(a, c)
    x1, y1 = point(b, d)
    x, y = (x0+x1)/2, (y0+y1)/2
    w, dep = abs(x1-x0)-.012, abs(y1-y0)-.012
    g.box('ten_two_person_tabletops', 'white', (x, y, .755), (w, dep, .045))
    for sx in [-1, 1]:
        for sy in [-1, 1]:
            g.tube('table_gray_supports', 'steel', (x+sx*(w/2-.10), y+sy*(dep/2-.06), .035),
                   (x+sx*(w/2-.10), y+sy*(dep/2-.06), .73), .023)
    return [min(x0,x1), max(x0,x1), min(y0,y1), max(y0,y1)]


def reopened_mesh_checks(objects):
    checks = {}
    for obj in objects:
        mesh = obj.data
        edges = {}
        volume = 0.0
        for face in mesh.polygons:
            ids = list(face.vertices)
            for a, b in zip(ids, ids[1:]+ids[:1]):
                k = (min(a,b), max(a,b))
                count, winding = edges.get(k, (0,0))
                edges[k] = (count+1, winding+(1 if a<b else -1))
            a = mesh.vertices[ids[0]].co
            for i in range(1,len(ids)-1):
                volume += a.dot(mesh.vertices[ids[i]].co.cross(mesh.vertices[ids[i+1]].co))/6
        assert all(n == 2 and w == 0 for n,w in edges.values()), obj.name
        assert volume > 0, (obj.name, volume)
        assert len(mesh.uv_layers) == 1
        checks[obj.name] = {'allEdgesOppositelyPaired': True, 'positiveSignedVolume': volume}
    return checks


def build():
    assert BASELINE.exists() and digest(BASELINE) == BASELINE_SHA
    sources = []
    for name, sha, url in SOURCE_FILES:
        path = ROOT / 'data/collections/interiors/images' / name
        assert path.exists() and digest(path) == sha, name
        sources.append({'path': str(path.relative_to(ROOT)), 'sha256': sha, 'url': url,
                        'retrievedDate': '2026-09-12', 'captureDate': 'Unknown. Historical page refreshed17Aug2022; this is not image creation date.'})
    OUTPUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = SCENE
    collection = bpy.data.collections.new(COLLECTION)
    scene.collection.children.link(collection)
    g = RoomGeometry(collection, PREFIX)
    for key, rgb in [('white',(.72,.78,.76)), ('wall',(.52,.52,.46)), ('carpet',(.38,.39,.36)),
                     ('dark',(.025,.028,.028)), ('mesh',(.105,.12,.12)), ('oak',(.31,.23,.16)),
                     ('board',(.79,.82,.79)), ('steel',(.29,.32,.32)), ('exit',(.025,.38,.13))]:
        color(g, key, rgb)
    height = 3.4
    outline = [(148,630),(501,630),(501,320),(378,320),(378,291),(206,291),(206,320),(148,320)]
    g.prism('plan_bay_outline_floor', 'carpet', [point(*p) for p in outline], -.12, .12)
    left, front = point(501,630)
    right, rear = point(148,320)
    door_left, door_right = point(501,630)[0], point(451,630)[0]
    # Single inward-swinging opening is traced at the plan bottom-right corner.
    g.box('concrete_teaching_wall', 'wall', ((door_right+right)/2,front-.09,height/2), (right-door_right,.18,height))
    g.box('door_left_jamb', 'wall', (door_left-.055,front-.09,1.7), (.11,.18,3.4))
    g.box('door_lintel', 'wall', ((door_left+door_right)/2,front-.09,2.87), (door_right-door_left,.18,1.06))
    # Closed door leaf remains in its opening; the plan's inward sweep is audited separately.
    g.box('single_dark_door_leaf', 'dark', ((door_left+door_right)/2,front-.04,1.16), (door_right-door_left-.035,.055,2.32))
    g.box('door_vision_panel', 'glass', (door_right-.27,front+.005,1.45), (.12,.025,1.05))
    g.tube('door_pull', 'steel', (door_right-.12,front+.045,.91), (door_right-.12,front+.045,1.2), .012)
    g.box('exit_sign', 'exit', ((door_left+door_right)/2,front+.025,2.52), (.45,.04,.18))
    # Screen and concrete wall are photo evidence; precise horizontal registration is estimated.
    g.box('teaching_white_backing', 'board', (-.45,front+.035,1.95), (4.25,.06,1.8))
    g.box('projection_screen_frame', 'dark', (-.55,front+.12,2.08), (2.42,.07,1.70))
    g.box('projection_screen_face', 'screen', (-.55,front+.164,2.08), (2.30,.023,1.58))
    g.box('projection_screen_bottom_bar', 'dark', (-.55,front+.188,1.245), (2.45,.04,.055))
    # Photo's neighbouring slatted wall and two boards; exact side-wall alignment estimated.
    g.box('slatted_side_wall_backing', 'dark', (right+.035,(front+rear)/2,height/2), (.13,rear-front,height))
    for i in range(86):
        y = front+.04+(rear-front-.08)*i/85
        g.box('wood_acoustic_slats', 'oak', (right-.049,y,height/2), (.065,.044,height))
    for y in [-1.10,1.24]:
        g.box('two_side_whiteboards', 'board', (right-.10,y,1.77), (.047,2.0,1.11))
    # Other walls are low cutaways; preserve the plan's rear bay without invented elevations.
    for a,b in [(148,206),(378,501)]:
        xa,ya=point(a,320); xb,yb=point(b,320)
        g.box('rear_cutaway_wall', 'wall', ((xa+xb)/2,ya+.05,.16), (abs(xb-xa),.1,.32))
    g.box('left_cutaway_wall', 'wall', (left-.05,(rear+front)/2,.16), (.1,rear-front,.32))
    bay_l, bay_y = point(378,291)
    bay_r, _ = point(206,291)
    for x in [bay_l,bay_r]:
        g.box('bay_return_cutaways', 'wall', (x,(bay_y+rear)/2,.16), (.09,bay_y-rear,.32))
    # Plan shows two bay panes; heights are estimates. Glazing is sectioned
    # above1.14metres so opaque Workbench glazing cannot conceal the seating.
    g.box('two_pane_bay_glass', 'glass', ((bay_l+bay_r)/2,bay_y,.98), (bay_r-bay_l,.026,.32))
    for x in [bay_l,(bay_l+bay_r)/2,bay_r]:
        g.box('bay_window_mullions', 'steel', (x,bay_y-.025,1.76), (.05,.055,1.94))
    for z in [.8,2.72]:
        g.box('bay_window_rails', 'steel', ((bay_l+bay_r)/2,bay_y-.025,z), (bay_r-bay_l,.055,.05))
    rectangles = [(234,293,383,404),(293,352,383,404),(352,410,383,404),
                  (211,234,380,438),(211,234,438,497),
                  (410,433,380,438),(410,433,438,498),(410,433,498,556),
                  (263,322,445,470),(322,381,445,470)]
    tables = [table(g,r) for r in rectangles]
    seats = []
    groups = [('rear-six',[(x,375) for x in [249,279,308,337,367,396]],0),
              ('plan-left-four',[(206,y) for y in [391,421,451,480]],-math.pi/2),
              ('plan-right-six',[(437,y) for y in [392,422,451,479,510,539]],math.pi/2),
              ('central-four',[(x,436) for x in [277,307,337,366]],0)]
    for label, positions, angle in groups:
        for px,py in positions:
            center=chair(g,px,py,angle)
            seats.append({'group':label,'planPixel':[px,py],'center':center,'angleRadians':angle})
    # Separate lecturer position is present in the plan and photograph, excluded from capacity20.
    tx,ty=point(224,542)
    g.box('lecturer_station_top', 'white', (tx,ty,.89), (1.07,.70,.055))
    g.box('lecturer_station_pedestal', 'steel', (tx,ty,.425), (.83,.55,.85))
    g.box('lecturer_monitor', 'dark', (tx-.12,ty-.11,1.16), (.43,.055,.29))
    g.tube('monitor_stand', 'steel', (tx-.12,ty-.11,.94), (tx-.12,ty-.11,1.03), .026)
    chair(g,224,579,math.pi,'lecturer')
    # Photo-visible concrete beams, black cylindrical lights and white projector.
    # Only front ceiling sections retained so the exact seating remains visible.
    for x in [-2.25,.18,2.61]:
        g.box('cutaway_concrete_beams', 'wall', (x,front+.98,3.33), (.26,2.02,.30))
        for y in [front+.35,front+1.54]:
            g.tube('black_downlight_cylinders', 'dark', (x+.34,y,2.95), (x+.34,y,3.28), .09)
    g.box('white_projector_body', 'white', (-.55,front+1.25,2.98), (.50,.40,.20))
    g.tube('projector_mount', 'steel', (-.55,front+1.25,3.08), (-.55,front+1.25,3.43), .022)
    g.box('projector_lens', 'dark', (-.55,front+1.04,2.98), (.12,.026,.09))
    objects = g.finish()
    assert len(seats)==20 and len(tables)==10
    collection['studentSeatCount']=20
    collection['roomSample']=True
    for obj in objects:
        obj['roomCode']='MAR.1.07'
        obj['scope']='Historical paired-source independent room; metric dimensions and photo-to-plan registration estimated'
    next(o for o in objects if 'student_black_seats' in o.name)['studentSeatCount']=20
    scope='依据LSE官方MAR.1.07历史平面与照片建立20座研讨教室：外围U形16座、中央4座、10张双人桌、单门与后侧双格窗带；保留单投影幕、相邻木格栅墙两块白板、灰地毯和黑椅。尺寸、层高、窗高及照片与平面墙面对应关系估计；不推断整层连通，不代表2026年现状。'
    space={'id':'mar-107','code':'MAR','collection':COLLECTION,'label':'MAR.1.07研讨教室','gallery':'mar-107-interior','scope':scope,
           'interiorStudy':{'kind':'room-sample','label':'MAR.1.07研讨教室','scope':scope},
           'interiorView':{'position':[-11.6,10.0,-12.6],'target':[0,1,0],'fov':48}}
    collection['authoringRecord']=json.dumps(space,ensure_ascii=False)
    camera=bpy.data.objects.new(PREFIX+'camera',bpy.data.cameras.new(PREFIX+'camera'))
    scene.collection.objects.link(camera)
    camera.location=(-11.6,12.6,10.0)
    camera.rotation_euler=(Vector((0,0,1))-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type='ORTHO';camera.data.ortho_scale=14.4;scene.camera=camera
    scene.world=bpy.data.worlds.new(PREFIX+'world');scene.world.color=(.8,.82,.83)
    scene.render.engine='BLENDER_WORKBENCH'
    shade=scene.display.shading;shade.light='STUDIO';shade.color_type='MATERIAL';shade.studiolight_rotate_z=math.pi
    shade.show_shadows=True;shade.show_cavity=True;shade.cavity_type='BOTH';shade.background_type='WORLD'
    scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUTPUT/'mar107-cutaway.png')
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT/'component.blend'))
    bpy.ops.render.render(write_still=True)
    component_sha=digest(OUTPUT/'component.blend')
    triangles=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in objects)
    assert triangles<40000
    # Verify the open-end approach and source-defined gaps between U limbs and central tables.
    aisle_checks=[]
    for lo,hi in [(234,263),(381,410)]:
        a,b=sorted([point(lo,0)[0],point(hi,0)[0]])
        ylo,yhi=sorted([point(0,445)[1],point(0,470)[1]])
        overlap=[r for r in tables if r[1]>a+1e-8 and r[0]<b-1e-8 and r[3]>ylo+1e-8 and r[2]<yhi-1e-8]
        seat_overlap=[s for s in seats if s['center'][0]+.23>a and s['center'][0]-.23<b
                      and s['center'][1]+.23>ylo and s['center'][1]-.23<yhi]
        assert not overlap and not seat_overlap
        aisle_checks.append({'planPixels':[lo,hi],'clearWidthMetres':b-a,'tableIntrusions':0,'chairIntrusions':0,
                             'note':'Central-table side gap. Side chairs lie beyond outer U-table edges; this is not an egress-width certification.'})
    door_center=Vector((door_left,front))
    radius=door_right-door_left
    # Nearest table/seat envelopes stay beyond the inward door swept circle.
    obstacle_clearance=[]
    for r in tables:
        nearest=Vector((max(r[0],min(door_center.x,r[1])),max(r[2],min(door_center.y,r[3]))))
        obstacle_clearance.append((nearest-door_center).length-radius)
    obstacle_clearance += [math.dist(s['center'],door_center)-.34-radius for s in seats]
    assert min(obstacle_clearance)>.5
    spacing=min(math.dist(a['center'],b['center']) for i,a in enumerate(seats) for b in seats[i+1:])
    assert spacing>.55
    names=sorted(o.name for o in objects)
    report={'baselineSha256':BASELINE_SHA,'componentPath':str((OUTPUT/'component.blend').relative_to(ROOT)),
            'componentSha256':component_sha,'targetCollection':COLLECTION,'addedObjects':names,'archivedObjects':[],
            'collectionSpec':{'name':COLLECTION,'scene':SCENE,'kind':'independent-room'},'space':space,
            'studentSeatCount':20,'lecturerSeatCount':1,'deskCount':10,'seatPositions':seats,
            'layout':{'perimeterUSeatCount':16,'centralSeatCount':4,'planGroupCounts':[6,4,6,4]},
            'planMapping':{'originPixel':[325,475],'rotationDegrees':180,'metresPerPixel':SCALE,'heightMetres':height,
                           'dimensionsAreEstimated':True,'outlinePixels':outline,'tableRectanglesPixels':rectangles,
                           'doorOpeningPixels':[451,501,630],'bayWindowPixels':[206,378,291],
                           'teachingWallRegistration':'Open end of U treated as teaching front; photograph-to-plan wall alignment estimated, not survey verified.'},
            'doorPassageChecks':{'singleDoorClearWidthMetres':radius,'swing':'Inward, per plan',
                                  'minimumStudentFurnitureClearanceBeyondDoorSweepMetres':min(obstacle_clearance),
                                  'centralSideGaps':aisle_checks,'frontOpenEndDepthMetres':(630-556)*SCALE},
            'minimumSeatCenterSpacingMetres':spacing,'triangleCount':triangles,'triangleBudget':40000,
            'closedSolidProof':g.solid_proof,'sources':sources,
            'limitations':['Historical same-room sources; image dates unknown and no current2026 claim.',
                           'Unmeasured .024metres/pixel scale and3.4metre height; window heights and frames estimated; glazing sectioned above1.14metres.',
                           'Teaching screen and slatted two-board wall observed in photo; exact wall registration to plan estimated.',
                           'Right plan wall includes indistinct marks; no hidden opening, folding partition or corridor connectivity inferred.',
                           'Unseen sides and ceiling cut away; ceiling beam spacing, chair supports and lecturer pedestal simplified.',
                           'No photograph pixels, external textures or full-floor attribution embedded.'],
            'preview':str((OUTPUT/'mar107-cutaway.png').relative_to(ROOT))}
    bpy.ops.wm.open_mainfile(filepath=str(OUTPUT/'component.blend'))
    reopened=bpy.data.collections[COLLECTION]
    assert sorted(o.name for o in reopened.all_objects)==names
    assert len(bpy.data.scenes)==1 and bpy.data.scenes[SCENE].collection.children.get(COLLECTION)
    assert reopened['studentSeatCount']==20
    report['reopenedClosedSolidChecks']=reopened_mesh_checks(list(reopened.all_objects))
    assert digest(BASELINE)==BASELINE_SHA and digest(OUTPUT/'component.blend')==component_sha
    report['reopenedVerification']={'objectNamesMatch':True,'independentSceneOnly':True,'studentSeatCount':20,
                                    'baselineUnchanged':True,'componentSha256Match':True,'closedOutwardGeometry':True}
    (OUTPUT/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'component':report['componentPath'],'objects':len(names),'triangles':triangles,'seats':20,'reopened':True}))


if __name__=='__main__':
    build()
