"""Coordinate SAW's complete historic main circulation around the twin lifts.

Fixed authoring configuration for Blender's Text Editor. Source220 is read-only.
Historical drawing registration is retained. Every candidate is rejected before
native authoring because collision clearance does not establish the real route.
Run in Blender for read-only protection proof, then MachineLearning for source
comparison. Widths, interpolations and vertical dimensions remain estimates.
"""
from pathlib import Path
import hashlib,json,sys,math
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/saw-circulation221'
DATA=ROOT/'data/collections/saw-circulation221'
BASE=ROOT/'result/blender/LSE_campus_detailed_v220.blend'
SHA='974c47b4af06a6caa5f474c1c75e05ffb4084285cb1ef8a4ceb11bd93738f6c0'
LEVELS=[0.,3.45,8.1,11.1,14.1,18.,21.9]
COUNTS=[23,31,20,20,26,26]
ANCHORS=np.array([[-65.223399,-15.905616],[-84.252182,28.425],[-55.301,36.609104]])
# Centre stations trace the published stair zones. Full riser schedules are not
# recoverable from the diagram's drawing breaks, so retained counts are estimates.
ROUTES=[
 [(581,558),(615,512),(661,486)],
 [(740,488),(689,450),(634,490)],
 [(654,544),(733,539),(733,480),(633,505)],
 [(826,494),(750,448),(681,481)],
 [(726,528),(846,548),(809,492)],
 [(687,488),(787,472),(783,545),(697,532)],
]
WIDTHS=[1.55,1.25,1.15,1.20,1.15,1.10]

def write(name,value):
 OUT.mkdir(parents=True,exist_ok=True);(OUT/name).write_text(json.dumps(value,indent=2)+'\n')

def world(points):
 p=np.array(points);a,b,c=ANCHORS
 return a+(p[:,0:1]-145)/1200*(b-a)+(p[:,1:2]-400)/785*(c-b)

def plan_pixels(points):
 matrix=np.column_stack(((ANCHORS[1]-ANCHORS[0])/1200,(ANCHORS[2]-ANCHORS[1])/785))
 return (np.asarray(points)-ANCHORS[0])@np.linalg.inv(matrix).T+np.array([145,400])

def prepare():
 from shapely.geometry import Polygon
 from shapely.ops import unary_union
 from shapely.geometry.polygon import orient
 vectors=json.loads((ROOT/'result/blender/saw-floors216/vectors.json').read_text())
 registration=json.loads((ROOT/'result/blender/saw-floors216/registration.json').read_text())
 factor=1501/vectors['32']['pageSize'][0]
 cabins=[Polygon(world(np.array(next(c for c in vectors['32']['candidates']if c['index']==i)['pts'][:-1])*factor))for i in registration['32']['sourceControlCurveIndices']]
 lifts=unary_union(cabins);surfaces=[];routes=[]
 for flight,(points,count,width)in enumerate(zip(ROUTES,COUNTS,WIDTHS)):
  control=world(points)
  # One continuous rounded ribbon, with shared analytic edge stations. No
  # disconnected riser prisms or convex-hull patches are used at the turns.
  sampled=[control[0]]
  for n in range(1,len(control)-1):
   a,k,b=control[n-1:n+2];u=(k-a)/np.linalg.norm(k-a);v=(b-k)/np.linalg.norm(b-k)
   turn=math.atan2(u[0]*v[1]-u[1]*v[0],np.dot(u,v))
   limit=.85 if len(control)==3 else .48
   cut=min(2.,np.linalg.norm(k-a)*limit,np.linalg.norm(b-k)*limit)
   radius=cut/math.tan(abs(turn)/2)
   # Radius is retained only for this rejected diagnostic ribbon.
   before=k-u*cut;after=k+v*cut
   normal=np.array([-u[1],u[0]])*(1 if turn>0 else-1)
   center=before+normal*radius;radial=before-center
   sampled.append(before)
   for t in np.linspace(0,turn,41)[1:]:
    c,z=math.cos(t),math.sin(t);sampled.append(center+np.array([radial[0]*c-radial[1]*z,radial[0]*z+radial[1]*c]))
  sampled.append(control[-1]);samples=np.array(sampled)
  lengths=np.r_[0,np.cumsum(np.linalg.norm(np.diff(samples,axis=0),axis=1))]
  distances=np.linspace(0,lengths[-1],count+1)
  def sample_at(d):return np.array([np.interp(d,lengths,samples[:,axis])for axis in range(2)])
  centres=np.array([sample_at(d)for d in distances])
  tangent=np.array([sample_at(min(d+.005,lengths[-1]))-sample_at(max(d-.005,0))for d in distances]);tangent/=np.linalg.norm(tangent,axis=1)[:,None]
  normals=np.c_[-tangent[:,1],tangent[:,0]]
  sides=np.array([centres-normals*width/2,centres+normals*width/2]).transpose(1,0,2)
  for index in range(count):
   poly=Polygon([sides[index,0],sides[index,1],sides[index+1,1],sides[index+1,0]])
   if not poly.is_valid:print('INVALID',flight,index)
   rise=(LEVELS[flight+1]-LEVELS[flight])/count
   top=LEVELS[flight]+rise*(index+1)
   surfaces.append(dict(flight=flight,index=index,top=top,bottom=top-rise+.002,ring=list(orient(poly,sign=1).exterior.coords)[:-1]))
  routes.append(dict(flight=flight,width=width,length=lengths[-1],centres=centres.tolist(),sides=sides.tolist(),count=count,rise=rise))
 conflicts=[];lift_conflicts=[]
 for i,a in enumerate(surfaces):
  p=Polygon(a['ring']);overlap=p.intersection(lifts).area
  if overlap>1e-5:lift_conflicts.append(dict(tread=i,flight=a['flight'],area=overlap))
  for j,b in enumerate(surfaces[i+1:],i+1):
   if a['flight']==b['flight'] and abs(a['index']-b['index'])<=1:continue
   area=p.intersection(Polygon(b['ring'])).area
   if area<.001:continue
   low,high=sorted([a,b],key=lambda s:s['top']);gap=high['bottom']-low['top']
   if gap<2.1:conflicts.append(dict(a=i,b=j,flightA=a['flight'],flightB=b['flight'],indexA=a['index'],indexB=b['index'],area=area,gap=gap))
 report=dict(routes=routes,surfaces=surfaces,liftConflicts=lift_conflicts,stairConflicts=conflicts,liftPolygons=[list(p.exterior.coords)for p in cabins])
 write('feasibility.json',report)
 print('SAW221_FEASIBILITY',len(lift_conflicts),len(conflicts),[(x['flight'],round(x['length'],2),round(x['rise'],3))for x in routes])
 print(conflicts[:20])
 return report


def inspect_native():
 import bpy
 from mathutils import Vector
 sys.path.insert(0,str(ROOT/'web/tools'))
 from integrate_exterior_round194 import object_fingerprint,accepted_fingerprints,update_scene
 from refine_portsmouth_exterior207 import material_fingerprint
 assert hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
 accepted=accepted_fingerprints(ROOT/'result/blender/stage220',SHA)
 actual={obj.name:object_fingerprint(obj)for obj in bpy.data.objects}
 assert actual==accepted and len(actual)==7631
 materials={m.name:material_fingerprint(m)for m in bpy.data.materials}
 metadata=json.loads((ROOT/'web/tools/building-metadata.json').read_text())
 spaces={s['collection']:sorted(o.name for o in bpy.data.collections[s['collection']].all_objects)for s in metadata['spaces']}
 protected={name for names in spaces.values()for name in names};assert len(spaces)==19
 obj=bpy.data.objects['SAW173_registered_main_treads'];tops=[]
 for face in obj.data.polygons:
  points=np.array([list(obj.matrix_world@obj.data.vertices[i].co)for i in face.vertices])
  normal=(obj.matrix_world.to_3x3().inverted().transposed()@face.normal).normalized()
  if np.ptp(points[:,2])<1e-5 and normal.z>.99:
   tops.append(dict(height=float(points[:,2].mean()),ring=points[:,:2].tolist()))
 write('native-tread-tops.json',dict(baselineSha256=SHA,sourceObject=obj.name,faces=tops))
 assert actual=={obj.name:object_fingerprint(obj)for obj in bpy.data.objects}
 assert all(material_fingerprint(bpy.data.materials[name])==value for name,value in materials.items())
 assert all(sorted(o.name for o in bpy.data.collections[name].all_objects)==members for name,members in spaces.items())
 write('native-preservation.json',dict(baselineSha256=SHA,acceptedOriginalObjectsVerified=len(actual),originalMaterialsVerified=len(materials),protectedRoomCollections=len(spaces),protectedRoomObjects=len(protected),allOriginalFingerprintsUnchanged=True,allOriginalMaterialNodesUnchanged=True,originalGeometryUVTransformsAndBindingsVerified=True,originalModifiersNotMutated=True,originalObjectCollectionMembershipNotMutated=True,readOnlyNoObjectOrMaterialMutations=True,completeNativeNeverSaved=True,nativeBytesUnchanged=hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA))
 print('SAW221_READ_ONLY_NATIVE_VERIFIED',len(actual),len(materials),len(spaces),len(protected),len(tops),flush=True)


def source_review(report):
 from shapely.geometry import Polygon
 from shapely.ops import unary_union
 from PIL import Image,ImageDraw
 source=json.loads((ROOT/'result/blender/saw-circulation218/source-section-correspondence.json').read_text())
 spacings=[]
 for flight in source['flights']:
  for group in flight['sourceGroups']:
   for a,b in zip(group['sections'],group['sections'][1:]):
    left=np.array(a['worldEndpoints']);right=np.array(b['worldEndpoints']);direction=left[1]-left[0];direction/=np.linalg.norm(direction)
    other=right[1]-right[0];other/=np.linalg.norm(other)
    if abs(np.dot(direction,other))>.99:
     normal=np.array([-direction[1],direction[0]])
     spacings.append(abs(float(np.dot(right.mean(0)-left.mean(0),normal))))
 spacing=float(np.median(spacings))
 observations=[]
 for route in report['routes']:
  going=route['length']/route['count']
  observations.append(dict(flight=route['flight'],pathLengthMetres=route['length'],retainedEstimatedRiserCount=route['count'],estimatedRiseMetres=route['rise'],centrelineGoingMetres=going,publishedParallelLineMedianSpacingMetres=spacing,goingToPublishedSpacingRatio=going/spacing,accepted=False))
 native=json.loads((OUT/'native-tread-tops.json').read_text());by_height={}
 for face in native['faces']:by_height.setdefault(round(face['height'],5),[]).append(Polygon(face['ring']))
 cabins=unary_union([Polygon(ring)for ring in report['liftPolygons']]);conflicts=[]
 for height,rings in sorted(by_height.items()):
  overlap=unary_union(rings).intersection(cabins).area
  if overlap>.0001:conflicts.append(dict(top=height,overlapSquareMetres=overlap))
 assert len(by_height)==146 and len(conflicts)==38
 write('retained-native-conflicts.json',dict(baselineSha256=SHA,actualTreads=len(by_height),conflictingTreads=len(conflicts),summedTreadCabinOverlapM2=sum(c['overlapSquareMetres']for c in conflicts),conflicts=conflicts,scope='Actual220 source tread top polygons against the unchanged12-control registered2014 twin-cabin footprints. Conflict remains unresolved.'))
 contact=Image.new('RGB',(1800,1000),'white');draw=ImageDraw.Draw(contact)
 registration=json.loads((ROOT/'result/blender/saw-floors216/registration.json').read_text())
 vectors=json.loads((ROOT/'result/blender/saw-floors216/vectors.json').read_text())
 for flight,route in enumerate(report['routes']):
  page=32-flight;im=Image.open(ROOT/f'data/previews/saw_occupants_guide_2014_p{page}.png').convert('RGB')
  reg=registration[str(page)];factor=1501/vectors[str(page)]['pageSize'][0];inverse=np.linalg.inv(reg['matrix']);off=-np.asarray(reg['offset'])*factor@inverse
  im=im.transform(im.size,Image.Transform.AFFINE,(inverse[0,0],inverse[1,0],off[0],inverse[0,1],inverse[1,1],off[1]),Image.Resampling.BICUBIC)
  d=ImageDraw.Draw(im);points=plan_pixels(route['centres']);d.line([tuple(p)for p in points],fill='#c61925',width=4)
  for cabin in report['liftPolygons']:d.line([tuple(p)for p in plan_pixels(cabin+[cabin[0]])],fill='#005990',width=3)
  im=im.crop((480,410,960,700)).resize((580,350));x=(flight%3)*600;y=(flight//3)*500;contact.paste(im,(x,y+80))
  draw.text((x+12,y+10),f'{flight}->{flight+1}: REJECTED diagnostic route',fill='#a00000')
  draw.text((x+12,y+32),f'length {route['length']:.2f}m; going {route['length']/route['count']:.3f}m',fill='black')
  draw.text((x+12,y+52),'No geometry authored; source routing incomplete',fill='black')
 contact.save(OUT/'rejected-route-source-proof.png')
 preservation=json.loads((OUT/'native-preservation.json').read_text())
 sources=[]
 for path,publication,year in [(ROOT/'data/documents/saw_occupants_guide_2014.pdf','LSE occupants guide',2014),(ROOT/'data/collections/saw-circulation217/architectural-review-2014.pdf','Architectural Review March2014, architect-hosted PDF',2014),(DATA/'concrete-quarterly-summer2014.pdf','Concrete Quarterly Summer2014 issue248, printed p13',2014)]:
  sources.append(dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),publication=publication,publicationYear=year,photographDate='unknown',current2026ConditionEstablished=False))
 audit=dict(version=221,status='not_accepted_no_component',auditOnly=True,componentPath=None,componentSha256=None,baselinePath=str(BASE.relative_to(ROOT)),baselineSha256=SHA,addedObjects=[],archivedObjects=[],changedObjects=[],interiorCollection='SAW_PUBLIC_INTERIOR_study',replacesInteriorCollection=None,
  sourceProofs=['data/collections/saw-circulation221/guide-core-contact.png','data/collections/saw-circulation221/source-vector-core-proof.png','data/collections/saw-circulation221/ar4-section-dd.png','data/collections/saw-circulation221/cq13.png','result/blender/saw-circulation221/rejected-route-source-proof.png'],
  candidateRejected=True,candidateLiftConflicts=len(report['liftConflicts']),candidateStairConflicts=len(report['stairConflicts']),candidateRouteLengthAndGoing=observations,
  publishedParallelLineMedianSpacingMetres=spacing,currentNativeConflictCount=len(conflicts),retainedNativeConflictProof='retained-native-conflicts.json',verification=preservation,sources=sources,
  sourceFindings=['Guide stair line groups are incomplete at drawing breaks; selected endpoint spans cannot be treated as complete riser schedules or clear widths.',
   'The first two shortcut ribbons clear the cabins but have centreline goings materially shorter than the parallel published riser spacing. A collision-only pass would accept the wrong stair.',
   'Adjacent-floor diagrams contain multiple incoming/outgoing and projected stair portions. No unambiguous directional registration of all selected groups has been established.',
   'Architectural Review DD/BB/CC sections show local stair/core relations but do not cut every upper winder; the fourth/fifth inside corner remains unresolved.',
   'Concrete Quarterly contractor account and Dennis Gilbert built photo establish continuous in-situ flights, sloping soffits and cast edge walls, with pale terrazzo treads. They do not identify all floor transitions or their dimensions.'],
  decision='No component is accepted. Existing220 historic stair retains38 tread/cabin conflicts; no hidden removal or arbitrary rerouting is applied.',
  nextRequiredEvidence='A floor-numbered continuous walk-through or architect/contractor main-stair general arrangement identifying up/down runs, intermediate turns and landing datums; register it with the fixed twin lifts before rebuilding floors and shafts.',
  limitations=['All inherited geographic anchors and vertical datums remain estimates.','The rejected routes are diagnostic geometry, not measured alternatives or a compliance assessment.','No2026 complete fitout or current condition claim.','No source photograph is used as a public texture.'])
 write('audit.json',audit)
 # Retain compact numerical evidence, not a large expanded candidate mesh dump.
 write('feasibility.json',dict(status='rejected_before_native_authoring',surfacesAnalyzed=len(report['surfaces']),liftConflicts=report['liftConflicts'],stairConflicts=report['stairConflicts'],routeEvidence=observations,accepted=False))
 (OUT/'native-tread-tops.json').unlink(missing_ok=True)
 print('SAW221_REJECTED_WITH_EVIDENCE',len(conflicts),'native conflicts remain; no component')


if __name__=='__main__':
 try:import bpy
 except ModuleNotFoundError:source_review(prepare())
 else:inspect_native()
