"""Restore CBG's metric2m glazing/1m solid office modules in the42m frame.

Run build_candidate() in Blender. This is a private component, not a release.
RSHP publishes the3m office module; placement of circulation strips and precise
upper-floor levels remain inherited estimates. Current wing/public rooms survive.
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
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from build_room_samples167 import RoomGeometry
from integrate_exterior_round194 import object_fingerprint
from refine_ground_orientation199 import closed_islands,signed_volume
from refine_cbg_roof203 import frame

SOURCE=ROOT/'result/blender/cbg-wing203/cbg-wing203-component.blend'
OUT=ROOT/'result/blender/cbg-office204'
PREFIX='CBG204_OFFICE_'
HEIGHT=52.2
STEP=HEIGHT/13
CLEAR=[None,-9,-9,-1,-1,-9,-17,-25,-25,-17,-9,-1,-1]


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def build_candidate():
    OUT.mkdir(parents=True,exist_ok=True)
    source_sha=digest(SOURCE)
    source_report=json.loads((SOURCE.parent/'audit.json').read_text())
    mapping=json.loads((ROOT/'result/blender/cbg-georegistration202/rebuild-mapping.json').read_text())
    local,world=frame(mapping)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(SOURCE),link=False)as(src,loaded):loaded.objects=list(source_report['addedObjects'])
    sources=list(loaded.objects)
    original={obj.name:object_fingerprint(obj)for obj in sources}
    collection=bpy.data.collections.new(PREFIX+'PRIVATE_REVIEW');bpy.context.scene.collection.children.link(collection)
    replacements=[];owned=[];archived=[]
    for source in sources:
        if not source.data.vertices:continue
        owner=source.get('originalObject','')
        selected=('office_'in owner or 'curtain_with_door_apertures'in owner or 'vision_transoms'in owner)
        if not selected:continue
        target=source.copy();target.data=source.data.copy();target.name=PREFIX+'retained_'+source.name
        bm=bmesh.new();bm.from_mesh(target.data);delete=[];removed=0
        for faces,closed in closed_islands(bm):
            vertices={v for face in faces for v in face.verts}
            pts=[local(target.matrix_world@v.co)for v in vertices]
            centre=sum(pts,Vector())/len(pts)
            if centre.x<.15 and abs(centre.y)<.35 and min(p.z for p in pts)>3*STEP-.21:
                delete.extend(vertices);removed+=1
        if not removed:
            bm.free();bpy.data.objects.remove(target,do_unlink=True);continue
        bmesh.ops.delete(bm,geom=list(set(delete)),context='VERTS');bm.to_mesh(target.data);bm.free();target.data.update()
        collection.objects.link(target);owned.append(target);archived.append(source.name)
        replacements.append(dict(source=source.name,target=target.name,removedComponents=removed,originalObject=owner))
    def material(owner_part):return next(o for o in sources if owner_part in o.get('originalObject','')).data.materials[0]
    g=RoomGeometry(collection,PREFIX)
    g.materials.update(glass=material('office_glass'),solid=material('office_solid'),frame=material('office_frames'))
    modules=[];clear_modules=[]
    def box(family,mat,lo,hi):
        g.box(family,mat,tuple((a+b)/2 for a,b in zip(lo,hi)),tuple(b-a for a,b in zip(lo,hi)))
    for floor in range(3,13):
        centre=(CLEAR[floor]-7)*42/49;half=7.8*42/49
        for index in range(14):
            x=-42+index*3;x1=x+3
            z0=floor*STEP+.08;z1=(floor+1)*STEP-.08;vent=floor*STEP+STEP*.665
            office=x1<=centre-half-.10 or x>=centre+half+.10
            if office:
                box('metric_office_glass','glass',(x+.035,-.018,z0),(x+1.965,.017,z1))
                box('metric_office_solid','solid',(x+2.035,-.105,z0),(x+2.965,-.025,z1))
                divisions=[0,2,3];modules.append(dict(floor=floor,x0=x,x1=x1,glazingNominalWidth=2,solidNominalWidth=1))
                box('metric_office_vent_transoms','frame',(x,-.145,vent-.022),(x+2,-.025,vent+.022))
            else:
                box('retained_circulation_glass','glass',(x+.035,-.018,z0),(x+2.965,.017,z1))
                divisions=[0,1.5,3];clear_modules.append(dict(floor=floor,x0=x,x1=x1))
            for offset in divisions:
                box('metric_front_jambs','frame',(x+offset-.025,-.145,z0),(x+offset+.025,-.025,z1))
            for z in [z0,z1]:box('metric_front_heads_sills','frame',(x,-.145,z-.025),(x+3,-.025,z+.025))
    added=g.finish()
    for obj in added:
        for vertex in obj.data.vertices:vertex.co=world(vertex.co)
        obj.data.update();obj['destinationCollection']='CBG_EXTERIOR'
        obj['candidateScope']='RSHP3moffice module; circulation registration still provisional'
    owned+=added
    assert len(modules)>60
    assert all(object_fingerprint(o)==original[o.name]for o in sources)
    # Probe the authored2m glass and1m leaf directly. Solar shades are separate
    # outer geometry; this tests backing/partition at the window skin itself.
    all_visible=[o for o in sources if o.name not in archived]+owned
    vv=[];ff=[];owners=[]
    for obj in all_visible:
        offset=len(vv);vv.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        ff.extend(tuple(offset+i for i in face.vertices)for face in obj.data.polygons);owners.extend([obj.name]*len(obj.data.polygons))
    tree=BVHTree.FromPolygons(vv,ff);direction=world((0,1,0))-world((0,0,0));checks=[]
    for module in modules:
        z=module['floor']*STEP+.80
        for kind,offset in [('glass',.8),('solid',2.5)]:
            ray=world((module['x0']+offset,-.21,z));hit=tree.ray_cast(ray,direction,.4)
            name=owners[hit[2]]if hit[2]is not None else None
            expected=PREFIX+'metric_office_'+kind
            assert name==expected,(module,kind,name)
            checks.append(dict(floor=module['floor'],x=module['x0']+offset,kind=kind,firstSurface=name))
    path=OUT/'cbg-office204-component.blend'
    bpy.data.libraries.write(str(path),set(owned),fake_user=True,compress=True)
    fingerprints={o.name:object_fingerprint(o)for o in owned}
    report=dict(status='private-office-modules-not-for-release',componentPath=str(path.relative_to(ROOT)),componentSha256=digest(path),
                inputPath=str(SOURCE.relative_to(ROOT)),inputSha256=source_sha,addedObjects=list(fingerprints),archivedInputObjects=archived,
                replacements=replacements,officeModules=modules,clearCirculationModules=clear_modules,surfaceProbes=checks,
                source=dict(url='https://rshp.com/projects/education/lse-centre-building/',verified='2026-10-14',specification='2m wide glazed panel with top high level opening vent and1m solid inward opening panel'),
                nominalFrontage=42,nominalModulePitch=3,nominalColumns=14,
                limitations=['Circulation strips retained from inherited meandering gallery/stair study, not a current measured elevation.',
                'Solar-fin spacing and roof cutbacks are separate components; exact office counts and top stair connection still need whole-building reconciliation.',
                'No new room allocations or opening animations are inferred.'])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(path),link=False)as(src,reopened):reopened.objects=list(fingerprints)
    for obj in reopened.objects:
        bpy.context.scene.collection.objects.link(obj);assert object_fingerprint(obj)==fingerprints[obj.name]
        bm=bmesh.new();bm.from_mesh(obj.data);bm.normal_update()
        assert all(not closed or signed_volume(faces)>0 for faces,closed in closed_islands(bm)),obj.name;bm.free()
    report['verification']=dict(componentReopened=True,addedFingerprintsPreserved=True,inputPreserved=digest(SOURCE)==source_sha,
                                sourceFingerprintsPreserved=True,surfaceProbeCount=len(checks))
    (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('CBG204_OFFICE_REOPENED',len(modules),len(checks),len(fingerprints),flush=True)


if __name__=='__main__':build_candidate()
