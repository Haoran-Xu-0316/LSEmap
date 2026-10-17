"""Fixed237review of the existing LSE Square tree-pool understory."""
from pathlib import Path
import hashlib
import json
import sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'result/blender/street-environment237'
DATA = ROOT/'data/collections/street-environment237'
BASE = ROOT/'result/blender/LSE_campus_detailed_v236.blend'
BASE_SHA = '3834a5f04b94806175ec8344944a03da7694d7ef1447e9cbb37ed44a684bf6bd'
SOIL = 'SITE222_Square_six_tree_pool_soil'
STONE = 'SITE229_Square_six_jointed_stone_tree_pool_enclosures'
OWNER = '00_SITE'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def inspect():
    import bpy
    from mathutils import Vector
    sys.path.insert(0,str(ROOT/'web/tools'))
    from integrate_exterior_round194 import object_fingerprint,update_scene
    from refine_portsmouth_exterior207 import material_fingerprint
    from refine_streets230 import components
    assert sha(BASE) == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    soil = bpy.data.objects[SOIL]
    assert not soil.hide_render
    tops = []
    for face in soil.data.polygons:
        points = [soil.matrix_world@soil.data.vertices[i].co for i in face.vertices]
        if all(abs(p.z-.37)<1e-5 for p in points):
            tops.append(dict(face=face.index,points=[list(p) for p in points],centre=list(sum(points,Vector())/len(points))))
    assert len(tops) == 6
    low_foliage, trunks = [], []
    for obj in scene.objects:
        if obj.type != 'MESH' or obj.hide_render:
            continue
        bounds = [obj.matrix_world@Vector(p) for p in obj.bound_box]
        if min(p.x for p in bounds)>54 or max(p.x for p in bounds)<24 or min(p.y for p in bounds)>-19 or max(p.y for p in bounds)<-36:
            continue
        slots = {i for i,m in enumerate(obj.data.materials) if m and any(k in m.name.lower() for k in ['foliage','leaf'])}
        hits = []
        for face in obj.data.polygons:
            if face.material_index not in slots:
                continue
            points = [obj.matrix_world@obj.data.vertices[i].co for i in face.vertices]
            if min(p.z for p in points)<1.1 and max(p.x for p in points)>24 and min(p.x for p in points)<54 and max(p.y for p in points)>-36 and min(p.y for p in points)<-19:
                hits.append(face.index)
        if hits:
            low_foliage.append(dict(name=obj.name,faces=hits))
        if not any(k in obj.name.lower() for k in ['trunk','stem']):
            continue
        for part in components(obj):
            points = [obj.matrix_world@obj.data.vertices[i].co for i in part]
            centre = sum(points,Vector())/len(points)
            if 24<centre.x<54 and -36<centre.y<-19 and min(p.z for p in points)<1:
                trunks.append(dict(object=obj.name,centre=list(centre),points=[list(p) for p in points]))
    material_names = [m.name for obj in bpy.data.collections[OWNER].all_objects if obj.type=='MESH' and not obj.hide_render for m in obj.data.materials if m and 'foliage' in m.name.lower()]
    write(OUT/'native-inspection.json',dict(baselineSha256=BASE_SHA,objects=len(bpy.data.objects),materials=len(bpy.data.materials),soilObject=SOIL,soilOwner=[c.name for c in soil.users_collection],soilFingerprint=object_fingerprint(soil),soilTopFaces=tops,existingLowFoliage=low_foliage,registeredTrunks=trunks,existingSiteFoliageMaterials=sorted(set(material_names)),soilMaterialBindings=[m.name for m in soil.data.materials],soilMaterialFingerprints={m.name:material_fingerprint(m) for m in soil.data.materials}))
    print('STREET237_INSPECTION',len(tops),'lowfoliage',low_foliage,'trunks',len(trunks),flush=True)


ADDED = 'SITE237_Square_six_tree_pool_soil_and_opaque_understory'
FOLIAGE = 'LANDSCAPE179_Houghton_planter_crowns_foliage_mid'

def native_state():
    import bpy
    from integrate_exterior_round194 import object_fingerprint
    from refine_portsmouth_exterior207 import material_fingerprint
    from refine_ksw_exterior219 import modifier_state
    metadata=json.loads((DATA/'metadata-baseline.json').read_text())
    return dict(objects={o.name:object_fingerprint(o)for o in bpy.data.objects},materials={m.name:material_fingerprint(m)for m in bpy.data.materials},owners={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects},modifiers={o.name:modifier_state(o)for o in bpy.data.objects},props={o.name:repr(sorted(o.items()))for o in bpy.data.objects},visibility={o.name:o.hide_render for o in bpy.data.objects},rooms={r['collection']:sorted(o.name for o in bpy.data.collections[r['collection']].all_objects)for r in metadata['spaces']})

def preserve(state):
    import bpy
    from integrate_exterior_round194 import object_fingerprint
    from refine_portsmouth_exterior207 import material_fingerprint
    from refine_ksw_exterior219 import modifier_state
    for n,v in state['objects'].items():assert object_fingerprint(bpy.data.objects[n])==v,n
    for n,v in state['materials'].items():assert material_fingerprint(bpy.data.materials[n])==v,n
    for n,v in state['owners'].items():assert sorted(c.name for c in bpy.data.objects[n].users_collection)==v,n
    for n,v in state['modifiers'].items():assert modifier_state(bpy.data.objects[n])==v,n
    for n,v in state['props'].items():assert repr(sorted(bpy.data.objects[n].items()))==v,n
    for n,v in state['visibility'].items():assert bpy.data.objects[n].hide_render==v,n
    for n,v in state['rooms'].items():assert sorted(o.name for o in bpy.data.collections[n].all_objects)==v,n
    assert sha(BASE)==BASE_SHA

def mesh_record(obj):
    obj.data.calc_loop_triangles()
    return dict(name=obj.name,matrix=[list(r)for r in obj.matrix_world],vertices=[list(v.co)for v in obj.data.vertices],faces=[list(p.vertices)for p in obj.data.polygons],materialIndices=[p.material_index for p in obj.data.polygons],uv={u.name:[list(v.uv)for v in u.data]for u in obj.data.uv_layers},triangles=len(obj.data.loop_triangles),customNormals=obj.data.has_custom_normals)

def build():
    import bpy
    import bmesh
    from mathutils import Vector
    sys.path.insert(0,str(ROOT/'web/tools'))
    from integrate_exterior_round194 import object_fingerprint,update_scene
    from refine_portsmouth_exterior207 import material_fingerprint
    assert sha(BASE)==BASE_SHA
    plan=json.loads((OUT/'understory-plan.json').read_text())
    assert plan['baselineSha256']==BASE_SHA
    metadata=DATA/'metadata-baseline.json'
    if not metadata.exists():metadata.write_bytes((ROOT/'web/tools/building-metadata.json').read_bytes())
    bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
    state=native_state()
    assert len(state['objects'])==8584 and len(state['rooms'])==35 and len(set().union(*(set(v)for v in state['rooms'].values())))==1485
    source=bpy.data.objects[SOIL]
    assert not source.hide_render and sorted(c.name for c in source.users_collection)==[OWNER]
    assert not source.data.has_custom_normals
    original=mesh_record(source)
    clone=source.copy();clone.data=source.data.copy();clone.name=ADDED;clone.data.name=ADDED
    bpy.data.collections[OWNER].objects.link(clone)
    clone.data.materials.append(bpy.data.materials[FOLIAGE])
    assert len(clone.data.materials)==2
    bm=bmesh.new();bm.from_mesh(clone.data)
    new_vertices=[bm.verts.new(clone.matrix_world.inverted()@Vector(p))for p in plan['vertices']]
    for indices in plan['faces']:
        face=bm.faces.new([new_vertices[i]for i in indices]);face.material_index=1;face.smooth=False
    bm.to_mesh(clone.data);bm.free();clone.data.update()
    clone['originalObject']=SOIL
    clone['scope237']='Coarse estimated low understory inside six unchanged tree pools; no species or flower identification'
    clone['sourceGeometryRetained']=True
    clone['opaqueUnderstoryEstimated']=True
    actual=mesh_record(clone)
    nv,nf=len(original['vertices']),len(original['faces'])
    assert actual['vertices'][:nv]==original['vertices'] and actual['faces'][:nf]==original['faces']
    assert actual['materialIndices'][:nf]==original['materialIndices']
    for name,values in original['uv'].items():assert actual['uv'][name][:len(values)]==values
    assert actual['triangles']-original['triangles']==plan['newTriangles']
    preserve(state)
    component=OUT/'component.blend';assert not component.exists()
    bpy.data.libraries.write(str(component),{clone},fake_user=True,compress=True)
    component_sha=sha(component)
    write(OUT/'serialized-mesh.json',dict(componentSha256=component_sha,source=original,replacement=actual,sourceVertexCount=nv,sourcePolygonCount=nf))
    refs=['result/blender/site_geometry.json','data/collections/street-environment222/gillespies-square-built.jpg','data/collections/street-environment222/gillespies-square-east.webp','data/collections/street-environment222/sources.json','data/collections/streets/raw/public_realm_strategy_2022.pdf','data/collections/street-environment237/metadata-baseline.json','result/blender/street-environment237/native-inspection.json','result/blender/street-environment237/understory-plan.json']
    write(OUT/'audit.json',dict(version=237,status='SAVED_PENDING_REOPEN_AND_PRODUCTION_VIEWER',baseline=str(BASE.relative_to(ROOT)),baselineSha256=BASE_SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=component_sha,targetCollection=OWNER,destinationCollection=OWNER,addedObjects=[ADDED],archivedObjects=[SOIL],changedObjects=[],addedFingerprints={ADDED:object_fingerprint(clone)},replacementMaterialBindings={ADDED:[m.name for m in clone.data.materials]},addedMaterialFingerprints={m.name:material_fingerprint(m)for m in clone.data.materials},sourceObjectFingerprints={SOIL:state['objects'][SOIL]},objectOwners={ADDED:OWNER},archiveOwners={SOIL:state['owners'][SOIL]},sourceHashes={p:sha(ROOT/p)for p in refs},sourceManifest='data/collections/street-environment237/sources.json',budget=dict(addedObjects=1,archivedObjects=1,newMaterials=0,newTextures=0,originalSoilVertices=nv,originalSoilPolygons=nf,newUnderstorySolids=len(plan['rootRecords']),newUnderstoryTriangles=plan['newTriangles'],originalTriangles=original['triangles'],savedTriangles=actual['triangles'],triangleDelta=actual['triangles']-original['triangles'],materialSetDeltaForMergedProductionSITE=0),pools=plan['pools'],preservation=dict(originalObjects=len(state['objects']),originalMaterials=len(state['materials']),oldSpaces=35,oldSpaceMembers=1485,allOriginalSoilCoordinatesFacesUVsAndBindingsExact=True,noFullNativeSaved=True),limitations=['Published built photographs are not a237dated survey; capture dates unknown.','Leaf-cluster form,count,coverage and0.25–0.32mheight above soil are visual estimates; no species or flower identity inferred.','Opaque leaves remain coarse closed solids. This is understory massing,not per-leaf botanical reconstruction.','Existing stone pools,soil,tree positions,crowns,paving and all ground datums remain unchanged.']))
    print('STREET237_COMPONENT_SAVED',component_sha,plan['newTriangles'],len(plan['rootRecords']),flush=True)

if __name__ == '__main__':
    build()
