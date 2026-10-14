"""Recover the mapped public sports hardcourt omitted by the site generator.

Run in the existing Python environment to prepare source-plan triangles, then
open in Blender's Text Editor to author a separate, audited component library.
Only five incorrectly grass-classed court objects are listed for replacement.
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
OUT = ROOT/'result/blender/park-courts212'
SITE = ROOT/'result/blender/site_geometry.json'
OSM = ROOT/'data/collections/streets/raw/osm_map.osm'
PLAN = OUT/'court-plan.json'
PREFIX = 'COURTS212_'
COURT_IDS = [str(i) for i in range(1268323928,1268323933)]
SURFACE_Z = .057
sys.path.insert(0,str(ROOT/'web/tools'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value,indent=2)+'\n')


def prepare_plan():
    from shapely import constrained_delaunay_triangles, orient_polygons
    from shapely.geometry import LineString, Polygon
    from shapely.ops import unary_union
    OUT.mkdir(parents=True,exist_ok=True)
    site = json.loads(SITE.read_text())
    tree = ET.parse(OSM).getroot()
    nodes = {n.attrib['id']:n.attrib for n in tree.findall('node')}
    way = next(w for w in tree.findall('way') if w.attrib['id']=='301471945')
    tags = {t.attrib['k']:t.attrib['v'] for t in way.findall('tag')}
    assert tags['surface']=='tarmac' and tags['landuse']=='recreation_ground'
    def ecef(lon,lat):
        lon,lat=map(math.radians,(lon,lat))
        r=6378137/math.sqrt(1-6.69437999014e-3*math.sin(lat)**2)
        return (r*math.cos(lat)*math.cos(lon),r*math.cos(lat)*math.sin(lon),r*(1-6.69437999014e-3)*math.sin(lat))
    origin=ecef(*site['origin_lon_lat'])
    lon0,lat0=map(math.radians,site['origin_lon_lat'])
    def enu(node):
        p=ecef(float(node['lon']),float(node['lat']))
        dx,dy,dz=(p[i]-origin[i] for i in range(3))
        return [-math.sin(lon0)*dx+math.cos(lon0)*dy,
                -math.sin(lat0)*math.cos(lon0)*dx-math.sin(lat0)*math.sin(lon0)*dy+math.cos(lat0)*dz]
    footprint=orient_polygons(Polygon([enu(nodes[n.attrib['ref']]) for n in way.findall('nd')]))
    assert footprint.is_valid and footprint.area>1200
    def triangles(geometry):
        return [list(p.exterior.coords)[:-1] for p in constrained_delaunay_triangles(orient_polygons(geometry)).geoms if p.area>1e-10]
    courts=[]; line_sets={'tennis':[],'netball':[]}; nets=[]
    for source_id in COURT_IDS:
        row=next(r for r in site['greens'] if r['id']=='way/'+source_id)
        ring=row['geometry']['coordinates'][0][:-1]
        assert row['properties']['surface']=='tarmac'
        # All supplied rings are rectangles, with the first edge across a tennis
        # baseline or along a netball sideline. Affine interpolation retains the
        # archived corners instead of silently imposing regulation dimensions.
        p0,p1,p2,p3=ring
        def point(x,y):
            return [p0[i]+(p1[i]-p0[i])*x+(p3[i]-p0[i])*y for i in range(2)]
        a=math.dist(p0,p1); b=math.dist(p0,p3)
        sport=row['properties']['sport']
        lines=[ring+[ring[0]]]
        if sport=='tennis':
            inner=(1-8.23/10.97)/2
            for x in [inner,1-inner]:lines.append([point(x,0),point(x,1)])
            service=6.40/23.77
            for y in [.5-service,.5+service]:lines.append([point(inner,y),point(1-inner,y)])
            lines.append([point(.5,.5-service),point(.5,.5+service)])
            for y,dy in [(0,.1/b),(1,-.1/b)]:lines.append([point(.5,y),point(.5,y+dy)])
            nets.append(dict(id=row['id'],left=point(-.914/a,.5),right=point(1+.914/a,.5)))
        else:
            for x in [1/3,2/3]:lines.append([point(x,0),point(x,1)])
            # Standard layout is fitted to the mapped rectangle. Its dimensions
            # differ from a surveyed regulation court; do not move mapped edges.
            lines.append([point(.5+.45/30.5*math.cos(t),.5+.45/15.25*math.sin(t)) for t in [2*math.pi*i/64 for i in range(65)]])
            for x,sign in [(0,1),(1,-1)]:
                lines.append([point(x+sign*4.9/30.5*math.cos(t),.5+4.9/15.25*math.sin(t)) for t in [-math.pi/2+math.pi*i/64 for i in range(65)]])
        region=unary_union([LineString(line).buffer(.025,cap_style=2,join_style=2) for line in lines]).intersection(footprint)
        line_sets[sport].append(region)
        poly=Polygon(ring)
        assert footprint.buffer(.0001).covers(poly)
        courts.append(dict(id=row['id'],sport=sport,ring=ring,edgeLengthsMetres=[a,b],
                           referenceDimensionsMetres=[10.97,23.77] if sport=='tennis' else [30.5,15.25],
                           dimensionStatus='Archived mapped boundary; standard internal ratios fitted to source; not an as-built court survey'))
    tennis=unary_union(line_sets['tennis'])
    # Primary lines win at crossings. The two sets never form coplanar duplicate
    # polygons, and their subdued tone does not claim a measured paint colour.
    netball=unary_union(line_sets['netball']).difference(tennis)
    for net in nets:
        assert footprint.contains(LineString([net['left'],net['right']]))
    save(PLAN,dict(baselineSha256=BASE_SHA,sourceHashes={str(p.relative_to(ROOT)):sha(p) for p in [OSM,SITE]},
          facility=dict(id='way/301471945',version=way.attrib['version'],timestamp=way.attrib['timestamp'],tags=tags,
                        ring=list(footprint.exterior.coords)[:-1],areaSquareMetres=footprint.area),
          courts=courts,nets=nets,surfaceTriangles=triangles(footprint),tennisTriangles=triangles(tennis),netballTriangles=triangles(netball),
          lineAreaSquareMetres=dict(tennis=tennis.area,netball=netball.area),
          sources=[dict(url='https://camdenactive.camden.gov.uk/sports/lincolnsinnfields/',retrieved='2026-10-15',claim='Three tarmac tennis courts'),
                   dict(url='https://camdenactive.camden.gov.uk/courses/41/netball/',retrieved='2026-10-15',claim='Two netball bookings at same convertible site'),
                   dict(url='https://camdenactive.camden.gov.uk/Uploads/Image/CamdenGreenSpace1608%20LIF%20tennis.jpg',local='operator-courts.jpg',sha256=sha(OUT/'operator-courts.jpg'),claim='Operator photograph shows grey hardcourt, white tennis lines and nets; publication and capture date unspecified; viewed as visual evidence only, no image texture reused'),
                   dict(url='https://www.itftennis.com/en/about-us/organisation/tennis-glossary/',claim='Standard singles/doubles/service-line ratios and net heights'),
                   dict(url='https://netball.sport/game/facilities-and-equipment/',claim='Standard thirds, centre circle and goal circle proportions')]))
    print('COURTS212_PLAN',footprint.area,len(tennis.geoms) if hasattr(tennis,'geoms') else 1)


def build_component():
    import bpy
    from mathutils import Vector
    from integrate_exterior_round194 import object_fingerprint
    from refine_portsmouth_exterior207 import material_fingerprint
    assert sha(BASE)==BASE_SHA
    plan=json.loads(PLAN.read_text())
    assert plan['baselineSha256']==BASE_SHA
    assert all(sha(ROOT/p)==h for p,h in plan['sourceHashes'].items())
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
    scene=bpy.context.scene
    before={o.name:object_fingerprint(o) for o in bpy.data.objects}
    visibility={o.name:o.hide_render for o in bpy.data.objects}
    materials={m.name:material_fingerprint(m) for m in bpy.data.materials}
    archived=['GROUND199_GIS_green_way/'+i for i in COURT_IDS]
    for name in archived:
        o=bpy.data.objects[name]
        assert not o.hide_render and all('grass' in m.name for m in o.data.materials)
        assert all(abs((o.matrix_world@v.co).z-.05)<.000001 for v in o.data.vertices)
    collection=bpy.data.collections['03_PUBLIC_REALM']
    added=[]
    def material(name,colour):
        m=bpy.data.materials.new(PREFIX+name);m.diffuse_color=(*colour,1);m.use_nodes=True
        node=m.node_tree.nodes.get('Principled BSDF');node.inputs['Base Color'].default_value=(*colour,1);node.inputs['Roughness'].default_value=.86
        return m
    tarmac=material('estimated_neutral_grey_tarmac',(.19,.21,.20))
    white=material('white_tennis_paint',(.78,.79,.75))
    faded=material('estimated_secondary_netball_paint',(.46,.48,.44))
    dark=material('estimated_dark_netting',(.025,.038,.031))
    metal=material('estimated_green_net_posts',(.04,.13,.08))
    def mesh_object(name,vertices,faces,mat):
        mesh=bpy.data.meshes.new(PREFIX+name+'_mesh');mesh.from_pydata(vertices,[],faces);mesh.materials.append(mat);mesh.update()
        uv=mesh.uv_layers.new(name='MetricUV')
        for f in mesh.polygons:
            for i in f.loop_indices:uv.data[i].uv=mesh.vertices[mesh.loops[i].vertex_index].co.xy
        o=bpy.data.objects.new(PREFIX+name,mesh);collection.objects.link(o)
        o['destinationCollection']=collection.name;o['sourceOsmFacility']='way/301471945'
        o['dimensionStatus']='Mapped footprint and court positions; internal markings, net dimensions and colours estimated from rules/operator photo'
        added.append(o);return o
    for name,key,z,mat in [('whole_tarmac_surface','surfaceTriangles',SURFACE_Z,tarmac),('three_tennis_markings','tennisTriangles',SURFACE_Z+.001,white),('two_netball_markings','netballTriangles',SURFACE_Z+.001,faded)]:
        verts=[];faces=[]
        for triangle in plan[key]:
            start=len(verts);verts.extend((p[0],p[1],z) for p in triangle)
            area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(triangle,triangle[1:]+triangle[:1]))
            faces.append(tuple(start+i for i in ([0,1,2] if area>0 else [2,1,0])))
        mesh_object(name,verts,faces,mat)
    # Narrow rectangular ribbons batch all open net grid strands into one mesh.
    # They have real open holes; no opaque grey billboard or texture alpha.
    batches={key:([],[]) for key in ['net_mesh','net_tapes','net_posts']}
    def ribbon(family,a,b,width):
        verts,faces=batches[family];a,b=Vector(a),Vector(b)
        direction=(b-a).normalized();n=Vector((-direction.z,0,direction.x))
        if n.length<.1:n=Vector((0,0,1))
        n.normalize();n*=width/2;start=len(verts)
        verts.extend([a-n,b-n,b+n,a+n]);faces.append(tuple(start+i for i in range(4)))
    def box(family,center,u,length,width,height):
        verts,faces=batches[family];center=Vector(center);u=Vector(u);n=Vector((-u.y,u.x,0));start=len(verts)
        verts.extend(center+u*x*length/2+n*y*width/2+Vector((0,0,z*height/2)) for x,y,z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)])
        faces.extend(tuple(start+i for i in f) for f in [(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
    for net in plan['nets']:
        a=Vector((*net['left'],SURFACE_Z));b=Vector((*net['right'],SURFACE_Z));u=(b-a).normalized();length=(b-a).length
        def p(t,height):return a+(b-a)*t+Vector((0,0,height))
        def top(t):return .914+(.156*(2*t-1)**2)
        for endpoint in [a,b]:box('net_posts',endpoint+Vector((0,0,.55)),u,.065,.065,1.10)
        count=math.ceil(length/.14)
        for i in range(count+1):
            t=i/count;ribbon('net_mesh',p(t,.055),p(t,top(t)-.025),.004)
        for row in range(1,7):
            for i in range(32):
                t0,t1=i/32,(i+1)/32
                ribbon('net_mesh',p(t0,.055+(top(t0)-.08)*row/7),p(t1,.055+(top(t1)-.08)*row/7),.004)
        for i in range(32):
            t0,t1=i/32,(i+1)/32;ribbon('net_tapes',p(t0,top(t0)),p(t1,top(t1)),.045)
        ribbon('net_tapes',p(.5,.02),p(.5,top(.5)),.04)
    for family,mat in [('net_mesh',dark),('net_tapes',white),('net_posts',metal)]:
        mesh_object('three_tennis_'+family,*batches[family],mat)
    assert all(object_fingerprint(bpy.data.objects[n])==h for n,h in before.items())
    assert all(bpy.data.objects[n].hide_render==v for n,v in visibility.items())
    assert all(material_fingerprint(bpy.data.materials[n])==h for n,h in materials.items())
    assert set(bpy.data.objects.keys())-set(before)=={o.name for o in added}
    component=OUT/'component.blend';assert not component.exists()
    bpy.data.libraries.write(str(component),set(added),fake_user=True,compress=True)
    fingerprints={o.name:object_fingerprint(o) for o in added}
    authored_materials={m.name:material_fingerprint(m) for m in [tarmac,white,faded,dark,metal]}
    audit=dict(version=212,status='component-verified-ready-for-integration',baseline=str(BASE.relative_to(ROOT)),baselineSha256=BASE_SHA,
          componentPath=str(component.relative_to(ROOT)),componentSha256=sha(component),targetCollection=collection.name,destinationCollection=collection.name,
          addedObjects=[o.name for o in added],archivedObjects=archived,changedObjects=[],addedFingerprints=fingerprints,
          sourceHashes=plan['sourceHashes'],sources=plan['sources'],facility=plan['facility'],courts=plan['courts'],nets=plan['nets'],
          defect='Five overlapping tennis/netball pitch objects carry the park grass material; mapped enclosing tarmac recreation_ground omitted entirely.',
          repair='One mapped whole-facility tarmac sheet replaces five overlapping grass pitch sheets. Court markings share this single physical surface.',
          geometryBudget=dict(objects=len(added),vertices=sum(len(o.data.vertices) for o in added),polygons=sum(len(o.data.polygons) for o in added),triangles=sum(sum(len(f.vertices)-2 for f in o.data.polygons) for o in added),materials=5),
          originalGeometryUVsMaterialsAndVisibilityPreserved=True,baselineAndInputsUnchanged=True,
          addedMaterialFingerprints=authored_materials,
          dimensionsEstimated=dict(lineWidthMetres=.05,surfaceElevationMetres=SURFACE_Z,netPostHeightMetres=1.1,netCentreHeightMetres=.914,netEndHeightMetres=1.07,netGridApproximateMetres=.14),
          scope='Public Lincoln\'s Inn Fields original mapped sports enclosure only. No park fence, court fence, paths, buildings, other ground or private Inn changes.',
          limitations=['Archived OSM geometry dated2024-04-02, retrieved2026-09-12; operator page checked2026-10-15, hosted photograph is undated. No current measured survey implied.',
                       'Original mapped pitch dimensions retained, including small departures from regulation dimensions; service/circle dimensions use fitted standard proportions.',
                       'Grey tarmac, white tennis paint and nets are photo-supported classes; precise colours, secondary netball paint tone, line widths and net construction are estimates.',
                       'Three tennis nets illustrate operator-photographed tennis configuration; no claim of current booking, access, operating state, simultaneous tennis/netball use or permanently installed netball poles.',
                       'Full tarmac boundary comes from source way301471945, not an inferred rectangle or union of court outlines. The original whole-park sheet remains below the recovered sports surface.'])
    save(OUT/'audit.json',audit)
    # Reopen serialized library and validate actual geometry against authoring.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(component),link=False) as (source,target):
        assert set(source.objects)==set(fingerprints);target.objects=list(fingerprints)
    for o in target.objects:assert object_fingerprint(o)==fingerprints[o.name]
    assert all(material_fingerprint(bpy.data.materials[n])==h for n,h in authored_materials.items())
    assert sha(BASE)==BASE_SHA and all(sha(ROOT/p)==h for p,h in plan['sourceHashes'].items())
    save(OUT/'reopened-verification.json',dict(componentSha256=sha(component),objectsVerified=len(target.objects),geometryUVsAndMaterialsVerified=True,baselineAndInputsUnchanged=True))
    print('COURTS212_READY',len(added),audit['geometryBudget'])


if __name__=='__main__':
    try:import bpy
    except ModuleNotFoundError:prepare_plan()
    else:build_component()
