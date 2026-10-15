"""Read-only audit of Marshall's built entrance controls and native door geometry.

The2022architect-authored ground plan and built photographs establish revolving
entrances. Native214has two flat north entrance leaves, but no accepted ground-
plan-to-native entrance registration. The existing coarse third-floor fit has a
2.852m independent diagonal residual, comparable to an entire door assembly.
Do not fabricate positioned door drums or change the public-hall perimeter.
This fixed workflow writes inspection evidence only, never a Blender component.
"""
from pathlib import Path
import hashlib
import json
import math

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'result/blender/LSE_campus_detailed_v214.blend'
BASE_SHA='58d38dabb75db4fed63d79e1e26ad46da5c7ba809567ab074c70329f9b4880a6'
OUT=ROOT/'result/blender/mar-entrances215'
PREFIX='MAR_ENTRY215'
ORIGIN=Vector((-8.696325894899289,49.33154396120258,0))
U=Vector((math.cos(math.radians(22)),math.sin(math.radians(22)),0))
N=Vector((-U.y,U.x,0))
EXTERIOR='MAR_EXTERIOR'
PUBLIC='MAR_PUBLIC_INTERIOR_study'
DOOR='MAR_EXTERIOR168_single_surface_entry_glass'
SOURCES=[
 {'url':'https://cdn.ca.emap.com/wp-content/uploads/sites/12/2022/04/grafton-architects-architectural-review.pdf',
  'path':'data/collections/mar-built-registration-2026/grafton-marshall-built-plans-2022.pdf',
  'basis':'Architect-authored built2022publication; page1 ground plan, not2017design.',
  'observation':'Two small circular door symbols at each diagonal-frontage transition, and one larger circle at the recessed third entrance: five circles across three entrance groups.'},
 {'url':'https://www.macegroup.com/en-us/projects/the-lese-marshall-building/',
  'basis':'Contractor project description, live rechecked2026-10-15.',
  'observation':'Three separate entrances provide access to the Great Hall.'},
 {'url':'https://www.soane.org/exhibitions/neighbours-space-and-time-grafton-architects-soane-museum',
  'basis':'Museum/Grafton exhibition account,2022; live rechecked2026-10-15.',
  'observation':'Great Hall environmental strategy explicitly includes revolving doors.'},
 {'url':'https://nickkane.co.uk/portfolio_page/marshall-building-lse-london-grafton-architects/',
  'path':'data/collections/architecture_round5/images/MAR/MAR_mar_kane_03.jpg',
  'basis':'Built north exterior photograph; exact capture date unknown.',
  'observation':'Visible curved revolving entrance enclosure beneath the recessed north facade. Photo is insufficient to establish metric drum centre, radius and accessible leaf placement.'},
]


def local(point):
    relative=point-ORIGIN
    return Vector((relative.dot(U),relative.dot(N),point.z))


def components(obj):
    bm=bmesh.new();bm.from_mesh(obj.data);bm.verts.ensure_lookup_table();seen=set();result=[]
    for seed in bm.verts:
        if seed.index in seen:continue
        pending=[seed];seen.add(seed.index);points=[]
        while pending:
            vertex=pending.pop();points.append(obj.matrix_world@vertex.co)
            for edge in vertex.link_edges:
                other=edge.other_vert(vertex)
                if other.index not in seen:seen.add(other.index);pending.append(other)
        result.append({'vertices':len(points),'center':list(sum(points,Vector())/len(points)),
                       'bounds':[[min(p[i] for p in points),max(p[i] for p in points)] for i in range(3)]})
    bm.free();return result


def native_inventory():
    rows=[]
    for obj in bpy.data.objects:
        if 'MAR' not in obj.name and not any('MAR' in c.name for c in obj.users_collection):continue
        if obj.type!='MESH' or obj.hide_render or not obj.data.vertices:continue
        points=[obj.matrix_world@v.co for v in obj.data.vertices]
        bounds=[[min(p[i] for p in points),max(p[i] for p in points)] for i in range(3)]
        if bounds[2][0]>7:continue
        row={'name':obj.name,'collections':[c.name for c in obj.users_collection],'bounds':bounds,
             'vertices':len(points),'faces':len(obj.data.polygons),'materials':[m.name if m else None for m in obj.data.materials]}
        if any(word in obj.name.lower() for word in ('entr','door','ground','glass','wall')):row['parts']=components(obj)
        rows.append(row)
    return {'baselineSha256':BASE_SHA,'collections':[c.name for c in bpy.data.collections if 'MAR' in c.name],'objects':rows}


def public_objects():
    return {o for name in (EXTERIOR,PUBLIC) for o in bpy.data.collections[name].all_objects if o.type=='MESH' and not o.hide_render and o.data.vertices}


def ray_tree(objects):
    points=[];polygons=[];owners=[];materials=[]
    for obj in objects:
        offset=len(points);points.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        for face in obj.data.polygons:
            polygons.append(tuple(offset+i for i in face.vertices));owners.append(obj.name)
            material=obj.data.materials[face.material_index] if len(obj.data.materials)>face.material_index else None
            materials.append(material.name if material else None)
    return BVHTree.FromPolygons(points,polygons,all_triangles=False),owners,materials


def entrance_rays(objects):
    tree,owners,materials=ray_tree(objects);rows=[]
    for part in components(bpy.data.objects[DOOR]):
        centre=Vector(part['center']);origin=centre+N*8;hits=[];travel=0.0
        for count in range(30):
            hit=tree.ray_cast(origin-N*travel,-N,12-travel)
            if hit[0] is None:break
            distance=travel+hit[3];point=hit[0]
            hits.append({'object':owners[hit[2]],'material':materials[hit[2]],'point':list(point),'nativeLocal':list(local(point)),
                         'distanceFromExternalStart':distance,'outwardDistanceFromDoor':(point-centre).dot(N)})
            travel=distance+.025
            if travel>12:break
        rows.append({'doorCentre':list(centre),'nativeLocalDoorCentre':list(local(centre)),
                     'externalStart':list(origin),'inwardDirection':list(-N),'hits':hits})
    return rows


def ground_cut(objects):
    segments=[];height=1.45
    for obj in objects:
        points=[obj.matrix_world@v.co for v in obj.data.vertices]
        for face in obj.data.polygons:
            vertices=[points[i] for i in face.vertices]
            if min(p.z for p in vertices)>=height or max(p.z for p in vertices)<=height:continue
            hits=[]
            for i,a in enumerate(vertices):
                b=vertices[(i+1)%len(vertices)]
                if (a.z-height)*(b.z-height)<0:
                    point=a+(b-a)*(height-a.z)/(b.z-a.z)
                    if all((point-old).length>1e-5 for old in hits):hits.append(point)
            if len(hits)!=2:continue
            segments.append({'object':obj.name,'points':[list(local(p)) for p in hits],
                             'glass':any(word in obj.name.lower() for word in ('glass','glazing')),'door':obj.name==DOOR})
    return {'height':height,'coordinateSystem':'Native local22degree basis; origin unchanged. Not registered to the source ground plan.',
            'origin':list(ORIGIN),'u':list(U),'n':list(N),'segments':segments}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    inventory=native_inventory();objects=public_objects();rays=entrance_rays(objects);cut=ground_cut(objects)
    assert len(components(bpy.data.objects[DOOR]))==2
    assert all(part['vertices']==4 for part in components(bpy.data.objects[DOOR]))
    assert len(bpy.data.objects[DOOR].data.polygons)==2
    registration=json.loads((ROOT/'result/blender/mar_built_plan_registration/registration.json').read_text())
    for source in SOURCES:
        if 'path' in source:source['sha256']=hashlib.sha256((ROOT/source['path']).read_bytes()).hexdigest()
    assert SOURCES[0]['sha256']=='d675da320087039168890f7afbf055490f9c8e4530f59921e9e5e53f6fc8bc47'
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA
    report={'version':215,'auditOnly':True,'baseline':str(BASE.relative_to(ROOT)),'baselineSha256':BASE_SHA,
            'componentPath':None,'componentSha256':None,'targetCollection':EXTERIOR,
            'addedObjects':[],'archivedObjects':[],'changedObjects':[],
            'actualNativeEntranceFinding':{'visibleEntryGlass':DOOR,'independentLeaves':2,'faces':2,'verticesPerLeaf':4,
                 'coordinatedVisibleFrames':['MAR_D5_entry_door_jamb','MAR_D5_entry_door_rail','MAR_D5_door_operator','MAR_D5_entry_pull_handle'],
                 'visibleRevolvingAssembliesFound':0,'reviewedCollections':[EXTERIOR,PUBLIC],
                 'inventoryIncludesIndependentMARCollections':True,'visibleLowLevelMeshObjectsReviewed':len(inventory['objects']),
                 'existingLeafApproachRaysUnobstructed':all(row['hits'] and row['hits'][0]['object']==DOOR and abs(row['hits'][0]['outwardDistanceFromDoor'])<1e-4 for row in rays),
                 'approachRayScope':'One native north-normal probe through each leaf centre; no separate wall/glass obstruction was hit before either leaf. This does not verify full accessible clearance.'},
            'sourceEntranceFinding':{'entranceGroups':3,'circularDoorSymbols':5,'groups':[2,2,1],
                 'revolvingDoorTypeCorroborated':True,'accessibleDoorPositionAndSwingVerified':False},
            'registrationGap':{'availableControl':'Third-floor outer outline only; no accepted ground-floor door-centre registration.',
                 'fitMaxResidualMetres':registration['fitMaxResidualMetres'],
                 'independentDiagonalMaxResidualMetres':registration['independentDiagonalMaxResidualMetres'],
                 'sourceAxisFinding':registration['axisFinding'],
                 'missing':['Ground-plan glazing-line corners tied to corresponding native ground-floor facets.',
                            'Five revolving drum centres/radii and adjacent accessible-leaf locations tied to those controls.',
                            'Coordinated mapping of recessed north forecourt, existing flat entry screen, and public-hall glass boundary.'],
                 'reasonForNoGeometryEdit':'A2.852m independent outline mismatch is comparable to a door drum. Existing flat screens cannot safely be replaced or displaced by copying plan circles without registering and opening the actual hall envelope.'},
            'originalGeometryPreserved':True,'originalUVPreserved':True,'originalMaterialNodesPreserved':True,
            'everyIndependentRoomPreserved':True,'publicExportRangeAndIndoorLightingPreserved':True,
            'nativeSourceUnchanged':True,'sourceRechecked':'2026-10-15','references':SOURCES,
            'evidence':{'nativeInventory':'inventory.json','entryRays':'entry-rays.json','nativeGroundCut':'native-ground-cut.json',
                        'nativeGroundCutPreview':'native-ground-cut.png','sourceGroundPlan':'ground-plan.png'},
            'nextConcretePrerequisite':'Establish accepted ground-plan entrance controls at all three transitions before editing wall/glass openings and revolving units.',
            'limitations':['Published built2022plans and photographs do not establish2026condition or measured current dimensions.',
                           'Absence of a visible revolving assembly is established for the reviewed native MAR exterior/public geometry; source symbol counts do not determine accessible door operation or leaf swing.',
                           'No model component, scene save, export, integration or deployment was performed.']}
    for name,data in [('inventory.json',inventory),('entry-rays.json',rays),('native-ground-cut.json',cut),('audit.json',report)]:
        (OUT/name).write_text(json.dumps(data,indent=2)+'\n')
    print('MAR_ENTRY215_AUDIT_ONLY_READY',len(inventory['objects']),len(cut['segments']),flush=True)


if __name__=='__main__':main()
