"""Restore mapped pedestrian areas omitted by the original line-only road builder.

Fixed authoring workflow: first run in Blender to inspect existing surfaces, run
in the existing Python environment to triangulate the plan, then run in Blender
to build a separate component. Source geometry and materials remain untouched.
"""
from pathlib import Path
import hashlib
import json
import math
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'result/blender/LSE_campus_detailed_v210.blend'
BASE_SHA = '7a9483a9aaacc37f2461516f22eca464231d4b73ab11d8a825176e9d27950ba5'
OUT = ROOT/'result/blender/street-surfaces211'
AREAS = {'relation/5992662': 'Strand_forecourt', 'way/429289484': 'Sheffield_Street'}
ASPHALT = ['SITE198_Continuous_asphalt_road_network', 'SITE209_Mapped_asphalt_footways']
PLAN = OUT/'surface-plan.json'
sys.path.insert(0, str(ROOT/'web/tools'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')


def audit_native():
    import bpy
    from mathutils import Vector
    assert sha(BASE) == BASE_SHA
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    site = json.loads((ROOT/'result/blender/site_geometry.json').read_text())
    bounds = []
    for row in site['roads']:
        if row['geometry']['type'] != 'Polygon':
            continue
        points = row['geometry']['coordinates'][0]
        bounds.append((min(p[0] for p in points), min(p[1] for p in points),
                       max(p[0] for p in points), max(p[1] for p in points)))
    rows = []
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or obj.hide_render or obj.hide_get():
            continue
        corners = [obj.matrix_world@Vector(v) for v in obj.bound_box]
        extent = (min(v.x for v in corners), min(v.y for v in corners),
                  max(v.x for v in corners), max(v.y for v in corners))
        if min(v.z for v in corners) > .85 or max(v.z for v in corners) < .015:
            continue
        if not any(extent[0] <= b[2] and extent[2] >= b[0] and extent[1] <= b[3] and extent[3] >= b[1] for b in bounds):
            continue
        vertices = [obj.matrix_world@v.co for v in obj.data.vertices]
        faces = []
        for face in obj.data.polygons:
            points = [vertices[i] for i in face.vertices]
            if min(p.z for p in points) < .015 or max(p.z for p in points) >= .85:
                continue
            if max(p.z for p in points)-min(p.z for p in points) > .0001:
                continue
            if abs(sum(a.x*b.y-b.x*a.y for a, b in zip(points, points[1:]+points[:1]))) < 1e-8:
                continue
            faces.append(dict(points=[list(p) for p in points],
                              material=obj.data.materials[face.material_index].name if obj.data.materials else None))
        if faces:
            rows.append(dict(name=obj.name, faces=faces))
    save(OUT/'native-surfaces.json', dict(baselineSha256=BASE_SHA, objects=rows))


def prepare_plan():
    from shapely import constrained_delaunay_triangles, make_valid, orient_polygons, set_precision
    from shapely.affinity import rotate
    from shapely.geometry import Polygon, box, shape
    from shapely.ops import unary_union
    native = json.loads((OUT/'native-surfaces.json').read_text())
    assert native['baselineSha256'] == BASE_SHA
    site = json.loads((ROOT/'result/blender/site_geometry.json').read_text())

    def tidy(geometry):
        return orient_polygons(set_precision(set_precision(make_valid(geometry), .0001), 0))

    def footprint(row):
        return tidy(unary_union([Polygon([p[:2] for p in face['points']]) for face in row['faces']]))

    def triangles(geometry):
        return [list(p.exterior.coords)[:-1] for p in constrained_delaunay_triangles(geometry).geoms if p.area > 1e-9]

    paved = [row for row in native['objects'] if row['name'].startswith(('SITE', 'GROUND'))
             and any(any(token in (f['material'] or '').lower() for token in ('paving', 'site_v47_slab', 'site_v47_edge', 'site_v47_grout', 'yorkstone')) for f in row['faces'])]
    existing = tidy(unary_union([footprint(row) for row in paved]))
    buildings = unary_union([Polygon(t) for b in site['buildings'] for t in b['triangles']])
    greens = unary_union([shape(g['geometry']) for g in site['greens'] if g['geometry']['type'] in ('Polygon', 'MultiPolygon')])
    exclusions = buildings.union(greens)
    areas, regions = [], []
    for source_id, label in AREAS.items():
        source = next(row for row in site['roads'] if row['id'] == source_id)
        mapped = tidy(shape(source['geometry']))
        region = tidy(mapped.difference(exclusions))
        missing = tidy(region.difference(existing))
        assert missing.area > 5, (label, missing.area)
        # The source polygon governs the walking boundary. Tile size/course angle
        # are restrained presentation estimates, not a surveyed laying pattern.
        angle = 14 if label == 'Strand_forecourt' else 0
        rotated = rotate(missing, -angle, origin=(0, 0))
        x0, y0, x1, y1 = rotated.bounds
        tiles = []
        for row in range(math.floor(y0/.6), math.ceil(y1/.6)):
            stagger = .45 if row % 2 else 0
            for column in range(math.floor((x0-stagger)/.9), math.ceil((x1-stagger)/.9)):
                tile = box(column*.9+stagger+.003, row*.6+.003,
                           (column+1)*.9+stagger-.003, (row+1)*.6-.003)
                clipped = rotate(tile, angle, origin=(0, 0)).intersection(missing)
                if clipped.area > .000001:
                    tiles.append(dict(shade=(row*17+column*13) % 5, triangles=triangles(clipped)))
        regions.append(region)
        areas.append(dict(id=source_id, name=label, properties=source['properties'],
                          mappedAreaM2=mapped.area, retainedExistingPavingM2=region.intersection(existing).area,
                          excludedBuildingOrGreenAreaM2=mapped.intersection(exclusions).area,
                          restoredAreaM2=missing.area, boundary=triangles(missing), tiles=tiles,
                          coarseTileSizeMetres=[.9, .6], estimatedCourseAngleDegrees=angle))
    correction = tidy(unary_union(regions))
    replacements = []
    for name in ASPHALT:
        row = next(row for row in native['objects'] if row['name'] == name)
        old = footprint(row)
        removed = old.intersection(correction)
        new = orient_polygons(make_valid(old.difference(correction)))
        assert removed.area > .01
        assert new.intersection(correction).area < 1e-6
        assert old.symmetric_difference(new.union(removed)).area < .01
        replacements.append(dict(source=name, name='SITE211_'+name.removeprefix('SITE'),
                                 originalAreaM2=old.area, removedPedestrianOverlapM2=removed.area,
                                 retainedAreaM2=new.area, triangles=triangles(new)))
    save(PLAN, dict(baselineSha256=BASE_SHA, areas=areas, replacements=replacements,
                   restoredAreaM2=sum(row['restoredAreaM2'] for row in areas),
                   removedAsphaltOverlapM2=sum(row['removedPedestrianOverlapM2'] for row in replacements),
                   limitations='Archived OSM pedestrian-area boundaries and explicit paving-stones tags; relation5992662 remains version3 on source recheck. Existing building/green footprints and all detailed paving retained. Stone colours,0.9×0.6m courses and14degree Strand alignment are visual estimates, not as-built slab surveys. No invented route, street furniture or traffic marking.'))
    print('STREET211_PLAN', [(a['name'], round(a['restoredAreaM2'], 2)) for a in areas], flush=True)


def build_component():
    import bpy
    from integrate_exterior_round194 import object_fingerprint
    from refine_portsmouth_exterior207 import material_fingerprint
    assert sha(BASE) == BASE_SHA
    plan = json.loads(PLAN.read_text())
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    originals = {obj.name: object_fingerprint(obj) for obj in bpy.data.objects}
    materials = {m.name: material_fingerprint(m) for m in bpy.data.materials}
    owned, records = [], []

    def material(name, color):
        result = bpy.data.materials.new(name)
        result.diffuse_color = (*color, 1)
        result.use_nodes = True
        shader = result.node_tree.nodes['Principled BSDF']
        shader.inputs['Base Color'].default_value = (*color, 1)
        shader.inputs['Roughness'].default_value = .9
        return result

    def sheet(name, groups, slots, height, original=None):
        vertices, faces, indices, lookup = [], [], [], {}
        for triangles, slot in groups:
            for tri in triangles:
                ordered = tri if sum(a[0]*b[1]-b[0]*a[1] for a, b in zip(tri, tri[1:]+tri[:1])) > 0 else list(reversed(tri))
                face = []
                for point in ordered:
                    key = (round(point[0], 6), round(point[1], 6), height)
                    if key not in lookup:
                        lookup[key] = len(vertices)
                        vertices.append(key)
                    face.append(lookup[key])
                if len(set(face)) == 3:
                    faces.append(tuple(face))
                    indices.append(slot)
        mesh = bpy.data.meshes.new(name+'_mesh')
        mesh.from_pydata(vertices, [], faces)
        for slot in slots:
            mesh.materials.append(slot)
        for face, slot in zip(mesh.polygons, indices):
            face.material_index = slot
        mesh.update()
        uv = mesh.uv_layers.new(name='MetricUV')
        for loop in mesh.loops:
            uv.data[loop.index].uv = mesh.vertices[loop.vertex_index].co.xy
        mesh.normals_split_custom_set_from_vertices([(0, 0, 1)]*len(mesh.vertices))
        obj = bpy.data.objects.new(name, mesh)
        bpy.data.collections['00_SITE'].objects.link(obj)
        if original:
            obj['originalObject'] = original
        obj['scope'] = plan['limitations']
        owned.append(obj)
        records.append(dict(name=name, triangles=len(mesh.polygons), vertices=len(mesh.vertices),
                            materials=len(slots), height=height))
        return obj

    for row in plan['replacements']:
        source = bpy.data.objects[row['source']]
        sheet(row['name'], [(row['triangles'], 0)], [source.data.materials[0]], .024, source.name)
    for area in plan['areas']:
        label = area['name']
        base_color = (.30, .285, .25) if label == 'Strand_forecourt' else (.245, .253, .238)
        palette = [material(f'SITE211_SITE_V47_yorkstone_{label}_{i}', tuple(c*(.96+i*.02) for c in base_color)) for i in range(5)]
        grout = material('SITE211_SITE_V47_grout_'+label, (.10, .105, .095))
        sheet('SITE211_'+label+'_joint_bed', [(area['boundary'], 0)], [grout], .021)
        sheet('SITE211_'+label+'_stone_courses', [(tile['triangles'], tile['shade']) for tile in area['tiles']], palette, .024)
    assert all(object_fingerprint(bpy.data.objects[name]) == value for name, value in originals.items())
    assert all(material_fingerprint(bpy.data.materials[name]) == value for name, value in materials.items())
    fingerprints = {obj.name: object_fingerprint(obj) for obj in owned}
    component = OUT/'component.blend'
    bpy.data.libraries.write(str(component), set(owned), fake_user=True, compress=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(component), link=False) as (_, target):
        target.objects = list(fingerprints)
    for obj in target.objects:
        bpy.context.scene.collection.objects.link(obj)
        assert object_fingerprint(obj) == fingerprints[obj.name]
    assert sha(BASE) == BASE_SHA
    save(OUT/'audit.json', dict(version=211, baselineSha256=BASE_SHA,
         componentPath=str(component.relative_to(ROOT)), componentSha256=sha(component),
         targetCollection='00_SITE', addedObjects=list(fingerprints), archivedObjects=ASPHALT,
         records=records, restoredAreaM2=plan['restoredAreaM2'], removedAsphaltOverlapM2=plan['removedAsphaltOverlapM2'],
         originalsVerified=len(originals), originalMaterialsVerified=len(materials),
         verification=dict(componentReopened=True, originalGeometryUVMaterialsPreserved=True),
         scope='Restore mapped Strand forecourt and Sheffield walking-area gaps; subtract misplaced asphalt from the mapped pedestrian regions, preserve existing detailed paving and source building/green exclusions.',
         limitations=plan['limitations']))
    print('STREET211_COMPONENT', len(owned), flush=True)


if __name__ == '__main__':
    try:
        import bpy
    except ImportError:
        prepare_plan()
    else:
        build_component() if PLAN.exists() else audit_native()
