"""Restore upward pedestrian surfaces and two flush native walking-path joins.

Apply in the loaded campus scene. This does not infer new street corridors or
alter buildings. Retained street vertices/materials/corner UVs stay exact; only
one-sided paving face winding is corrected. Two small joins use existing native
walking-road footprints clipped against existing paving/building outlines.
The inherited street widths and local heights are estimates, not a survey.
"""
from pathlib import Path
import array, hashlib, json
import bpy, bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'result/blender/street-connections194'
SOURCE = ROOT / 'result/blender/LSE_campus_detailed_v193.blend'
SOURCE_SHA256 = '795f45f02fae1087a138cb3fd4d63a62869182d5c0cfaab202e4c2a9e98855fb'
SURFACES = (
    'SITE_V47_Portsmouth_Street',
    'SITE_V47_Sheffield_Street',
    'SITE_V47_Clare_Market',
    'SITE_V47_John_Watkins_Plaza',
    'SITE167_Houghton_paving_with_cover_openings',
)
PATCHES = [{'sourceRoad': 'Road_LSE Square.002',
  'nearestPaving': 'SITE_V47_Clare_Market',
  'area': 0.6496805746919907,
  'center': [23.898761759634866, -38.79438621267313],
  'outer': [[22.32653433020654, -38.18860370007782],
            [22.574257567133195, -38.108496716451135],
            [25.509908493588487, -39.3916595926017],
            [25.431408672487006, -39.571253373583325],
            [22.2876136200065, -38.19711283274457]],
  'holes': [],
  'triangles': [[[25.431408672487006, -39.571253373583325],
                 [22.574257567133195, -38.108496716451135],
                 [25.509908493588487, -39.3916595926017]],
                [[22.32653433020654, -38.18860370007782],
                 [25.431408672487006, -39.571253373583325],
                 [22.2876136200065, -38.19711283274457]],
                [[22.574257567133195, -38.108496716451135],
                 [25.431408672487006, -39.571253373583325],
                 [22.32653433020654, -38.18860370007782]]],
  'top': 0.05,
  'bottom': 0.024,
  'derivedArea': 0.6497113857226451},
 {'sourceRoad': '00_SITE_Road_Portugal Street.001',
  'nearestPaving': 'SITE_V47_Sheffield_Street',
  'area': 1.4258626116704987,
  'center': [-54.163594877213754, -27.784716502126564],
  'outer': [[-53.25820773459051, -27.920631684167386],
            [-54.61718555190637, -28.46127383248713],
            [-54.62563391337478, -28.452856577188356],
            [-54.88416580100561, -28.13643153648425],
            [-55.109067215027224, -27.795282159703874],
            [-55.297991259378385, -27.43296841614374],
            [-55.30516696873908, -27.41492176224071],
            [-55.14149808622019, -27.349162742732748],
            [-54.998103581330554, -27.771439167821256],
            [-54.99379347862385, -27.774118724575846],
            [-52.97964675326867, -27.090254253298024]],
  'holes': [],
  'triangles': [[[-53.25820773459051, -27.920631684167386],
                 [-54.61718555190637, -28.46127383248713],
                 [-54.62563391337478, -28.452856577188356]],
                [[-54.99379347862385, -27.774118724575846],
                 [-54.88416580100561, -28.13643153648425],
                 [-55.109067215027224, -27.795282159703874]],
                [[-55.14149808622019, -27.349162742732748],
                 [-55.297991259378385, -27.43296841614374],
                 [-55.30516696873908, -27.41492176224071]],
                [[-55.109067215027224, -27.795282159703874],
                 [-55.14149808622019, -27.349162742732748],
                 [-54.998103581330554, -27.771439167821256]],
                [[-54.99379347862385, -27.774118724575846],
                 [-52.97964675326867, -27.090254253298024],
                 [-53.25820773459051, -27.920631684167386]],
                [[-54.88416580100561, -28.13643153648425],
                 [-53.25820773459051, -27.920631684167386],
                 [-54.62563391337478, -28.452856577188356]],
                [[-55.14149808622019, -27.349162742732748],
                 [-55.109067215027224, -27.795282159703874],
                 [-55.297991259378385, -27.43296841614374]],
                [[-54.88416580100561, -28.13643153648425],
                 [-54.99379347862385, -27.774118724575846],
                 [-53.25820773459051, -27.920631684167386]],
                [[-55.109067215027224, -27.795282159703874],
                 [-54.998103581330554, -27.771439167821256],
                 [-54.99379347862385, -27.774118724575846]]],
  'top': 0.05,
  'bottom': 0.024,
  'derivedArea': 1.425889100850946}]
COLLECTION = '00_SITE'
PREFIX = 'SITE194_'
JOIN = PREFIX + 'Flush_LSE_Square_and_Sheffield_walking_joins'


def geometry_digest(obj):
    digest = hashlib.sha256(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
    digest.update(array.array('i', [i for p in obj.data.polygons for i in p.vertices]).tobytes())
    return digest.hexdigest()


def corner_signature(mesh):
    """Orientation independent signature of every face and per-corner UV."""
    result = []
    for face in mesh.polygons:
        corners = []
        for index in face.loop_indices:
            corner = [mesh.loops[index].vertex_index]
            for layer in mesh.uv_layers:
                corner.extend(round(float(value), 7) for value in layer.data[index].uv)
            corners.append(tuple(corner))
        result.append((face.material_index, tuple(sorted(corners))))
    return hashlib.sha256(repr(sorted(result)).encode()).hexdigest()


def downward_count(obj):
    normal_matrix = obj.matrix_world.inverted().transposed().to_3x3()
    return sum((normal_matrix @ face.normal).z < -.2 for face in obj.data.polygons)


def apply_street_connections194():
    names = [PREFIX + name for name in SURFACES] + [JOIN]
    if all(bpy.data.objects.get(name) for name in names):
        return dict(alreadyApplied=True, addedObjects=[], archivedObjects=[], changedObjects=[], destinationCollection=COLLECTION)
    assert not any(bpy.data.objects.get(name) for name in names), 'Partial street194 component present'
    collection = bpy.data.collections[COLLECTION]
    originals = [bpy.data.objects[name] for name in SURFACES]
    unchanged = {obj.name: geometry_digest(obj) for obj in originals}
    rows = []
    owned = []
    for source in originals:
        assert not source.hide_render, source.name
        before_uv = corner_signature(source.data)
        positions = array.array('f', [v for point in source.data.vertices for v in point.co]).tobytes()
        clone = source.copy()
        clone.data = source.data.copy()
        clone.name = PREFIX + source.name
        clone.data.name = clone.name
        collection.objects.link(clone)
        clone.hide_render = False
        clone.hide_viewport = False
        clone.hide_set(False)
        normal_matrix = clone.matrix_world.inverted().transposed().to_3x3()
        bm = bmesh.new()
        bm.from_mesh(clone.data)
        bm.normal_update()
        reverse = [face for face in bm.faces if (normal_matrix @ face.normal).z < -.2]
        assert reverse, source.name
        bmesh.ops.reverse_faces(bm, faces=reverse)
        count = len(reverse)
        bm.to_mesh(clone.data)
        bm.free()
        clone.data.update()
        assert positions == array.array('f', [v for point in clone.data.vertices for v in point.co]).tobytes()
        assert before_uv == corner_signature(clone.data), source.name + ' UV or material binding changed'
        assert downward_count(clone) == 0, source.name
        clone['originalObject'] = source.name
        clone['streetConnections194'] = True
        clone['scope'] = 'One-sided street walking face winding corrected; exact source vertices, UV corners and material slots retained'
        rows.append(dict(source=source.name, owned=clone.name, changedFaceWinding=count, beforeDownwardFaces=downward_count(source), afterDownwardFaces=0, vertices=len(clone.data.vertices), faces=len(clone.data.polygons), exactVertices=True, exactFaceMembership=True, exactCornerUVsAndMaterialSlots=True))
        source.hide_render = True
        source.hide_set(True)
        owned.append(clone)
    verts, faces = [], []
    lookup = {}
    def vertex(p, z):
        key = (round(p[0], 7), round(p[1], 7), z)
        if key not in lookup:
            lookup[key] = len(verts)
            verts.append(key)
        return lookup[key]
    for patch in PATCHES:
        assert bpy.data.objects.get(patch['sourceRoad']), patch['sourceRoad']
        for triangle in patch['triangles']:
            ids = [vertex(p, patch['top']) for p in triangle]
            a, b, c = [Vector(verts[i]) for i in ids]
            if (b-a).cross(c-a).z < 0:
                ids.reverse()
            faces.append(tuple(ids))
        for ring in [patch['outer'], *patch['holes']]:
            for a, b in zip(ring, ring[1:] + ring[:1]):
                faces.append((vertex(a, patch['top']), vertex(a, patch['bottom']), vertex(b, patch['bottom']), vertex(b, patch['top'])))
    mesh = bpy.data.meshes.new(JOIN)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    mesh.materials.append(bpy.data.materials['Pale campus paving'])
    uv = mesh.uv_layers.new(name='MetricUV')
    for face in mesh.polygons:
        for index in face.loop_indices:
            p = mesh.vertices[mesh.loops[index].vertex_index].co
            uv.data[index].uv = (p.x, p.y)
    obj = bpy.data.objects.new(JOIN, mesh)
    collection.objects.link(obj)
    obj['streetConnections194'] = True
    obj['scope'] = 'Two low native walking-road slivers raised26mm to retained stone paving;3D road positions estimated, no surveyed curb datum'
    obj['sourceRoads'] = [patch['sourceRoad'] for patch in PATCHES]
    obj['walkingTop'] = .05
    obj['walkingBottom'] = .024
    owned.append(obj)
    for source in originals:
        assert unchanged[source.name] == geometry_digest(source)
    for layer in bpy.context.scene.view_layers:
        layer.update()
    return dict(alreadyApplied=False, addedObjects=[o.name for o in owned], archivedObjects=list(SURFACES), changedObjects=[], destinationCollection=COLLECTION, changes=[dict(source=row['source'], owned=row['owned'], collection=COLLECTION) for row in rows] + [dict(source=None, owned=JOIN, collection=COLLECTION)], pavingFaceAudit=rows, addedVertices=len(verts), addedFaces=len(faces), addedTopTriangles=sum(len(patch['triangles']) for patch in PATCHES), flushJoinAreaM2=sum(patch['derivedArea'] for patch in PATCHES), patches=PATCHES, sourceReferences=['data/collections/public-realm-2026/mapped-streets.json', 'result/blender/site_geometry.json', 'data/collections/public-realm-2026/user-references/reference-09.png', 'data/collections/streets/raw/public_realm_strategy_2022.pdf'], derivation='Existing native low Pale campus paving road polygons intersected with0.9m existing higher stone-paving boundary belt and archived mapped pedestrian centreline4m corridor, subtracting all native high paving with4mm gap and mapped building polygons with20mm buffer. Excludes Local_ground_datum, tree pools and unsupported expansion candidates.', limitations=['Only two joins need raising in inspected mapped low walking-road footprints; other candidates were ground boundaries or tree openings and were not filled.', 'Retained source widths, paver lengths and heights are estimates; not current surveyed asbuilt.', 'Paving normal correction preserves all five existing physical layouts; no new route is invented.', 'No new lake, road furniture or buildings.'])


def render_review(scene, path, location, target, scale):
    camera_data = bpy.data.cameras.new('STREET194_ReviewCamera')
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    scene.collection.objects.link(camera)
    camera.location = location
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera_data.type = 'ORTHO'
    camera_data.ortho_scale = scale
    scene.camera = camera
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera, do_unlink=True)
    bpy.data.cameras.remove(camera_data)


def build_component():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA256
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    scene = bpy.context.scene
    views = [
        ('clare-square', (29,-40,14), (24,-39,0), 10),
        ('sheffield-join', (-59,-33,16), (-54,-28,0), 13),
        ('watkins-paving', (40,-14,28), (36,-5,0), 20),
    ]
    for label, location, target, scale in views:
        render_review(scene, OUTPUT/(label+'-before.png'), location, target, scale)
    report = apply_street_connections194()
    component = OUTPUT/'street-connections194-component.blend'
    bpy.data.libraries.write(str(component), set(bpy.data.objects[name] for name in report['addedObjects']), fake_user=True, compress=True)
    report['component'] = str(component.relative_to(ROOT))
    report['componentSha256'] = hashlib.sha256(component.read_bytes()).hexdigest()
    report['baseline'] = str(SOURCE.relative_to(ROOT))
    report['baselineSha256'] = SOURCE_SHA256
    report['renderedViews'] = [label+'-'+phase+'.png' for label, *_ in views for phase in ['before','after']]
    for label, location, target, scale in views:
        render_review(scene, OUTPUT/(label+'-after.png'), location, target, scale)
    (OUTPUT/'audit.json').write_text(json.dumps(report, indent=2)+'\n')
    print('STREET194_COMPONENT', len(report['addedObjects']), report['flushJoinAreaM2'], report['addedFaces'])


if __name__ == '__main__':
    build_component()
