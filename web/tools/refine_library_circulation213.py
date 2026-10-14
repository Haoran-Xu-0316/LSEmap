"""Open the inherited LRB ramp/gallery links without rebuilding the atrium.

Run in Blender's Text Editor. Only seven owned rail copies replace the
continuous barriers across the six existing links. Public guide topology
supports connected circulation; existing radii, station and dimensions stay
estimated. The baseline, roof, slabs and independent room studies are read-only.
"""
from pathlib import Path
import hashlib,json,math,sys
import bpy,bmesh
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/library-circulation213'
BASE=ROOT/'result/blender/LSE_campus_detailed_v212.blend'
BASE_SHA='65165c8a72c8208170c839085fef2954bf61a4f19a4a134d75ebcd289b9d7207'
COMPONENT=OUT/'library-circulation213-component.blend'
COLLECTION='LRB_PUBLIC_INTERIOR168_study'
CENTRE=Vector((75.593385,13.262314,0)); GATE_HALF=1.02
NAMES=['spiral_horizontal_rails','spiral_continuous_handrail','spiral_guard_posts','rail_footplates','gallery_horizontal_rails','gallery_circular_handrail','gallery_posts']
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import object_fingerprint,update_scene

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def evaluate_public_scene():
    bpy.context.window.scene=bpy.data.scenes['REVIEW_LRB168_INTERIOR']
    bpy.context.view_layer.update()

def components(mesh):
    parents=list(range(len(mesh.vertices)))
    def root(i):
        while parents[i]!=i:
            parents[i]=parents[parents[i]];i=parents[i]
        return i
    for e in mesh.edges:
        a,b=map(root,e.vertices);parents[b]=a
    groups={}
    for v in mesh.vertices:groups.setdefault(root(v.index),dict(vertices=[],faces=[]))['vertices'].append(v.index)
    for f in mesh.polygons:groups[root(f.vertices[0])]['faces'].append(f.index)
    return list(groups.values())

def clipped_part(old,part,side):
    mesh=old.data;bm=bmesh.new();mapping={i:bm.verts.new(mesh.vertices[i].co)for i in part['vertices']}
    uv_layers={u.name:bm.loops.layers.uv.new(u.name)for u in mesh.uv_layers}
    for fi in part['faces']:
        poly=mesh.polygons[fi];f=bm.faces.new([mapping[i]for i in poly.vertices]);f.material_index=poly.material_index;f.smooth=poly.use_smooth
        for dest,li in zip(f.loops,poly.loop_indices):
            for u in mesh.uv_layers:dest[uv_layers[u.name]].uv=u.data[li].uv
    plane_y=CENTRE.y+side*GATE_HALF-old.matrix_world.translation.y
    result=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(0,plane_y,0),plane_no=(0,side,0),clear_inner=True,clear_outer=False)
    boundary=[e for e in bm.edges if e.is_boundary]
    if boundary:
        caps=bmesh.ops.holes_fill(bm,edges=boundary,sides=0)['faces']
        for f in caps:
            for l in f.loops:
                p=old.matrix_world@l.vert.co
                for uv in uv_layers.values():l[uv].uv=(p.x,p.z)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.verts.ensure_lookup_table();bm.verts.index_update()
    if bm.verts:
        assert all(side*((old.matrix_world@v.co).y-CENTRE.y)>=GATE_HALF-2e-6 for v in bm.verts)
    assert all(e.is_manifold for e in bm.edges),'Clipped tube must remain closed'
    pts=[v.co.copy()for v in bm.verts]
    faces=[dict(ids=[v.index for v in f.verts],material=f.material_index,smooth=f.smooth,uv={name:[tuple(l[layer].uv)for l in f.loops]for name,layer in uv_layers.items()})for f in bm.faces]
    bm.free();return pts,faces

def replacement(old):
    verts=[];faces=[];infos=[];stats=dict(originalComponents=0,retainedComponents=0,removedComponents=0,trimmedComponents=0)
    def append(pts,fs):
        start=len(verts);verts.extend(pts)
        for f in fs:faces.append([start+i for i in f['ids']]);infos.append(f)
    for part in components(old.data):
        stats['originalComponents']+=1
        pts=[old.matrix_world@old.data.vertices[i].co for i in part['vertices']]
        mean_x=sum(p.x for p in pts)/len(pts)-CENTRE.x
        eligible=mean_x>(9.5 if 'gallery_'in old.name else 8.0)
        crossing=eligible and min(p.y for p in pts)<CENTRE.y+GATE_HALF and max(p.y for p in pts)>CENTRE.y-GATE_HALF
        if not crossing:
            lookup={v:i for i,v in enumerate(part['vertices'])}
            fs=[dict(ids=[lookup[i]for i in old.data.polygons[fi].vertices],material=old.data.polygons[fi].material_index,smooth=old.data.polygons[fi].use_smooth,uv={u.name:[tuple(u.data[li].uv)for li in old.data.polygons[fi].loop_indices]for u in old.data.uv_layers})for fi in part['faces']]
            append([old.data.vertices[i].co.copy()for i in part['vertices']],fs);stats['retainedComponents']+=1;continue
        produced=False
        for side in [-1,1]:
            if any(side*(p.y-CENTRE.y)>GATE_HALF+1e-7 for p in pts):
                v,f=clipped_part(old,part,side);append(v,f);produced=True
        stats['trimmedComponents'if produced else'removedComponents']+=1
    new=old.copy();new.data=bpy.data.meshes.new('LRB_CIRC213_'+old.name.removeprefix('LRB168__LRB_')+'_mesh');new.name='LRB_CIRC213_'+old.name.removeprefix('LRB168__LRB_')
    new.data.from_pydata(verts,[],faces);new.data.update()
    for m in old.data.materials:new.data.materials.append(m)
    for poly,info in zip(new.data.polygons,infos):poly.material_index=info['material'];poly.use_smooth=info['smooth']
    for u in old.data.uv_layers:
        target=new.data.uv_layers.new(name=u.name)
        for poly,info in zip(new.data.polygons,infos):
            for li,uv in zip(poly.loop_indices,info['uv'][u.name]):target.data[li].uv=uv
    new['originalObject']=old.name;new['destinationCollection']=COLLECTION;new['buildingCode']='LRB';new['sourcePlan']='data/documents/library_floor_plans.pdf pages2-7';new['scope']='Open inherited circulation links by clipping only transverse guard segments; location and dimensions estimated';new['dimensionsEstimated']=True
    bpy.data.collections[COLLECTION].objects.link(new)
    assert [m.name for m in new.data.materials]==[m.name for m in old.data.materials]
    stats['originalPolygons']=len(old.data.polygons);stats['replacementPolygons']=len(new.data.polygons)
    return new,stats

def passage_counts(objects):
    levels=[]
    for floor,index in [('LG',0),('G',1),('1',2),('2',3),('3',4),('4',5)]:
        z=-3.68+4*index;counts={}
        for o in objects:
            count=sum(1 for v in o.data.vertices if 8.06<(o.matrix_world@v.co).x-CENTRE.x<10.13 and abs((o.matrix_world@v.co).y-CENTRE.y)<.95 and z+.15<(o.matrix_world@v.co).z<z+1.25)
            if count:counts[o.name]=count
        levels.append(dict(floor=floor,datum=z,clearWidth=1.90,clearHeightBand=[.15,1.25],obstructingVertices=counts))
    return levels

def support_probes():
    names=['LRB168__LRB_helical_solid_slab','LRB168__LRB_ramp_gallery_landings','LRB168__LRB_library_floor_slabs','LRB168_LG_atrium_foundation']
    trees={n:BVHTree.FromPolygons([bpy.data.objects[n].matrix_world@v.co for v in bpy.data.objects[n].data.vertices],[list(f.vertices)for f in bpy.data.objects[n].data.polygons])for n in names}
    records=[]
    for floor,index in [('LG',0),('G',1),('1',2),('2',3),('3',4),('4',5)]:
        z=-3.68+4*index
        for y in [-.8,0,.8]:
            for x in [8.24,8.5,9.2,9.75,9.85,10.04]:
                hits=[]
                for n,t in trees.items():
                    p,_,_,_=t.ray_cast(Vector((CENTRE.x+x,CENTRE.y+y,z+.5)),Vector((0,0,-1)),1)
                    if p:hits.append((p.z,n))
                assert hits,(floor,x,y)
                highest,n=max(hits);assert abs(highest-z)<.15,(floor,x,y,highest)
                records.append(dict(floor=floor,xy=[CENTRE.x+x,CENTRE.y+y],supportObject=n,supportZ=highest,datumDifference=highest-z))
    return records

def render(label,old_names,new_names):
    evaluate_public_scene()
    scene=bpy.data.scenes.new('LRB_CIRC213_REVIEW');scene.render.engine='CYCLES';scene.cycles.samples=16;scene.render.resolution_x=1100;scene.render.resolution_y=760;scene.render.resolution_percentage=100
    scene.world=bpy.data.worlds.new('LRB_CIRC213_REVIEW_WORLD');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.8,.85,.9,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.6
    copies=[]
    for old in list(bpy.data.collections[COLLECTION].all_objects):
        if old.type!='MESH' or old.hide_render or old.name in(new_names if label=='before'else old_names):continue
        clone=old.copy();clone.data=old.data.copy();clone.data.transform(old.matrix_basis.copy());clone.matrix_basis=Matrix.Identity(4)
        bm=bmesh.new();bm.from_mesh(clone.data)
        bmesh.ops.delete(bm,geom=[v for v in bm.verts if not 3.92<=v.co.z<=6.2 or not 81.5<=v.co.x<=87.2 or not 9.5<=v.co.y<=17.0],context='VERTS');bm.to_mesh(clone.data);bm.free()
        if not clone.data.polygons:bpy.data.objects.remove(clone);continue
        scene.collection.objects.link(clone);copies.append(clone)
    camera=bpy.data.objects.new('LRB_CIRC213_CAMERA',bpy.data.cameras.new('LRB_CIRC213_CAMERA'));scene.collection.objects.link(camera);scene.camera=camera;camera.data.type='ORTHO';camera.data.ortho_scale=7.3;camera.location=(91,7.1,9.0);camera.rotation_euler=(Vector((84.4,13.26,4.9))-camera.location).to_track_quat('-Z','Y').to_euler()
    light=bpy.data.objects.new('LRB_CIRC213_SUN',bpy.data.lights.new('LRB_CIRC213_SUN','SUN'));scene.collection.objects.link(light);light.rotation_euler=(.45,-.35,-.3);light.data.energy=2
    bpy.context.window.scene=scene;bpy.context.view_layer.update();(OUT/(label+'-render-state.json')).write_text(json.dumps([dict(name=o.name,matrix=[list(r)for r in o.matrix_world],min=[min((o.matrix_world@v.co)[k]for v in o.data.vertices)for k in range(3)],max=[max((o.matrix_world@v.co)[k]for v in o.data.vertices)for k in range(3)])for o in copies],indent=2));scene.render.filepath=str(OUT/(label+'-floor1-link.png'));scene.render.image_settings.file_format='PNG';bpy.ops.render.render(write_still=True)
    bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
    for o in copies+[camera,light]:bpy.data.objects.remove(o,do_unlink=True)
    bpy.data.scenes.remove(scene)

def run():
    OUT.mkdir(parents=True,exist_ok=True);assert sha(BASE)==BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene();evaluate_public_scene()
    originals={o.name:object_fingerprint(o)for o in bpy.data.objects};visibility={o.name:o.hide_render for o in bpy.data.objects}
    material_states={m.name:repr((m.diffuse_color[:],[(n.name,[(s.name,str(s.default_value))for s in n.inputs if hasattr(s,'default_value')])for n in m.node_tree.nodes]if m.node_tree else[]))for m in bpy.data.materials}
    old=[bpy.data.objects['LRB168__LRB_'+n]for n in NAMES];before=passage_counts(old);probes=support_probes();added=[];changes=[]
    for o in old:
        new,stats=replacement(o);added.append(new);changes.append(dict(original=o.name,replacement=new.name,**stats))
    update_scene();evaluate_public_scene();after=passage_counts(added);assert all(not x['obstructingVertices']for x in after)
    assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
    states={o.name:object_fingerprint(o)for o in added};bindings={o.name:[m.name for m in o.data.materials]for o in added};bpy.data.libraries.write(str(COMPONENT),set(added),fake_user=True,compress=True)
    render('before',[o.name for o in old],[o.name for o in added]);render('after',[o.name for o in old],[o.name for o in added])
    audit=dict(version=213,building='LRB',baseline=str(BASE.relative_to(ROOT)),baselineSha256=BASE_SHA,component=str(COMPONENT.relative_to(ROOT)),componentSha256=sha(COMPONENT),destinationCollection=COLLECTION,targetCollection=COLLECTION,addedObjects=[o.name for o in added],archivedObjects=[o.name for o in old],originalObjectPolicy='Retain all native originals; listed seven guards archived only on subsequent integration',changes=changes,sourcePlan=dict(path='data/documents/library_floor_plans.pdf',sha256=sha(ROOT/'data/documents/library_floor_plans.pdf'),pages=[2,3,4,5,6,7],url='https://www.lse.ac.uk/asset-library/information/library-floor-plans-pdf.pdf',liveRecheck='Web fetch timed out; archived PDF used'),primaryStructureSource=dict(url='https://tyrensakt.com/projects/lse-library/',liveRechecked=True,completedYear=2001),sourcePhoto='data/collections/library_round5/photos/LRB_9cf4d6340481.jpg',sourcePhotoSha256=sha(ROOT/'data/collections/library_round5/photos/LRB_9cf4d6340481.jpg'),inheritedAtriumCentre=list(CENTRE),clearGateWidth=2*GATE_HALF,beforePassage=before,afterPassage=after,supportProbeCount=len(probes),supportProbes=probes,scope='Remove the transverse barriers across six inherited ramp/gallery links, clipping and capping owned rail copies only',limitations=['Official guide supports public circulation topology but does not establish exact architectural guard openings.','Existing common circular floor opening, bridge position,4m pitch and radial dimensions remain estimated; guide north-side ramp/lift orientation has not been re-registered.','Inherited level-link slab top is20mm above slab datum; carpet offsets and ramp-height blending remain unchanged. Support probes allow15cm local variation and do not certify accessibility compliance.','No roof, lightwell, lift geometry, slab or room layout changed;5th-floor staff service and side emergency stairs remain unresolved.','Photographic source belongs to completed2001 project; shooting date and current2026 arrangement unverified.'])
    (OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene();evaluate_public_scene()
    with bpy.data.libraries.load(str(COMPONENT),link=False)as(src,dst):
        assert set(src.objects)==set(states);dst.objects=list(states)
    for o in dst.objects:
        bpy.data.collections[COLLECTION].objects.link(o)
        for i,name in enumerate(bindings[o.name]):o.data.materials[i]=bpy.data.materials[name]
    update_scene();evaluate_public_scene()
    assert all(object_fingerprint(o)==states[o.name]for o in dst.objects)
    for m in list(bpy.data.materials):
        if m.name not in material_states and m.users==0:bpy.data.materials.remove(m)
    assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in originals.items());assert all(bpy.data.objects[n].hide_render==v for n,v in visibility.items())
    assert all(repr((m.diffuse_color[:],[(n.name,[(s.name,str(s.default_value))for s in n.inputs if hasattr(s,'default_value')])for n in m.node_tree.nodes]if m.node_tree else[]))==material_states[m.name]for m in bpy.data.materials)
    assert all(not x['obstructingVertices']for x in passage_counts(dst.objects));assert len(support_probes())==len(probes)
    verification=dict(savedComponentReopened=True,componentSha256=sha(COMPONENT),baselineSha256=sha(BASE),baselineUnchanged=sha(BASE)==BASE_SHA,originalObjectsVerified=len(originals),originalGeometryUVsAndMaterialBindingsUnchanged=True,allOriginalVisibilityUnchanged=True,allOriginalMaterialsUnchanged=True,newObjectsVerified=len(states),supportProbesVerified=len(probes),clearLinksVerified=6,beforeAfterSameCameraLighting=True,roofLightwellAndRoomStudiesUnchanged=True,noFullCampusWritten=True)
    (OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n');print('LRB_CIRC213_VERIFIED',verification,flush=True)

if __name__=='__main__':
    run();bpy.ops.wm.quit_blender()
