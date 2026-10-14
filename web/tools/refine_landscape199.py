"""Soften 510 retained campus crown envelopes without adding trees.

Blender Text Editor entry point. One opaque batched replacement keeps all 522
connected crown masses, including the 12 Watkins masses authored in179.
Contours and foliage colour remain presentation estimates, not species records.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'result/blender/LSE_campus_detailed_v198.blend'
BASE_SHA = 'b45a6a433f350226beecfd201457420d86b2d253796098f86ff5417d5752b27e'
OUT = ROOT / 'result/blender/landscape199'
SOURCE = 'LANDSCAPE179_Watkins_registered_crowns'
NAME = 'LANDSCAPE199_Campus_registered_crowns'
TARGET = '03_PUBLIC_REALM'
SOURCE_URL = 'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/2022-LSE-Public-Realm-Strategy.pdf'


def fingerprint(obj):
    mesh = obj.data
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    for data, field, kind, width in ((mesh.vertices, 'co', 'f', 3), (mesh.loops, 'vertex_index', 'i', 1),
                                     (mesh.polygons, 'material_index', 'i', 1), (mesh.polygons, 'use_smooth', 'b', 1)):
        values = array.array(kind, [0]) * (len(data) * width)
        data.foreach_get(field, values); digest.update(values.tobytes())
    for layer in mesh.uv_layers:
        values = array.array('f', [0]) * (len(layer.data) * 2)
        layer.data.foreach_get('uv', values); digest.update(values.tobytes())
    return digest.hexdigest()


def connected_groups(mesh):
    adjacency = [[] for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices; adjacency[a].append(b); adjacency[b].append(a)
    groups, seen = [], set()
    for vertex in range(len(adjacency)):
        if vertex in seen: continue
        pending, group = [vertex], []
        seen.add(vertex)
        while pending:
            a = pending.pop(); group.append(a)
            for b in adjacency[a]:
                if b not in seen: seen.add(b); pending.append(b)
        groups.append(set(group))
    return groups


def protected_state(mesh, vertices):
    digest = hashlib.sha256()
    digest.update(str([(v, tuple(mesh.vertices[v].co)) for v in sorted(vertices)]).encode())
    for polygon in mesh.polygons:
        if polygon.vertices[0] not in vertices: continue
        assert all(v in vertices for v in polygon.vertices)
        record = (tuple(polygon.vertices), polygon.material_index, polygon.use_smooth,
                  [(layer.name, [tuple(layer.data[i].uv) for i in polygon.loop_indices]) for layer in mesh.uv_layers])
        digest.update(str(record).encode())
    return digest.hexdigest()


def envelope(points, indices):
    low = Vector(tuple(min(points[i][j] for i in indices) for j in range(3)))
    high = Vector(tuple(max(points[i][j] for i in indices) for j in range(3)))
    return low, high


def finish(source, name, colour):
    material = source.copy(); material.name = name
    p = material.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*colour, 1)
    p.inputs['Roughness'].default_value = .9
    p.inputs['Metallic'].default_value = 0
    p.inputs['Alpha'].default_value = 1
    p.inputs['Transmission Weight'].default_value = 0
    material.diffuse_color = (*colour, 1)
    material['webBaseColor'] = list(colour) + [1]
    material['webRoughness'] = .9; material['webMetallic'] = 0
    material['presentationEstimated'] = True; material['sourceURL'] = SOURCE_URL
    return material


def replacement(source):
    mesh = source.data
    groups = connected_groups(mesh)
    assert len(groups) == 522
    modified = [i for i, group in enumerate(groups) if len(group) == 42]
    protected = [i for i, group in enumerate(groups) if len(group) == 162]
    assert len(modified) == 510 and len(protected) == 12
    points = [v.co.copy() for v in mesh.vertices]
    bounds = [envelope(points, group) for group in groups]
    by_vertex = {v: i for i, group in enumerate(groups) for v in group}
    faces, slots, smooth = [], [], []
    uv_data = {layer.name: [] for layer in mesh.uv_layers}
    midpoint_cache = {}
    def midpoint(a, b, group):
        key = tuple(sorted((a, b)))
        if key not in midpoint_cache:
            midpoint_cache[key] = len(points); points.append((points[a] + points[b]) / 2)
            groups[group].add(midpoint_cache[key])
        return midpoint_cache[key]
    for polygon in mesh.polygons:
        group = by_vertex[polygon.vertices[0]]
        assert all(by_vertex[v] == group for v in polygon.vertices)
        source_uv = {layer.name: [Vector(layer.data[i].uv) for i in polygon.loop_indices] for layer in mesh.uv_layers}
        if group in protected:
            faces.append(tuple(polygon.vertices)); slots.append(polygon.material_index); smooth.append(polygon.use_smooth)
            for label, uvs in source_uv.items(): uv_data[label].extend(uvs)
            continue
        assert len(polygon.vertices) == 3
        a, b, c = polygon.vertices
        ab, bc, ca = midpoint(a, b, group), midpoint(b, c, group), midpoint(c, a, group)
        faces.extend(((a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)))
        # Two subdued opaque finishes shared by every tree; no per-leaf patches.
        slot = 3 + (1 if math.sin(group * 1.73 + .4) > .1 else 0)
        slots.extend([slot] * 4); smooth.extend([True] * 4)
        for label, uvs in source_uv.items():
            ua, ub, uc = uvs; uab, ubc, uca = (ua+ub)/2, (ub+uc)/2, (uc+ua)/2
            uv_data[label].extend((ua, uab, uca, uab, ub, ubc, uca, ubc, uc, uab, ubc, uca))
    for index in modified:
        group = groups[index]; low, high = bounds[index]
        centre, radius = (low + high) / 2, (high - low) / 2
        seed = index * 2.3999632297
        for vertex in group:
            q = Vector(tuple((points[vertex][j] - centre[j]) / radius[j] for j in range(3)))
            q.normalize()
            # Even directional field keeps antipodal balance and the crown centre.
            factor = 1 + .115 * math.sin(5*q.x*q.y + seed) + .065 * math.cos(7*q.y*q.z-seed*.73) + .045 * math.sin(8*q.z*q.x+seed*.31)
            points[vertex] = centre + Vector(tuple(q[j]*radius[j]*factor for j in range(3)))
        actual_low, actual_high = envelope(points, group)
        for vertex in group:
            points[vertex] = Vector(tuple(low[j]+(points[vertex][j]-actual_low[j])/(actual_high[j]-actual_low[j])*(high[j]-low[j]) for j in range(3)))
    data = bpy.data.meshes.new(NAME + '_mesh'); data.from_pydata(points, [], faces); data.update()
    for material in mesh.materials: data.materials.append(material)
    for name, colour in [('LANDSCAPE199_foliage_deep', (.115, .205, .074)), ('LANDSCAPE199_foliage_soft', (.145, .235, .091))]:
        data.materials.append(finish(mesh.materials[0], name, colour))
    for polygon, slot, shade in zip(data.polygons, slots, smooth): polygon.material_index=slot; polygon.use_smooth=shade
    for label, values in uv_data.items():
        layer = data.uv_layers.new(name=label)
        for dst, uv in zip(layer.data, values): dst.uv = uv
    obj = source.copy(); obj.data = data; obj.name = NAME
    bpy.data.collections[TARGET].objects.link(obj)
    obj['originalObject'] = SOURCE
    # Deliberately no webGeometrySource alias: this replacement changes geometry.
    if 'webGeometrySource' in obj: del obj['webGeometrySource']
    obj['presentationEstimated'] = True
    obj['scope'] = '510 existing crown envelopes softened; 12 Watkins crowns and all Houghton crowns retained'
    obj['sourceURL'] = SOURCE_URL
    new_groups = connected_groups(data)
    assert len(new_groups) == 522 and all(len(group) == 162 for group in new_groups)
    checks=[]
    for index, group in enumerate(groups):
        low, high = bounds[index]; current_low, current_high = envelope(points, group)
        delta = max(abs(a-b) for original,current in ((low,current_low),(high,current_high)) for a,b in zip(original,current))
        assert delta < .00002
        mean = Vector(tuple(math.fsum(points[v][j] for v in group) / len(group) for j in range(3)))
        if index in modified: assert (mean - (low+high)/2).length < .00005, (index, list(mean), list((low+high)/2))
        checks.append(dict(group=index,modified=index in modified,low=list(low),high=list(high),maxEnvelopeError=delta))
    for index in protected:
        assert all(points[v] == mesh.vertices[v].co for v in groups[index])
    return obj, checks


def preview(phase, only=None):
    scene = bpy.data.scenes.new('LANDSCAPE199_preview_' + phase)
    collection = bpy.data.collections.new(scene.name + '_objects'); scene.collection.children.link(collection)
    for obj in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects:
        if obj.type in {'MESH','FONT','CURVE'} and not obj.hide_render: collection.objects.link(obj)
    world = bpy.data.worlds.new(scene.name+'_world'); world.use_nodes=True
    env=world.node_tree.nodes.new('ShaderNodeTexEnvironment')
    env.image=bpy.data.images.load(str(ROOT/'web/public/environment/kloppenheim-daylight-1k.hdr'),check_existing=True)
    world.node_tree.links.new(env.outputs['Color'],world.node_tree.nodes['Background'].inputs[0])
    world.node_tree.nodes['Background'].inputs[1].default_value=.65;scene.world=world
    light=bpy.data.lights.new(scene.name+'_sun','SUN');light.energy=1.8;light.angle=.1
    sun=bpy.data.objects.new(light.name,light);collection.objects.link(sun)
    sun.rotation_euler=Vector((-.6,.5,-1)).to_track_quat('-Z','Y').to_euler()
    camera_data=bpy.data.cameras.new(scene.name+'_camera');camera=bpy.data.objects.new(camera_data.name,camera_data)
    collection.objects.link(camera);scene.camera=camera
    scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.use_denoising=True
    scene.render.resolution_x=1280;scene.render.resolution_y=900;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
    views={'whole':(Vector((0,25,0)),Vector((340,-410,360)),540),
           'street':(Vector((-75,165,7)),Vector((-45,135,2.2)),180)}
    camera_data.type='ORTHO'
    for name,(target,location,scale)in views.items():
        if only and name not in only: continue
        camera_data.type = 'PERSP' if name == 'street' else 'ORTHO'
        camera_data.lens = 30
        camera.location=location;camera.rotation_euler=(target-location).to_track_quat('-Z','Y').to_euler();camera_data.ortho_scale=scale
        scene.render.filepath=str(OUT/(phase+'-'+name+'.png'))
        bpy.ops.render.render(write_still=True,scene=scene.name)
    bpy.data.scenes.remove(scene);bpy.data.collections.remove(collection)


def build_component():
    OUT.mkdir(parents=True,exist_ok=True)
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:layer.update()
    source=bpy.data.objects[SOURCE]
    source_state=fingerprint(source)
    protected_ids=set().union(*(g for g in connected_groups(source.data) if len(g)==162))
    protected_digest=protected_state(source.data,protected_ids)
    houghton=bpy.data.objects['LANDSCAPE179_Houghton_planter_crowns'];houghton_state=fingerprint(houghton)
    assert not source.hide_render
    preview('before')
    obj,checks=replacement(source)
    assert protected_state(obj.data,protected_ids)==protected_digest
    source.hide_render=True;source.hide_set(True);obj.hide_render=False;obj.hide_set(False)
    assert fingerprint(source)==source_state and fingerprint(houghton)==houghton_state
    before_triangles=sum(len(p.vertices)-2 for p in source.data.polygons)
    after_triangles=sum(len(p.vertices)-2 for p in obj.data.polygons)
    assert after_triangles-before_triangles<=200000
    preview('after')
    path=OUT/'landscape199-component.blend'
    bpy.data.libraries.write(str(path),{obj},fake_user=True)
    state=fingerprint(obj)
    report=dict(version=199,baseline=str(BASE.relative_to(ROOT)),baselineSha256=BASE_SHA,
                componentPath=str(path.relative_to(ROOT)),componentSha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                targetCollection=TARGET,addedObjects=[NAME],archivedObjects=[SOURCE],changedObjects=[],
                replacements=[dict(originalObject=SOURCE,original=SOURCE,replacement=NAME,targetCollection=TARGET)],
                scope='510 of522 retained crown masses refined across the campus surroundings; no new trees or positions',
                references=[dict(url=SOURCE_URL,path='data/collections/streets/derived/review_public_realm_pdf_page75.png',date='2022 report; historical photograph',supports='Broad planted street character only; no species or surveyed canopy dimensions inferred')],
                performance=dict(verticesBefore=len(source.data.vertices),verticesAfter=len(obj.data.vertices),trianglesBefore=before_triangles,trianglesAfter=after_triangles,addedTriangles=after_triangles-before_triangles,objectsBefore=1,objectsAfter=1,nonEmptyMaterialPrimitivesBefore=3,nonEmptyMaterialPrimitivesAfter=4,newTextures=0,alphaCards=0,animations=0),
                crownEnvelopeChecks=checks,protectedWatkinsMasses=12,protectedHoughtonObject=houghton.name,
                previews=['before-whole.png','after-whole.png','before-street.png','after-street.png'],
                previewLighting='Identical HDR, sun1.8, AgX,8Cycles samples',
                limitations=['Estimated foliage masses and colour, not species identification or a2026 condition survey.','Tree locations, crown width, depth, height, centre, trunk meshes and12 refinedWatkins masses are retained.','No individual branches or leaves; opaque low-cost continuous geometry intentionally avoids alpha overdraw.'])
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(path))
    obj=bpy.data.objects[NAME]
    assert fingerprint(obj)==state and len(connected_groups(obj.data))==522
    assert all(m.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value==1 for m in obj.data.materials)
    report['verification']=dict(savedComponentReopened=True,baselineUnchanged=hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA,sourceMeshUnmodified=True,houghtonUnmodified=True,all522EnvelopeAndCentreChecksPassed=True,all12WatkinsMassesUnmodified=True,componentState=state,protectedGeometryNormalsMaterialIndicesAndUVSha256=protected_digest)
    (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('LANDSCAPE199_COMPONENT_READY',report['performance'],flush=True)


if __name__=='__main__':
    build_component()
