"""Recover mapped pedestrian surfaces without inventing routes or road widths.

Fixed configuration: open in Blender's Text Editor once to audit the current
campus, prepare the plan in the existing Python environment, then open again to
build the component. Preserve the source model, original meshes and materials.
OSM surface tags are archived evidence, not a current measured campus survey.
"""
from pathlib import Path
import hashlib
import json
import math
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'result/blender/LSE_campus_detailed_v208.blend'
BASE_SHA = 'da07d198617bd18bceaece14682b9d0995a288655b6c5aa0ac8d2765e883b92c'
OUT = ROOT/'result/blender/pedestrian-surfaces209'
PATH_SOURCE = 'GROUND199_00_SITE_Road_footway'
GREEN_SOURCES = ['GROUND199_GIS_green_way/30613392', 'GROUND199_GIS_green_way/4075108']
PLAN = OUT/'surface-plan.json'
PRECISION = .0001
sys.path.insert(0, str(ROOT/'web/tools'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, record):
    path.write_text(json.dumps(record, indent=2)+'\n')


def audit_native():
    import bpy
    assert sha(BASE) == BASE_SHA
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    rows = []
    for name in [PATH_SOURCE, *GREEN_SOURCES]:
        obj = bpy.data.objects[name]
        assert obj.type == 'MESH' and not obj.hide_render
        rows.append(dict(name=name, vertices=[list(obj.matrix_world@v.co) for v in obj.data.vertices],
                         faces=[list(face.vertices) for face in obj.data.polygons],
                         materials=[m.name for m in obj.data.materials],
                         collections=[collection.name for collection in obj.users_collection]))
    write_json(OUT/'native-audit.json', dict(baselineSha256=BASE_SHA, objects=rows))


def prepare_plan():
    from shapely import constrained_delaunay_triangles, orient_polygons, set_precision
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    audit = json.loads((OUT/'native-audit.json').read_text())
    assert audit['baselineSha256'] == BASE_SHA
    native = next(row for row in audit['objects'] if row['name'] == PATH_SOURCE)
    tops = []
    for face in native['faces']:
        points = [native['vertices'][index] for index in face]
        if all(abs(point[2]-.024) < 1e-6 for point in points):
            tops.append(Polygon([point[:2] for point in points]))
    site = json.loads((ROOT/'result/blender/site_geometry.json').read_text())
    ways = [r for r in site['roads'] if r['geometry']['type'] == 'LineString'
            and r['properties'].get('highway') == 'footway' and not r['properties'].get('name')]
    segments = [(r, a, b) for r in ways
                for a, b in zip(r['geometry']['coordinates'], r['geometry']['coordinates'][1:])
                if math.dist(a, b) > .1]
    assert len(segments) == len(tops) == 645
    records = []
    maximum = 0
    asphalt = []
    for (way, a, b), polygon in zip(segments, tops):
        length = math.dist(a, b)
        dx, dy = (b[0]-a[0])/length, (b[1]-a[1])/length
        expected = Polygon([(a[0]-.025*dx-.8*dy, a[1]-.025*dy+.8*dx),
                            (b[0]+.025*dx-.8*dy, b[1]+.025*dy+.8*dx),
                            (b[0]+.025*dx+.8*dy, b[1]+.025*dy-.8*dx),
                            (a[0]-.025*dx+.8*dy, a[1]-.025*dy-.8*dx)])
        error = expected.hausdorff_distance(polygon)
        assert error < .000025, (way['id'], error)
        maximum = max(maximum, error)
        surface = way['properties'].get('surface')
        records.append(dict(way=way['id'], surface=surface,
                            osmTimestamp=way['properties'].get('osm_timestamp'), boundaryErrorMetres=error))
        if surface == 'asphalt':
            asphalt.append(polygon)
    source_footprint = unary_union(tops)
    paths = set_precision(orient_polygons(set_precision(source_footprint, PRECISION)), 0)
    asphalt_union = orient_polygons(set_precision(set_precision(unary_union(asphalt), PRECISION), 0).intersection(paths))
    paving = orient_polygons(paths.difference(asphalt_union))
    assert asphalt_union.intersection(paving).area < 1e-7
    assert paths.symmetric_difference(asphalt_union.union(paving)).area < 1e-6
    assert source_footprint.hausdorff_distance(paths) < PRECISION
    assert source_footprint.symmetric_difference(paths).area < .5

    def shape_plan(geometry):
        geometry = orient_polygons(geometry)
        parts = [geometry] if geometry.geom_type == 'Polygon' else list(geometry.geoms)
        parts = [part for part in parts if part.geom_type == 'Polygon' and part.area > 1e-8]
        triangles = list(constrained_delaunay_triangles(geometry).geoms)
        assert abs(sum(triangle.area for triangle in triangles)-geometry.area) < 1e-5
        return dict(areaM2=geometry.area,
                    polygons=[dict(outer=list(part.exterior.coords)[:-1],
                                   holes=[list(ring.coords)[:-1] for ring in part.interiors]) for part in parts],
                    triangles=[list(triangle.exterior.coords)[:-1] for triangle in triangles])

    grasses = []
    for name in GREEN_SOURCES:
        row = next(item for item in audit['objects'] if item['name'] == name)
        source = unary_union([Polygon([row['vertices'][index][:2] for index in face]) for face in row['faces']])
        grass = set_precision(orient_polygons(set_precision(source, PRECISION)), 0)
        exposed = grass.intersection(paths)
        retained = orient_polygons(grass.difference(paths))
        assert exposed.area > 100
        assert retained.intersection(paths).area < 1e-7
        assert abs(retained.area+exposed.area-grass.area) < 1e-5
        assert source.symmetric_difference(grass).area < .2
        heights = [point[2] for point in row['vertices']]
        assert max(heights)-min(heights) < 1e-6
        grasses.append(dict(source=name, z=heights[0], sourceAreaM2=source.area,
                            exposedMappedPathAreaM2=exposed.area, geometry=shape_plan(retained)))
    plan = dict(baselineSha256=BASE_SHA, sourceObject=PATH_SOURCE, sources=records,
                sourceWays=len(ways), explicitAsphaltWays=sum(r['properties'].get('surface') == 'asphalt' for r in ways),
                sourceWidthMetres=1.6, preservedTop=.024, preservedBottom=0,
                matchedSegments=len(segments), maxRegistrationErrorMetres=maximum,
                precisionMetres=PRECISION, sourceFootprintAreaM2=source_footprint.area,
                retainedFootprintAreaM2=paths.area,
                redundantCoplanarAreaM2=sum(polygon.area for polygon in tops)-source_footprint.area,
                boundaryMaximumDeviationMetres=source_footprint.hausdorff_distance(paths),
                symmetricDifferenceAreaM2=source_footprint.symmetric_difference(paths).area,
                asphalt=shape_plan(asphalt_union), paving=shape_plan(paving), grasses=grasses,
                evidence='Archived OSM LineStrings and explicit surface tags match all645 original native strips within25micrometres. Original park sheets atz0.05 cover path tops atz0.024.',
                limitations='Mapped routes and original1.6m width are inherited estimates. Only explicit asphalt tags change surface class; unspecified, paved, concrete and paving-stone ways retain their existing pale finish. No current survey or new water feature is inferred.')
    write_json(PLAN, plan)
    print('PEDESTRIAN209_PLAN', len(segments), 'exposedM2', sum(g['exposedMappedPathAreaM2'] for g in grasses), flush=True)


def build_component():
    import bpy
    import bmesh
    from integrate_exterior_round194 import object_fingerprint
    from refine_portsmouth_exterior207 import material_fingerprint
    assert sha(BASE) == BASE_SHA
    plan = json.loads(PLAN.read_text())
    assert plan['baselineSha256'] == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    objects_before = {obj.name: object_fingerprint(obj) for obj in bpy.data.objects}
    materials_before = {mat.name: material_fingerprint(mat) for mat in bpy.data.materials}
    owned = []
    records = []

    def create_surface(name, geometry, source, material, top, bottom=None):
        vertices, faces, lookup = [], [], {}
        def vertex(point, z):
            key = (round(point[0], 8), round(point[1], 8), z)
            if key not in lookup:
                lookup[key] = len(vertices)
                vertices.append(key)
            return lookup[key]
        for triangle in geometry['triangles']:
            area = sum(a[0]*b[1]-b[0]*a[1] for a, b in zip(triangle, triangle[1:]+triangle[:1]))
            ordered = triangle if area > 0 else list(reversed(triangle))
            faces.append(tuple(vertex(point, top) for point in ordered))
            if bottom is not None:
                faces.append(tuple(vertex(point, bottom) for point in reversed(ordered)))
        if bottom is not None:
            for polygon in geometry['polygons']:
                for ring in [polygon['outer'], *polygon['holes']]:
                    for a, b in zip(ring, ring[1:]+ring[:1]):
                        faces.append((vertex(a, bottom), vertex(b, bottom), vertex(b, top), vertex(a, top)))
        mesh = bpy.data.meshes.new(name+'_mesh')
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        private = material.copy()
        private.name = name+'_'+material.name
        mesh.materials.append(private)
        layer = mesh.uv_layers.new(name='MetricUV')
        for loop in mesh.loops:
            layer.data[loop.index].uv = mesh.vertices[loop.vertex_index].co.xy
        obj = bpy.data.objects.new(name, mesh)
        for collection in source.users_collection:
            collection.objects.link(obj)
        obj['originalObject'] = source.name
        obj['surfaceEvidence'] = plan['evidence']
        obj['surfaceLimitations'] = plan['limitations']
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.normal_update()
        # GEOS retains sub-micrometre overlay slivers that collapse when Blender
        # stores32-bit mesh coordinates. Weld only within30micrometres, below
        # the audited0.1mm boundary tolerance, then remove collapsed faces.
        vertices_before = len(bm.verts)
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=.00003)
        bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=.00003)
        bm.normal_update()
        def relative_area(face):
            # BMFace.calc_area loses narrow triangles at large world offsets.
            # Evaluate cross products relative to the first corner instead.
            points = [tuple(vertex.co) for vertex in face.verts]
            origin = points[0]
            value = 0
            for i in range(1, len(points)-1):
                u = [points[i][j]-origin[j] for j in range(3)]
                v = [points[i+1][j]-origin[j] for j in range(3)]
                cross = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
                value += math.sqrt(sum(item*item for item in cross))/2
            return value
        assert all(relative_area(face) > 1e-12 for face in bm.faces)
        if bottom is None:
            assert all(abs(vertex.co.z-top) < 1e-6 for vertex in bm.verts)
            volume = None
        else:
            assert all(edge.is_manifold for edge in bm.edges), name
            volume = bm.calc_volume(signed=True)
            assert volume > 0
        welded_vertices = vertices_before-len(bm.verts)
        bm.to_mesh(mesh)
        mesh.update()
        if bottom is None:
            mesh.normals_split_custom_set_from_vertices([(0, 0, 1)]*len(mesh.vertices))
        bm.free()
        owned.append(obj)
        records.append(dict(name=name, source=source.name, vertices=len(vertices), faces=len(faces),
                            areaM2=geometry['areaM2'], signedVolume=volume, flatUpwardSheet=bottom is None, weldedVertices=welded_vertices))

    path = bpy.data.objects[PATH_SOURCE]
    create_surface('SITE209_Mapped_asphalt_footways', plan['asphalt'], path,
                   bpy.data.materials['Road asphalt'], plan['preservedTop'])
    create_surface('SITE209_Continuous_paved_footways', plan['paving'], path,
                   path.data.materials[0], plan['preservedTop'])
    for grass in plan['grasses']:
        source = bpy.data.objects[grass['source']]
        name = 'SITE209_'+source.name.replace('GROUND199_', '').replace('/', '_')+'_path_openings'
        create_surface(name, grass['geometry'], source, source.data.materials[0], grass['z'])
    assert all(object_fingerprint(bpy.data.objects[name]) == state for name, state in objects_before.items())
    assert all(material_fingerprint(bpy.data.materials[name]) == state for name, state in materials_before.items())
    expected = {obj.name: object_fingerprint(obj) for obj in owned}
    component = OUT/'pedestrian-surfaces209-component.blend'
    bpy.data.libraries.write(str(component), set(owned), fake_user=True, compress=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(component), link=False) as (source, target):
        target.objects = list(expected)
    for obj in target.objects:
        bpy.context.scene.collection.objects.link(obj)
        assert object_fingerprint(obj) == expected[obj.name]
    assert sha(BASE) == BASE_SHA
    report = dict(version=209, baseline=str(BASE.relative_to(ROOT)), baselineSha256=BASE_SHA,
                  componentPath=str(component.relative_to(ROOT)), componentSha256=sha(component),
                  addedObjects=list(expected), archivedObjects=[PATH_SOURCE, *GREEN_SOURCES],
                  targetCollection='00_SITE', records=records,
                  originalsVerified=len(objects_before), originalMaterialsVerified=len(materials_before),
                  scope='Recover mapped park paths, dissolve duplicate footway top surfaces and respect archived explicit asphalt finishes. Retain surface heights, approximate widths and routes; clip only mapped path footprints from two existing park sheets. Flat finish sheets replace the old24mm-deep footway boxes; all originals remain archived.',
                  limitations=plan['limitations'], verification=dict(componentReopened=True,
                  ownedFingerprintsVerified=True, baselineUnchanged=True, originalGeometryUVMaterialsPreserved=True))
    write_json(OUT/'audit.json', report)
    print('PEDESTRIAN209_COMPONENT', len(owned), flush=True)


if __name__ == '__main__':
    try:
        import bpy
    except ImportError:
        prepare_plan()
    else:
        if PLAN.exists():
            build_component()
        else:
            audit_native()
