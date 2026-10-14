"""Independently verify the combined private CBG facade and canopy interfaces."""
from pathlib import Path
import hashlib
import json
import sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from refine_cbg_roof203 import frame
OUT=ROOT/'result/blender/cbg-assembled204'


def verify():
    report=json.loads((OUT/'audit.json').read_text())
    path=ROOT/report['componentPath']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==report['componentSha256']
    mapping=json.loads((ROOT/'result/blender/cbg-georegistration202/rebuild-mapping.json').read_text())
    local,world=frame(mapping)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(path),link=False)as(src,loaded):loaded.objects=list(report['addedObjects'])
    objects=list(loaded.objects)
    for obj in objects:bpy.context.scene.collection.objects.link(obj)
    vv=[];ff=[];owners=[]
    for obj in objects:
        offset=len(vv);vv.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        ff.extend(tuple(offset+i for i in face.vertices)for face in obj.data.polygons);owners.extend([obj.name]*len(obj.data.polygons))
    tree=BVHTree.FromPolygons(vv,ff)
    office=json.loads((ROOT/'result/blender/cbg-office204/audit.json').read_text());checks=[]
    direction=world((0,1,0))-world((0,0,0))
    for probe in office['surfaceProbes']:
        origin=world((probe['x'],-.21,probe['floor']*52.2/13+.80))
        hit=tree.ray_cast(origin,direction,.4);name=owners[hit[2]]if hit[2]is not None else None
        assert name==probe['firstSurface'],(probe,name)
        checks.append(dict(kind=probe['kind'],floor=probe['floor'],x=probe['x'],firstSurface=name))
    canopy=tree.ray_cast(world((-2,3.7,51.7)),Vector((0,0,-1)),10)
    assert canopy[0]is not None
    assert abs(canopy[0].z-(11*52.2/13+.17))<.2,(canopy[0],owners[canopy[2]])
    removed=set(report['removedInputObjects']);assert not removed&set(o.name for o in objects)
    assert not any(o.name.startswith('CBG203_ROOF_CBG194_GLASS181_CBG_NEXT_office_glass')for o in objects)
    proof=dict(componentReopened=True,officeProbes=len(checks),metricModulesSurviveRoofMerge=True,
               roofLegacyLowerMeshesExcluded=True,obsoleteInputObjectsAbsent=True,canopyClearanceHit=dict(object=owners[canopy[2]],z=canopy[0].z),
               notApprovedForRelease=True,remaining=report['limitations'])
    (OUT/'independent-verification.json').write_text(json.dumps(proof,indent=2)+'\n')
    print('CBG204_ASSEMBLY_PROBES',len(checks),flush=True)


if __name__=='__main__':verify()
