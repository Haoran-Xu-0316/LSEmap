"""Audit actual walking surfaces around Houghton, Clare Market and Portugal.

Fixed native paths. Accepted217 fingerprints are checked before reading surface
geometry. Existing source photographs and mapped boundaries remain authoritative.
"""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'result/blender/LSE_campus_detailed_v217.blend'
SHA='daac71eaf581c94e544fe7098e51f897273223a981bd8f1b4b637d56d4469423'
OUT=ROOT/'result/blender/street-environment218';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'web/tools'))
def save(name,value):(OUT/name).write_text(json.dumps(value,indent=2)+'\n')
def open_verified():
 import bpy
 from integrate_exterior_round194 import object_fingerprint,update_scene
 assert hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
 before=json.loads((ROOT/'result/blender/stage217/baseline-state.json').read_text())['fingerprints'];added=json.loads((ROOT/'result/blender/stage217/building-refinement.json').read_text())['addedFingerprints'];expected={**before,**added}
 differences=[dict(name=n,expected=f,actual=object_fingerprint(bpy.data.objects[n]))for n,f in expected.items()if object_fingerprint(bpy.data.objects[n])!=f]
 save('baseline-verification.json',dict(baselineSha256=SHA,acceptedObjectsVerified=len(expected),differences=differences));assert not differences,differences
 return bpy.context.scene

def inspect():
 import bpy
 from mathutils import Vector
 scene=open_verified();rows=[];furniture=[]
 for obj in scene.objects:
  if obj.type!='MESH'or obj.hide_render or obj.hide_get():continue
  if not obj.name.startswith(('SITE','GROUND','00_SITE','03_PUBLIC_REALM')):continue
  corners=[obj.matrix_world@Vector(p)for p in obj.bound_box]
  if min(p.x for p in corners)>105 or max(p.x for p in corners)<-85 or min(p.y for p in corners)>115 or max(p.y for p in corners)<-115:continue
  if min(p.z for p in corners)>.15 or max(p.z for p in corners)<.015:continue
  materials=[m.name if m else ''for m in obj.data.materials];points=[obj.matrix_world@v.co for v in obj.data.vertices];faces=[]
  if any(k in obj.name.lower()for k in ['furniture','bench','bin','bollard','planter']):furniture.append(dict(name=obj.name,materials=materials,bounds=[[min(p[i]for p in corners)for i in range(3)],[max(p[i]for p in corners)for i in range(3)]]))
  for face in obj.data.polygons:
   pp=[points[i]for i in face.vertices];z=pp[0].z
   if min(p.z for p in pp)<.015 or max(p.z for p in pp)>.15 or max(p.z for p in pp)-min(p.z for p in pp)>1e-5:continue
   if min(p.x for p in pp)>105 or max(p.x for p in pp)<-85 or min(p.y for p in pp)>115 or max(p.y for p in pp)<-115:continue
   material=materials[face.material_index]if materials else ''
   if not any(k in material.lower()for k in ['paving','asphalt','tarmac','slab','yorkstone','grout','edge']):continue
   signed=sum(a.x*b.y-b.x*a.y for a,b in zip(pp,pp[1:]+pp[:1]))/2
   if abs(signed)<1e-9:continue
   faces.append(dict(index=face.index,points=[list(p)for p in pp],material=material,area=abs(signed),signed=signed,z=z))
  if faces:rows.append(dict(name=obj.name,materials=materials,faces=faces))
 save('native-surfaces.json',dict(baselineSha256=SHA,objects=rows,furniture=furniture));print('SITE218_INSPECT',len(rows),sum(len(r['faces'])for r in rows),len(furniture),flush=True)

def review():
 from collections import defaultdict
 from shapely.geometry import Polygon,box,shape,mapping
 from shapely.ops import unary_union
 import gzip,math,struct
 source=OUT/'native-surfaces.json';native=json.loads(source.read_text());roi=box(-85,-115,105,115);groups=[]
 old=json.loads((ROOT/'result/blender/stage217/baseline-state.json').read_text())['fingerprints'];new=json.loads((ROOT/'result/blender/stage217/building-refinement.json').read_text())['addedFingerprints'];fingerprints={**old,**new}
 for row in native['objects']:
  byz=defaultdict(list)
  for face in row['faces']:
   if face['signed']>0:byz[round(face['z'],4)].append(face)
  for z,faces in byz.items():
   geometry=unary_union([Polygon([p[:2]for p in f['points']])for f in faces]).intersection(roi)
   if geometry.area>.0001:groups.append(dict(name=row['name'],z=z,geometry=geometry))
 heights=sorted(set(r['z']for r in groups));above={z:unary_union([r['geometry']for r in groups if r['z']>z+.0001])for z in heights};target='SITE216_At_grade_asphalt_underground_route_removed';pairs=[]
 for i,a in enumerate(groups):
  for b in groups[i+1:]:
   if abs(a['z']-b['z'])>.0001:continue
   intersection=a['geometry'].intersection(b['geometry'])
   if intersection.area<.01:continue
   visible=intersection.difference(above[a['z']])
   if visible.area<.01:continue
   pairs.append(dict(first=a['name'],second=b['name'],heightMetres=a['z'],rawAreaM2=intersection.area,coveredByHigherPavingAreaM2=intersection.area-visible.area,exposedCoplanarAreaM2=visible.area,rawGeometry=mapping(intersection),exposedGeometry=mapping(visible)))
 pairs.sort(key=lambda p:p['exposedCoplanarAreaM2'],reverse=True)
 conflicts=[r for r in pairs if target in (r['first'],r['second'])and any(n.startswith('GROUND199')for n in (r['first'],r['second']))]
 same=next(r for r in pairs if set((r['first'],r['second']))=={target,'SITE211_209_Mapped_asphalt_footways'})
 focus=unary_union([shape(r['rawGeometry'])for r in conflicts+[same]]);involved=set(n for p in conflicts+[same]for n in (p['first'],p['second']));records=[]
 for row in native['objects']:
  faces=[f for f in row['faces']if f['signed']>0 and(row['name']in involved or f['z']>.0241)and Polygon([p[:2]for p in f['points']]).intersects(focus)]
  if faces:records.append(dict(name=row['name'],sourceFingerprint=fingerprints[row['name']],materials=row['materials'],faces=faces))
 witness=dict(baselineSha256=SHA,sourceAcceptedFingerprints='result/blender/stage217/baseline-state.json plus building-refinement.json',objects=records,conflicts=conflicts,sameAsphalt=same)
 payload=json.dumps(witness,separators=(',',':')).encode();compressed=gzip.compress(payload,compresslevel=9,mtime=0);(OUT/'conflict-witness.json.gz').write_bytes(compressed)
 site=json.loads((ROOT/'result/blender/site_geometry.json').read_text());ids=['way/23613971','way/766878419','way/23613972','relation/19133691','way/352797305'];refs=[r for r in site['roads']if r['id']in ids]
 # Match the retained shallow native strip to its original mapped segment.
 assignments=[]
 for name in sorted(involved):
  if not name.startswith('GROUND199'):continue
  row=next(r for r in native['objects']if r['name']==name);footprint=unary_union([Polygon([p[:2]for p in f['points']])for f in row['faces']if f['signed']>0 and abs(f['z']-.024)<1e-5]);candidates=[]
  for route in site['roads']:
   if route['geometry']['type']!='LineString'or route['properties'].get('highway')!='pedestrian':continue
   for index,(a,b)in enumerate(zip(route['geometry']['coordinates'],route['geometry']['coordinates'][1:])):
    length=math.dist(a,b)
    if length<.1:continue
    u=[(b[i]-a[i])/length for i in range(2)];v=[-u[1],u[0]]
    poly=Polygon([(p[0]+sg*.025*u[0]+sd*3*v[0],p[1]+sg*.025*u[1]+sd*3*v[1])for p,sg,sd in[(a,-1,1),(b,1,1),(b,1,-1),(a,-1,-1)]])
    difference=footprint.symmetric_difference(poly).area
    candidates.append((difference,route,index))
  candidates.sort(key=lambda v:v[0]);error,route,index=candidates[0]
  assignments.append(dict(object=name,sourceWay=route['id'],sourceSegment=index,symmetricDifferenceM2=error,sourceProperties=route['properties'],matchVerified=error<.001))
  assert error<.001,(name,error)
 mapped=unary_union([shape(r['geometry'])for r in refs if r['geometry']['type']in ('Polygon','MultiPolygon')]);exposed=unary_union([shape(r['exposedGeometry'])for r in conflicts]);materials=json.loads((ROOT/'result/blender/stage217/source-material-state.json').read_text())['materials'];m1='Road asphalt.002';m2='SITE209_Mapped_asphalt_footways_Road asphalt.001';assert materials[m1]==materials[m2]
 report=dict(version=218,reviewOnly=True,baselineSha256=SHA,addedObjects=[],archivedObjects=[],changedObjects=[],componentPath=None,findings=conflicts,exposedPaleAsphaltUnionM2=exposed.area,overlapInsideMappedPedestrianAreasM2=exposed.intersection(mapped).area,overlapOutsideMappedPedestrianAreasM2=exposed.difference(mapped).area,sourceReferences=refs,paleStripSourceAssignments=assignments,asphaltOwner='Road_St Clement Lane.003',asphaltSourceWay='way/23613971',sameAsphaltOverlap=dict(areaM2=same['exposedCoplanarAreaM2'],materials=[m1,m2],identicalAcceptedMaterialNodeFingerprint=materials[m1],visualAssessment='Both source node fingerprints and original world-metric UV policy coincide; this overlap alone does not establish visible colour shimmer.'),decision='No geometry modification. Source-marked stone pedestrian strips and explicitly asphalt St Clement Lane share estimated native widths outside mapped pedestrian-area polygons. No surveyed kerb boundary identifies the correct material priority.',requiredEvidence='A georegistered current photograph or measured kerb/surface boundary at LSE Square/St Clement Lane/John Watkins junction around native(28,-19), sufficient to distinguish lane asphalt from adjoining pedestrian stone; do not infer from a wider nearby plaza photograph.',limitations=['All retained native road widths and ground levels are schematic estimates, not a curb or accessibility survey.','Higher horizontal paving is excluded from the coplanar estimate; this is a ground-surface audit, not a claim that roofs and foliage never occlude the view.','2026-09-12OSM archive and2021photographs published2022 do not establish October2026on-site conditions.','The existing49.52m2same-asphalt intersection remains; this round does not substitute deduplication for unproven visible improvement.'],sourcePhotoContext=['data/collections/streets/derived/review_public_realm_pdf_page23.png','data/collections/streets/derived/review_public_realm_pdf_page75.png'],sourcePhotoScope='General Clare Market and John Watkins stone-paved public-space context only; neither photo provides a registered measured kerb at this exact conflict.',witnessFile='result/blender/street-environment218/conflict-witness.json.gz',witnessSha256=hashlib.sha256(compressed).hexdigest(),witnessFaces=sum(len(r['faces'])for r in records),witnessCompressedBytes=len(compressed))
 # Keep the full official road spelling in the provenance statement.
 report['asphaltOwner']="Road_St Clement's Lane.003"
 report['asphaltOwningCollection']='00_SITE'
 report['asphaltCollectionProvenance']='Accepted216component targetCollection;217retains the original street object.'
 report['noNativeMutation']=True
 save('audit.json',report);print('SITE218_REVIEW',exposed.area,len(compressed),report['witnessFaces'],flush=True)

def verify_witness():
 import gzip
 from shapely.geometry import Polygon,shape
 from shapely.ops import unary_union
 a=json.loads((OUT/'audit.json').read_text());blob=(OUT/'conflict-witness.json.gz').read_bytes();assert hashlib.sha256(blob).hexdigest()==a['witnessSha256'];w=json.loads(gzip.decompress(blob));geometries={}
 for row in w['objects']:
  for height in set(round(f['z'],4)for f in row['faces']):geometries[(row['name'],height)]=unary_union([Polygon([p[:2]for p in f['points']])for f in row['faces']if abs(f['z']-height)<1e-5])
 checks=[]
 for p in w['conflicts']+[w['sameAsphalt']]:
  raw=geometries[(p['first'],p['heightMetres'])].intersection(geometries[(p['second'],p['heightMetres'])]);above=unary_union([g for(n,z),g in geometries.items()if z>p['heightMetres']+.0001]);exposed=raw.difference(above)
  # Witness triangles extend beyond the original audit ROI. The previously
  # saved raw intersection is an explicit spatial scope, not a new boundary.
  scoped=exposed.intersection(shape(p['rawGeometry']))
  error=scoped.symmetric_difference(shape(p['exposedGeometry'])).area
  assert error<1e-7,error
  checks.append(dict(first=p['first'],second=p['second'],recomputedExposedM2=scoped.area,symmetricDifferenceM2=error))
 save('witness-verification.json',dict(verified=True,baselineSha256=SHA,checks=checks));print('SITE218_WITNESS_VERIFIED',len(checks),flush=True)

if __name__=='__main__':
 try:import bpy
 except ImportError:
  if(OUT/'native-surfaces.json').exists():review()
  verify_witness()
 else:inspect()
