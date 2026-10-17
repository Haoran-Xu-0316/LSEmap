"""Inspect registered CKK public atrium glazing and exterior display ownership.

Fixed v233 read-only diagnosis. Existing classrooms, source meshes and material
nodes are untouched. Candidate work, if justified by this evidence, is separate.
"""
from pathlib import Path
import json,hashlib,sys,math
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'result/blender/LSE_campus_detailed_v233.blend'
SHA='b1d01b4b74a7f9e33d9bab25e73f51f39361659b9236ca98c34056137d8b6660'
OUT=ROOT/'result/blender/ckk-glazing234'
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import update_scene
from audit_col_exterior234 import snapshot
CENTRE=Vector((-110.49102024587766,77.56014819690478,0))
U=Vector((math.cos(math.radians(22)),math.sin(math.radians(22)),0));N=Vector((-U.y,U.x,0))
def local(p):
 q=p-CENTRE;return[q.dot(U),q.dot(N),p.z]
def world(x,y,z):return CENTRE+U*x+N*y+Vector((0,0,z))
def save(name,value):(OUT/name).write_text(json.dumps(value,indent=2)+'\n')
def optics(mat):
 node=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)if mat.use_nodes else None
 return dict(name=mat.name,diffuse=list(mat.diffuse_color),alpha=node.inputs['Alpha'].default_value if node else None,transmission=node.inputs['Transmission Weight'].default_value if node else None,metallic=node.inputs['Metallic'].default_value if node else None,roughness=node.inputs['Roughness'].default_value if node else None,properties=dict(mat.items()))
def diagnose():
 assert hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA
 OUT.mkdir(parents=True,exist_ok=True);bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene();assert len(bpy.data.objects)==8529
 original=snapshot();material_ids={m.name:m.as_pointer()for m in bpy.data.materials};metadata=json.loads((ROOT/'web/tools/building-metadata.json').read_text());spaces={r['collection']:sorted(o.name for o in bpy.data.collections[r['collection']].all_objects)for r in metadata['spaces']};assert len(spaces)==34 and len({n for members in spaces.values()for n in members})==1433
 public=bpy.data.collections['CKK_PUBLIC_INTERIOR_study'];exterior=bpy.data.collections['CKK_EXTERIOR'];publicnames={o.name for o in public.all_objects};exteriornames={o.name for o in exterior.all_objects};rows=[];visible=[]
 for obj in public.all_objects:
  if obj.type!='MESH'or obj.hide_render:continue
  points=[obj.matrix_world@v.co for v in obj.data.vertices];pp=[local(p)for p in points];obj.data.calc_loop_triangles()
  row=dict(name=obj.name,worldBounds=[[min(p[i]for p in points),max(p[i]for p in points)]for i in range(3)],localBounds=[[min(p[i]for p in pp),max(p[i]for p in pp)]for i in range(3)],vertices=[list(p)for p in points],faces=[list(p.vertices)for p in obj.data.polygons],triangles=[list(t.vertices)for t in obj.data.loop_triangles],materials=[optics(m)for m in obj.data.materials if m],owners=[c.name for c in obj.users_collection],inExterior=obj.name in exteriornames,inCampus=obj.name in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects)
  rows.append(row);visible.append(obj)
 save('native-public-surfaces.json',dict(baselineSha256=SHA,objects=rows))
 candidates=[o for o in set(list(public.all_objects)+list(exterior.all_objects))if o.type=='MESH'and not o.hide_render]
 verts=[];faces=[];owners=[]
 for obj in candidates:
  offset=len(verts);verts.extend(obj.matrix_world@v.co for v in obj.data.vertices);faces.extend(tuple(offset+i for i in p.vertices)for p in obj.data.polygons);owners.extend([obj.name]*len(obj.data.polygons))
 tree=BVHTree.FromPolygons(verts,faces)
 def cast(origin,direction,length):
  hits=[];o=origin.copy();travelled=0
  for _ in range(64):
   hit=tree.ray_cast(o,direction,length-travelled)
   if hit[0]is None:break
   travelled+=(hit[0]-o).length;hits.append(dict(object=owners[hit[2]],distance=travelled,point=list(hit[0])));o=hit[0]+direction*.003;travelled+=.003
  return hits
 rays=[]
 for x in [-9.02,-1.02,6.98]:
  for y in [-9.02,-1.02,6.98]:rays.append(dict(kind='roof_outward',localStart=[x,y,12.5],hits=cast(world(x,y,12.5),Vector((0,0,1)),30)))
 for x in [-3.6,-1.2,1.2,3.6]:
  for z in [2.3,3.4,4.4]:rays.append(dict(kind='entrance_glass_and_backing',localStart=[x,13.65,z],hits=cast(world(x,13.65,z),N,5)))
 support=[]
 for x in [-3.6,-1.2,1.2,3.6]:
  for y in [13.6,13.8,14.2,15.0,16.0]:support.append(dict(localStart=[x,y,1.87],hits=cast(world(x,y,1.87),Vector((0,0,-1)),2.5)))
 save('entrance-floor-support.json',support)
 save('exterior-inventory.json',[dict(name=o.name,localBounds=[[min(local(o.matrix_world@v.co)[i]for v in o.data.vertices),max(local(o.matrix_world@v.co)[i]for v in o.data.vertices)]for i in range(3)],materials=[optics(m)for m in o.data.materials if m])for o in exterior.all_objects if o.type=='MESH'and not o.hide_render])
 save('native-diagnosis.json',dict(baselineSha256=SHA,objects=len(rows),visiblePublicObjectsInExterior=sum(r['inExterior']for r in rows),visiblePublicObjectsInCampus=sum(r['inCampus']for r in rows),publicCollectionScenes=[s.name for s in bpy.data.scenes if public.name in s.collection.children],glazing=[dict(name=r['name'],localBounds=r['localBounds'],materials=r['materials'])for r in rows if any(k in r['name']for k in ['glass','glaz'])],rays=rays,baselineBytesUnchanged=hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA))
 assert snapshot()==original
 assert {m.name:m.as_pointer()for m in bpy.data.materials}==material_ids
 assert {name:sorted(o.name for o in bpy.data.collections[name].all_objects)for name in spaces}==spaces
 save('native-preservation.json',dict(originalObjectsVerified=len(original),originalMaterialsUntouched=len(material_ids),protectedSpaces=len(spaces),protectedSpaceObjects=len({n for members in spaces.values()for n in members}),allGeometryUVBindingsTransformsModifiersPropertiesOwnersVisibilityUnchanged=True,baselineBytesUnchanged=hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA,noNativeOrComponentSaved=True))
 print('CKK234_DIAGNOSED',len(rows),sum(r['inExterior']for r in rows),sum(r['inCampus']for r in rows),flush=True)
def finalize_review():
 """Freeze the precise unresolved support issue; do not make an empty component."""
 diagnosis=json.loads((OUT/'native-diagnosis.json').read_text());support=json.loads((OUT/'entrance-floor-support.json').read_text());web=json.loads((OUT/'web-asset-diagnosis.json').read_text());preservation=json.loads((OUT/'native-preservation.json').read_text())
 roof=[r for r in diagnosis['rays']if r['kind']=='roof_outward'];doors=[r for r in diagnosis['rays']if r['kind']=='entrance_glass_and_backing']
 assert len(roof)==9 and all(len(r['hits'])==2 and all(h['object']=='CKK_individual_roof_glass_panels'for h in r['hits'])for r in roof)
 assert len(doors)==12 and all(any(h['object']=='CKK_rear_atrium_wall'for h in r['hits'])for r in doors)
 assert len(support)==20 and all(not r['hits']for r in support if r['localStart'][1]>=14.2)
 audit=dict(version=234,building='CKK',auditOnly=True,status='glazing-already-transparent-entrance-support-unresolved',baselinePath=str(BASE.relative_to(ROOT)),baselineSha256=SHA,targetCollection='CKK_PUBLIC_INTERIOR_study',componentProduced=False,componentPath=None,componentSha256=None,addedObjects=[],archivedObjects=[],changedObjects=[],verification=preservation,sourceManifest='data/collections/ckk-glazing234/sources.json',nativeDiagnostic='native-diagnosis.json',nativeSurfaceEvidence='native-public-surfaces.json',actualFloorSupport='entrance-floor-support.json',webAssetEvidence='web-asset-diagnosis.json',previews=['entrance-source-native-section.png'],sourceInterpretation=dict(photo='Grimshaw014 shows the central glazed doors, timber landing and hall beyond;009/022 show the glazed roof.',nativeCorrespondence='Original build_atria.py models four door centres at x=-3.6/-1.2/1.2/3.6m opposite the Sounding Board. The photographic composition corresponds, but no measured plan establishes the geographic route beyond the doors.',doorLocalBounds=dict(x=[-4.725,4.725],y=[13.685,13.715],z=[1.875,4.825]),backingLocalBounds=dict(x=[-15,15],y=[13.9,14.1],z=[0,14]),existingRaisedDeckTop=1.84,existingBoardTop=1.858,existingDeckEndY=13.7),findings=[dict(region='Public display ownership',finding='112 visible public meshes are in the campus. Export selection already includes the CKK public collection. Both detailed exterior and interior assets contain the209 timber structure and shared transparent glazing; no ownership correction is needed.'),dict(region='Roof glazing',finding='Native transmission=0.94, metallic=0; detailed web material uses BLEND with alpha=0.30. Nine actual skylight-centre rays hit only two glass surfaces and no opaque overlaid roof through42.5m height.'),dict(region='Entrance glazing',finding='Native transmission=0.94 and webOpacity=0.16; detailed web material uses BLEND with alpha=0.16. Twelve actual sightlines pass the door and duplicate rear glass but are blocked by the retained continuous rear wall.'),dict(region='Doorway support',finding='Four door lanes at y13.6m have boards at1.858m. At y13.8m only the0.23m ground slab remains. At y14.2/15/16m no existing floor triangle lies within a2.5m downward ray. A short threshold cannot connect to an existing landing beyond the wall.')],decision='Keep existing optics and ownership. Do not open the backing wall into an unsupported/unmodeled cavity; no invented room, office, backing or inner-street floor. A registered existing ground/entrance plan is needed before a bounded supported doorway repair.',limitations=['No enabled browser was available; production HTTP asset retrieval returned403. The catalogue-named local production GLBs match catalogue SHAs; live viewer acceptance is not claimed.','Historical2008 project photographs do not verify2026 condition.','Native atrium dimensions and street registration are inherited estimates. The photograph does not precisely locate the unmodeled2.5m background band.','No component was made; save/reappend validation and before/after improvement are not claimed.'])
 save('audit.json',audit)
 print('CKK234_UNRESOLVED_SUPPORT_AUDIT_READY',flush=True)

if __name__=='__main__':
 diagnose()
 finalize_review()
