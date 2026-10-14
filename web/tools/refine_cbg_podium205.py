"""Complete the private CBG southern podium in registered202 coordinates.

Call build_candidate() from Blender. The independent architect sheet establishes
2storeys; estimated8.333m Z aligns with the adjoining teaching Level2. No rooms,
furniture or unsupported hidden building systems are authored here.
"""
from pathlib import Path
import hashlib
import json
import math
import sys
import bpy
import bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from build_room_samples167 import RoomGeometry
from integrate_exterior_round194 import object_fingerprint
from refine_ground_orientation199 import closed_islands,signed_volume
from refine_cbg_roof203 import frame,volume_planes,trim_object
SOURCE=ROOT/'result/blender/cbg-assembled204/cbg-assembled204-component.blend'
NATIVE=ROOT/'result/blender/LSE_campus_detailed_v204.blend'
MAPPING=ROOT/'result/blender/cbg-georegistration202/rebuild-mapping.json'
OUT=ROOT/'result/blender/cbg-podium205'
PREFIX='CBG205_PODIUM_'
STEP=25/6
ROOF=2*STEP


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def area(polygon):return abs(sum(a[0]*b[1]-b[0]*a[1]for a,b in zip(polygon,polygon[1:]+polygon[:1])))/2


def build_candidate():
    OUT.mkdir(parents=True,exist_ok=True)
    reference_paths=[ROOT/'data/documents/centre_building_rshp_current.pdf',ROOT/'data/collections/exteriors/images/cbg_rshp_028.jpg',ROOT/'data/collections/cbg_roof_registration/level12-plan-rshp-2016.jpg',ROOT/'data/collections/exteriors/pages/cbg_rshp_images.json']
    hashes={str(p.relative_to(ROOT)):digest(p)for p in [SOURCE,NATIVE,MAPPING]+reference_paths}
    source_audit=json.loads((SOURCE.parent/'audit.json').read_text());assert digest(SOURCE)==source_audit['componentSha256']
    assert digest(NATIVE)=='a12a1ae48f98b7b0447af030667ec17e1c25eb757405a056e62b2ddc772be956'
    mapping=json.loads(MAPPING.read_text());local,world=frame(mapping)
    provisional=mapping['southern_amenity_podium']['provisional_polygon_local']
    wing=mapping['houghton_teaching_block']['GIS_polygon_local'];tower=mapping['tower']['GIS_tower_polygon_local']
    # Shared vertices use the actual registered GISedges, without expanding the
    # provisional independently traced southern boundary into either neighbour.
    outline=[wing[3],wing[2],tower[3],provisional[3]]
    A,B,C,D=[Vector(p)for p in outline]
    signed=sum(a[0]*b[1]-b[0]*a[1]for a,b in zip(outline,outline[1:]+outline[:1]))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene;scene.name='CBG205_PODIUM_PRIVATE'
    with bpy.data.libraries.load(str(SOURCE),link=False)as(src,loaded):loaded.objects=list(source_audit['addedObjects'])
    inputs=list(loaded.objects);protected={obj.name:object_fingerprint(obj)for obj in inputs}
    collection=bpy.data.collections.new('CBG205_PODIUM_PRIVATE');scene.collection.children.link(collection)
    def find_material(fragment):return next(o.data.materials[0]for o in inputs if fragment in o.name)
    geometry=RoomGeometry(collection,PREFIX)
    geometry.materials.update(glass=find_material('teaching_glazing'),frame=find_material('teaching_mullions'),slab=find_material('registered_teaching_floor_plates'),paint=find_material('registered_teaching_columns'))
    def material(key,color):
        mat=bpy.data.materials.new(PREFIX+key);mat.diffuse_color=(*color,1);mat.use_nodes=True;shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=mat.diffuse_color;shader.inputs['Roughness'].default_value=.85;geometry.materials[key]=mat
    material('paving',(.61,.61,.56));material('planter',(.20,.22,.20));material('foliage',(.18,.30,.12))
    for level in range(3):geometry.prism('registered_podium_floor_roof_plates','slab',outline,level*STEP-.275,.27)
    geometry.prism('second_floor_terrace_paving','paving',outline,ROOF-.005,.075)
    perimeter=[]
    for edge in [2,3]:
        a,b=Vector(outline[edge]),Vector(outline[(edge+1)%4]);delta=b-a;length=delta.length;axis=delta.normalized();outward=Vector((axis.y,-axis.x))*(1 if signed>0 else -1);angle=math.atan2(axis.y,axis.x)
        def at(distance,z,inset=.11):
            point=a+axis*distance-outward*inset
            return(point.x,point.y,z)
        divisions=max(1,round(length/1.5));bays=max(1,round(length/6));width=length/divisions
        for floor in range(2):
            bottom,top=floor*STEP,(floor+1)*STEP
            for division in range(divisions):
                geometry.box('podium_external_glazing','glass',at((division+.5)*width,(bottom+top)/2),(width-.065,.035,STEP-.16),angle)
            for division in range(divisions+1):
                distance=min(length-.065,max(.065,division*width))
                geometry.box('podium_external_mullions','frame',at(distance,(bottom+top)/2),(.075,.12,STEP),angle)
            for z in [bottom+.08,top-.08]:geometry.box('podium_glazing_heads_sills','frame',at(length/2,z),(length-.08,.12,.16),angle)
            geometry.box('podium_structural_edge_beams','paint',at(length/2,bottom+.10,.28),(length-.12,.40,.22),angle)
        for bay in range(bays+1):
            distance=min(length-.28,max(.28,bay*length/bays))
            geometry.box('podium_structural_columns','paint',at(distance,ROOF/2,.32),(.40,.42,ROOF),angle)
        geometry.box('podium_roof_edge_beams','paint',at(length/2,ROOF-.14,.28),(length-.12,.40,.27),angle)
        geometry.box('podium_terrace_guard_glass','glass',at(length/2,ROOF+.63,.16),(length-.18,.035,1.03),angle)
        geometry.box('podium_terrace_guard_toprail','frame',at(length/2,ROOF+1.16,.16),(length-.18,.055,.065),angle)
        perimeter.append(dict(edge=edge,length=length,estimatedGlazingDivisions=divisions,estimatedStructuralBays=bays))
    # Bilinear strips follow the actual tapered terrace. RSHP028 supplies raised
    # planting strips and clear central circulation, not surveyed plant species.
    def garden_point(u,v):return B.lerp(A,u).lerp(C.lerp(D,u),v)
    garden_polygons=[]
    for v0,v1 in [(.08,.20),(.82,.95)]:
        for u0,u1 in [(.035,.24),(.27,.48),(.51,.72),(.75,.965)]:
            points=[tuple(garden_point(u,v))for u,v in [(u0,v0),(u1,v0),(u1,v1),(u0,v1)]]
            geometry.prism('terrace_raised_planter_masses','planter',points,ROOF+.07,.30)
            foliage=[tuple(garden_point(u,v))for u,v in [(u0+.008,v0+.015),(u1-.008,v0+.015),(u1-.008,v1-.015),(u0+.008,v1-.015)]]
            geometry.prism('terrace_planted_garden_masses','foliage',foliage,ROOF+.37,.38);garden_polygons.append(points)
    added=geometry.finish()
    for obj in added:
        for vertex in obj.data.vertices:vertex.co=world(vertex.co)
        obj.data.update();obj['destinationCollection']=('CBG_PUBLIC_INTERIOR_study' if any(family in obj.name for family in ['registered_podium_floor_roof_plates','podium_structural_edge_beams','podium_structural_columns','podium_roof_edge_beams']) else 'CBG_EXTERIOR');obj['candidateScope']='Southern2storeyamenitypodium; exact heights and facade modules estimated'
    # The podium converts the lower portion of the wing's rear facade into a
    # shared internal interface. Clip only those external skin/shade families.
    edge_axis=(A-B).normalized();normal=Vector((-edge_axis.y,edge_axis.x))
    strip=[tuple(B-edge_axis*.15-normal*1.12),tuple(A+edge_axis*.15-normal*1.12),tuple(A+edge_axis*.15+normal*1.12),tuple(B-edge_axis*.15+normal*1.12)]
    shared_planes=volume_planes(strip,-1+60,ROOF+.07+60)
    # Reject everything above the terrace first. Processing XY first also splits
    # unmodified upper facade islands and adds unnecessary internal seam faces.
    volumes=[[shared_planes[-1],shared_planes[-2]]+shared_planes[:-2]]
    replacements=[]
    for source in inputs:
        if not source.name.startswith('CBG204_TEACHING_'):continue
        if not any(t in source.name for t in ['teaching_glazing','teaching_mullions','teaching_transoms','solar_blade','solar_shade_head_sill']):continue
        def shifted_local(p):
            q=local(p);q.z+=60;return q
        def shifted_world(p):return world((p[0],p[1],p[2]-60))
        working=source.copy();working['originalObject']=source.get('originalObject',source.name)
        result=trim_object(working,shifted_local,shifted_world,volumes)
        bpy.data.objects.remove(working,do_unlink=True)
        if result:
            target,row=result;target.name=PREFIX+'shared_edge_retained_'+source.name;target['destinationCollection']=source.get('destinationCollection','CBG_EXTERIOR');collection.objects.link(target);added.append(target)
            row['source']=source.name;row['target']=target.name;replacements.append(row)
    assert all(object_fingerprint(o)==protected[o.name]for o in inputs)
    topology=[]
    for obj in added:
        bm=bmesh.new();bm.from_mesh(obj.data);bm.normal_update();islands=closed_islands(bm)
        assert all(closed and signed_volume(faces)>0 for faces,closed in islands),obj.name
        topology.append(dict(object=obj.name,closedOutwardComponents=len(islands)));bm.free()
    component=OUT/'cbg-podium205-component.blend';bpy.data.libraries.write(str(component),set(added),fake_user=True,compress=True)
    fingerprints={o.name:object_fingerprint(o)for o in added}
    remove=[row['source']for row in replacements]
    report=dict(status='private-bounded-podium-candidate-not-for-release',componentPath=str(component.relative_to(ROOT)),componentSha256=digest(component),inputComponentPath=str(SOURCE.relative_to(ROOT)),inputComponentSha256=digest(SOURCE),addedObjects=list(fingerprints),removeObjects=remove,replacements=replacements,inputHashes=hashes,
        podiumPolygon=outline,provisionalPolygon=provisional,sharedVertexCorrectionsMetres=[(Vector(a)-Vector(b)).length for a,b in zip(outline,provisional)],floorLevels=[0,STEP,ROOF],estimatedHeightMetres=ROOF,verifiedStoreys=2,
        heightEvidence=dict(architectSheet='data/documents/centre_building_rshp_current.pdf, PDFpage2 explicitly states2,6,13storeys',builtPhoto='data/collections/exteriors/images/cbg_rshp_028.jpg, RSHPcaptionRoofterraceonthesecondfloor',metresStatus='Estimated from neighbouring25m/sixlevel teaching wing; not measured'),
        gardenEvidence='RSHP028builtphoto: raised linear planted beds and central pavedterrace; plant species, detailedbedlengths and planternodes not surveyed',perimeter=perimeter,gardenPolygons=garden_polygons,topology=topology,
        contacts=dict(wingSharedEdge=[outline[0],outline[1]],towerSharedEdge=[outline[1],outline[2]],footprintAreaSquareMetres=area(outline),floorCoverageRatio=1.0,noNewExteriorOnSharedEdges=True,lowerSharedWingFacadeCutbackToRoof=True),
        limitations=['XYboundary reuses provisional2016architecttrace plus registeredGISedges; no surveyedasbuiltpodiumplan.', '8.333mheight,1.5mglazingdivision,6mstructuralbay and roofguarddimensions are presentation estimates.', 'Publicpodiumshelldefined withfloors,externalcurtainwall,structureandlandscapedroof; exactroompartitions/doors unverified.'])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(component),link=False)as(src,reopened):reopened.objects=list(fingerprints)
    added=list(reopened.objects);scene=bpy.context.scene
    for obj in added:scene.collection.objects.link(obj);assert object_fingerprint(obj)==fingerprints[obj.name]
    report['verification']=dict(componentReopened=True,allFingerprintsMatch=True,allShellsClosedOutward=True,inputHashesUnchanged=all(digest(ROOT/p)==h for p,h in hashes.items()),protectedSourceObjectsUnchanged=True)
    with bpy.data.libraries.load(str(SOURCE),link=False)as(src,context):context.objects=[name for name in source_audit['addedObjects']if name not in remove]
    for obj in context.objects:scene.collection.objects.link(obj)
    scene.world=bpy.data.worlds.new('CBG205_podium_world');scene.world.color=(.8,.82,.84);scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_cavity=True
    scene.render.resolution_x,scene.render.resolution_y=1500,1000;scene.render.resolution_percentage=100
    cam=bpy.data.objects.new('CBG205_podium_camera',bpy.data.cameras.new('CBG205_podium_camera'));scene.collection.objects.link(cam);scene.camera=cam;cam.data.type='ORTHO'
    for name,position,target,scale in [('podium',(54,64,34),(19,8,9),67),('whole',(65,80,67),(-3,2,23),107),('terrace',(47,40,33),(19,8,8),57)]:
        cam.location=world(position);cam.rotation_euler=(world(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale;scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
    review=OUT/'cbg-podium205-review.blend';bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(review));report['reviewPath']=str(review.relative_to(ROOT));report['reviewSha256']=digest(review)
    (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n');print('CBG205_PODIUM_REOPENED',len(added),len(replacements),flush=True)


if __name__=='__main__':build_candidate()
