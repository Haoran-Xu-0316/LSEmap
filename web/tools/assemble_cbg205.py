"""Merge independently checked CBG envelope, podium and connected roof stairs.

The current campus stays read-only. Semantic aliases resolve to actual native
objects; explicit collections separate external skins from public structure.
Run in Blender's Text Editor after the two bounded205 builders have completed.
"""
from pathlib import Path
import hashlib,json,sys
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import object_fingerprint,geometry_policy_name,integrate
from refine_ground_orientation199 import closed_islands,signed_volume
from refine_cbg_roof203 import frame
OUT=ROOT/'result/blender/cbg-assembled205'
BASE=ROOT/'result/blender/LSE_campus_detailed_v204.blend'
BASE_SHA='a12a1ae48f98b7b0447af030667ec17e1c25eb757405a056e62b2ddc772be956'

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def assemble():
    OUT.mkdir(parents=True,exist_ok=True)
    assert digest(BASE)==BASE_SHA
    envelope=json.loads((ROOT/'result/blender/cbg-envelope202/audit.json').read_text())
    baseline=json.loads((ROOT/'result/blender/stage204/baseline-state.json').read_text())
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:layer.update()
    originals={name:object_fingerprint(bpy.data.objects[name])for name in envelope['archivedObjects']}
    assert all(value==baseline['fingerprints'][name]for name,value in originals.items())
    assert all(not bpy.data.objects[name].hide_render for name in originals)
    policies={name:geometry_policy_name(bpy.data.objects[name])for name in originals}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objects=[];aliases={};ownership={};frozen={};removed=[]
    def append(report):
        path=ROOT/report['componentPath'];assert digest(path)==report['componentSha256']
        frozen[str(path.relative_to(ROOT))]=digest(path)
        with bpy.data.libraries.load(str(path),link=False)as(src,loaded):loaded.objects=list(report['addedObjects'])
        result=list(loaded.objects)
        for obj in result:
            owner=obj.get('originalObject')
            # Follow aliases from a bounded component back through the assembly.
            seen=set()
            while owner in aliases:
                assert owner not in seen;seen.add(owner);owner=aliases[owner]
            if owner:
                assert owner in originals,(obj.name,owner)
                obj['originalObject']=owner;obj['webGeometrySource']=policies[owner]
            elif 'originalObject'in obj:del obj['originalObject']
            aliases[obj.name]=owner
            obj['destinationCollection']=obj.get('destinationCollection')or ownership.get(obj.name,'CBG_EXTERIOR')
            ownership[obj.name]=obj['destinationCollection']
            bpy.context.scene.collection.objects.link(obj)
        return result
    core=json.loads((ROOT/'result/blender/cbg-assembled204/audit.json').read_text());objects+=append(core)
    for folder in ['cbg-podium205','cbg-stair205']:
        report=json.loads((ROOT/f'result/blender/{folder}/audit.json').read_text())
        input_sha=report.get('inputComponentSha256')or report['inputHashes'][core['componentPath']]
        assert input_sha==core['componentSha256'],folder
        targets=report['removeObjects'];byname={o.name:o for o in objects};assert set(targets)<=set(byname),folder
        replacements=append(report)
        for name in targets:
            obj=byname[name];objects.remove(obj);bpy.data.objects.remove(obj,do_unlink=True);removed.append(name)
        objects+=replacements
    assert len({o.name for o in objects})==len(objects)
    local,world=frame(json.loads((ROOT/'result/blender/cbg-georegistration202/rebuild-mapping.json').read_text()))
    vertices=[];faces=[];owners=[];topology=[]
    for obj in objects:
        assert obj.get('destinationCollection')in{'CBG_EXTERIOR','CBG_PUBLIC_INTERIOR_study'},obj.name
        bm=bmesh.new();bm.from_mesh(obj.data);bm.normal_update();closed_count=0
        for island,closed in closed_islands(bm):
            if closed:assert signed_volume(island)>0,obj.name;closed_count+=1
        bm.free();topology.append({'object':obj.name,'closedComponents':closed_count})
        offset=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        faces.extend(tuple(offset+i for i in face.vertices)for face in obj.data.polygons);owners.extend([obj.name]*len(obj.data.polygons))
    tree=BVHTree.FromPolygons(vertices,faces)
    office=json.loads((ROOT/'result/blender/cbg-office204/audit.json').read_text());direction=world((0,1,0))-world((0,0,0))
    for probe in office['surfaceProbes']:
        hit=tree.ray_cast(world((probe['x'],-.21,probe['floor']*52.2/13+.80)),direction,.4)
        assert hit[2]is not None and owners[hit[2]]==probe['firstSurface'],(probe,hit)
    canopy=tree.ray_cast(world((-2,3.7,51.7)),Vector((0,0,-1)),10)
    assert canopy[0]and abs(canopy[0].z-(11*52.2/13+.17))<.2
    path=OUT/'cbg-assembled205-component.blend';bpy.data.libraries.write(str(path),set(objects),fake_user=True,compress=True)
    fingerprints={o.name:object_fingerprint(o)for o in objects}
    report=dict(componentPath=str(path.relative_to(ROOT)),componentSha256=digest(path),baselineSha256=BASE_SHA,
        addedObjects=list(fingerprints),archivedObjects=list(originals),changedObjects=[],nativeOwnerFingerprints=originals,
        inputHashes=frozen,removedInputObjects=removed,officeProbes=len(office['surfaceProbes']),topology=topology,
        targetCollection='CBG_EXTERIOR',scope='Registered42m tower, stepped teachingwing, two-storey amenitypodium, office modules, roof terraces and connected highest stair.',
        limitations='Design-plan/photo-informed dimensions and circulation remain estimates. Independent room studies retain their historical local coordinates; exact as-built room partitions unverified.')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(path),link=False)as(src,loaded):loaded.objects=list(fingerprints)
    for obj in loaded.objects:
        bpy.context.scene.collection.objects.link(obj);assert object_fingerprint(obj)==fingerprints[obj.name]
    report['verification']={'componentReopened':True,'fingerprintsMatch':True,'officeSurfaceProbes':len(office['surfaceProbes']),
        'nativeOwnersMatchPreviousAcceptedFile':True,'inputHashesUnchanged':all(digest(ROOT/p)==sha for p,sha in frozen.items())}
    (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    assert digest(BASE)==BASE_SHA
    print('CBG205_ASSEMBLY_REOPENED',len(fingerprints),len(originals),flush=True)
    integrate(base=BASE,destination=ROOT/'result/blender/LSE_campus_detailed_v205.blend',proof=ROOT/'result/blender/stage205',
        version=205,reports=[('CBG','result/blender/cbg-assembled205/audit.json','CBG_EXTERIOR')],scope=report['scope'])

if __name__=='__main__':assemble()
