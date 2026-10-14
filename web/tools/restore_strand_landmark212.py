"""Restore the omitted Strand church as a source-bounded contextual landmark.

Run in the existing Python environment to prepare mapped outlines and real wall
apertures; then run in Blender to create a separate, verified component. The
listed form and2025 restoration elevation guide the silhouette. Height, window
spacing and secondary roof geometry are estimates, not measured as-built data.
"""
from pathlib import Path
import hashlib
import json
import math
import sys
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'result/blender/LSE_campus_detailed_v211.blend'
BASE_SHA = '630ebd5e999685f8d646a2613774bc925dabe6f62f5c23404882703ed8a96eca'
OUT = ROOT/'result/blender/strand-church212'
PLAN = OUT/'geometry-plan.json'
ANGLE = math.radians(10.415448289106735)
sys.path.insert(0, str(ROOT/'web/tools'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')


def prepare_plan():
    from shapely import constrained_delaunay_triangles, orient_polygons
    from shapely.affinity import rotate, translate
    from shapely.geometry import Polygon, box
    from shapely.ops import unary_union
    source = ET.parse(ROOT/'data/collections/streets/raw/osm_map.osm').getroot()
    nodes = {n.attrib['id']: n for n in source.findall('node')}
    way = next(w for w in source.findall('way') if w.attrib['id'] == '25904232')
    tags = {t.attrib['k']: t.attrib['v'] for t in way.findall('tag')}
    assert tags['building'] == 'church' and tags['name'] == 'St Clement Danes'
    lon0, lat0 = map(math.radians, (-.1167, 51.5146))
    def ecef(lon, lat):
        lon, lat = map(math.radians, (lon, lat))
        n = 6378137/math.sqrt(1-6.69437999014e-3*math.sin(lat)**2)
        return [n*math.cos(lat)*math.cos(lon), n*math.cos(lat)*math.sin(lon), n*(1-6.69437999014e-3)*math.sin(lat)]
    origin = ecef(-.1167, 51.5146)
    ring = []
    for row in way.findall('nd'):
        n = nodes[row.attrib['ref']]
        d = [a-b for a,b in zip(ecef(float(n.attrib['lon']), float(n.attrib['lat'])), origin)]
        ring.append([-math.sin(lon0)*d[0]+math.cos(lon0)*d[1],
                     -math.sin(lat0)*math.cos(lon0)*d[0]-math.sin(lat0)*math.sin(lon0)*d[1]+math.cos(lat0)*d[2]])
    world = Polygon(ring)
    centre = list(world.centroid.coords)[0]
    footprint = orient_polygons(translate(rotate(world, -math.degrees(ANGLE), origin=centre), -centre[0], -centre[1]))
    site = json.loads((ROOT/'result/blender/site_geometry.json').read_text())
    mapped_tower = next(b for b in site['buildings'] if b['id']=='way/445807204')
    tower_world = Polygon(mapped_tower['rings'][0])
    tower_local = translate(rotate(tower_world, -math.degrees(ANGLE), origin=centre), -centre[0], -centre[1])
    tower_centre = list(tower_local.centroid.coords)[0]
    main = footprint.intersection(box(-13.64, -30, 30, 30))
    porch = footprint.difference(main)
    def tris(shape):
        return [list(t.exterior.coords)[:-1] for t in constrained_delaunay_triangles(shape).geoms]
    def arched(cx, bottom, spring, radius):
        return Polygon([(cx-radius,bottom),(cx+radius,bottom),
                        *[(cx+radius*math.cos(t*math.pi/12), spring+radius*math.sin(t*math.pi/12)) for t in range(13)]])
    walls = []
    for polygon, height, part in [(main,13.2,'nave'),(porch,13.2,'porch')]:
        points = list(orient_polygons(polygon).exterior.coords)[:-1]
        for a,b in zip(points,points[1:]+points[:1]):
            length = math.dist(a,b)
            if length < .001:
                continue
            apertures = []
            if part == 'nave' and length > 19 and abs(a[1]) > 9 and abs(b[1]) > 9:
                for bay in range(5):
                    cx = length*(bay+.5)/5
                    apertures += [dict(outline=list(arched(cx,1.2,3.25,1.1).exterior.coords)[:-1],kind='lower',centre=cx),
                                  dict(outline=list(arched(cx,5.8,10.1,1.1).exterior.coords)[:-1],kind='upper',centre=cx)]
            elif part == 'porch' and a[0] < -19 and b[0] < -19:
                apertures = [dict(outline=list(arched(length/2, .05,2.55,1.1).exterior.coords)[:-1],kind='door',centre=length/2)]
            holes = unary_union([Polygon(o['outline']) for o in apertures])
            panel = box(0,.05,length,height).difference(holes)
            walls.append(dict(a=a,b=b,length=length,height=height,triangles=tris(panel),apertures=apertures))
    roof = []
    roof_shape = main
    for region in [roof_shape.intersection(box(-30,-30,30,0)),roof_shape.intersection(box(-30,0,30,30))]:
        roof += tris(region)
    save(PLAN, dict(osmWay=way.attrib, tags=tags, centre=centre, angle=ANGLE,
          footprintAreaM2=world.area, towerCentre=tower_centre, towerFootprintAreaM2=tower_world.area, footprint=list(footprint.exterior.coords)[:-1],
          floor=tris(footprint), walls=walls, roof=roof,
          windowApertures=sum(len(w['apertures']) for w in walls),
          mainRoofBase=13.2, naveRoofRidge=17.5, estimatedOverallHeight=42.3,
          sources=['https://historicengland.org.uk/listing/the-list/list-entry/1237099',
                   'https://stclementdanesraf.org/steeple/',
                   'https://www.stace.co.uk/news-insights/milestone-reached-at-st-clement-danes-church/',
                   'https://www.openstreetmap.org/way/25904232'],
          limits='Mapped footprint; listed west tower, apsidal east end, paired domed lobbies and three diminishing octagonal open stages.2026-09-24 project update confirms steeple rebuild milestone on2026-09-10, not complete site/scaffold removal.42.3m overall height, window placement, roof slopes and secondary sections are visual estimates. No complete church interior or measured current envelope claim.'))
    print('CHURCH212_PLAN', world.area, flush=True)


def build_component():
    import bpy
    import bmesh
    from mathutils import Vector
    from mathutils.geometry import tessellate_polygon
    from mathutils.bvhtree import BVHTree
    from integrate_exterior_round194 import object_fingerprint
    from refine_portsmouth_exterior207 import material_fingerprint
    assert sha(BASE) == BASE_SHA
    plan = json.loads(PLAN.read_text())
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    original = {o.name: object_fingerprint(o) for o in bpy.data.objects}
    material_before = {m.name: material_fingerprint(m) for m in bpy.data.materials}
    collection = bpy.data.collections['01_CITY_CONTEXT_estimated_heights']
    cx,cy = plan['centre'];c,s=math.cos(ANGLE),math.sin(ANGLE)
    def world(point):
        x,y,z=point
        return (cx+c*x-s*y,cy+s*x+c*y,z)
    materials = {}
    for name,color,roughness,metal in [('limestone',(.43,.435,.41),.82,0),('lead_roof',(.22,.245,.255),.55,.55),
                                    ('glass_opaque_proxy',(.105,.135,.15),.24,0),('clock_dark',(.018,.024,.025),.65,0),
                                    ('gilt',(.55,.39,.085),.4,.72)]:
        m=bpy.data.materials.new('CHURCH212_'+name);m.use_nodes=True;m.diffuse_color=(*color,1)
        shader=m.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=(*color,1)
        shader.inputs['Roughness'].default_value=roughness;shader.inputs['Metallic'].default_value=metal
        materials[name]=m
    groups={}
    class Batch:
        def __init__(self,name,material):
            self.name='CHURCH212_'+name;self.material=materials[material];self.vertices=[];self.faces=[]
        def add(self,points,faces):
            offset=len(self.vertices);self.vertices += [world(p) for p in points]
            self.faces += [tuple(offset+i for i in f) for f in faces]
        def box(self,location,size,angle=0):
            x,y,z=location;w,d,h=size;cc,ss=math.cos(angle),math.sin(angle)
            points=[(x+cc*a-ss*b,y+ss*a+cc*b,z+t) for t in [-h/2,h/2] for a,b in [(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)]]
            self.add(points,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
        def cylinder(self,location,radius,height,sides=12):
            x,y,z=location
            points=[(x+radius*math.cos(i*math.tau/sides),y+radius*math.sin(i*math.tau/sides),level) for level in [z-height/2,z+height/2] for i in range(sides)]
            self.add(points,[tuple(reversed(range(sides))),tuple(range(sides,2*sides))]+[(i,(i+1)%sides,(i+1)%sides+sides,i+sides) for i in range(sides)])
        def profile(self,x,y,levels,sides=16):
            points=[(x+r*math.cos(i*math.tau/sides),y+r*math.sin(i*math.tau/sides),z) for r,z in levels for i in range(sides)]
            self.add(points,[(k*sides+i,k*sides+(i+1)%sides,(k+1)*sides+(i+1)%sides,(k+1)*sides+i) for k in range(len(levels)-1) for i in range(sides)])
        def finish(self):
            mesh=bpy.data.meshes.new(self.name+'_mesh');mesh.from_pydata(self.vertices,[],self.faces);mesh.materials.append(self.material);mesh.update()
            bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
            uv=mesh.uv_layers.new(name='MetricSurfaceUV')
            for face in mesh.polygons:
                points=[mesh.vertices[i].co for i in face.vertices];origin=points[0];u=(points[1]-origin).normalized();v=face.normal.cross(u)
                for index,point in zip(face.loop_indices,points):uv.data[index].uv=((point-origin).dot(u),(point-origin).dot(v))
            obj=bpy.data.objects.new(self.name,mesh);collection.objects.link(obj);obj['scope']=plan['limits'];return obj
    for name,material in [('nave_walls','limestone'),('roof_shells','lead_roof'),('facade_frames','limestone'),
                          ('retained_opaque_windows','glass_opaque_proxy'),('tower_structure','limestone'),
                          ('clock_faces','clock_dark'),('gilt_details','gilt')]:groups[name]=Batch(name,material)
    stone,roof,frames,glass,tower,clock,gilt=[groups[n] for n in groups]
    for tri in plan['floor']:
        stone.add([(*p,.05) for p in tri],[(0,1,2)])
    window_probes=[]
    for wall in plan['walls']:
        a,b=wall['a'],wall['b'];length=wall['length'];u=((b[0]-a[0])/length,(b[1]-a[1])/length);n=(u[1],-u[0])
        def wall_point(x,z,depth=0):return (a[0]+u[0]*x+n[0]*depth,a[1]+u[1]*x+n[1]*depth,z)
        for tri in wall['triangles']:
            stone.add([wall_point(x,z) for x,z in tri],[(0,1,2)])
        for opening in wall['apertures']:
            outline=opening['outline'];coords=[Vector((x,z,0)) for x,z in outline]
            for tri in tessellate_polygon([coords]):
                points=[coords[i] if isinstance(i,int) else i for i in tri]
                glass.add([wall_point(p.x,p.y,-.12) for p in points],[(0,1,2)])
            for aa,bb in zip(outline,outline[1:]+outline[:1]):
                frames.add([wall_point(*aa,-.12),wall_point(*bb,-.12),wall_point(*bb,.08),wall_point(*aa,.08)],[(0,1,2,3)])
            x=opening['centre'];z=7.8 if opening['kind']=='upper' else 2.5
            window_probes.append(dict(start=world(wall_point(x,z,.4)),direction=(-c*n[0]+s*n[1],-s*n[0]-c*n[1],0)))
            if opening['kind']!='door':
                frames.box(wall_point(x,z,-.055),(.065,.10,4.2 if opening['kind']=='upper' else 2.1),math.atan2(u[1],u[0]))
    for tri in plan['roof']:
        roof.add([(x,y,13.2+4.3*max(0,1-abs(y)/10.7)) for x,y in tri],[(0,1,2)])
    # The two source-described domed western lobbies are shallow lead caps.
    for y in [-6.8,6.8]:
        roof.profile(-10,y,[(3.25,13.2),(3.2,13.55),(2.9,14.25),(2.15,15.05),(.85,15.65),(.05,15.8)],24)
    # Clock stage below the square bell stage; support is inside the mapped body.
    tx,ty=plan['towerCentre']
    tower.box((tx,ty,14.85),(6.4,6.4,3.3));tower.box((tx,ty,16.6),(7.1,7.1,.3))
    for x,y in [(-2.87,-2.87),(-2.87,2.87),(2.87,-2.87),(2.87,2.87)]:
        tower.box((tx+x,ty+y,19.1),(.62,.62,4.7))
    tower.box((tx,ty,21.65),(7.1,7.1,.35))
    # Four actual open square-bell-stage faces; no opaque filler inside them.
    for side in range(4):
        angle=side*math.pi/2;ux,uy=math.cos(angle),math.sin(angle);nx,ny=uy,-ux
        for i in range(16):
            aa,bb=i*math.pi/16,(i+1)*math.pi/16
            pts=[(tx+ux*r*math.cos(t)+nx*(3.02+d),ty+uy*r*math.cos(t)+ny*(3.02+d),19.8+r*math.sin(t)) for d in [-.14,.14] for r,t in [(1.05,aa),(1.05,bb),(1.37,bb),(1.37,aa)]]
            tower.add(pts,[(0,1,2,3),(4,7,6,5),(0,4,5,1),(3,2,6,7)])
        # Clock disks lie outside the opaque lower tower face.
        points=[(tx+nx*3.215+ux*1.12*math.cos(i*math.tau/32),ty+ny*3.215+uy*1.12*math.cos(i*math.tau/32),14.7+1.12*math.sin(i*math.tau/32)) for i in range(32)]
        clock.add(points,[tuple(range(32))])
        for hand_angle,hand_length in [(math.pi/2,.8),(math.pi*.17,.58)]:
            endx,endy=hand_length*math.cos(hand_angle),hand_length*math.sin(hand_angle)
            points=[(tx+nx*3.235+ux*x,ty+ny*3.235+uy*x,14.7+z) for x,z in [(0,-.035),(endx,endy-.035),(endx,endy+.035),(0,.035)]]
            gilt.add(points,[(0,1,2,3)])
    # Three diminishing open octagonal stages follow the published elevation.
    for radius,z0,z1 in [(3.15,22.05,28.6),(2.03,31.0,35.0),(1.12,37.05,39.55)]:
        tower.profile(tx,ty,[(radius+.18,z0),(radius+.18,z0+.22),(radius,z0+.3)],8)
        for i in range(8):
            angle=i*math.tau/8
            tower.cylinder((tx+radius*math.cos(angle),ty+radius*math.sin(angle),(z0+z1)/2),.23 if radius>2 else .15,z1-z0,10)
        tower.profile(tx,ty,[(radius,z1-.18),(radius+.25,z1),(radius+.25,z1+.22)],8)
        for i in range(8):
            a,b=i*math.tau/8,(i+1)*math.tau/8
            pa,pb=(radius*math.cos(a),radius*math.sin(a)),(radius*math.cos(b),radius*math.sin(b))
            length=math.dist(pa,pb);ux,uy=(pb[0]-pa[0])/length,(pb[1]-pa[1])/length
            mx,my=(pa[0]+pb[0])/2,(pa[1]+pb[1])/2;nx,ny=uy,-ux
            inner=max(.24,length/2-(.23 if radius>2 else .15))
            for segment in range(12):
                aa,bb=segment*math.pi/12,(segment+1)*math.pi/12
                pts=[(tx+mx+ux*r*math.cos(t)+nx*d,ty+my+uy*r*math.cos(t)+ny*d,z1-inner-.12+r*math.sin(t)) for d in [-.12,.12] for r,t in [(inner,aa),(inner,bb),(inner+.2,bb),(inner+.2,aa)]]
                tower.add(pts,[(0,1,2,3),(4,7,6,5),(0,4,5,1),(3,2,6,7)])
    tower.profile(tx,ty,[(3.4,28.82),(3.25,29.15),(2.6,30.25),(2.03,31.0)],16)
    tower.profile(tx,ty,[(2.28,35.22),(2.05,35.65),(1.45,36.65),(1.12,37.05)],16)
    roof.profile(tx,ty,[(1.36,39.77),(1.12,40.2),(.68,40.8),(.12,41.05)],16)
    gilt.profile(tx,ty,[(.07,41.05),(.07,41.35),(.24,41.45),(.3,41.65),(.16,41.92),(.07,42.0),(.07,42.3)],16)
    for axis in [0,math.pi/2]:gilt.box((tx,ty,42.1),(1.0,.035,.045),axis)
    owned=[g.finish() for g in groups.values()]
    assert all(object_fingerprint(bpy.data.objects[name])==value for name,value in original.items())
    assert all(material_fingerprint(bpy.data.materials[name])==value for name,value in material_before.items())
    # Verify true cut wall apertures without decorative glazing/frame occlusion.
    body=owned[0];bvh=BVHTree.FromPolygons([v.co for v in body.data.vertices],[list(f.vertices) for f in body.data.polygons])
    for probe in window_probes:
        assert bvh.ray_cast(Vector(probe['start']),Vector(probe['direction']),.7)[0] is None,probe
    fingerprints={o.name:object_fingerprint(o) for o in owned};component=OUT/'component.blend'
    bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(component),link=False) as (_,target):target.objects=list(fingerprints)
    for obj in target.objects:
        bpy.context.scene.collection.objects.link(obj);assert object_fingerprint(obj)==fingerprints[obj.name]
    assert sha(BASE)==BASE_SHA
    triangles=sum(sum(len(f.vertices)-2 for f in o.data.polygons) for o in target.objects)
    save(OUT/'audit.json',dict(version=212,baselineSha256=BASE_SHA,componentPath=str(component.relative_to(ROOT)),
          componentSha256=sha(component),targetCollection='01_CITY_CONTEXT_estimated_heights',addedObjects=list(fingerprints),archivedObjects=[],
          footprintAreaM2=plan['footprintAreaM2'],mappedTowerCentre=plan['towerCentre'],heightEstimateMetres=plan['estimatedOverallHeight'],
          wallApertures=plan['windowApertures'],apertureRays=len(window_probes),triangles=triangles,
          originalsVerified=len(original),originalMaterialsVerified=len(material_before),
          verification=dict(componentReopened=True,originalGeometryUVMaterialsPreserved=True,trueWallApertures=True),
          scope='Restore omitted St Clement Danes context footprint, nave, apsidal east end, lead roofs, clock stage and three diminishing open steeple stages; no LSE building identity changed.',sources=plan['sources'],limitations=plan['limits']))
    print('CHURCH212_COMPONENT',len(owned),triangles,flush=True)


if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    try:
        import bpy
    except ImportError:
        prepare_plan()
    else:
        build_component()
