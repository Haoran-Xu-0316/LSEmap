"""Source-led refinements to existing LSE Square tree-pool seating.

Run this fixed file in Blender to author, reopen, then render its fixed phases.
Run it in MachineLearning Python for independent saved-mesh planar checks.
Accepted v228 is never overwritten. Source
photographs remain private evidence and are never used as surface textures.
"""
from pathlib import Path
import sys, json, hashlib
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/street-fixtures229'
DATA = ROOT / 'data/collections/street-fixtures229'
BASE = ROOT / 'result/blender/LSE_campus_detailed_v228.blend'
SHA = '0ddf5bb3791d146690d2af1f44b4cb6b113930cf687bc30d1cb916d84f4f066b'
sys.path.insert(0, str(ROOT / 'web/tools'))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

def inspect():
    import bpy
    from mathutils import Vector
    from integrate_exterior_round194 import update_scene, object_fingerprint, accepted_fingerprints
    assert digest(BASE) == SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    original = {o.name: object_fingerprint(o) for o in bpy.data.objects}
    assert original == accepted_fingerprints(ROOT / 'result/blender/stage228', SHA)
    rows = []
    for obj in bpy.data.collections['00_SITE'].all_objects:
        if obj.type != 'MESH' or obj.hide_render:
            continue
        if not any(k in obj.name.lower() for k in ['pool', 'bollard', 'bench', 'rail', 'bin', 'cycle', 'lamp']):
            continue
        points = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
        rows.append(dict(name=obj.name, low=[min(p[i] for p in points) for i in range(3)],
                         high=[max(p[i] for p in points) for i in range(3)],
                         vertices=len(obj.data.vertices), faces=len(obj.data.polygons),
                         materials=[m.name for m in obj.data.materials]))
    write('native-input.json', dict(baselineSha256=SHA, objects=len(original), materials=len(bpy.data.materials), fixtures=rows))
    print('FIXTURES229_INSPECT', json.dumps(rows), flush=True)



def render_fixture_comparison(source, obj, soil_name, original_visibility):
    import bpy
    from mathutils import Vector
    replacement_name = obj.name
    # Two useful fixed close views keep the fixture geometry readable. Preview
    # scenes link original campus objects read-only; trees are omitted from the
    # close technical crops because their existing canopy hides the stone.
    previews = []
    views = [dict(name='square-stone-joints', position=(45,-34,3.8), target=(49.5,-28.5,.26), scale=6.4),
             dict(name='square-stone-context', position=(44,-43,23), target=(38,-27,.3), scale=34)]
    from refine_street_connections194 import render_review
    scene = bpy.data.scenes.new('STREET229_REVIEW')
    for candidate in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects:
        if candidate.type != 'MESH' or candidate.hide_render: continue
        points = [candidate.matrix_world @ Vector(p) for p in candidate.bound_box]
        if min(p.x for p in points)>57 or max(p.x for p in points)<23 or min(p.y for p in points)>-17 or max(p.y for p in points)<-38:continue
        if max(p.z for p in points)>.55:continue
        if any(k in candidate.name.lower() for k in ['tree','vegetation','canop']) and candidate.name not in [replacement_name,soil_name]:continue
        scene.collection.objects.link(candidate)
    world = bpy.data.worlds.new('STREET229_REVIEW_WORLD')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.75,.79,.86,1)
    world.node_tree.nodes['Background'].inputs[1].default_value = .8
    scene.world = world
    light_data = bpy.data.lights.new('STREET229_REVIEW_SUN', 'SUN')
    light_data.energy = 2.5
    light = bpy.data.objects.new('STREET229_REVIEW_SUN', light_data)
    scene.collection.objects.link(light)
    light.rotation_euler = (.45,-.3,-.5)
    bpy.context.window.scene = scene
    scene.collection.objects.link(source)
    for phase in ['before','after']:
        source.hide_render = phase == 'after'
        obj.hide_render = phase == 'before'
        for view in views:
            path = OUT / (phase+'-'+view['name']+'.png')
            render_review(scene, path, view['position'], view['target'], view['scale'])
            previews.append(path.name)
    obj.hide_render = False
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    bpy.data.objects.remove(light, do_unlink=True)
    bpy.data.lights.remove(light_data)
    bpy.data.scenes.remove(scene)
    bpy.data.worlds.remove(world)
    source.hide_render = original_visibility
    return previews, views


def build_component():
    import bpy, bmesh, math
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    from integrate_exterior_round194 import update_scene, object_fingerprint, accepted_fingerprints
    from refine_portsmouth_exterior207 import material_fingerprint
    from build_clm_hongkong_room220 import modifier_payload
    original_name = 'SITE222_Square_six_stone_tree_pool_enclosures'
    replacement_name = 'SITE229_Square_six_jointed_stone_tree_pool_enclosures'
    assert digest(BASE) == SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    metadata = json.loads((ROOT / 'web/tools/building-metadata.json').read_text())
    rooms = {r['collection']: sorted(o.name for o in bpy.data.collections[r['collection']].all_objects) for r in metadata['spaces']}
    assert len(rooms) == 27 and len(set().union(*(set(v) for v in rooms.values()))) == 1068
    originals = {o.name: object_fingerprint(o) for o in bpy.data.objects}
    assert len(originals) == 8074 and originals == accepted_fingerprints(ROOT / 'result/blender/stage228', SHA)
    materials = {m.name: material_fingerprint(m) for m in bpy.data.materials}
    ownership = {o.name: sorted(c.name for c in o.users_collection) for o in bpy.data.objects}
    visibility = {o.name: o.hide_render for o in bpy.data.objects}
    modifiers = {o.name: hashlib.sha256(json.dumps([modifier_payload(m) for m in o.modifiers], sort_keys=True).encode()).hexdigest() for o in bpy.data.objects}
    scene_membership = {s.name: sorted(o.name for o in s.objects) for s in bpy.data.scenes}
    assert ownership[original_name] == ['00_SITE']
    source = bpy.data.objects[original_name]
    assert not source.hide_render
    plan = json.loads((ROOT / 'result/blender/street-environment222/planter-plan.json').read_text())['planters']
    vertices, faces, face_materials = [], [], []
    segments = []
    def add_prism(points, bottom, top, joint=False):
        offset = len(vertices)
        vertices.extend((x, y, z) for z in [bottom, top] for x, y in points)
        faces.extend(tuple(offset+i for i in f) for f in [(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
        face_materials.extend([0, 0 if joint else 1, 0, 0, 0, 0])
    def mix(a, b, t):
        return [a[i] * (1-t) + b[i] * t for i in range(2)]
    # The registration, envelope and estimated height of all six accepted rings
    # are retained. Only shallow module joints and cap edge breaks are authored.
    # Three divisions per existing ~3m side are a visual construction estimate,
    # not an assertion that individual source slab centres were surveyed.
    for pool in plan:
        outer, inner = pool['outer'], pool['inner']
        for side in range(4):
            nxt = (side+1) % 4
            length = math.dist(outer[side], outer[nxt])
            half_joint = .0015 / length
            for index in range(3):
                t0 = index / 3 + (half_joint if index else 0)
                t1 = (index+1) / 3 - (half_joint if index < 2 else 0)
                polygon = [mix(outer[side], outer[nxt], t0), mix(outer[side], outer[nxt], t1),
                           mix(inner[side], inner[nxt], t1), mix(inner[side], inner[nxt], t0)]
                add_prism(polygon, .04, .47)
                segments.append(dict(pool=pool['index'], side=side, module=index, footprint=polygon,
                                     supportPoint=[sum(p[0] for p in polygon)/4, sum(p[1] for p in polygon)/4],
                                     bottom=.04, top=.47))
            # Narrow recessed stone joints close every module seam. They sit
            # on the same retained foundation and stop3mm below the coping.
            for division in [1,2]:
                t0, t1 = division/3-half_joint, division/3+half_joint
                a,b = mix(outer[side],outer[nxt],t0),mix(outer[side],outer[nxt],t1)
                c,d = mix(inner[side],inner[nxt],t1),mix(inner[side],inner[nxt],t0)
                a,d = mix(a,d,.011),mix(a,d,.989)
                b,c = mix(b,c,.011),mix(b,c,.989)
                add_prism([a,b,c,d],.04,.467,joint=True)
    mesh = bpy.data.meshes.new(replacement_name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    for material in source.data.materials:
        mesh.materials.append(material)
    for face,index in zip(mesh.polygons,face_materials):
        face.material_index = index
    # A small physical arris break gives highlights without floating overlays.
    bm = bmesh.new(); bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=.002, segments=1, affect='EDGES', clamp_overlap=True)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    assert all(edge.is_manifold for edge in bm.edges)
    volume = bm.calc_volume(signed=True)
    assert volume > 0
    bm.to_mesh(mesh); bm.free(); mesh.update()
    uv = mesh.uv_layers.new(name='MetricUV')
    for face in mesh.polygons:
        for loop in face.loop_indices:
            p = mesh.vertices[mesh.loops[loop].vertex_index].co
            uv.data[loop].uv = (p.x, p.y) if abs(face.normal.z) > .5 else (p.x+p.y, p.z)
    obj = bpy.data.objects.new(replacement_name, mesh)
    bpy.data.collections['00_SITE'].objects.link(obj)
    obj['originalObject'] = original_name
    obj['destinationCollection'] = '00_SITE'
    obj['scope'] = 'Photo-supported pale stone module joints and arris breaks within six retained222 tree-pool rings. No new seat tiers or fixture locations.'
    obj['dimensionStatus'] = '3mm joints,2mm arris breaks and three divisions per side are visual estimates; source capture dates unknown.'
    update_scene()
    # Independently ray-cast the new stone feet onto the actual accepted closed
    # soil foundation. Sample each of the72 pieces, excluding bevel strips.
    soil_name = 'SITE222_Square_six_tree_pool_soil'
    soil = bpy.data.objects[soil_name]
    tree = BVHTree.FromPolygons([soil.matrix_world @ v.co for v in soil.data.vertices], [tuple(f.vertices) for f in soil.data.polygons])
    contacts = []
    for row in segments:
        x, y = row['supportPoint']
        hit = tree.ray_cast(Vector((x,y,.042)), Vector((0,0,-1)), .006)
        assert hit[0] is not None and abs(hit[0].z-.04) < .00001
        contacts.append(dict(pool=row['pool'], side=row['side'], module=row['module'], xy=[x,y], source=soil_name, foundationTop=hit[0].z, stoneFoot=.04))
    def inside(p, ring):
        return all((b[0]-a[0])*(p.y-a[1])-(b[1]-a[1])*(p.x-a[0]) >= -.00002 for a,b in zip(ring,ring[1:]+ring[:1]))
    assert all(any(inside(v.co,p['sourceHole']['coordinates'][0][:-1]) for p in plan) for v in mesh.vertices)
    bindings = [m.name for m in mesh.materials]
    new_fingerprint = object_fingerprint(obj)
    component = OUT / 'street-fixtures229-component.blend'
    bpy.data.libraries.write(str(component), {obj}, fake_user=True, compress=True)
    component_sha = digest(component)
    # Standalone component is reopened in a fresh Blender file by this same
    # process, then the accepted baseline is reopened before append verification.
    bpy.ops.wm.open_mainfile(filepath=str(component))
    standalone = bpy.data.objects[replacement_name]
    assert object_fingerprint(standalone) == new_fingerprint
    bm = bmesh.new(); bm.from_mesh(standalone.data)
    assert all(e.is_manifold for e in bm.edges)
    reopened_volume = bm.calc_volume(signed=True); bm.free()
    assert abs(reopened_volume-volume) < .000001
    bpy.ops.wm.open_mainfile(filepath=str(BASE)); update_scene()
    with bpy.data.libraries.load(str(component), link=False) as (available, loaded):
        loaded.objects = [replacement_name]
    obj = loaded.objects[0]
    for slot, name in enumerate(bindings):
        obj.data.materials[slot] = bpy.data.materials[name]
    bpy.data.collections['00_SITE'].objects.link(obj)
    update_scene()
    assert object_fingerprint(obj) == new_fingerprint
    assert all(object_fingerprint(bpy.data.objects[n]) == f for n,f in originals.items())
    assert all(material_fingerprint(bpy.data.materials[n]) == f for n,f in materials.items())
    assert all(sorted(c.name for c in bpy.data.objects[n].users_collection) == v for n,v in ownership.items())
    assert all(bpy.data.objects[n].hide_render == v for n,v in visibility.items())
    assert all(hashlib.sha256(json.dumps([modifier_payload(m) for m in bpy.data.objects[n].modifiers],sort_keys=True).encode()).hexdigest() == v for n,v in modifiers.items())
    assert all(sorted(o.name for o in bpy.data.collections[c].all_objects) == names for c,names in rooms.items())
    assert all(sorted(n for n in bpy.data.scenes[s].objects.keys() if n != replacement_name) == names for s,names in scene_membership.items())
    assert digest(BASE) == SHA and digest(component) == component_sha
    source = bpy.data.objects[original_name]
    source.hide_render = True
    previews, views = render_fixture_comparison(source,obj,soil_name,visibility[original_name])
    support = dict(actualFoundation=soil_name, actualSupportSamples=len(contacts), maximumSupportErrorM=max(abs(r['foundationTop']-r['stoneFoot']) for r in contacts), contacts=contacts,
                   feetRegisteredAtZ=.04, outerAndInnerSourceBoundsRetained=True, newFootprintOutsideOriginalHolesM2=0, newWalkingPavingOverlapM2=0,
                   noPathWidthOrPavingHeightChange=True, stepsNotAddedWithoutPerPoolRegistration=True)
    verification = dict(savedComponentIndependentlyReopened=True, appendedComponentReopened=True,
                        originalObjectsVerified=len(originals), originalMaterialsVerified=len(materials),
                        protectedSpacesVerified=len(rooms), protectedSpaceObjectsVerified=1068,
                        originalGeometryUVTransformsMaterialNodesModifiersMembershipsUnchanged=True,
                        protectedRoomSceneMembershipUnchanged=True, originalVisibilityPreserved=True,
                        sourceAndComponentSha256Rechecked=True, noFullNativeWritten=True,
                        allComponentEdgesManifold=True, closedVolumeM3=reopened_volume,
                        moduleCount=len(segments), recessedJointInfillCount=48, componentVertices=len(obj.data.vertices), componentFaces=len(obj.data.polygons), physicalChecks=support)
    source_refs = [dict(path=str((ROOT/'data/collections/street-environment222'/name).relative_to(ROOT)), sha256=digest(ROOT/'data/collections/street-environment222'/name),captureDate='unknown',
                        supports='Pale stone tree-pool edging with visible slab divisions and softened stone arrises; exact joint count and dimensions are not measured.')
                   for name in ['gillespies-square-built.jpg','gillespies-square-east.webp']]
    manifest = dict(version=229, baselineSha256=SHA, sources=source_refs,
                    existingSourceManifest='data/collections/street-environment222/sources.json',
                    rejectedScope='Stepped seating appears in the photo foreground, but exact tier geometry cannot be uniquely registered to each retained hole. No new seat tier or displaced path is fabricated.',
                    referencePolicy='Private evidence only; no source photo pixels in authored materials or exported textures.',
                    dimensions=dict(jointWidthEstimateM=.003, arrisBreakEstimateM=.002, sideModuleCountEstimate=3, retainedAbsoluteFootZ=.04, retainedAbsoluteTopZ=.47))
    (DATA/'sources.json').write_text(json.dumps(manifest,indent=2)+'\n')
    suggestions = [dict(code='CAMPUS',name='campus-square-stone-joints',label='LSE Square石材树池',
                        view=dict(position=[51,3.8,34],target=[49.5,.26,28.5],fov=43)),
                   dict(code='CAMPUS',name='campus-square-stone-context',label='LSE Square树池组',view=dict(position=[55,16,43],target=[42,.3,27],fov=43))]
    audit = dict(version=229,building='CAMPUS',baselinePath=str(BASE.relative_to(ROOT)),baselineSha256=SHA,
                 componentPath=str(component.relative_to(ROOT)),componentSha256=component_sha,destinationCollection='00_SITE',targetCollection='00_SITE',
                 addedObjects=[replacement_name],archivedObjects=[original_name],changedObjects=[],
                 addedFingerprints={replacement_name:new_fingerprint},replacementMaterialBindings={replacement_name:bindings},
                 sourceManifest=str((DATA/'sources.json').relative_to(ROOT)),verification=verification,gallerySuggestions=suggestions,previews=previews,
                 scope='Replace six continuous pale stone tree-pool rings with physically jointed stone modules and2mm arris breaks. Retain accepted six outer/inner envelopes, stone top/feet, soil, trees and all walking surfaces.',
                 limitations=['Photographs are undated, not October2026 current-condition evidence.','Three modules per side,3mm joints and2mm arris breaks are photographic construction estimates, not measured slab registration.','Actual foreground stepped seating is not extended because per-pool tier registration is unresolved.','No original asphalt or stone footprint, elevation, UV, route, building or room is modified.'])
    write('audit.json',audit);write('verification.json',verification);write('support-checks.json',support);write('view-suggestions.json',suggestions)
    print('FIXTURES229_READY',component_sha,len(obj.data.vertices),len(obj.data.polygons),len(materials),flush=True)

def render_verified_views():
    import bpy
    from mathutils import Vector
    from integrate_exterior_round194 import update_scene, object_fingerprint
    audit=json.loads((OUT/'audit.json').read_text())
    component=ROOT/audit['componentPath']
    assert digest(BASE)==SHA and digest(component)==audit['componentSha256']
    bpy.ops.wm.open_mainfile(filepath=str(BASE)); update_scene()
    replacement_name=audit['addedObjects'][0]
    original_name=audit['archivedObjects'][0]
    with bpy.data.libraries.load(str(component),link=False) as (available,loaded):loaded.objects=[replacement_name]
    obj=loaded.objects[0]
    for index,name in enumerate(audit['replacementMaterialBindings'][replacement_name]):obj.data.materials[index]=bpy.data.materials[name]
    bpy.data.collections['00_SITE'].objects.link(obj)
    assert object_fingerprint(obj)==audit['addedFingerprints'][replacement_name]
    source=bpy.data.objects[original_name]
    soil_name='SITE222_Square_six_tree_pool_soil'
    visibility={original_name:source.hide_render}
    source.hide_render=True
    previews, views = render_fixture_comparison(source,obj,soil_name,visibility[original_name])
    audit['previews']=previews
    audit['previewPolicy']='Identical before/after technical views. Existing trees and geometry above0.55m are omitted only from these unsaved preview scenes to show stone construction and retained paving.'
    audit['gallerySuggestions']=[dict(code='CAMPUS',name='campus-square-stone-joints',label='LSE Square石材树池',view=dict(position=[45,3.8,34],target=[49.5,.26,28.5],fov=43)),dict(code='CAMPUS',name='campus-square-stone-row',label='LSE Square树池组',view=dict(position=[35,2.2,32],target=[44,.25,26.5],fov=54))]
    write('audit.json',audit);write('view-suggestions.json',audit['gallerySuggestions'])
    write('preview-verification.json',dict(componentSha256=digest(component),baselineSha256=digest(BASE),identicalBeforeAfterViews=views,previews=previews,sourceAndComponentUnchanged=True))
    print('FIXTURES229_PREVIEWS_READY',flush=True)


def verify_full_campus_views():
    """Render actual campus visibility and ray-test physical stone samples."""
    import bpy,math
    from mathutils import Vector
    from integrate_exterior_round194 import update_scene,object_fingerprint
    audit=json.loads((OUT/'audit.json').read_text())
    component=ROOT/audit['componentPath']
    assert digest(BASE)==SHA and digest(component)==audit['componentSha256']
    bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
    scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
    replacement_name=audit['addedObjects'][0]
    with bpy.data.libraries.load(str(component),link=False)as(available,loaded):loaded.objects=[replacement_name]
    obj=loaded.objects[0]
    for index,name in enumerate(audit['replacementMaterialBindings'][replacement_name]):obj.data.materials[index]=bpy.data.materials[name]
    bpy.data.collections['00_SITE'].objects.link(obj)
    assert object_fingerprint(obj)==audit['addedFingerprints'][replacement_name]
    bpy.data.objects[audit['archivedObjects'][0]].hide_render=True
    obj.hide_render=False
    # ray_cast uses viewport visibility. Bring it into agreement with the same
    # accepted render visibility without hiding any active tree or building.
    for candidate in scene.objects:
        if candidate.hide_render:candidate.hide_set(True)
    obj.hide_set(False)
    update_scene()
    camera_data=bpy.data.cameras.new('STREET229_FULL_CAMPUS_CAMERA')
    camera=bpy.data.objects.new(camera_data.name,camera_data);scene.collection.objects.link(camera);scene.camera=camera
    camera_data.type='PERSP';camera_data.sensor_fit='VERTICAL';camera_data.clip_start=.05;camera_data.clip_end=500
    scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1000;scene.render.resolution_y=750;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    if hasattr(scene,'eevee')and hasattr(scene.eevee,'taa_render_samples'):scene.eevee.taa_render_samples=8
    plan=json.loads((ROOT/'result/blender/street-environment222/planter-plan.json').read_text())['planters']
    samples=[]
    for pool in plan:
        for side in range(4):
            next_side=(side+1)%4
            for fraction in [.15,.5,.85]:
                outer=Vector((*[pool['outer'][side][i]*(1-fraction)+pool['outer'][next_side][i]*fraction for i in range(2)],.47))
                inner=Vector((*[pool['inner'][side][i]*(1-fraction)+pool['inner'][next_side][i]*fraction for i in range(2)],.47))
                samples.append(dict(pool=pool['index'],side=side,position=(outer+inner)/2))
    results=[]
    for entry in audit['gallerySuggestions']:
        view=entry['view'];eye=Vector((view['position'][0],-view['position'][2],view['position'][1]));target=Vector((view['target'][0],-view['target'][2],view['target'][1]))
        camera.location=eye;camera.rotation_euler=(target-eye).to_track_quat('-Z','Y').to_euler();camera_data.lens=camera_data.sensor_height/(2*math.tan(math.radians(view['fov'])/2));scene.view_layers[0].update()
        graph=bpy.context.evaluated_depsgraph_get();rows=[]
        projection=camera.calc_matrix_camera(graph,x=1000,y=750,scale_x=1,scale_y=1)@camera.matrix_world.inverted()
        for sample in samples:
            clip=projection@Vector((*sample['position'],1))
            screen=Vector((clip.x/clip.w*.5+.5,clip.y/clip.w*.5+.5,clip.w))
            if not(0<=screen.x<=1 and 0<=screen.y<=1 and screen.z>0):continue
            direction=sample['position']-eye;hit=scene.ray_cast(graph,eye,direction.normalized(),distance=direction.length+.03)
            rows.append(dict(pool=sample['pool'],side=sample['side'],firstHit=hit[4].name if hit[0]else None,
                             visibleStone=bool(hit[0]and hit[4].name==replacement_name),screenXY=[screen.x,screen.y],
                             expectedStonePoint=list(sample['position'])))
        visible=sum(row['visibleStone']for row in rows)
        # Six short axis probes reject an eye embedded in physical geometry.
        eye_probes=[]
        for direction in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]:
            hit=scene.ray_cast(graph,eye,Vector(direction),distance=.25)
            eye_probes.append(dict(direction=direction,nearHit=hit[4].name if hit[0]else None,distance=(hit[1]-eye).length if hit[0]else None))
        assert visible>=6, (entry['name'],visible,rows)
        assert all(row['nearHit']is None for row in eye_probes),(entry['name'],eye_probes)
        path=OUT/('production-'+entry['name']+'.png');scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
        results.append(dict(name=entry['name'],view=view,preview=path.name,visibleStoneSamples=visible,inFrameStoneSamples=len(rows),
                            clearEyeRadiusM=.25,eyeProbes=eye_probes,stoneVisibilityRays=rows))
    assert digest(BASE)==SHA and digest(component)==audit['componentSha256']
    proof=dict(baselineSha256=SHA,componentSha256=audit['componentSha256'],fullNativeCampusVisibility=True,verticalFovMatchesProduction=True,
               allAcceptedTreesAndSurroundingBuildingsRetained=True,onlyListedOldCircleArchived=True,noFullNativeSaved=True,results=results)
    write('production-view-verification.json',proof)
    audit['productionViewVerification']='result/blender/street-fixtures229/production-view-verification.json'
    audit['productionPreviews']=[row['preview']for row in results]
    write('audit.json',audit)
    bpy.data.objects.remove(camera,do_unlink=True);bpy.data.cameras.remove(camera_data)
    print('FIXTURES229_FULL_CAMPUS_VIEWS',[(r['name'],r['visibleStoneSamples'])for r in results],flush=True)


def verify_saved_component():
    """Fresh-process proof and compact stored-float witness for planar QA."""
    import bpy, bmesh
    from integrate_exterior_round194 import object_fingerprint
    audit = json.loads((OUT/'audit.json').read_text())
    component = ROOT/audit['componentPath']
    assert digest(component) == audit['componentSha256'] and digest(BASE) == SHA
    bpy.ops.wm.open_mainfile(filepath=str(component))
    obj = bpy.data.objects[audit['addedObjects'][0]]
    assert object_fingerprint(obj) == audit['addedFingerprints'][obj.name]
    bm = bmesh.new(); bm.from_mesh(obj.data)
    assert all(e.is_manifold for e in bm.edges)
    volume = bm.calc_volume(signed=True)
    pending=set(bm.verts); islands=[]
    while pending:
        start=pending.pop(); group={start}; queue=[start]
        while queue:
            vertex=queue.pop()
            for edge in vertex.link_edges:
                other=edge.other_vert(vertex)
                if other in pending:
                    pending.remove(other); group.add(other); queue.append(other)
        island_faces={face for vertex in group for face in vertex.link_faces}
        signed_volume=0.0
        for face in island_faces:
            points=[vertex.co for vertex in face.verts]
            for index in range(1,len(points)-1):signed_volume+=points[0].dot(points[index].cross(points[index+1]))/6
        assert signed_volume>0 and abs(min(v.co.z for v in group)-.04)<.000001
        islands.append(dict(vertices=len(group),closedVolumeM3=signed_volume,footZ=min(v.co.z for v in group)))
    assert len(islands)==120
    bm.free()
    witness = dict(componentSha256=digest(component), vertices=[list(v.co) for v in obj.data.vertices],
                   faces=[list(f.vertices) for f in obj.data.polygons], faceNormals=[list(f.normal) for f in obj.data.polygons],
                   closedVolumeM3=volume, allEdgesManifold=True, closedSolidPieces=islands)
    write('saved-component-witness.json',witness)
    print('FIXTURES229_FRESH_PROCESS_REOPENED',len(obj.data.vertices),len(obj.data.polygons),flush=True)


def verify_planar_coverage():
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    audit = json.loads((OUT/'audit.json').read_text())
    witness = json.loads((OUT/'saved-component-witness.json').read_text())
    assert witness['componentSha256'] == audit['componentSha256'] == digest(ROOT/audit['componentPath'])
    plan = json.loads((ROOT/'result/blender/street-environment222/planter-plan.json').read_text())['planters']
    expected = unary_union([Polygon(p['outer'],[p['inner']]) for p in plan])
    holes = unary_union([Polygon(p['sourceHole']['coordinates'][0]) for p in plan])
    # Every stored face, including bevels, is projected independently; vertical
    # faces have zero area and are ignored. No extra fixture footprint is hidden
    # behind the gallery viewpoint or a nominal bounding box.
    projected, top_faces = [], []
    for face,normal in zip(witness['faces'],witness['faceNormals']):
        shape = Polygon([witness['vertices'][i][:2] for i in face])
        if shape.area > 1e-12:
            projected.append(shape.buffer(0))
            if normal[2] > .0001:top_faces.append(shape.buffer(0))
    actual = unary_union(projected)
    excess = actual.difference(expected.buffer(.00001)).area
    walking = actual.difference(holes).area
    top_union = unary_union(top_faces)
    top_overlap = sum(p.area for p in top_faces)-top_union.area
    flat_top_faces=[Polygon([witness['vertices'][i][:2] for i in face]).buffer(0) for face,normal in zip(witness['faces'],witness['faceNormals']) if normal[2]>.99999]
    coplanar_overlap=sum(p.area for p in flat_top_faces)-unary_union(flat_top_faces).area
    assert abs(coplanar_overlap)<1e-10 and abs(top_overlap)<.00002
    assert excess < 1e-10 and walking < 1e-10
    # All retained original stone has an unchanged closed soil foundation at
    # z.04. Newly authored seams are3mm wide, filled toz.467 and thus cannot
    # become holes through a walkway or expose an unsupported slab underside.
    report = dict(freshProcessComponentReopened=True,savedFloat32AllFacesProjected=True,
                  savedFootprintM2=actual.area, originalRingFootprintM2=expected.area,
                  upwardSurfaceProjectedSelfOverlapM2=top_overlap,
                  coplanarStoneAndInfillTopOverlapM2=coplanar_overlap,
                  projectedBevelNumericalToleranceM2=.00002,
                  footprintBeyondOriginalStoneAt10MicrometreToleranceM2=excess,
                  footprintBeyondOriginalTreeHolesM2=walking,
                  remainingJointAndArrisRecessAreaM2=expected.difference(actual).area,
                  jointRecessDepthEstimateM=.003, jointInfillCount=48,
                  originalWalkingSurfacesRemovedM2=0, addedPathObstructionM2=0,
                  closedManifoldComponent=True, independentlyClosedPositivePieces=len(witness['closedSolidPieces']),
                  everyStoneAndInfillFootAtFoundation=True, positiveClosedVolumeM3=witness['closedVolumeM3'],
                  originalBaselineUnchanged=digest(BASE)==SHA)
    write('saved-geometry-verification.json',report)
    audit['verification']['savedGeometryIndependentVerification']=report
    write('audit.json',audit)
    verification = json.loads((OUT/'verification.json').read_text())
    verification['savedGeometryIndependentVerification']=report
    write('verification.json',verification)
    print('FIXTURES229_PLANAR_PASS',json.dumps(report),flush=True)


if __name__ == '__main__':
    if 'bpy' not in sys.modules:
        verify_planar_coverage()
    elif (OUT/'preview-verification.json').exists() and not (OUT/'production-view-verification.json').exists():
        verify_full_campus_views()
    elif (OUT/'saved-component-witness.json').exists() and not (OUT/'preview-verification.json').exists():
        render_verified_views()
    elif (OUT/'audit.json').exists():
        verify_saved_component()
    else:
        build_component()
