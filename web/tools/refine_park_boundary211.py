"""Restore the explicitly mapped public park fence, with eight clear entrances.

Open in Blender's Text Editor. Archived OSM gives the fence alignment and gate
clear widths; the simple metal section is an estimated proxy, not an as-built
railing survey. Do not alter grass, streets, buildings or private Lincoln's Inn.
"""
from pathlib import Path
import hashlib
import json
import math
import sys
import xml.etree.ElementTree as ET

import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'result/blender/LSE_campus_detailed_v210.blend'
BASE_SHA = '7a9483a9aaacc37f2461516f22eca464231d4b73ab11d8a825176e9d27950ba5'
OUT = ROOT/'result/blender/park-boundary211'
OSM = ROOT/'data/collections/streets/raw/osm_map.osm'
SITE = ROOT/'result/blender/site_geometry.json'
WAY_ID = '30613392'
PREFIX = 'PARK211_'
HEIGHT = 1.48
POST_SIZE = .09
GROUND = .05
sys.path.insert(0, str(ROOT/'web/tools'))
from integrate_exterior_round194 import object_fingerprint
from refine_portsmouth_exterior207 import material_fingerprint


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, record):
    path.write_text(json.dumps(record, indent=2)+'\n')


def mapped_boundary():
    """Register OSM node order against the exact existing local ENU park ring."""
    data = json.loads(SITE.read_text())
    park = next(row for row in data['greens'] if row['id'] == 'way/'+WAY_ID)
    ring = [Vector((p[0], p[1], 0)) for p in park['geometry']['coordinates'][0][:-1]]
    root = ET.parse(OSM).getroot()
    nodes = {node.attrib['id']: node for node in root.findall('node')}
    way = next(item for item in root.findall('way') if item.attrib['id'] == WAY_ID)
    tags = {tag.attrib['k']: tag.attrib['v'] for tag in way.findall('tag')}
    assert tags['barrier'] == 'fence' and tags['fence_type'] == tags['material'] == 'metal'
    assert tags['leisure'] == 'park' and tags['operator'] == 'London Borough of Camden'
    refs = [item.attrib['ref'] for item in way.findall('nd')][:-1]
    assert len(refs) == len(ring) == 16
    lon0, lat0 = map(math.radians, data['origin_lon_lat'])
    gates = []
    for index, ref in enumerate(refs):
        node = nodes[ref]
        properties = {tag.attrib['k']: tag.attrib['v'] for tag in node.findall('tag')}
        if properties.get('barrier') == 'gate':
            gates.append(dict(node=ref, index=index, centre=list(ring[index]),
                              clearWidthMetres=float(properties['maxwidth:physical']),
                              properties=properties, timestamp=node.attrib['timestamp']))
    # Preserve the float64 ENU projection used by the existing site preparation;
    # avoid float32 ECEF subtraction at Earth's radius.
    def ecef_double(lon, lat):
        lon, lat = map(math.radians, (lon, lat))
        radius = 6378137/math.sqrt(1-6.69437999014e-3*math.sin(lat)**2)
        return (radius*math.cos(lat)*math.cos(lon), radius*math.cos(lat)*math.sin(lon), radius*(1-6.69437999014e-3)*math.sin(lat))
    origin = ecef_double(*data['origin_lon_lat'])
    maximum_error = 0
    for index, ref in enumerate(refs):
        node = nodes[ref]
        target = ecef_double(float(node.attrib['lon']), float(node.attrib['lat']))
        dx, dy, dz = (target[i]-origin[i] for i in range(3))
        x = -math.sin(lon0)*dx+math.cos(lon0)*dy
        y = -math.sin(lat0)*math.cos(lon0)*dx-math.sin(lat0)*math.sin(lon0)*dy+math.cos(lat0)*dz
        maximum_error = max(maximum_error, math.hypot(x-ring[index].x, y-ring[index].y))
    assert maximum_error < .00003
    assert len(gates) == 8
    return ring, gates, dict(id='way/'+WAY_ID, timestamp=way.attrib['timestamp'],
                            tags=tags, maxRegistrationErrorMetres=maximum_error)


class FenceBatch:
    """Batch the whole boundary by construction family to keep the scene light."""
    def __init__(self, name):
        self.name = name
        self.vertices = []
        self.faces = []
        self.members = 0

    def box(self, centre, size, direction):
        u = direction.normalized()
        n = Vector((-u.y, u.x, 0))
        centre = Vector(centre)
        start = len(self.vertices)
        self.vertices.extend(centre+u*(x*size[0]/2)+n*(y*size[1]/2)+Vector((0,0,z*size[2]/2))
                             for x,y,z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                                           (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)])
        self.faces.extend(tuple(start+i for i in face) for face in [(3,2,1,0),(4,5,6,7),
                          (0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
        self.members += 1

    def finish(self, material, collection):
        mesh = bpy.data.meshes.new(self.name+'_mesh')
        mesh.from_pydata(self.vertices, [], self.faces)
        mesh.materials.append(material)
        mesh.update()
        uv = mesh.uv_layers.new(name='MetricUV')
        for polygon in mesh.polygons:
            for index in polygon.loop_indices:
                vertex = mesh.vertices[mesh.loops[index].vertex_index].co
                uv.data[index].uv = vertex.xy
        bm = bmesh.new()
        bm.from_mesh(mesh)
        assert all(edge.is_manifold for edge in bm.edges)
        assert bm.calc_volume(signed=True) > 0
        bm.free()
        obj = bpy.data.objects.new(self.name, mesh)
        collection.objects.link(obj)
        obj['destinationCollection'] = collection.name
        obj['sourceOsmWay'] = 'way/'+WAY_ID
        obj['dimensionStatus'] = 'Mapped fence alignment and entrance widths; estimated section height, pitch and finish'
        return obj


def build_component():
    assert sha(BASE) == BASE_SHA
    OUT.mkdir(parents=True, exist_ok=True)
    source_hashes = {str(path.relative_to(ROOT)): sha(path) for path in [OSM, SITE]}
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    scene = bpy.context.scene
    before = {obj.name: object_fingerprint(obj) for obj in bpy.data.objects}
    visibility = {obj.name: obj.hide_render for obj in bpy.data.objects}
    materials_before = {mat.name: material_fingerprint(mat) for mat in bpy.data.materials}
    ring, gates, source = mapped_boundary()
    # Probe every native perimeter segment at standing fence height. These short
    # cross-boundary rays establish the missing vertical enclosure, independently
    # from object naming and from the existing horizontal grass polygons.
    probes = []
    deps = bpy.context.evaluated_depsgraph_get()
    for index, a in enumerate(ring):
        b = ring[(index+1)%len(ring)]
        direction = (b-a).normalized()
        normal = Vector((-direction.y, direction.x, 0))
        midpoint = (a+b)/2+Vector((0,0,.8))
        hit = scene.ray_cast(deps, midpoint-normal*.2, normal, distance=.4)
        probes.append(dict(segment=index, point=list(midpoint), nativeHit=hit[4].name if hit[0] else None))
    assert all(row['nativeHit'] is None for row in probes), probes
    collection = bpy.data.collections['03_PUBLIC_REALM']
    material = bpy.data.materials['5LF_black'].copy()
    material.name = PREFIX+'estimated_dark_metal'
    material['finishEvidence'] = 'OSM specifies metal; dark finish retained as estimated neutral proxy, not measured coating'
    batches = {family: FenceBatch(PREFIX+family) for family in ['perimeter_posts','perimeter_rails','perimeter_vertical_bars']}
    by_index = {gate['index']: gate for gate in gates}
    segments = []
    for index, a in enumerate(ring):
        next_index = (index+1)%len(ring)
        b = ring[next_index]
        length = (b-a).length
        u = (b-a).normalized()
        trim_start = by_index[index]['clearWidthMetres']/2+POST_SIZE/2 if index in by_index else 0
        trim_end = by_index[next_index]['clearWidthMetres']/2+POST_SIZE/2 if next_index in by_index else 0
        lo, hi = trim_start, length-trim_end
        assert hi > lo
        for height in [.45, 1.26]:
            batches['perimeter_rails'].box(a+u*((lo+hi)/2)+Vector((0,0,GROUND+height)), (hi-lo,.038,.045), u)
        post_count = math.ceil((hi-lo)/2.7)
        for post in range(post_count+1):
            distance = lo+(hi-lo)*post/post_count
            # End posts are shared at mapped non-gate vertices; keep one per corner.
            if post == post_count and next_index not in by_index:
                continue
            batches['perimeter_posts'].box(a+u*distance+Vector((0,0,GROUND+HEIGHT/2)), (POST_SIZE,POST_SIZE,HEIGHT), u)
        bar_count = math.ceil((hi-lo)/.22)
        for bar in range(1,bar_count):
            distance = lo+(hi-lo)*bar/bar_count
            batches['perimeter_vertical_bars'].box(a+u*distance+Vector((0,0,GROUND+HEIGHT/2)), (.024,.024,HEIGHT), u)
        segments.append(dict(index=index, sourceStart=list(a), sourceEnd=list(b),
                             fenceStart=list(a+u*lo), fenceEnd=list(a+u*hi), lengthMetres=hi-lo,
                             startGate=by_index.get(index,{}).get('node'), endGate=by_index.get(next_index,{}).get('node')))
    added = [batch.finish(material, collection) for batch in batches.values()]
    for layer in scene.view_layers:
        layer.update()
    # Opening centres must remain clear through the whole height after authoring.
    entrance_probes = []
    for gate in gates:
        point = Vector(gate['centre'])
        u = (ring[(gate['index']+1)%len(ring)]-ring[gate['index']-1]).normalized()
        normal = Vector((-u.y,u.x,0))
        for fraction in [-.48,0,.48]:
            centre = point+u*(gate['clearWidthMetres']*fraction)+Vector((0,0,.8))
            hit = scene.ray_cast(deps,centre-normal*.2,normal,distance=.4)
            assert not hit[0], (gate['node'],fraction,hit[4].name if hit[0] else None)
        entrance_probes.append(dict(node=gate['node'],clearWidthMetres=gate['clearWidthMetres'],threeCrossingRaysClear=True))
    assert all(object_fingerprint(bpy.data.objects[name]) == fingerprint for name,fingerprint in before.items())
    assert all(bpy.data.objects[name].hide_render == hidden for name,hidden in visibility.items())
    assert all(material_fingerprint(bpy.data.materials[name]) == fingerprint for name,fingerprint in materials_before.items())
    assert set(bpy.data.objects.keys())-set(before) == {obj.name for obj in added}
    component = OUT/'component.blend'
    assert not component.exists(), 'Retain existing proof files'
    bpy.data.libraries.write(str(component),set(added),fake_user=True,compress=True)
    fingerprints = {obj.name:object_fingerprint(obj) for obj in added}
    for path in [OSM,SITE]:
        assert sha(path) == source_hashes[str(path.relative_to(ROOT))]
    assert sha(BASE) == BASE_SHA
    audit = dict(version=211,status='component-verified-ready-for-integration',
        baseline=str(BASE.relative_to(ROOT)),baselineSha256=BASE_SHA,
        component=str(component.relative_to(ROOT)),componentSha256=sha(component),
        destinationCollection=collection.name,addedObjects=[obj.name for obj in added],
        archivedObjects=[],changedObjects=[],addedFingerprints=fingerprints,sourceHashes=source_hashes,
        source=source,gates=gates,segments=segments,nativeBoundaryProbes=probes,entranceClearanceChecks=entrance_probes,
        defect='All16 native park perimeter cross-boundary probes atz0.8 miss vertical enclosure despite explicit OSM metal fence and8 measured gates.',
        construction={family:dict(members=batch.members,vertices=len(batch.vertices),faces=len(batch.faces)) for family,batch in batches.items()},
        dimensionsEstimated=dict(heightMetres=HEIGHT,postSectionMetres=POST_SIZE,picketPitchMaximumMetres=.22,postPitchMaximumMetres=2.7),
        geometryBudget=dict(objects=len(added),vertices=sum(len(batch.vertices) for batch in batches.values()),
                            quads=sum(len(batch.faces) for batch in batches.values()),
                            triangles=2*sum(len(batch.faces) for batch in batches.values()),materials=1,drawGroups=3),
        fencedLengthMetres=sum(row['lengthMetres'] for row in segments),
        allOriginalObjectsAndMaterialsPreserved=True,baselineAndInputsUnchanged=True,
        scope='Public Lincoln\'s Inn Fields park way/30613392 perimeter only; no private Lincoln\'s Inn, court fence, street paving or building changes.',
        limitations=['OSM archive establishes mapped fence and eight gate widths, not an October2026 on-site survey.',
                     'Fence height, member spacing, section, coating and simple two-rail profile are estimated proxies; no ornamental finials invented.',
                     'Entrance voids preserve access; gate leaf shape and operating/opening state are unverified and are not reconstructed.',
                     'Mapped widths use source maxwidth:physical; gate locations and park alignment inherit existing local ENU geometry.'])
    write_json(OUT/'audit.json',audit)
    # Reopen the written library through Blender and check the actual serialized
    # object geometry, UVs and bindings without changing the accepted campus file.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(component),link=False) as (source_data,target):
        assert set(fingerprints) == set(source_data.objects)
        target.objects = list(fingerprints)
    for obj in target.objects:
        assert object_fingerprint(obj) == fingerprints[obj.name], obj.name
    write_json(OUT/'reopened-verification.json',dict(componentSha256=sha(component),
              objectsVerified=len(target.objects),geometryUVsAndMaterialsVerified=True,
              gateClearanceRays=24,baselineAndInputsUnchanged=sha(BASE)==BASE_SHA))
    print('PARK211_READY',len(added),'segments',len(segments),'gates',len(gates),flush=True)


if __name__ == '__main__':
    build_component()
