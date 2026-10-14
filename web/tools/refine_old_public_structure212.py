"""Inspect shared Old Building public circulation; does not modify the baseline."""
from pathlib import Path
import hashlib
import json
import bpy
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'result/blender/LSE_campus_detailed_v211.blend'
OUT = ROOT/'result/blender/old-public212'
BASE_SHA = '630ebd5e999685f8d646a2613774bc925dabe6f62f5c23404882703ed8a96eca'

def inspect():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    rows=[]
    for c in bpy.data.collections:
        if c.name.startswith('OLD'):
            objects=[]
            for o in c.objects:
                if o.type != 'MESH':continue
                v=[o.matrix_world @ Vector(b) for b in o.bound_box]
                objects.append(dict(name=o.name,visible=not o.hide_render,bounds=[[min(p[i] for p in v) for i in range(3)],[max(p[i] for p in v) for i in range(3)]],materials=[m.name for m in o.data.materials if m],matrix=[list(r) for r in o.matrix_world],properties={k:str(o[k]) for k in o.keys()}))
            rows.append(dict(collection=c.name,children=[x.name for x in c.children],objects=objects))
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'native-inventory.json').write_text(json.dumps(rows,indent=2)+'\n')
    print('OLD_PUBLIC212_INVENTORY',[(r['collection'],len(r['objects'])) for r in rows])



def audit_circulation():
    """Measure the already registered public entrance, retaining all data blocks."""
    import sys
    from mathutils.bvhtree import BVHTree
    sys.path.insert(0,str(ROOT/'web/tools'))
    from refine_old_foyer174 import entrance_frame
    from integrate_exterior_round194 import object_fingerprint
    from refine_col_exterior195 import state
    scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
    bpy.context.window.scene=scene
    bpy.context.view_layer.update()
    fingerprints={o.name:object_fingerprint(o) for o in bpy.data.objects}
    origin,right,outward,scale=entrance_frame()
    inward=-outward
    frame=bpy.data.objects['OLD174_foyer_upper_dark_wood_floor'].matrix_world
    inv=frame.inverted()
    foyer=bpy.data.collections['OLD_MAIN_FOYER174']
    exterior=bpy.data.collections['OLD_EXTERIOR']
    active=[o for o in exterior.all_objects if o.type=='MESH' and not o.hide_render]
    trees={o.name:BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[list(p.vertices) for p in o.data.polygons]) for o in active}
    floors=['OLD196_FOYER_lower_limestone_floor','OLD174_foyer_four_solid_risers','OLD174_foyer_upper_dark_wood_floor']
    paths=[]
    for plan_y in [810,790,760,710,685,680,670,655,643,600,550,490,480,470,450,420,390]:
        local_y=(814-plan_y)*scale
        p=frame@Vector((0,local_y,3))
        hits=[]
        for name in floors:
            hit=trees[name].ray_cast(p,Vector((0,0,-1)),4)
            if hit[0] is not None:hits.append((hit[0].z,name))
        z,name=max(hits) if hits else (None,None)
        obstructions=[]
        if z is not None:
            # Vertical torso interval; floors beneath the feet are excluded.
            start=frame@Vector((0,local_y,z+.25))
            for n,t in trees.items():
                if n in floors or any(k in n.lower() for k in ['glass','glazing','mat','light','rail','guard','display','monitor','counter','bench']):continue
                hit=t.ray_cast(start,Vector((0,0,1)),1.35)
                if hit[0] is not None:obstructions.append(dict(object=n,z=hit[0].z))
        paths.append(dict(planPixel=[762,plan_y],localXY=[0,local_y],floorZ=z,floorObject=name,torsoVerticalIntersections=obstructions))
    doorway=[]
    for x in [-.75,0,.75]:
        p=frame@Vector((x,0,1.6))
        hits=[]
        for n,t in trees.items():
            if n.startswith('OLD174_foyer') or n.startswith('OLD196_FOYER') or any(k in n.lower() for k in ['glass','glazing','door','steel','handle']):continue
            hit=t.ray_cast(p+outward*.3,inward,.6)
            if hit[0] is not None:hits.append(n)
        doorway.append(dict(localX=x,height=1.6,opaqueBlockingObjects=hits))
    studies=[]
    for n in ['OLD_PUBLIC_INTERIOR_study','OLD321_ROOM200_study','OLD_SSC_ROOM_study']:
        c=bpy.data.collections[n]
        pts=[o.matrix_world@Vector(b) for o in c.all_objects if o.type=='MESH' for b in o.bound_box]
        studies.append(dict(collection=n,meshCount=sum(o.type=='MESH' for o in c.all_objects),bounds=[[min(v[i] for v in pts) for i in range(3)],[max(v[i] for v in pts) for i in range(3)]],registeredToWholeBuilding=False))
    assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items())
    audit=dict(version=212,kind='read-only-public-structure-audit',baselinePath=str(BASE.relative_to(ROOT)),baselineSha256=BASE_SHA,
        componentPath=None,componentSha256=None,addedObjects=[],archivedObjects=[],targetCollection='OLD_MAIN_FOYER174',destinationCollection='OLD_MAIN_FOYER174',
        result='No component generated: no demonstrated existing-geometry registration defect can be corrected from the available evidence.',
        sourceURL='https://www.designengine.co.uk/projects/reception-london-school-of-economics/',sourcePeriod='2011 built refurbishment',sourceReverified='2026-10-15',current2026ConditionVerified=False,
        archivedPlan='result/blender/old_foyer173/reception8.jpg',archivedPhotograph='result/blender/old_foyer173/reception-main.jpg',
        frame=dict(origin=list(origin),right=list(right),inward=list(inward),metresPerPlanPixel=scale,doorCentrePlanPixel=[762,814]),
        representedPlanArea=dict(lowerVestibulePixels=[[550,685],[953,786]],centralUpperPixels=[[692,488],[833,643]],doorRegistration='Existing historical plan scaled from the accepted entrance width, not an independently surveyed scale.'),
        circulationSamples=paths,doorwayOpaqueSamples=doorway,independentStudies=studies,
        unresolved=[dict(id='OLD-PUBLIC-CROSS-CORRIDOR',locationPlanPixels=[[550,375],[1125,465]],issue='Cross-corridor, side doors and north continuation appear in the historical architect plan but are outside the represented floor. Dashed plan features and transitions need section/level evidence before constructing a walkable flat continuation.'),
                    dict(id='OLD-PUBLIC-LIFT-POCKETS',locationPlanPixels=[[605,488],[690,600],[834,488],[899,642]],issue='Two lift pockets and adjacent side stairs are absent. Shaft/stair heights, rise counts and higher-floor endpoints are not verified.'),
                    dict(id='OLD-PUBLIC-STOREY-NETWORK',issue='No continuous public floor/stair graph exists beyond the registered entrance strip. Three independent room studies do not establish complete storey geometry or registration.'),
                    dict(id='OLD-FINANCE-STAIRCASE',issue='Official2016 source establishes a staff-office link between3rd, mezzanine3 and4th floor on the north side, but not coordinates or a public entrance connection. It cannot safely be used to invent a lobby staircase.')],
        preserved=dict(originalObjects=len(fingerprints),allOriginalObjectFingerprintsUnchanged=True,allOriginalMaterialAndUVStatesUnchanged=True,baselineFileUnchanged=hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA),
        fingerprints={n:fingerprints[n] for n in [o.name for o in foyer.all_objects]},materialAndUVStates={o.name:state(o) for o in foyer.all_objects if o.type=='MESH'})
    (OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print('OLD_PUBLIC212_AUDIT',json.dumps(dict(paths=paths,doorway=doorway)))




def build_historical_continuation():
    """Extend only the architect-plan public T junction, leaving shafts unbuilt."""
    import sys
    sys.path.insert(0,str(ROOT/'web/tools'))
    from build_room_samples167 import RoomGeometry
    from integrate_exterior_round194 import object_fingerprint
    from refine_col_exterior195 import state
    scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
    foyer=bpy.data.collections['OLD_MAIN_FOYER174']
    old_floor=bpy.data.objects['OLD174_foyer_upper_dark_wood_floor']
    frame=old_floor.matrix_world.copy()
    audit=json.loads((OUT/'audit.json').read_text())
    scale=audit['frame']['metresPerPlanPixel']
    fingerprints={o.name:object_fingerprint(o) for o in bpy.data.objects}
    original_names=set(fingerprints)
    def material_snapshot():
        def value(v):
            if isinstance(v,(str,int,float,bool)) or v is None:return v
            try:return list(v)
            except TypeError:return str(v)
        return {m.name:hashlib.sha256(json.dumps(dict(diffuse=list(m.diffuse_color),roughness=m.roughness,metallic=m.metallic,nodes=[dict(type=n.bl_idname,name=n.name,inputs=[(i.name,value(i.default_value)) for i in n.inputs if hasattr(i,'default_value')]) for n in m.node_tree.nodes] if m.node_tree else [],links=[(l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name) for l in m.node_tree.links] if m.node_tree else []),sort_keys=True).encode()).hexdigest() for m in bpy.data.materials}
    material_before=material_snapshot()
    visibility={o.name:(o.hide_render,o.hide_viewport,o.hide_get()) for o in bpy.data.objects}
    collection=bpy.data.collections.new('OLD_PUBLIC212_COMPONENT');scene.collection.children.link(collection)
    g=RoomGeometry(collection,'OLD_PUBLIC212_')
    g.materials['dark']=old_floor.data.materials[0].copy();g.materials['dark'].name='OLD_PUBLIC212_historical_corridor_floor_material'
    source_wall=bpy.data.objects['OLD174_foyer_upper_corridor_walls']
    g.materials['wall']=source_wall.data.materials[0].copy();g.materials['wall'].name='OLD_PUBLIC212_historical_corridor_wall_material'
    def p(x,y):return ((x-762)*scale,(814-y)*scale)
    # Deliberately stop within the open public corridor, before the angled west
    # route and the north branch; neither unverified terminal is closed off.
    outline=[p(x,y) for x,y in [(650,375),(1114,375),(1114,455),(833,455),(833,488),(692,488),(692,455),(650,455)]]
    g.prism('historical_public_T_corridor_floor','dark',outline,1.105,.14)
    # The long solid north wall between two door pairs is unambiguous in plan.
    # Clear door gaps at x593..646 and x871..924 remain fully open.
    for xa,xb in [(650,871),(924,972)]:
        x0,y=p(xa,375);x1,_=p(xb,375)
        g.box('historical_cross_corridor_north_wall','wall',((x0+x1)/2,y,2.745),(x1-x0,.16,3.0))
    # Existing central wall strips end at y488. Carry their proven direction to
    # the public cross-corridor only, without constructing adjoining rooms.
    for px in [692,833]:
        x,y0=p(px,488);_,y1=p(px,465)
        g.box('historical_central_throat_wall','wall',(x,(y0+y1)/2,2.745),(.16,y1-y0,3.0))
    added={o.name:o for o in g.finish()}
    for o in added.values():
        o.matrix_world=frame
        o['referencePeriod']='2011 architect plan; current2026layout unverified'
        o['sourceURL']=audit['sourceURL']
        o['dimensionBasis']='Existing door-based plan scale retained; floor continuation level and3m wall height estimated'
        o['scope']='Partial connected historical G-floor public corridor. No side rooms, lifts, stairs or complete-storey claim.'
    bpy.context.view_layer.update()
    # Floors meet at y488 with identical elevation and no positive overlap.
    floor=added['OLD_PUBLIC212_historical_public_T_corridor_floor']
    top=max(v.co.z for v in floor.data.vertices)
    old_top=max(v.co.z for v in old_floor.data.vertices)
    assert abs(top-old_top)<1e-6
    seam_y=p(762,488)[1]
    assert abs(min(v.co.y for v in floor.data.vertices)-max(v.co.y for v in old_floor.data.vertices))<1e-6
    # Mesh/UV/material states are compared before preview mutations.
    assert all(object_fingerprint(bpy.data.objects[n])==value for n,value in fingerprints.items())
    from mathutils.bvhtree import BVHTree
    def tree(o):return BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[list(f.vertices) for f in o.data.polygons])
    trees={n:tree(o) for n,o in added.items()}
    support=[]
    for x,y in [(762,480),(762,465),(762,440),(762,390),(670,420),(850,420),(1000,420),(1090,420)]:
        xx,yy=p(x,y);hit=trees[floor.name].ray_cast(frame@Vector((xx,yy,2)),Vector((0,0,-1)),2)
        assert hit[0] is not None
        support.append(dict(planPixel=[x,y],floorZ=hit[0].z))
    collision=[]
    for o in bpy.data.collections['OLD_EXTERIOR'].all_objects:
        if o.name in added or o.type!='MESH' or o.hide_render:continue
        # The original connection floor/walls intentionally meet at a common
        # edge. Floor top support does not claim global navigation compliance.
        if o.name.startswith(('OLD174_foyer','OLD196_FOYER')):continue
        hits=trees[floor.name].overlap(tree(o))
        if hits:
            segments=[]
            for face_id in sorted({b for a,b in hits}):
                poly=o.data.polygons[face_id]
                vertices=[frame.inverted()@(o.matrix_world@o.data.vertices[i].co) for i in poly.vertices]
                cuts=[]
                for a,b in zip(vertices,vertices[1:]+vertices[:1]):
                    if (a.z-top)*(b.z-top)<=0 and abs(b.z-a.z)>1e-8:
                        q=a+(b-a)*((top-a.z)/(b.z-a.z))
                        cuts.append([q.x/scale+762,814-q.y/scale])
                if len(cuts)>=2:segments.append(cuts)
            collision.append(dict(object=o.name,trianglePairs=len(hits),horizontalPlaneIntersectionPlanPixels=segments))
    # Same-view, same-light review of the actual registered foyer plus new route.
    originals={o.name for o in foyer.all_objects if not o.hide_render}
    for o in scene.objects:
        if o.type in {'MESH','FONT','CURVE'}:o.hide_render=o.name not in originals|set(added)
        if o.type=='LIGHT':o.hide_render=True
    cam=bpy.data.objects.new('OLD_PUBLIC212_preview_camera',bpy.data.cameras.new('OLD_PUBLIC212_preview_camera'));scene.collection.objects.link(cam)
    cam.data.type='ORTHO';cam.data.ortho_scale=35
    cam.location=frame@Vector((17,-17,28));target=frame@Vector((0,10,1.4));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();scene.camera=cam
    world=bpy.data.worlds.new('OLD_PUBLIC212_preview_world');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.78,.82,.87,1);world.node_tree.nodes['Background'].inputs[1].default_value=.65;scene.world=world
    ld=bpy.data.lights.new('OLD_PUBLIC212_preview_sun','SUN');ld.energy=2;light=bpy.data.objects.new(ld.name,ld);scene.collection.objects.link(light);light.rotation_euler=Vector((-.6,.5,-1)).to_track_quat('-Z','Y').to_euler()
    scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True;scene.render.resolution_x=1300;scene.render.resolution_y=950;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
    for phase in ['before','after']:
        for o in added.values():o.hide_render=phase=='before'
        scene.render.filepath=str(OUT/('before.png' if phase=='before' else 'candidate-rejected.png' if collision else 'after.png'));bpy.ops.render.render(write_still=True)
    for n,values in visibility.items():
        o=bpy.data.objects[n];o.hide_render,o.hide_viewport=values[:2];o.hide_set(values[2])
    for o in added.values():o.hide_render=False;o.hide_viewport=False;o.hide_set(False)
    assert all(object_fingerprint(bpy.data.objects[n])==value for n,value in fingerprints.items())
    if collision:
        audit.update(kind='rejected-registration-audit',result='No component generated. Extending the2011architect T corridor using the existing door-based registration intersects accepted exterior fabric.',rejectedCandidate=dict(objects=list(added),exteriorIntersections=collision,expectedFloorAreaSquareMetres=(464*80+141*33)*scale*scale,floorSeamMatched=True,supportSamples=support),addedObjects=[],archivedObjects=[],componentPath=None,componentSha256=None,nextEvidenceNeeded=['A measured G-floor plan tied to Houghton/Clare elevations or at least three non-collinear plan-to-building control points.','An independently confirmed entrance plan scale: the current width-based registration is not validated across the building footprint.','Ground-floor sections or spot levels at foyer, side lift landings and cross corridor.','Current2025as-built lift/stair plans before extending beyond the historical2011entrance region.'],sameLightReview=dict(before='result/blender/old-public212/before.png',rejectedCandidate='result/blender/old-public212/candidate-rejected.png'),baselineUnchanged=hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA,originalFingerprintsVerified=len(fingerprints))
        (OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
        (OUT/'verification.json').write_text(json.dumps(dict(noComponentGenerated=True,rejectedForExteriorIntersections=True,baselineFileUnchanged=True,originalObjectFingerprintsPreserved=len(fingerprints),floorSupportSamples=len(support),sameLightDiagnosticViews=True),indent=2)+'\n')
        print('OLD_PUBLIC212_CANDIDATE_REJECTED',json.dumps(collision),flush=True)
        return
    material_after=material_snapshot()
    assert all(material_after[n]==v for n,v in material_before.items())
    component=OUT/'old-public212-component.blend' 
    bpy.data.libraries.write(str(component),set(added.values()),fake_user=True,compress=True)
    audit['excludedWestBranch']=audit.get('rejectedCandidate',{})
    audit.pop('rejectedCandidate',None)
    audit.pop('sameLightReview',None)
    audit.update(kind='bounded-historical-public-structure-component',result='Connected the registered foyer to the historical public T corridor shown in the same architect plan. This remains a partial historical ground-floor structure.',componentPath=str(component.relative_to(ROOT)),componentSha256=hashlib.sha256(component.read_bytes()).hexdigest(),addedObjects=list(added),archivedObjects=[],supportSamples=support,exteriorFloorIntersectionPairs=collision,seam=dict(planY=488,worldFloorZ=old_top,positionMismatchMetres=0),addedFingerprints={n:object_fingerprint(o) for n,o in added.items()},addedStates={n:state(o) for n,o in added.items()},floorAreaSquareMetres=(464*80+141*33)*scale*scale,originalMaterialFingerprints=material_before,scope='Historical central throat and bounded eastern cross-corridor walking surface, plus four plan-visible wall sections. Side lifts, side stairs, rooms and remaining building floors stay unresolved.',assumptions=['Plan scaled using the existing registered door width, not a surveyed architectural scale.','Onward corridor continues at existing upper G-floor level1.245m. No section drawing independently confirms this level.','Wall heights3m and thickness0.16m inherited as estimates.','West limit x650 stops before the source-to-native registration conflict atx615-639; it is an open cutaway, not a terminal wall. East end also remains a cutaway.'])
    audit['unresolved'][0]['issue']='Only the bounded public T corridor is represented. Angled west route, east route, northern return and all connected rooms remain outside this component; complete building registration still requires measured full-storey plans/sections.'
    audit['fingerprints']=audit['addedFingerprints']
    audit['source']=audit['sourceURL']
    audit['referencePeriod']='2011 architect plan; current2026condition unverified'
    (OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    expected=audit['addedFingerprints'];bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(component),link=False) as (available,target):target.objects=list(added)
    for o in target.objects:bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.update()
    for o in target.objects:assert object_fingerprint(o)==expected[o.name],o.name
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA
    (OUT/'verification.json').write_text(json.dumps(dict(componentReopened=True,addedObjectFingerprintsVerified=len(added),originalObjectFingerprintsPreserved=len(original_names),baselineUnchanged=True,exteriorIntersectionPairs=0,floorSupportSamples=len(support),doorwayExistingOpaqueBlockers=0,sameLightBeforeAfter=True,originalMaterialFingerprintsPreserved=len(material_before)),indent=2)+'\n')
    print('OLD_PUBLIC212_COMPONENT_VERIFIED',len(added))



def verify_complete_component_against_exterior():
    """Reopen the bounded component and check all its meshes against fabric."""
    from mathutils.bvhtree import BVHTree
    audit=json.loads((OUT/'audit.json').read_text())
    component=ROOT/audit['componentPath']
    assert hashlib.sha256(component.read_bytes()).hexdigest()==audit['componentSha256']
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
    with bpy.data.libraries.load(str(component),link=False) as (available,target):target.objects=list(audit['addedObjects'])
    for o in target.objects:scene.collection.objects.link(o)
    bpy.context.view_layer.update()
    def tree(o):return BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[list(f.vertices) for f in o.data.polygons])
    additions={o.name:tree(o) for o in target.objects}
    collisions=[]
    for o in bpy.data.collections['OLD_EXTERIOR'].all_objects:
        if o.type!='MESH' or o.hide_render or o.name.startswith(('OLD174_foyer','OLD196_FOYER')):continue
        fabric=tree(o)
        for name,candidate in additions.items():
            pairs=candidate.overlap(fabric)
            if pairs:collisions.append(dict(addedObject=name,exteriorObject=o.name,trianglePairs=len(pairs)))
    assert not collisions,collisions
    verification=json.loads((OUT/'verification.json').read_text())
    verification.update(allAddedMeshesExteriorCollisionPairs=0,componentReopenedForFabricCheck=True)
    (OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
    audit['allAddedMeshesExteriorCollisionPairs']=[]
    (OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print('OLD_PUBLIC212_ALL_MESH_FABRIC_CHECK',len(additions),flush=True)

if __name__=='__main__':
    inspect()
    if not (OUT/'audit.json').exists():audit_circulation()
    build_historical_continuation()
    if json.loads((OUT/'audit.json').read_text()).get('componentPath'):
        verify_complete_component_against_exterior()


def isolate_component_materials():
    """Make the delivered material names independent of integration suffixes."""
    import sys
    sys.path.insert(0,str(ROOT/'web/tools'))
    from integrate_exterior_round194 import object_fingerprint
    audit=json.loads((OUT/'audit.json').read_text())
    component=ROOT/audit['componentPath']
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(component),link=False) as (available,target):target.objects=list(audit['addedObjects'])
    material_cache={}
    for obj in target.objects:
        bpy.context.scene.collection.objects.link(obj)
        for index,original in enumerate(obj.data.materials):
            if original.name not in material_cache:
                material=original.copy();material.name='OLD_PUBLIC212_historical_corridor_'+('floor' if 'floor' in obj.name else 'wall')+'_material';material_cache[original.name]=material
            obj.data.materials[index]=material_cache[original.name]
    bpy.context.view_layer.update()
    audit['addedFingerprints']={o.name:object_fingerprint(o) for o in target.objects}
    audit['fingerprints']=audit['addedFingerprints']
    bpy.data.libraries.write(str(component),set(target.objects),fake_user=True,compress=True)
    audit['componentSha256']=hashlib.sha256(component.read_bytes()).hexdigest()
    (OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(component),link=False) as (available,target):target.objects=list(audit['addedObjects'])
    for o in target.objects:bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.update()
    for o in target.objects:assert object_fingerprint(o)==audit['fingerprints'][o.name]
    verification=json.loads((OUT/'verification.json').read_text());verification['standalonePrefixOwnedMaterials']=len(material_cache)
    (OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
    print('OLD_PUBLIC212_PREFIX_MATERIALS_VERIFIED',len(material_cache),flush=True)
