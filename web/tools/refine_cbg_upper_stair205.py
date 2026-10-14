"""Complete the private registered upper CBG stair with measured mesh endpoints.

Use build_candidate() in Blender's Text Editor. Existing eight flights and all
source files remain unchanged. Only a bounded rear approach and upper switchback
are authored here; inherited elevations are design estimates, not survey facts.
"""
from pathlib import Path
import hashlib
import json
import math
import sys
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from refine_cbg_roof203 import frame, HEIGHT, END_DECK, REAR_DECK
from refine_ground_orientation199 import closed_islands, signed_volume
from refine_cbg_roof_envelope import BOX_FACES, components
from integrate_exterior_round194 import object_fingerprint

SOURCE = ROOT / 'result/blender/cbg-assembled204/cbg-assembled204-component.blend'
OUT = ROOT / 'result/blender/cbg-stair205'
PREFIX = 'CBG205_STAIR_'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_candidate():
    OUT.mkdir(parents=True, exist_ok=True)
    assembly = json.loads((SOURCE.parent / 'audit.json').read_text())
    assert digest(SOURCE) == assembly['componentSha256']
    inputs = [SOURCE, ROOT/'result/blender/cbg-roof203/cbg-roof203-component.blend',
              ROOT/'result/blender/cbg-georegistration202/rebuild-mapping.json']
    frozen = {str(p.relative_to(ROOT)): digest(p) for p in inputs}
    mapping = json.loads(inputs[-1].read_text())
    local, world = frame(mapping)
    corners = mapping['tower']['traced_roof_landmarks_local']
    fl, fr, rl, rr = [Vector(corners[n]['local']) for n in
                      ['upperStairFrontLeft','upperStairFrontRight','upperStairRearLeft','upperStairRearRight']]
    def point(u, v, z):
        p = fl.lerp(fr,u).lerp(rl.lerp(rr,u),v)
        return Vector((p.x,p.y,z))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = 'CBG205_UPPER_STAIR_PRIVATE_REVIEW'
    context = bpy.data.collections.new('CBG204_READ_ONLY_CONTEXT')
    candidate = bpy.data.collections.new('CBG205_UPPER_STAIR_COMPONENT')
    scene.collection.children.link(context)
    scene.collection.children.link(candidate)
    with bpy.data.libraries.load(str(SOURCE), link=False) as (src, dst):
        dst.objects = list(assembly['addedObjects'])
    sources = list(dst.objects)
    for obj in sources:
        context.objects.link(obj)
    bpy.context.view_layer.update()
    before = {o.name: object_fingerprint(o) for o in sources}
    remove = ['CBG203_ROOF_registered_upper_return_stair_treads',
              'CBG203_ROOF_registered_upper_return_stair_mid_landing']
    for name in remove:
        bpy.data.objects[name].hide_render = True
    lower = bpy.data.objects['CBG203_ROOF_lower_retained_CBG_D_tower_stair_landing_platforms']
    lower_groups = [[local(lower.matrix_world @ lower.data.vertices[i].co) for i in group]
                    for group in components(lower.data)]
    final_lower = max(lower_groups,key=lambda ps:max(p.z for p in ps))
    bottom = max(p.z for p in final_lower)
    floor = next(o for o in sources if o.get('originalObject','').endswith('tower_floor_plates'))
    top = max(local(floor.matrix_world @ v.co).z for v in floor.data.vertices)
    rise = (top-bottom)/28
    mid = bottom + rise*14
    wood = next(m for m in bpy.data.materials if 'oak' in m.name)
    steel = next(m for m in bpy.data.materials if 'charcoal_thermal_frames' in m.name)
    concrete = next(m for m in bpy.data.materials if 'exposed_concrete' in m.name)
    pale = next(m for m in bpy.data.materials if 'pale' in m.name)
    rows=[]
    def mesh(name, verts, faces, material, role):
        data = bpy.data.meshes.new(PREFIX+name)
        data.from_pydata([world(p) for p in verts],[],faces)
        data.materials.append(material)
        uv = data.uv_layers.new(name='SurfaceUV')
        for face in data.polygons:
            for li in face.loop_indices:
                p=verts[data.loops[li].vertex_index]
                uv.data[li].uv=(p[0],p[1])
        bm=bmesh.new();bm.from_mesh(data);bm.normal_update()
        for faces,closed in closed_islands(bm):
            assert closed,name
            if signed_volume(faces)<0:bmesh.ops.reverse_faces(bm,faces=list(faces))
        bm.to_mesh(data);bm.free();data.update()
        obj=bpy.data.objects.new(data.name,data);candidate.objects.link(obj)
        obj['destinationCollection']='CBG_PUBLIC_INTERIOR_study'
        obj['candidateScope']=role
        obj['zEvidence']='Measured saved mesh endpoints; inherited52.2m/13height remains provisional'
        rows.append(dict(target=obj.name,role=role,sourceOwners=['CBG_PUBLIC_INTERIOR_study']))
        return obj
    def prism(name, poly, z0, z1, material, role):
        n=len(poly);verts=[(p[0],p[1],z)for z in [z0,z1]for p in poly]
        faces=[tuple(reversed(range(n))),tuple(range(n,n*2))]
        faces += [(i,(i+1)%n,(i+1)%n+n,i+n)for i in range(n)]
        return mesh(name,verts,faces,material,role)
    def beam(name,a,b,width,depth,material,role):
        a,b=Vector(a),Vector(b);delta=b-a
        axis=delta.normalized()
        side=Vector((-axis.y,axis.x,0))
        if side.length<1e-8:side=Vector((1,0,0))
        side.normalize();side*=width/2
        vertical=axis.cross(side.normalized()).normalized()*depth/2
        verts=[tuple(p+s*side+t*vertical)for p in [a,b]for s,t in [(-1,-1),(1,-1),(1,1),(-1,1)]]
        return mesh(name,verts,BOX_FACES,material,role)
    tread_verts=[];tread_faces=[];walk=[]
    for flight in range(2):
        u0,u1=(.53,.95)if flight==0 else(.05,.47)
        vstart,vend=(1,.28)if flight==0 else(.28,1)
        for step in range(14):
            v0=vstart+(vend-vstart)*step/14;v1=vstart+(vend-vstart)*(step+1)/14
            z=bottom+(flight*14+step+1)*rise
            pts=[point(u,v,h)for h in [z-.12,z]for u,v in [(u0,v0),(u1,v0),(u1,v1),(u0,v1)]]
            offset=len(tread_verts);tread_verts+=pts
            tread_faces += [tuple(offset+i for i in f)for f in BOX_FACES]
            walk.append(dict(flight=flight+1,step=step+1,point=list(point((u0+u1)/2,(v0+v1)/2,z))))
        for side,u in enumerate([u0,u1]):
            beam(f'flight{flight+1}_stringer{side+1}',point(u,vstart,bottom+flight*rise*14-.19),
                 point(u,vend,bottom+(flight+1)*rise*14-.19),.09,.20,steel,'Continuous sloped stringer supporting the14treads')
            beam(f'flight{flight+1}_handrail{side+1}',point(u,vstart,bottom+flight*rise*14+1.08),
                 point(u,vend,bottom+(flight+1)*rise*14+1.08),.045,.045,steel,'Continuous handrail1.08mabove pitchline')
            for post in range(15):
                t=post/14;v=vstart+(vend-vstart)*t;z=bottom+(flight*14+post)*rise
                beam(f'flight{flight+1}_guard{side+1}_{post:02}',point(u,v,z+.02),point(u,v,z+1.06),.032,.032,pale,'Pale vertical guard at every tread edge')
    mesh('registered_switchback_28treads',tread_verts,tread_faces,wood,'Registered fourcorner footprint;28equal risers between measured adjacent saved floor levels')
    prism('registered_midlanding',[point(u,v,0)for u,v in [(0,0),(1,0),(1,.28),(0,.28)]],mid-.17,mid,concrete,'Fullwidth return landing with14risers on either side')
    # True horizontal route: existing eighth landing turns rearward into a1.25m
    # strip, then approaches registered right flight from its rear edge. Nothing
    # fills the original stair void or masks an additional unbuilt flight.
    right0,right1=point(.53,1,0),point(.95,1,0)
    y_back=max(right0.y,right1.y)+1.30
    x_turn=-9.10
    bottom_poly=[right0,right1,Vector((x_turn,right1.y,0)),Vector((x_turn,y_back,0)),Vector((right0.x,y_back,0))]
    prism('bottom_rear_approach',bottom_poly,bottom-.18,bottom,concrete,'Bounded rear L approach linking measured eighth landing to registered first flight')
    prism('bottom_existing_landing_overlap',[(-10.52,5.72),(-9.10,5.72),(-9.10,right1.y+.10),(-10.52,right1.y+.10)],bottom-.18,bottom,concrete,'1.42mwide turn tongue overlapping existing landing by0.74m')
    top0,top1=point(.05,1,0),point(.47,1,0)
    top_poly=[top0,top1,point(.47,1.24,0),point(.05,1.24,0)]
    prism('top_exit_landing',top_poly,top-.18,top,concrete,'Registered left flight discharges into upper floor via1.29mdeep landing beyond opening')
    def guard(name,a,b,z,post_spacing=.30):
        a,b=Vector(a),Vector(b);length=(b-a).length
        beam(name+'_top',(*a[:2],z+1.10),(*b[:2],z+1.10),.045,.045,steel,'Landing perimeter handrail; access edges remain open')
        count=max(1,math.ceil(length/post_spacing))
        for i in range(count+1):
            p=a.lerp(b,i/count)
            beam(name+f'_post{i:02}',(*p[:2],z+.02),(*p[:2],z+1.08),.032,.032,pale,'Landing pale vertical guard')
    for label,a,b,z in [('mid_front',point(0,0,0),point(1,0,0),mid),
                         ('mid_left',point(0,0,0),point(0,.28,0),mid),
                         ('mid_right',point(1,0,0),point(1,.28,0),mid),
                         ('bottom_rear',bottom_poly[3],bottom_poly[4],bottom),
                         ('bottom_west',bottom_poly[4],bottom_poly[0],bottom),
                         ('bottom_east',Vector((x_turn,5.72,0)),bottom_poly[3],bottom),
                         ('bottom_front',right1,Vector((-10.52,right1.y,0)),bottom),
                         ('exit_left',top0,point(.05,1.24,0),top),
                         ('exit_right',top1,point(.47,1.24,0),top)]:
        guard(label,a,b,z)
    # Batch repeated metal members into one mesh per material and function.
    # This keeps exported draw calls bounded while preserving each closed solid.
    for suffix, predicate, material, role in [
            ('paired_flight_stringers',lambda n:'_stringer' in n,steel,'Four continuous sloped structural stringers'),
            ('continuous_handrails',lambda n:'_handrail' in n or n.endswith('_top'),steel,'Flight and landing handrails with access edges open'),
            ('pale_vertical_guards',lambda n:'_guard' in n or '_post' in n,pale,'Flight and landing vertical pale guards')]:
        selected=[o for o in candidate.objects if predicate(o.name)]
        verts=[];faces=[];names={o.name for o in selected}
        for obj in selected:
            offset=len(verts)
            verts.extend(local(obj.matrix_world@v.co)for v in obj.data.vertices)
            faces.extend(tuple(offset+i for i in f.vertices)for f in obj.data.polygons)
        for obj in selected:bpy.data.objects.remove(obj,do_unlink=True)
        rows[:]=[row for row in rows if row['target'] not in names]
        mesh(suffix,verts,faces,material,role)
    # The original upper floor is cut to the full registered opening. Sample
    # clearance against every retained assembly mesh before accepting geometry.
    bpy.context.view_layer.update()
    trees=[]
    for obj in sources:
        if obj.type=='MESH'and not obj.hide_render:
            trees.append((obj.name,BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],[list(f.vertices)for f in obj.data.polygons])))
    probes=walk+[dict(flight=0,step=0,point=[-9.80,6.10,bottom]),
                 dict(flight=0,step=0,point=[-11.50,(right1.y+y_back)/2,bottom]),
                 dict(flight=3,step=0,point=list(point(.26,1.13,top)))]
    obstruction=[];headroom=[]
    for i,row in enumerate(probes):
        p=Vector(row['point']);hits=[]
        for name,tree in trees:
            hit,_,_,dist=tree.ray_cast(world((p.x,p.y,p.z+.035)),Vector((0,0,1)),2.065)
            if hit is not None:hits.append(dict(object=name,z=hit.z,clearance=hit.z-p.z))
        headroom.append(dict(sample=i,point=list(p),minimumRequired=2.10,hits=hits))
        if hits:obstruction.append(headroom[-1])
    # Endpoint support is sampled on the actual retained floor and landing,
    # independently of the authored geometry. It prevents a landing floating
    # over a trimmed floor opening from passing a simple equal-Z check.
    endpoint_support=[]
    for label,p,expected,target in [
            ('lower_turn_overlap',Vector((-9.8,6.0,bottom)),bottom,lower.name),
            ('upper_floor_overlap',point(.26,1.15,top),top,floor.name),
            ('upper_exit_floor',point(.26,1.26,top),top,floor.name)]:
        tree=next(tree for name,tree in trees if name==target)
        hit,_,_,_=tree.ray_cast(world((p.x,p.y,p.z+.10)),Vector((0,0,-1)),.4)
        assert hit is not None and abs(hit.z-expected)<.001,(label,hit,expected)
        endpoint_support.append(dict(sample=label,localXY=list(p[:2]),object=target,actualZ=hit.z,expectedZ=expected,gapMetres=abs(hit.z-expected)))
    topology=[]
    for obj in candidate.objects:
        assert all(f.area>1e-10 for f in obj.data.polygons),obj.name
        bm=bmesh.new();bm.from_mesh(obj.data);bm.normal_update()
        groups=closed_islands(bm)
        assert all(closed and signed_volume(faces)>0 for faces,closed in groups),obj.name
        topology.append(dict(object=obj.name,closedComponents=len(groups),openComponents=0,inwardComponents=0));bm.free()
    assert all(object_fingerprint(o)==before[o.name]for o in sources)
    path=OUT/'cbg-stair205-component.blend'
    added=list(candidate.objects)
    bpy.data.libraries.write(str(path),set(added),fake_user=True,compress=True)
    fingerprints={o.name:object_fingerprint(o)for o in added}
    report=dict(status='private-bounded-upper-stair-candidate',componentPath=str(path.relative_to(ROOT)),componentSha256=digest(path),
                inputHashes=frozen,removeObjects=remove,addedObjects=list(fingerprints),newGeometry=rows,topology=topology,
                measuredEndpoints=dict(lowerLandingTop=bottom,upperFloorTop=top,oldUpperBottom=END_DECK,oldUpperTop=REAR_DECK,
                                       lowerLandingBounds=[[min(p[j]for p in final_lower),max(p[j]for p in final_lower)]for j in range(3)]),
                staircase=dict(treads=28,flights=2,risersPerFlight=14,rise=rise,midLandingTop=mid,registeredCornerFootprint=[list(v)for v in [fl,fr,rr,rl]],
                               bottomApproachPolygon=[list(v[:2])for v in bottom_poly],topLandingPolygon=[list(v[:2])for v in top_poly],
                               bottomLandingMatchesExisting=True,topLandingMatchesExisting=True,retainedLowerFlightCount=8),
                headroomChecks=headroom,endpointSupportChecks=endpoint_support,obstructions=obstruction,
                limitations=['Saved-mesh elevations inherit provisional52.2m/13equalstoreys; no current measured stair survey.',
                             'Guard details and1.30mrear approach depth are modeled reconstruction dimensions, not measured plan claims.'])
    (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    # Native private review with whole assembly saved, then reopen component
    # independently and compare every authored geometry fingerprint.
    review_path=OUT/'cbg-stair205-review.blend'
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(review_path),check_existing=False)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(path),link=False)as(src,dst):dst.objects=list(fingerprints)
    for o in dst.objects:bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.update()
    assert all(object_fingerprint(o)==fingerprints[o.name]for o in dst.objects)
    # Recompute all28riser heights from the reopened saved tread solids.
    saved_treads=bpy.data.objects[PREFIX+'registered_switchback_28treads']
    saved_tops=sorted(max(local(saved_treads.matrix_world@saved_treads.data.vertices[i].co).z for i in group)
                      for group in components(saved_treads.data))
    measured_risers=[b-a for a,b in zip([bottom]+saved_tops,saved_tops)]
    assert len(saved_tops)==28 and max(abs(r-rise)for r in measured_risers)<1e-5
    for name,z in [('registered_midlanding',mid),('bottom_rear_approach',bottom),('top_exit_landing',top)]:
        obj=bpy.data.objects[PREFIX+name]
        assert abs(max(local(obj.matrix_world@v.co).z for v in obj.data.vertices)-z)<1e-5
    report['savedGeometryChecks']=dict(treadSolidCount=len(saved_tops),minimumRiser=min(measured_risers),
                                      maximumRiser=max(measured_risers),maximumRiserError=max(abs(r-rise)for r in measured_risers),
                                      lowerLandingToUpperFloorVerticalRise=top-bottom,
                                      firstStepAboveLowerLanding=saved_tops[0]-bottom,lastStepToUpperFloorGap=abs(saved_tops[-1]-top),
                                      midLandingLevelVerified=True,bottomLandingLevelVerified=True,topLandingLevelVerified=True)
    report['verification']=dict(componentReopened=True,allAddedFingerprintsMatch=True,
                                allRetainedSourceFingerprintsPreserved=True,actualEndpointSupportPass=True,inputHashesUnchanged=all(digest(ROOT/p)==sha for p,sha in frozen.items()),
                                equalRisers=True,landingLevelsMatchMeasuredEndpoints=True,headroomPass=not obstruction,
                                roofInterferencePass=not obstruction,closedOutwardGeometry=True)
    bpy.ops.wm.open_mainfile(filepath=str(review_path))
    assert all(object_fingerprint(bpy.data.objects[n])==fp for n,fp in fingerprints.items())
    scene=bpy.context.scene
    def render(name,view,focus,scale,cutaway):
        for obj in scene.objects:
            if obj.type=='MESH':
                if obj.name in remove:obj.hide_render=True
                elif cutaway and not ('stair'in obj.name.lower()):obj.hide_render=True
                elif name=='upper-stair-roof-context' and not ('stair'in obj.name.lower() or 'floor_plates'in obj.name or 'front_galleries'in obj.name):obj.hide_render=True
                else:obj.hide_render=False
        cam=bpy.data.objects.new(name,bpy.data.cameras.new(name));scene.collection.objects.link(cam)
        cam.location=world(view);cam.rotation_euler=(world(focus)-cam.location).to_track_quat('-Z','Y').to_euler()
        cam.data.type='ORTHO';cam.data.ortho_scale=scale;scene.camera=cam
        scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL'
        scene.display.shading.show_cavity=True;scene.display.shading.show_shadows=True
        scene.display.shading.background_type='WORLD'
        if scene.world is None:scene.world=bpy.data.worlds.new('CBG205_STAIR_review_background')
        scene.world.color=(.80,.82,.84)
        scene.render.resolution_x=1500;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
        scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/(name+'.png'))
        bpy.ops.render.render(write_still=True);bpy.data.objects.remove(cam,do_unlink=True)
    render('upper-stair-close',(-5,-8,52),(-12,4,46),14,True)
    render('upper-stair-rear-connection',(-4,17,51),(-12,5,46),13,True)
    render('upper-stair-roof-context',(-4,15,57),(-13,5,46),16,False)
    report['reviewPath']=str(review_path.relative_to(ROOT));report['reviewSha256']=digest(review_path)
    report['verification']['reviewReopened']=True
    (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('STAIR205_RESULT',json.dumps(dict(objects=len(added),rise=rise,obstructions=obstruction,verification=report['verification'])),flush=True)


if __name__=='__main__':
    build_candidate()
